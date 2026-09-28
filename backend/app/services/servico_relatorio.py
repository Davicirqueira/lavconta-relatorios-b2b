"""Regra de negócio do relatório de fechamento (Req 7).

UMA AGREGAÇÃO, DOIS CONSUMIDORES
    Os cartões do topo da tela leem ``resumo``; o rodapé da tabela lê ``totais``.
    Os dois saem da **mesma** passagem pelos dados: ``resumo`` é construído a
    partir do objeto ``totais`` já pronto, não de uma segunda soma.

    Isso torna estruturalmente impossível divergirem. É a correção do defeito B1
    do protótipo, em que o cartão e o rodapé mostravam valores diferentes no mesmo
    fechamento — num documento que o cliente usa para auditar a fatura, dois
    totais diferentes na mesma tela destroem a confiança.

O RELATÓRIO NÃO REAPLICA PREÇO
    Cada linha entra com o valor que foi **congelado** na criação do lançamento
    (Req 7.12). Um período de 15/08 a 15/09 soma lançamentos de dois meses, cada
    um com o preço do seu mês. O serviço nunca consulta a tabela de preços — nem
    precisa saber que ela existe.
"""

import unicodedata
import uuid
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.erros import nao_encontrado, periodo_invalido
from app.dominio import (
    ColunaDeItem,
    LinhaDeFechamento,
    LinhaDoRelatorio,
    Relatorio,
    ResumoDoRelatorio,
    TotaisDoRelatorio,
)
from app.repositories.protocolos import (
    RepositorioClienteProtocolo,
    RepositorioFechamentoProtocolo,
)

ZERO = Decimal("0.00")


def _chave_alfabetica(nome: str) -> tuple[str, str]:
    """Chave de ordenação alfabética previsível para nome de item.

    Ignora acento e caixa, para que "Roupão" fique entre "Lençol" e "Toalha" em
    vez de depois de "Z" — que é onde uma ordenação por ponto de código o
    colocaria.

    Ordenar em Python, e não no ``ORDER BY``, é deliberado: a ordem passa a não
    depender da collation do servidor de banco, então o mesmo fechamento sai igual
    no Postgres local e no gerenciado.

    O nome original entra como critério de desempate, para o resultado ser total
    mesmo entre nomes que normalizam igual ("Toalha" e "toalha").
    """
    decomposto = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(letra for letra in decomposto if not unicodedata.combining(letra))
    return (sem_acento.casefold(), nome.casefold())


