"""Regra de negócio de Preço (v1.1, Req 1).

A REGRA EM UMA FRASE
    O preço vale a partir do dia em que é definido e continua valendo até ser
    alterado, mesmo que o mês vire.

QUEM DECIDE "HOJE"
    O próprio serviço, pelo relógio injetado (padrão: ``hoje_sp``). A data de
    início nunca vem do cliente HTTP (Req 1.2): o navegador não escolhe a partir
    de quando um preço vale.

POR QUE A DATA DE REFERÊNCIA É A DO PEDIDO
    A resolução usa a **data do pedido**, nunca a data em que ele é digitado
    (Req 1.3). Um pedido do dia 5 lançado no dia 12, depois de uma alteração no
    dia 10, usa o preço antigo — é o que o cliente confere contra os pedidos.

ITEM SEM PREÇO
    Só quando o item não tem nenhum preço. Não existe valor zero implícito:
    cobrar zero por engano é pior que recusar a operação.

PEDIDO GRAVADO NÃO MUDA
    Nenhuma operação daqui toca ``lancamento_linhas``: o valor do pedido está
    congelado. ``impacto`` só conta quantos pedidos mantêm o valor anterior, para
    o operador ser avisado antes de confirmar (Req 1.6 e 1.13).
"""

import uuid
from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal
from typing import NoReturn

from sqlalchemy.exc import IntegrityError

from app.core.banco import nome_da_constraint_violada
from app.core.datas import hoje_sp
from app.core.erros import CodigoErro, ErroDeDominio, nao_encontrado
from app.dominio import ModoDeAlteracao, PrecoVigente, ResolucaoDePrecos
from app.models.item import Item
from app.models.preco import Preco
from app.repositories.protocolos import (
    RepositorioClienteProtocolo,
    RepositorioItemProtocolo,
    RepositorioPrecoProtocolo,
)

CONSTRAINT_UNICA_POR_DIA = "uq_precos_cliente_item_inicio"
CONSTRAINT_VALOR_POSITIVO = "ck_precos_valor_positivo"

# Duas casas: padrão monetário, sem fração de centavo
CASAS_DECIMAIS = 2


