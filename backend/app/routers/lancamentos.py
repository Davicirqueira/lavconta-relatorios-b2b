"""Endpoints de Lançamento.

Só transporte. O congelamento, a resolução de preço e as validações de unicidade
ficam inteiramente em ``servico_lancamento``.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.banco import SessaoBanco
from app.core.seguranca import usuario_atual
from app.dominio import LinhaSolicitada
from app.models.lancamento import Lancamento
from app.repositories.cliente_repo import RepositorioCliente
from app.repositories.item_repo import RepositorioItem
from app.repositories.lancamento_repo import RepositorioLancamento
from app.repositories.preco_repo import RepositorioPreco
from app.schemas.lancamento import (
    LancamentoEntrada,
    LancamentoResposta,
    LancamentoResumo,
    LinhaPrevia,
    LinhaResposta,
    PreviaEntrada,
    PreviaResposta,
)
from app.services.servico_lancamento import ServicoLancamento
from app.services.servico_preco import ServicoPreco

router = APIRouter(
    prefix="/api/lancamentos",
    tags=["lançamentos"],
    dependencies=[Depends(usuario_atual)],
)


def _servico(sessao: SessaoBanco) -> ServicoLancamento:
    repositorio_cliente = RepositorioCliente(sessao)
    repositorio_item = RepositorioItem(sessao)
    servico_preco = ServicoPreco(RepositorioPreco(sessao), repositorio_cliente, repositorio_item)
    return ServicoLancamento(
        RepositorioLancamento(sessao),
        repositorio_cliente,
        repositorio_item,
        servico_preco,
    )


def _solicitadas(entrada: LancamentoEntrada | PreviaEntrada) -> list[LinhaSolicitada]:
    return [
        LinhaSolicitada(item_id=linha.item_id, quantidade=linha.quantidade)
        for linha in entrada.linhas
    ]


def _montar_resposta(lancamento: Lancamento) -> LancamentoResposta:
    """Monta a resposta somando os totais a partir das linhas gravadas.

    Os totais derivam das mesmas linhas que a resposta exibe — não há um segundo
    cálculo que possa divergir do detalhe.
    """
    linhas = [LinhaResposta.model_validate(linha) for linha in lancamento.linhas]
    return LancamentoResposta(
        id=lancamento.id,
        cliente_id=lancamento.cliente_id,
        data=lancamento.data,
        comanda=lancamento.comanda,
        linhas=linhas,
        total_pecas=sum(linha.quantidade for linha in linhas),
        total_valor=sum((linha.total for linha in linhas), Decimal("0.00")),
    )


@router.get("", response_model=list[LancamentoResumo])
def listar_lancamentos(
    sessao: SessaoBanco,
    cliente_id: Annotated[uuid.UUID, Query(description="Cliente dono dos lançamentos.")],
    inicio: Annotated[date, Query(description="Primeiro dia do período (YYYY-MM-DD).")],
    fim: Annotated[date, Query(description="Último dia do período, inclusive.")],
) -> list[LancamentoResumo]:
    """Lançamentos de um cliente num período, em ordem de data."""
    lancamentos = _servico(sessao).listar(cliente_id, inicio, fim)

    return [
        LancamentoResumo(
            id=lancamento.id,
            cliente_id=lancamento.cliente_id,
            data=lancamento.data,
            comanda=lancamento.comanda,
            total_pecas=sum(linha.quantidade for linha in lancamento.linhas),
            total_valor=sum((linha.total for linha in lancamento.linhas), Decimal("0.00")),
        )
        for lancamento in lancamentos
    ]


@router.post("", response_model=LancamentoResposta, status_code=status.HTTP_201_CREATED)
def criar_lancamento(corpo: LancamentoEntrada, sessao: SessaoBanco) -> LancamentoResposta:
    """Cria o lançamento congelando o valor de cada linha.

    Recusa quando algum item não tem preço vigente para o mês da data, nomeando
    os itens faltantes.
    """
    lancamento = _servico(sessao).criar(
        corpo.cliente_id, corpo.data, _solicitadas(corpo), corpo.comanda
    )
    return _montar_resposta(lancamento)


@router.post("/previa", response_model=PreviaResposta)
def calcular_previa(corpo: PreviaEntrada, sessao: SessaoBanco) -> PreviaResposta:
    """Calcula os totais sem gravar nada.

    Alimenta a barra de totais da interface enquanto o operador digita, mantendo a
    autoridade de cálculo no servidor.

    Não falha por item sem preço: devolve `itens_sem_preco` e calcula o total com
    os demais. A recusa dura acontece ao salvar.
    """
    calculo = _servico(sessao).calcular_previa(corpo.cliente_id, corpo.data, _solicitadas(corpo))

    return PreviaResposta(
        linhas=[
            LinhaPrevia(
                item_id=linha.item_id,
                quantidade=linha.quantidade,
                valor_unitario=linha.valor_unitario,
                total=linha.total,
            )
            for linha in calculo.linhas
        ],
        total_pecas=calculo.total_pecas,
        total_valor=calculo.total_valor,
        itens_sem_preco=list(calculo.itens_sem_preco),
    )


@router.get("/{lancamento_id}", response_model=LancamentoResposta)
def obter_lancamento(lancamento_id: uuid.UUID, sessao: SessaoBanco) -> LancamentoResposta:
    return _montar_resposta(_servico(sessao).obter(lancamento_id))


@router.put("/{lancamento_id}", response_model=LancamentoResposta)
def editar_lancamento(
    lancamento_id: uuid.UUID, corpo: LancamentoEntrada, sessao: SessaoBanco
) -> LancamentoResposta:
    """Edita o lançamento preservando o valor congelado das linhas existentes.

    Linha nova é congelada pelo preço vigente no mês da **data do lançamento**,
    não pelo mês corrente.
    """
    lancamento = _servico(sessao).editar(
        lancamento_id,
        corpo.data,
        _solicitadas(corpo),
        corpo.comanda,
        cliente_id=corpo.cliente_id,
    )
    return _montar_resposta(lancamento)


@router.delete("/{lancamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_lancamento(lancamento_id: uuid.UUID, sessao: SessaoBanco) -> None:
    """Exclui o lançamento e suas linhas.

    A confirmação "Tem certeza?" é responsabilidade da interface: a API não tem
    como confirmar intenção.
    """
    _servico(sessao).excluir(lancamento_id)
