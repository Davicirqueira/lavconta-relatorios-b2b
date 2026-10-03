"""Endpoints de Preço (v1.1).

Só transporte. A regra inteira mora em ``servico_preco``. O "hoje" vem da
dependência ``hoje_de_negocio``, nunca do corpo da requisição.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.banco import SessaoBanco
from app.core.rate_limit import limiter
from app.core.relogio import HojeDeNegocio
from app.core.seguranca import usuario_atual
from app.dominio import ModoDeAlteracao, PrecoVigente
from app.repositories.cliente_repo import RepositorioCliente
from app.repositories.item_repo import RepositorioItem
from app.repositories.preco_repo import RepositorioPreco
from app.schemas.preco import (
    AlteracaoDePreco,
    ImpactoDaAlteracao,
    ItemComPreco,
    PrecoAtual,
    PrecosNaData,
)
from app.services.servico_preco import ServicoPreco

router = APIRouter(tags=["preços"], dependencies=[Depends(usuario_atual)])


def _servico(sessao: SessaoBanco, hoje: date) -> ServicoPreco:
    return ServicoPreco(
        RepositorioPreco(sessao),
        RepositorioCliente(sessao),
        RepositorioItem(sessao),
        hoje=lambda: hoje,
    )


@router.get("/api/clientes/{cliente_id}/precos", response_model=PrecosNaData)
def listar_precos_na_data(
    cliente_id: uuid.UUID,
    sessao: SessaoBanco,
    hoje: HojeDeNegocio,
    data: Annotated[
        date, Query(description="Data do pedido (YYYY-MM-DD).", examples=["2026-10-02"])
    ],
    incluir_inativos: Annotated[bool, Query(description="Inclui itens inativos.")] = False,
) -> PrecosNaData:
    """Preço de cada item do catálogo na data do pedido.

    Marca com `sem_preco` os itens que ainda não têm nenhum preço: eles impedem
    salvar o pedido, então a tela precisa destacá-los antes.
    """
    linhas = _servico(sessao, hoje).listar_na_data(
        cliente_id, data, incluir_inativos=incluir_inativos
    )
    return PrecosNaData(
        data=data,
        itens=[_item_com_preco(item.id, item.nome, vigente) for item, vigente in linhas],
    )


@router.put("/api/itens/{item_id}/preco", response_model=PrecoAtual)
@limiter.limit("60/minute")
def alterar_preco(
    request: Request,  # exigido pelo slowapi
    item_id: uuid.UUID,
    corpo: AlteracaoDePreco,
    sessao: SessaoBanco,
    hoje: HojeDeNegocio,
) -> PrecoAtual:
    """Muda o preço a partir de hoje ou corrige o preço atual.

    Pedidos já registrados não mudam em nenhum dos dois modos: o valor deles está
    congelado. Use `/preco/impacto` antes para avisar o operador.
    """
    preco = _servico(sessao, hoje).alterar(item_id, corpo.valor_unitario, corpo.modo)
    return PrecoAtual(
        valor_unitario=preco.valor_unitario,
        desde=preco.vigencia_inicio,
        e_hoje=preco.vigencia_inicio == hoje,
    )


@router.get("/api/itens/{item_id}/preco/impacto", response_model=ImpactoDaAlteracao)
def impacto_da_alteracao(
    item_id: uuid.UUID,
    sessao: SessaoBanco,
    hoje: HojeDeNegocio,
    valor_unitario: Annotated[Decimal, Query(gt=0, max_digits=10, decimal_places=2)],
    modo: Annotated[ModoDeAlteracao, Query()] = ModoDeAlteracao.A_PARTIR_DE_HOJE,
) -> ImpactoDaAlteracao:
    """Quantos pedidos já registrados continuam com o valor anterior."""
    quantidade = _servico(sessao, hoje).impacto(item_id, valor_unitario, modo)
    return ImpactoDaAlteracao(pedidos_com_valor_anterior=quantidade)


def _item_com_preco(item_id: uuid.UUID, nome: str, vigente: PrecoVigente | None) -> ItemComPreco:
    return ItemComPreco(
        item_id=item_id,
        nome=nome,
        valor_unitario=vigente.valor_unitario if vigente else None,
        desde=vigente.desde if vigente else None,
        sem_preco=vigente is None,
    )
