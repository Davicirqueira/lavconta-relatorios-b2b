"""Endpoints do Relatório de Fechamento.

Só transporte. A agregação, cálculo de totais e ordenação alfabética
ficam inteiramente em ``servico_relatorio``.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.banco import SessaoBanco
from app.core.seguranca import usuario_atual
from app.repositories.cliente_repo import RepositorioCliente
from app.repositories.lancamento_repo import RepositorioLancamento
from app.schemas.relatorio import RelatorioResposta
from app.services.servico_relatorio import ServicoRelatorio

router = APIRouter(
    prefix="/api/relatorio",
    tags=["relatório"],
    dependencies=[Depends(usuario_atual)],
)


def _servico(sessao: SessaoBanco) -> ServicoRelatorio:
    return ServicoRelatorio(
        RepositorioLancamento(sessao),
        RepositorioCliente(sessao),
    )


@router.get("", response_model=RelatorioResposta)
def gerar_relatorio(
    sessao: SessaoBanco,
    cliente_id: Annotated[uuid.UUID, Query(description="Cliente para o fechamento.")],
    inicio: Annotated[date, Query(description="Primeiro dia do período (YYYY-MM-DD).")],
    fim: Annotated[date, Query(description="Último dia do período, inclusive.")],
) -> RelatorioResposta:
    """Gera o relatório de fechamento de um cliente no período.

    Exige cliente_id, data inicial e final obrigatórios (Req 7.1, 7.2).
    """
    relatorio = _servico(sessao).gerar(cliente_id, inicio, fim)
    return RelatorioResposta.do_dominio(relatorio)
