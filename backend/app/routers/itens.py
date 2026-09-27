"""Endpoints de Item.

Dois grupos de caminho, pela natureza do recurso: as operações de coleção ficam
sob o cliente (``/api/clientes/{cliente_id}/itens``), porque o catálogo pertence
a um cliente; as de instância usam o id do item (``/api/itens/{item_id}``), que
já é único no sistema.

Só transporte: nenhuma regra de negócio aqui.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.banco import SessaoBanco
from app.core.seguranca import usuario_atual
from app.repositories.cliente_repo import RepositorioCliente
from app.repositories.item_repo import RepositorioItem
from app.schemas.item import ItemEntrada, ItemResposta
from app.services.servico_item import ServicoItem

router = APIRouter(tags=["catálogo"], dependencies=[Depends(usuario_atual)])


def _servico(sessao: SessaoBanco) -> ServicoItem:
    return ServicoItem(RepositorioItem(sessao), RepositorioCliente(sessao))


@router.get("/api/clientes/{cliente_id}/itens", response_model=list[ItemResposta])
def listar_itens(
    cliente_id: uuid.UUID,
    sessao: SessaoBanco,
    incluir_inativos: bool = Query(
        default=False,
        description="Inclui itens inativos, necessário para lançamento retroativo.",
    ),
) -> list[ItemResposta]:
    itens = _servico(sessao).listar(cliente_id, incluir_inativos=incluir_inativos)
    return [ItemResposta.model_validate(item) for item in itens]


@router.post(
    "/api/clientes/{cliente_id}/itens",
    response_model=ItemResposta,
    status_code=status.HTTP_201_CREATED,
)
def criar_item(cliente_id: uuid.UUID, corpo: ItemEntrada, sessao: SessaoBanco) -> ItemResposta:
    item = _servico(sessao).criar(cliente_id, corpo.nome)
    return ItemResposta.model_validate(item)


@router.get("/api/itens/{item_id}", response_model=ItemResposta)
def obter_item(item_id: uuid.UUID, sessao: SessaoBanco) -> ItemResposta:
    return ItemResposta.model_validate(_servico(sessao).obter(item_id))


@router.patch("/api/itens/{item_id}", response_model=ItemResposta)
def renomear_item(item_id: uuid.UUID, corpo: ItemEntrada, sessao: SessaoBanco) -> ItemResposta:
    return ItemResposta.model_validate(_servico(sessao).renomear(item_id, corpo.nome))


@router.post("/api/itens/{item_id}/inativar", response_model=ItemResposta)
def inativar_item(item_id: uuid.UUID, sessao: SessaoBanco) -> ItemResposta:
    return ItemResposta.model_validate(_servico(sessao).inativar(item_id))


@router.post("/api/itens/{item_id}/reativar", response_model=ItemResposta)
def reativar_item(item_id: uuid.UUID, sessao: SessaoBanco) -> ItemResposta:
    return ItemResposta.model_validate(_servico(sessao).reativar(item_id))


@router.delete("/api/itens/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_item(item_id: uuid.UUID, sessao: SessaoBanco) -> None:
    """Exclui apenas item nunca usado; com histórico, recusa e sugere inativar."""
    _servico(sessao).excluir(item_id)
