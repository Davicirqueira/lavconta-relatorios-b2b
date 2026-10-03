"""Endpoints de Item (catálogo com preço, v1.1).

Dois grupos de caminho, pela natureza do recurso: as operações de coleção ficam
sob o cliente (``/api/clientes/{cliente_id}/itens``), porque o catálogo pertence
a um cliente; as de instância usam o id do item (``/api/itens/{item_id}``), que
já é único no sistema.

Só transporte: nenhuma regra de negócio aqui. Todas as respostas trazem o preço
que vale hoje (``preco_atual``), para o cartão do catálogo exibi-lo.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.banco import SessaoBanco
from app.core.rate_limit import limiter
from app.core.relogio import HojeDeNegocio
from app.core.seguranca import usuario_atual
from app.dominio import PrecoVigente
from app.models.item import Item
from app.repositories.cliente_repo import RepositorioCliente
from app.repositories.item_repo import RepositorioItem
from app.repositories.preco_repo import RepositorioPreco
from app.schemas.item import ItemEntrada, ItemNovo, ItemResposta
from app.services.servico_catalogo import ServicoCatalogo
from app.services.servico_item import ServicoItem
from app.services.servico_preco import ServicoPreco

router = APIRouter(tags=["catálogo"], dependencies=[Depends(usuario_atual)])

# escrita: mesmo limite das demais rotas de escrita (engineering.md §4)
LIMITE_ESCRITA = "60/minute"


class _Servicos:
    """Monta os serviços de uma requisição com o mesmo "hoje"."""

    def __init__(self, sessao: SessaoBanco, hoje: date) -> None:
        repositorio_item = RepositorioItem(sessao)
        repositorio_cliente = RepositorioCliente(sessao)
        self.hoje = hoje
        self.item = ServicoItem(repositorio_item, repositorio_cliente)
        preco = ServicoPreco(
            RepositorioPreco(sessao), repositorio_cliente, repositorio_item, hoje=lambda: hoje
        )
        self.catalogo = ServicoCatalogo(self.item, preco)

    def resposta(self, par: tuple[Item, PrecoVigente | None]) -> ItemResposta:
        item, vigente = par
        return ItemResposta.de(item, vigente, self.hoje)


@router.get("/api/clientes/{cliente_id}/itens", response_model=list[ItemResposta])
def listar_itens(
    cliente_id: uuid.UUID,
    sessao: SessaoBanco,
    hoje: HojeDeNegocio,
    incluir_inativos: Annotated[
        bool,
        Query(description="Inclui itens inativos, necessário para lançamento retroativo."),
    ] = False,
) -> list[ItemResposta]:
    servicos = _Servicos(sessao, hoje)
    pares = servicos.catalogo.listar(cliente_id, incluir_inativos=incluir_inativos)
    return [servicos.resposta(par) for par in pares]


@router.post(
    "/api/clientes/{cliente_id}/itens",
    response_model=ItemResposta,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(LIMITE_ESCRITA)
def criar_item(
    request: Request,  # exigido pelo slowapi
    cliente_id: uuid.UUID,
    corpo: ItemNovo,
    sessao: SessaoBanco,
    hoje: HojeDeNegocio,
) -> ItemResposta:
    """Cria o item já com o preço por peça (os dois juntos ou nenhum)."""
    servicos = _Servicos(sessao, hoje)
    par = servicos.catalogo.criar_item_com_preco(cliente_id, corpo.nome, corpo.valor_unitario)
    return servicos.resposta(par)


@router.get("/api/itens/{item_id}", response_model=ItemResposta)
def obter_item(item_id: uuid.UUID, sessao: SessaoBanco, hoje: HojeDeNegocio) -> ItemResposta:
    servicos = _Servicos(sessao, hoje)
    return servicos.resposta(servicos.catalogo.obter(item_id))


@router.patch("/api/itens/{item_id}", response_model=ItemResposta)
@limiter.limit(LIMITE_ESCRITA)
def renomear_item(
    request: Request,
    item_id: uuid.UUID,
    corpo: ItemEntrada,
    sessao: SessaoBanco,
    hoje: HojeDeNegocio,
) -> ItemResposta:
    servicos = _Servicos(sessao, hoje)
    item = servicos.item.renomear(item_id, corpo.nome)
    return servicos.resposta(servicos.catalogo.com_preco(item))


@router.post("/api/itens/{item_id}/inativar", response_model=ItemResposta)
@limiter.limit(LIMITE_ESCRITA)
def inativar_item(
    request: Request, item_id: uuid.UUID, sessao: SessaoBanco, hoje: HojeDeNegocio
) -> ItemResposta:
    servicos = _Servicos(sessao, hoje)
    return servicos.resposta(servicos.catalogo.com_preco(servicos.item.inativar(item_id)))


@router.post("/api/itens/{item_id}/reativar", response_model=ItemResposta)
@limiter.limit(LIMITE_ESCRITA)
def reativar_item(
    request: Request, item_id: uuid.UUID, sessao: SessaoBanco, hoje: HojeDeNegocio
) -> ItemResposta:
    servicos = _Servicos(sessao, hoje)
    return servicos.resposta(servicos.catalogo.com_preco(servicos.item.reativar(item_id)))


@router.delete("/api/itens/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(LIMITE_ESCRITA)
def excluir_item(request: Request, item_id: uuid.UUID, sessao: SessaoBanco) -> None:
    """Exclui apenas item nunca usado; com histórico, recusa e sugere inativar."""
    ServicoItem(RepositorioItem(sessao), RepositorioCliente(sessao)).excluir(item_id)
