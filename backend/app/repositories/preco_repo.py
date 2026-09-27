"""Acesso a dados de Preço, incluindo a resolução da vigência.

A resolução é a consulta central do produto: dela sai o valor que será congelado
no lançamento e, por consequência, cobrado do cliente.
"""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dominio import PrecoVigente
from app.models.preco import Preco


class RepositorioPreco:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # --- resolução da vigência -------------------------------------------

    def resolver_vigentes(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        mes_referencia: date,
    ) -> dict[uuid.UUID, PrecoVigente]:
        """Preço vigente de cada item no mês de referência.

        Regra (Req 4.4 e 4.6): o vigente é o preço **mais recente** cuja vigência
        seja igual ou anterior ao mês consultado. Preço definido em junho continua
        valendo em setembro e em dezembro, até que outro seja definido.

        Usa ``DISTINCT ON`` para resolver todos os itens em **uma** consulta. A
        alternativa — uma consulta por item — seria N+1 e, no caso de um
        lançamento com dez itens, dez idas ao banco por operação.

        Itens ausentes no retorno são os **sem preço**: não existe valor definido
        até aquele mês. Quem chama compara o conjunto pedido com o retornado.
        """
        if not item_ids:
            return {}

        consulta = (
            select(Preco.item_id, Preco.valor_unitario, Preco.vigencia_mes)
            .where(
                Preco.cliente_id == cliente_id,
                Preco.item_id.in_(item_ids),
                Preco.vigencia_mes <= mes_referencia,
            )
            # DISTINCT ON (item_id) + ORDER BY vigencia_mes DESC devolve, para cada
            # item, apenas a linha de vigência mais recente. O índice
            # ix_precos_resolucao atende exatamente esta ordenação.
            .distinct(Preco.item_id)
            .order_by(Preco.item_id, Preco.vigencia_mes.desc())
        )

        return {
            linha.item_id: PrecoVigente(
                item_id=linha.item_id,
                valor_unitario=linha.valor_unitario,
                vigencia_origem=linha.vigencia_mes,
            )
            for linha in self._sessao.execute(consulta)
        }

    # --- leitura ----------------------------------------------------------

    def obter_do_mes(
        self, cliente_id: uuid.UUID, item_id: uuid.UUID, vigencia_mes: date
    ) -> Preco | None:
        """Preço definido exatamente naquele mês (não resolve propagação)."""
        consulta = select(Preco).where(
            Preco.cliente_id == cliente_id,
            Preco.item_id == item_id,
            Preco.vigencia_mes == vigencia_mes,
        )
        return self._sessao.scalars(consulta).first()

    def existe_algum(self, cliente_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        """Se o item já teve algum preço definido, em qualquer mês.

        Distingue "primeiro preço" de "alteração", o que muda a vigência sugerida
        (Req 4.15 e 4.16).
        """
        consulta = (
            select(Preco.id)
            .where(Preco.cliente_id == cliente_id, Preco.item_id == item_id)
            .limit(1)
        )
        return self._sessao.scalars(consulta).first() is not None

    # --- escrita ----------------------------------------------------------

    def inserir(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_mes: date,
        valor_unitario: Decimal,
    ) -> Preco:
        preco = Preco(
            cliente_id=cliente_id,
            item_id=item_id,
            vigencia_mes=vigencia_mes,
            valor_unitario=valor_unitario,
        )
        self._sessao.add(preco)
        self._sessao.flush()
        return preco

    def sincronizar(self) -> None:
        self._sessao.flush()
