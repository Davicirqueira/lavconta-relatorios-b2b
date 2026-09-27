"""Endpoints de Cliente.

Só transporte: valida a entrada com Pydantic, chama o serviço e mapeia a saída.
Nenhuma regra de negócio aqui (engineering.md §1).

A dependência de autenticação está no nível do ``APIRouter``, não rota a rota:
esquecer um ``Depends`` deixaria uma rota de dados pública. Um teste estrutural
varre as rotas e reforça isso.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.banco import SessaoBanco
from app.core.seguranca import usuario_atual
from app.repositories.cliente_repo import RepositorioCliente
from app.schemas.cliente import ClienteEntrada, ClienteResposta
from app.services.servico_cliente import ServicoCliente

router = APIRouter(
    prefix="/api/clientes",
    tags=["clientes"],
    dependencies=[Depends(usuario_atual)],
)


def _servico(sessao: SessaoBanco) -> ServicoCliente:
    return ServicoCliente(RepositorioCliente(sessao))


@router.get("", response_model=list[ClienteResposta])
def listar_clientes(
    sessao: SessaoBanco,
    incluir_inativos: bool = Query(
        default=False,
        description="Inclui clientes inativos na listagem.",
    ),
) -> list[ClienteResposta]:
    clientes = _servico(sessao).listar(incluir_inativos=incluir_inativos)
    return [ClienteResposta.model_validate(cliente) for cliente in clientes]


@router.post("", response_model=ClienteResposta, status_code=status.HTTP_201_CREATED)
def criar_cliente(corpo: ClienteEntrada, sessao: SessaoBanco) -> ClienteResposta:
    cliente = _servico(sessao).criar(corpo.nome)
    return ClienteResposta.model_validate(cliente)


@router.get("/{cliente_id}", response_model=ClienteResposta)
def obter_cliente(cliente_id: uuid.UUID, sessao: SessaoBanco) -> ClienteResposta:
    cliente = _servico(sessao).obter(cliente_id)
    return ClienteResposta.model_validate(cliente)


@router.patch("/{cliente_id}", response_model=ClienteResposta)
def renomear_cliente(
    cliente_id: uuid.UUID, corpo: ClienteEntrada, sessao: SessaoBanco
) -> ClienteResposta:
    cliente = _servico(sessao).renomear(cliente_id, corpo.nome)
    return ClienteResposta.model_validate(cliente)


@router.post("/{cliente_id}/inativar", response_model=ClienteResposta)
def inativar_cliente(cliente_id: uuid.UUID, sessao: SessaoBanco) -> ClienteResposta:
    cliente = _servico(sessao).inativar(cliente_id)
    return ClienteResposta.model_validate(cliente)


@router.post("/{cliente_id}/reativar", response_model=ClienteResposta)
def reativar_cliente(cliente_id: uuid.UUID, sessao: SessaoBanco) -> ClienteResposta:
    cliente = _servico(sessao).reativar(cliente_id)
    return ClienteResposta.model_validate(cliente)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_cliente(cliente_id: uuid.UUID, sessao: SessaoBanco) -> None:
    """Exclui apenas cliente sem lançamento; com histórico, recusa e sugere inativar."""
    _servico(sessao).excluir(cliente_id)
