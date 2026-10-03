"""Acesso a dados de Preço, incluindo a resolução do preço vigente.

A resolução é a consulta central do produto: dela sai o valor que será congelado
no pedido e, por consequência, cobrado do cliente.

REGRA DE RESOLUÇÃO (v1.1, design §1.2)
    Para um item, na data ``d`` do pedido:

    1. o preço com a maior ``vigencia_inicio`` menor ou igual a ``d``;
    2. se não houver, o preço com a **menor** ``vigencia_inicio`` — o primeiro
       preço vale também para datas anteriores (não há preço anterior a
       preservar, Req 1.7);
    3. se o item não tiver nenhum preço: sem preço.

    A regra vive só aqui (e no repositório falso dos testes, que a espelha).
"""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.dominio import PrecoVigente
from app.models.lancamento import Lancamento, LancamentoLinha
from app.models.preco import Preco


def _ordem_de_resolucao(data: date) -> tuple:
    """Ordenação que põe, para cada item, o preço certo em primeiro.

    - ``vigente DESC``: preços com início até a data vêm antes;
    - entre eles, o de início mais recente (``CASE`` é nulo para os não
      vigentes; ``NULLS LAST`` é necessário porque no Postgres nulo vem
      primeiro em ordem decrescente);
    - se nenhum for vigente, o de início mais antigo (o primeiro preço).
    """
    vigente = Preco.vigencia_inicio <= data
    return (
        vigente.desc(),
        case((vigente, Preco.vigencia_inicio)).desc().nulls_last(),
        Preco.vigencia_inicio.asc(),
    )


class RepositorioPreco:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # --- resolução --------------------------------------------------------

    def resolver_vigentes(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        data: date,
    ) -> dict[uuid.UUID, PrecoVigente]:
        """Preço vigente de cada item na data informada (regra no topo do módulo).

        Uma consulta para todos os itens (``DISTINCT ON``), sem N+1. Item ausente
        no retorno não tem nenhum preço.
        """
        if not item_ids:
            return {}

        consulta = (
            select(Preco.item_id, Preco.valor_unitario, Preco.vigencia_inicio)
            .where(Preco.cliente_id == cliente_id, Preco.item_id.in_(item_ids))
            .distinct(Preco.item_id)
            .order_by(Preco.item_id, *_ordem_de_resolucao(data))
        )
        return {
            linha.item_id: PrecoVigente(
                item_id=linha.item_id,
                valor_unitario=linha.valor_unitario,
                desde=linha.vigencia_inicio,
            )
            for linha in self._sessao.execute(consulta)
        }

    def obter_vigente(self, cliente_id: uuid.UUID, item_id: uuid.UUID, data: date) -> Preco | None:
        """O registro de preço que a resolução escolheria para a data (para alterar)."""
        consulta: Select = (
            select(Preco)
            .where(Preco.cliente_id == cliente_id, Preco.item_id == item_id)
            .order_by(*_ordem_de_resolucao(data))
            .limit(1)
        )
        return self._sessao.scalars(consulta).first()

    # --- leitura ----------------------------------------------------------

    def obter_no_dia(self, cliente_id: uuid.UUID, item_id: uuid.UUID, dia: date) -> Preco | None:
        """Preço com início exatamente naquele dia."""
        consulta = select(Preco).where(
            Preco.cliente_id == cliente_id,
            Preco.item_id == item_id,
            Preco.vigencia_inicio == dia,
        )
        return self._sessao.scalars(consulta).first()

    def inicios(self, cliente_id: uuid.UUID, item_id: uuid.UUID) -> list[date]:
        """Datas de início de todos os preços do item, da mais antiga à mais nova."""
        consulta = (
            select(Preco.vigencia_inicio)
            .where(Preco.cliente_id == cliente_id, Preco.item_id == item_id)
            .order_by(Preco.vigencia_inicio)
        )
        return list(self._sessao.scalars(consulta))

    def contar_pedidos_afetados(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        *,
        desde: date | None,
        ate_exclusivo: date | None,
        valor_diferente_de: Decimal,
    ) -> int:
        """Pedidos já gravados, no intervalo, com o item a um valor diferente.

        São os pedidos que **mantêm o valor anterior** depois de uma alteração de
        preço — usados para avisar o operador antes de confirmar (Req 1.6, 1.13).
        ``None`` em um limite significa sem limite daquele lado.
        """
        consulta = (
            select(func.count(func.distinct(Lancamento.id)))
            .join(LancamentoLinha, LancamentoLinha.lancamento_id == Lancamento.id)
            .where(
                Lancamento.cliente_id == cliente_id,
                LancamentoLinha.item_id == item_id,
                LancamentoLinha.valor_unitario_congelado != valor_diferente_de,
            )
        )
        if desde is not None:
            consulta = consulta.where(Lancamento.data >= desde)
        if ate_exclusivo is not None:
            consulta = consulta.where(Lancamento.data < ate_exclusivo)
        return int(self._sessao.scalar(consulta) or 0)

    # --- escrita ----------------------------------------------------------

    def inserir(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_inicio: date,
        valor_unitario: Decimal,
    ) -> Preco:
        preco = Preco(
            cliente_id=cliente_id,
            item_id=item_id,
            vigencia_inicio=vigencia_inicio,
            valor_unitario=valor_unitario,
        )
        self._sessao.add(preco)
        self._sessao.flush()
        return preco

    def sincronizar(self) -> None:
        self._sessao.flush()
