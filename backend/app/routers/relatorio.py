"""Endpoints do Relatório de Fechamento.

Só transporte. A agregação, cálculo de totais e ordenação alfabética
ficam inteiramente em ``servico_relatorio``.
"""

import re
import unicodedata
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.banco import SessaoBanco
from app.core.rate_limit import limiter
from app.core.seguranca import usuario_atual
from app.exports.excel import gerar_excel
from app.exports.pdf import gerar_pdf
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


def _nome_do_arquivo(cliente_nome: str, inicio: date, fim: date, extensao: str) -> str:
    """Gera nome descritivo: fechamento-hotel-aurora-2026-09-01-a-2026-09-30.xlsx"""
    decomposto = unicodedata.normalize("NFKD", cliente_nome)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento.lower()).strip("-")
    slug_final = slug or "relatorio"
    return f"fechamento-{slug_final}-{inicio.isoformat()}-a-{fim.isoformat()}.{extensao}"


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


@router.get("/excel")
@limiter.limit("30/minute")
def exportar_excel(
    request: Request,
    sessao: SessaoBanco,
    cliente_id: Annotated[uuid.UUID, Query(description="Cliente para o fechamento.")],
    inicio: Annotated[date, Query(description="Primeiro dia do período (YYYY-MM-DD).")],
    fim: Annotated[date, Query(description="Último dia do período, inclusive.")],
) -> Response:
    """Exporta o relatório de fechamento em planilha Excel (.xlsx).

    Consome a mesma estrutura do relatório em tela (Req 8.2, 8.5).
    """
    relatorio = _servico(sessao).gerar(cliente_id, inicio, fim)
    conteudo = gerar_excel(relatorio)
    nome_arquivo = _nome_do_arquivo(relatorio.cliente_nome, inicio, fim, "xlsx")
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.get("/pdf")
@limiter.limit("30/minute")
def exportar_pdf(
    request: Request,
    sessao: SessaoBanco,
    cliente_id: Annotated[uuid.UUID, Query(description="Cliente para o fechamento.")],
    inicio: Annotated[date, Query(description="Primeiro dia do período (YYYY-MM-DD).")],
    fim: Annotated[date, Query(description="Último dia do período, inclusive.")],
) -> Response:
    """Exporta o relatório de fechamento em documento PDF A4 paisagem.

    Consome a mesma estrutura do relatório em tela (Req 8.2, 8.5).
    """
    relatorio = _servico(sessao).gerar(cliente_id, inicio, fim)
    conteudo = gerar_pdf(relatorio)
    nome_arquivo = _nome_do_arquivo(relatorio.cliente_nome, inicio, fim, "pdf")
    return Response(
        content=conteudo,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )

