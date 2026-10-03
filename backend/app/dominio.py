"""Objetos de valor do domínio.

Estruturas simples, sem ORM e sem I/O, trocadas entre repositório e serviço
quando uma entidade não é a resposta certa. Ficam separadas dos modelos porque
não representam linha de tabela, e separadas dos schemas porque não são contrato
de API.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class PrecoVigente:
    """Preço aplicável a um item numa data.

    ``desde`` é o dia de início do preço aplicado. Pode ser anterior à data
    consultada (o preço vale até a próxima alteração) ou posterior a ela, quando
    o item só tem preços que começam depois: o primeiro preço vale também para
    datas anteriores (v1.1, Req 1.7).
    """

    item_id: uuid.UUID
    valor_unitario: Decimal
    desde: date


class ModoDeAlteracao(StrEnum):
    """Como uma alteração de preço é aplicada (v1.1, Req 1.11).

    ``A_PARTIR_DE_HOJE``: cria (ou ajusta) o preço com início hoje; pedidos de
    datas anteriores continuam com o preço antigo.

    ``CORRIGIR_ATUAL``: troca o valor do preço vigente hoje desde o dia em que
    ele foi definido, sem criar histórico. Serve para erro de digitação.

    Em nenhum dos dois um pedido já gravado muda: o valor dele está congelado.
    """

    A_PARTIR_DE_HOJE = "a_partir_de_hoje"
    CORRIGIR_ATUAL = "corrigir_atual"


@dataclass(frozen=True, slots=True)
class ResolucaoDePrecos:
    """Resultado de resolver preços para um conjunto de itens.

    Separa explicitamente o que foi resolvido do que **não tem preço**. Quem
    consome decide o que fazer com a ausência: o lançamento recusa (Req 5.14), a
    prévia de totais apenas informa.
    """

    vigentes: dict[uuid.UUID, PrecoVigente]
    sem_preco: tuple[uuid.UUID, ...]

    @property
    def completa(self) -> bool:
        return not self.sem_preco


@dataclass(frozen=True, slots=True)
class LinhaSolicitada:
    """Uma linha como o operador a informa: item e quantidade.

    Nunca traz valor. O preço é resolvido e congelado pelo servidor — aceitar
    valor do cliente seria permitir que o navegador definisse quanto custa.
    """

    item_id: uuid.UUID
    quantidade: int


@dataclass(frozen=True, slots=True)
class LinhaCalculada:
    """Uma linha com o valor já congelado e o total.

    ``valor_unitario`` é o preço vigente na data do pedido, capturado no momento
    do cálculo. Uma vez gravado, não é recalculado (Req 6.1 a 6.3).
    """

    item_id: uuid.UUID
    quantidade: int
    valor_unitario: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class CalculoDeLancamento:
    """Resultado do cálculo, compartilhado por criar, editar e prévia.

    Existe uma só implementação de cálculo no sistema. Se houvesse duas, uma
    divergiria — e a divergência apareceria como fatura errada.

    ``itens_sem_preco`` é devolvido em vez de levantar erro aqui: quem chama
    decide. A criação recusa (Req 5.14); a prévia apenas informa, para não ser
    hostil no meio da digitação.
    """

    linhas: tuple[LinhaCalculada, ...]
    total_pecas: int
    total_valor: Decimal
    itens_sem_preco: tuple[uuid.UUID, ...]

    @property
    def completo(self) -> bool:
        return not self.itens_sem_preco


# ---------------------------------------------------------------------------
# Relatório de fechamento (Req 7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LinhaDeFechamento:
    """Uma linha de lançamento como o banco a devolve para o relatório.

    Estrutura achatada, um registro por (lançamento, item): é o formato natural
    do ``join`` da consulta única do relatório. O serviço agrupa por lançamento.

    ``total`` vem da coluna gerada do banco, não de multiplicação em Python — é o
    mesmo valor que a linha do lançamento sempre teve.
    """

    lancamento_id: uuid.UUID
    data: date
    comanda: str | None
    item_id: uuid.UUID
    item_nome: str
    quantidade: int
    valor_unitario_congelado: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class ColunaDeItem:
    """Uma coluna de tipo de item no relatório.

    Só existe coluna para item com **ocorrência no período** (Req 7.7). Item do
    catálogo que ninguém pediu naquele intervalo não vira coluna vazia.
    """

    item_id: uuid.UUID
    nome: str


@dataclass(frozen=True, slots=True)
class LinhaDoRelatorio:
    """Uma linha do fechamento: um lançamento, com quantidade por item.

    ``quantidades`` é **mapa** de ``item_id``, não lista posicional. Item ausente
    no mapa significa célula vazia (Req 7.8), sem precisar enviar zeros e sem
    risco de desalinhar valores e colunas.
    """

    lancamento_id: uuid.UUID
    data: date
    comanda: str | None
    quantidades: dict[uuid.UUID, int]
    total_pecas: int
    total_valor: Decimal


@dataclass(frozen=True, slots=True)
class TotaisDoRelatorio:
    """Rodapé da tabela: total por item e totais do período (Req 7.11)."""

    por_item: dict[uuid.UUID, int]
    total_pecas: int
    total_valor: Decimal


@dataclass(frozen=True, slots=True)
class ResumoDoRelatorio:
    """Cartões do topo da tela.

    Derivado de ``TotaisDoRelatorio``, nunca recalculado a partir das linhas. É a
    correção estrutural do defeito B1 do protótipo, em que os cartões e o rodapé
    da tabela exibiam totais diferentes.

    ``media_diaria_pecas`` é métrica operacional de exibição: é a única divisão do
    sistema e **não participa de valor cobrado**. Arredondada para inteiro.
    """

    total_pecas: int
    total_valor: Decimal
    quantidade_lancamentos: int
    media_diaria_pecas: int


@dataclass(frozen=True, slots=True)
class LinhaResumoItem:
    """Um item a um valor por peça, somado no período (v1.1, Req 5.2 e 6.4).

    Uma linha por (item, valor congelado): se o preço mudou dentro do período, o
    mesmo item aparece em duas linhas, uma para cada valor (Req 5.4). Nada é
    reaplicado — ``subtotal`` é a soma dos totais das linhas de pedido.

    É o que permite ao cliente conferir preço × quantidade no documento.
    """

    item_id: uuid.UUID
    item_nome: str
    valor_unitario: Decimal
    quantidade: int
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class Relatorio:
    """Fechamento de um período para um cliente.

    Estrutura única consumida por tela, PDF e Excel. Os módulos de exportação
    **não recalculam nada** — se recalculassem, o documento enviado ao cliente
    poderia divergir do que o operador viu.
    """

    cliente_id: uuid.UUID
    cliente_nome: str
    inicio: date
    fim: date
    colunas_itens: tuple[ColunaDeItem, ...]
    linhas: tuple[LinhaDoRelatorio, ...]
    totais: TotaisDoRelatorio
    resumo: ResumoDoRelatorio
    # v1.1: derivado das mesmas linhas, sem consulta nova
    resumo_por_item: tuple[LinhaResumoItem, ...] = ()

    @property
    def vazio(self) -> bool:
        """Período sem nenhum lançamento (Req 7.13)."""
        return not self.linhas


# ---------------------------------------------------------------------------
# Relatório geral — todos os clientes (v1.1, Req 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LinhaDoResumoGeral:
    """Uma linha da consulta agrupada: (cliente, item, valor) somados no período."""

    cliente_id: uuid.UUID
    cliente_nome: str
    item_id: uuid.UUID
    item_nome: str
    valor_unitario: Decimal
    quantidade: int
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class SecaoDoCliente:
    """Um cliente no relatório geral: itens a cada valor e os totais dele."""

    cliente_id: uuid.UUID
    cliente_nome: str
    linhas: tuple[LinhaResumoItem, ...]
    total_pecas: int
    total_valor: Decimal


@dataclass(frozen=True, slots=True)
class RelatorioGeral:
    """Todos os clientes com pedido no período, e o total geral.

    Mesmo princípio do relatório por cliente: estrutura única para tela, PDF e
    Excel, e o total geral é a soma dos totais das seções já montadas.
    """

    inicio: date
    fim: date
    secoes: tuple[SecaoDoCliente, ...]
    total_pecas: int
    total_valor: Decimal

    @property
    def vazio(self) -> bool:
        return not self.secoes