class ServicoPreco:
    def __init__(
        self,
        repositorio: RepositorioPrecoProtocolo,
        repositorio_cliente: RepositorioClienteProtocolo,
        repositorio_item: RepositorioItemProtocolo,
        *,
        hoje: Callable[[], date] = hoje_sp,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_cliente = repositorio_cliente
        self._repositorio_item = repositorio_item
        self._hoje = hoje

    # --- resolução --------------------------------------------------------

    def resolver(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        data_referencia: date,
    ) -> ResolucaoDePrecos:
        """Preço vigente de cada item na data do pedido."""
        vigentes = self._repositorio.resolver_vigentes(cliente_id, item_ids, data_referencia)

        # preserva a ordem pedida, útil para mensagem de erro previsível
        sem_preco = tuple(item_id for item_id in dict.fromkeys(item_ids) if item_id not in vigentes)
        return ResolucaoDePrecos(vigentes=vigentes, sem_preco=sem_preco)

    def listar_na_data(
        self, cliente_id: uuid.UUID, data: date, *, incluir_inativos: bool = False
    ) -> list[tuple[Item, PrecoVigente | None]]:
        """Itens do cliente com o preço vigente na data (``None`` = sem preço).

        Uma consulta de itens e uma de preços, qualquer que seja o tamanho do
        catálogo.
        """
        self._exigir_cliente(cliente_id)
        itens = self._repositorio_item.listar_por_cliente(
            cliente_id, incluir_inativos=incluir_inativos
        )
        vigentes = self._repositorio.resolver_vigentes(
            cliente_id, [item.id for item in itens], data
        )
        return [(item, vigentes.get(item.id)) for item in itens]

    def hoje(self) -> date:
        """O "hoje" do serviço (para a camada de transporte montar a resposta)."""
        return self._hoje()

    def preco_atual(self, item_id: uuid.UUID) -> PrecoVigente | None:
        """Preço que vale hoje para o item."""
        item = self._exigir_item(item_id)
        return self._repositorio.resolver_vigentes(item.cliente_id, [item.id], self._hoje()).get(
            item.id
        )

    # --- escrita ----------------------------------------------------------

    def mudar_a_partir_de_hoje(self, item_id: uuid.UUID, valor_unitario: Decimal) -> Preco:
        """Novo preço com início hoje (Req 1.2).

        Se já existe preço com início hoje, ele é ajustado em vez de duplicado:
        duas alterações no mesmo dia viram uma (Req 1.4). Também serve para o
        primeiro preço de um item.
        """
        item = self._exigir_item(item_id)
        valor = self._validar_valor(valor_unitario)
        hoje = self._hoje()

        existente = self._repositorio.obter_no_dia(item.cliente_id, item.id, hoje)
        try:
            if existente is not None:
                existente.valor_unitario = valor
                self._repositorio.sincronizar()
                return existente
            return self._repositorio.inserir(item.cliente_id, item.id, hoje, valor)
        except IntegrityError as erro:
            self._relancar_traduzido(erro)

    def corrigir_atual(self, item_id: uuid.UUID, valor_unitario: Decimal) -> Preco:
        """Troca o valor do preço vigente hoje, desde o dia em que foi definido.

        Para erro de digitação (Req 1.11 e 1.12). Não cria histórico. Pedidos já
        gravados não mudam; pedidos lançados depois, inclusive retroativos dentro
        do período desse preço, usam o valor corrigido (Req 1.13).
        """
        item = self._exigir_item(item_id)
        valor = self._validar_valor(valor_unitario)

        atual = self._repositorio.obter_vigente(item.cliente_id, item.id, self._hoje())
        if atual is None:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "Este item ainda não tem preço para corrigir. Defina o preço primeiro.",
                {"campos": ["modo"]},
            )
        try:
            atual.valor_unitario = valor
            self._repositorio.sincronizar()
        except IntegrityError as erro:
            self._relancar_traduzido(erro)
        return atual

    def alterar(self, item_id: uuid.UUID, valor_unitario: Decimal, modo: ModoDeAlteracao) -> Preco:
        """Despacha para a operação do modo escolhido pelo operador."""
        if modo is ModoDeAlteracao.CORRIGIR_ATUAL:
            return self.corrigir_atual(item_id, valor_unitario)
        return self.mudar_a_partir_de_hoje(item_id, valor_unitario)

    # --- aviso antes de confirmar ------------------------------------------

    def impacto(self, item_id: uuid.UUID, valor_unitario: Decimal, modo: ModoDeAlteracao) -> int:
        """Quantos pedidos já gravados continuam com valor diferente do novo.

        Intervalo afetado pela alteração:

        - ``A_PARTIR_DE_HOJE``: de hoje até o próximo início posterior (se houver);
        - ``CORRIGIR_ATUAL``: do início do preço atual até o próximo início. Se o
          atual é o primeiro preço do item, sem limite inferior, porque o
          primeiro preço vale também para datas anteriores.

        Item sem preço: nada a manter, zero.
        """
        item = self._exigir_item(item_id)
        cliente_id = item.cliente_id
        valor = self._validar_valor(valor_unitario)
        hoje = self._hoje()
        inicios = self._repositorio.inicios(cliente_id, item.id)
        if not inicios:
            return 0

        if modo is ModoDeAlteracao.CORRIGIR_ATUAL:
            atual = self._repositorio.obter_vigente(cliente_id, item.id, hoje)
            if atual is None:
                return 0
            inicio_atual = atual.vigencia_inicio
            desde = None if inicio_atual == inicios[0] else inicio_atual
            referencia = inicio_atual
        else:
            desde = hoje
            referencia = hoje

        ate = next((inicio for inicio in inicios if inicio > referencia), None)
        return self._repositorio.contar_pedidos_afetados(
            cliente_id, item.id, desde=desde, ate_exclusivo=ate, valor_diferente_de=valor
        )

    # --- validação --------------------------------------------------------

    def validar_valor(self, valor: Decimal) -> Decimal:
        """Valida sem gravar: permite checar o preço antes de criar o item."""
        return self._validar_valor(valor)

    @staticmethod
    def _validar_valor(valor: Decimal) -> Decimal:
        """Exige valor positivo com no máximo duas casas decimais."""
        if valor <= 0:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "O preço deve ser maior que zero.",
                {"campos": ["valor_unitario"]},
            )

        expoente = valor.as_tuple().exponent
        if isinstance(expoente, int) and expoente < -CASAS_DECIMAIS:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "O preço deve ter no máximo duas casas decimais.",
                {"campos": ["valor_unitario"]},
            )

        # normaliza para duas casas, para que 4.5 e 4.50 sejam o mesmo valor
        return valor.quantize(Decimal("0.01"))

    def _exigir_cliente(self, cliente_id: uuid.UUID) -> None:
        if self._repositorio_cliente.obter_por_id(cliente_id) is None:
            raise nao_encontrado("Cliente")

    def _exigir_item(self, item_id: uuid.UUID) -> Item:
        """Item existente. O cliente do preço é sempre o do item.

        Derivar o cliente do item (em vez de recebê-lo) elimina por construção o
        caso "preço de um cliente apontando para item de outro"; a FK composta
        no banco continua como garantia final.
        """
        item = self._repositorio_item.obter_por_id(item_id)
        if item is None:
            raise nao_encontrado("Item")
        return item

    @staticmethod
    def _relancar_traduzido(erro: IntegrityError) -> NoReturn:
        constraint = nome_da_constraint_violada(erro)
        if constraint == CONSTRAINT_VALOR_POSITIVO:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "O preço deve ser maior que zero.",
                {"campos": ["valor_unitario"]},
            ) from erro
        if constraint == CONSTRAINT_UNICA_POR_DIA:
            # duas gravações simultâneas no mesmo dia: a outra venceu
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "O preço deste item acabou de ser alterado. Atualize a tela e tente de novo.",
            ) from erro
        raise erro