def _media_inteira(total: int, divisor: int) -> int:
    """Média arredondada para inteiro; zero quando não há divisor.

    Única divisão do sistema. É métrica de exibição e não participa de valor
    cobrado, por isso pode arredondar sem consequência contábil.
    """
    if divisor == 0:
        return 0
    return int((Decimal(total) / Decimal(divisor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class _Acumulador:
    """Estado parcial de um lançamento durante a agregação."""

    __slots__ = ("comanda", "data", "quantidades", "total_pecas", "total_valor")

    def __init__(self, data: date, comanda: str | None) -> None:
        self.data = data
        self.comanda = comanda
        self.quantidades: dict[uuid.UUID, int] = {}
        self.total_pecas = 0
        self.total_valor = ZERO

    def somar(self, registro: LinhaDeFechamento) -> None:
        # o mesmo item não repete no mesmo lançamento (constraint), mas somar em
        # vez de sobrescrever mantém o total correto caso a regra mude
        self.quantidades[registro.item_id] = (
            self.quantidades.get(registro.item_id, 0) + registro.quantidade
        )
        self.total_pecas += registro.quantidade
        self.total_valor += registro.total


class ServicoRelatorio:
    def __init__(
        self,
        repositorio: RepositorioFechamentoProtocolo,
        repositorio_cliente: RepositorioClienteProtocolo,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_cliente = repositorio_cliente

    def gerar(self, cliente_id: uuid.UUID, inicio: date, fim: date) -> Relatorio:
        """Monta o fechamento de um cliente num período.

        O relatório é sempre de **um** cliente (Req 7.2): misturar clientes num
        mesmo fechamento não corresponde a nada no negócio, já que a cobrança é
        individual e a tabela de preços também.

        Raises:
            ErroDeDominio: ``NAO_ENCONTRADO`` para cliente inexistente,
                ``PERIODO_INVALIDO`` quando a data inicial é posterior à final.
        """
        cliente = self._repositorio_cliente.obter_por_id(cliente_id)
        if cliente is None:
            raise nao_encontrado("Cliente")

        if inicio > fim:
            raise periodo_invalido()

        registros = self._repositorio.buscar_linhas_do_periodo(cliente_id, inicio, fim)

        colunas = self._montar_colunas(registros)
        linhas = self._montar_linhas(registros)
        totais = self._agregar(linhas, registros)

        return Relatorio(
            cliente_id=cliente.id,
            cliente_nome=cliente.nome,
            inicio=inicio,
            fim=fim,
            colunas_itens=colunas,
            linhas=linhas,
            totais=totais,
            # derivado do objeto de totais já pronto: não há segunda soma
            resumo=ResumoDoRelatorio(
                total_pecas=totais.total_pecas,
                total_valor=totais.total_valor,
                quantidade_lancamentos=len(linhas),
                media_diaria_pecas=_media_inteira(totais.total_pecas, len(linhas)),
            ),
        )

    # ------------------------------------------------------------------
    # Agregação
    # ------------------------------------------------------------------

    @staticmethod
    def _montar_colunas(registros: Iterable[LinhaDeFechamento]) -> tuple[ColunaDeItem, ...]:
        """Colunas apenas dos itens com ocorrência no período (Req 7.7).

        Item do catálogo que ninguém pediu no intervalo não gera coluna. Num
        fechamento que o cliente confere linha por linha, coluna inteira de zeros
        é ruído que atrapalha a auditoria.
        """
        nomes: dict[uuid.UUID, str] = {}
        for registro in registros:
            nomes.setdefault(registro.item_id, registro.item_nome)

        return tuple(
            ColunaDeItem(item_id=item_id, nome=nome)
            for item_id, nome in sorted(nomes.items(), key=lambda par: _chave_alfabetica(par[1]))
        )

    @staticmethod
    def _montar_linhas(
        registros: Iterable[LinhaDeFechamento],
    ) -> tuple[LinhaDoRelatorio, ...]:
        """Uma linha por lançamento, ordenada por data crescente (Req 7.9).

        Lançamento sem comanda mantém exatamente a mesma estrutura, com o campo
        nulo (Req 7.10): o campo não deixa de existir, só fica sem valor.
        """
        acumuladores: dict[uuid.UUID, _Acumulador] = {}
        for registro in registros:
            acumulador = acumuladores.get(registro.lancamento_id)
            if acumulador is None:
                acumulador = _Acumulador(registro.data, registro.comanda)
                acumuladores[registro.lancamento_id] = acumulador
            acumulador.somar(registro)

        linhas = [
            LinhaDoRelatorio(
                lancamento_id=lancamento_id,
                data=acumulador.data,
                comanda=acumulador.comanda,
                quantidades=dict(acumulador.quantidades),
                total_pecas=acumulador.total_pecas,
                total_valor=acumulador.total_valor,
            )
            for lancamento_id, acumulador in acumuladores.items()
        ]
        # ordenação explícita: não depende de o repositório ter ordenado. A ordem
        # de encontro desempata (sort estável), o que basta porque um cliente tem
        # no máximo um lançamento por data.
        return tuple(sorted(linhas, key=lambda linha: linha.data))

    @staticmethod
    def _agregar(
        linhas: Sequence[LinhaDoRelatorio],
        registros: Iterable[LinhaDeFechamento],
    ) -> TotaisDoRelatorio:
        """Totais do período: por item, de peças e em R$ (Req 7.11).

        Os totais de peças e em R$ saem da soma das **linhas já montadas**, não de
        um segundo laço sobre os registros brutos. Assim o rodapé é aritmeticamente
        a soma do que a tabela exibe — se a tabela estiver certa, o rodapé está.
        """
        por_item: dict[uuid.UUID, int] = {}
        for registro in registros:
            por_item[registro.item_id] = por_item.get(registro.item_id, 0) + registro.quantidade

        return TotaisDoRelatorio(
            por_item=por_item,
            total_pecas=sum(linha.total_pecas for linha in linhas),
            total_valor=sum((linha.total_valor for linha in linhas), ZERO),
        )
