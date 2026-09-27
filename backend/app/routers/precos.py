"""Endpoints de Preço.

Só transporte. A regra de vigência inteira mora em ``servico_preco``.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.banco import SessaoBanco
from app.core.datas import hoje_sp, texto_para_mes
from app.core.erros import CodigoErro, ErroDeDominio
from app.core.seguranca import usuario_atual
from app.repositories.cliente_repo import RepositorioCliente
from app.repositories.item_repo import RepositorioItem
from app.repositories.preco_repo import RepositorioPreco
from app.schemas.preco import (
    ItemComPreco,
    PrecoEntrada,
    PrecoResposta,
    PrecosDoMes,
    VigenciaSugerida,
)
from app.services.servico_preco import ServicoPreco

router = APIRouter(
    prefix="/api/clientes/{cliente_id}/precos",
    tags=["preços"],
    dependencies=[Depends(usuario_atual)],
)


def _servico(sessao: SessaoBanco) -> ServicoPreco:
    return ServicoPreco(
        RepositorioPreco(sessao),
        RepositorioCliente(sessao),
        RepositorioItem(sessao),
    )


def _interpretar_mes(mes: str | None) -> date:
    """Converte ``YYYY-MM``, ou usa o mês corrente em São Paulo."""
    if mes is None:
        return hoje_sp().replace(day=1)
    try:
        return texto_para_mes(mes)
    except ValueError as erro:
        raise ErroDeDominio(
            CodigoErro.VALIDACAO,
            "Mês inválido. Use o formato YYYY-MM.",
            {"campos": ["mes"]},
        ) from erro


@router.get("", response_model=PrecosDoMes)
def listar_precos_do_mes(
    cliente_id: uuid.UUID,
    sessao: SessaoBanco,
    mes: str | None = Query(
        default=None,
        description="Mês no formato YYYY-MM. Omitido, usa o mês corrente.",
        examples=["2026-09"],
    ),
    incluir_inativos: bool = Query(default=False, description="Inclui itens inativos do catálogo."),
) -> PrecosDoMes:
    """Tabela de preços do cliente para um mês.

    Devolve **todos** os itens do catálogo, marcando com `sem_preco` os que não têm
    valor definido — item sem preço impede lançamento, então a tela precisa
    destacá-los antes de o operador tentar.

    O campo `vigencia_origem` mostra de qual mês o preço foi herdado, dando
    transparência à propagação da vigência.
    """
    mes_referencia = _interpretar_mes(mes)
    linhas = _servico(sessao).listar_do_mes(
        cliente_id, mes_referencia, incluir_inativos=incluir_inativos
    )

    return PrecosDoMes(
        mes=mes_referencia,
        itens=[
            ItemComPreco(
                item_id=item_id,
                nome=nome,
                valor_unitario=vigente.valor_unitario if vigente else None,
                vigencia_origem=vigente.vigencia_origem if vigente else None,
                sem_preco=vigente is None,
            )
            for item_id, nome, vigente in linhas
        ],
    )


@router.put("", response_model=PrecoResposta)
def definir_preco(cliente_id: uuid.UUID, corpo: PrecoEntrada, sessao: SessaoBanco) -> PrecoResposta:
    """Define ou atualiza o preço de um item para um mês.

    Aceita mês futuro, para programar preço acordado com antecedência, e mês
    passado, para corrigir erro de digitação.

    Correção de mês passado **não altera lançamentos já criados**: eles guardam o
    valor congelado. A interface deve avisar isso ao operador.
    """
    preco = _servico(sessao).definir(cliente_id, corpo.item_id, corpo.mes, corpo.valor_unitario)
    return PrecoResposta.model_validate(preco)


@router.get("/vigencia-sugerida/{item_id}", response_model=VigenciaSugerida)
def obter_vigencia_sugerida(
    cliente_id: uuid.UUID, item_id: uuid.UUID, sessao: SessaoBanco
) -> VigenciaSugerida:
    """Mês que a interface deve propor ao definir o preço deste item.

    Evita que o frontend reimplemente a regra: quem decide é o backend.
    """
    sugestao = _servico(sessao).vigencia_sugerida(cliente_id, item_id, hoje_sp())

    return VigenciaSugerida(
        vigencia_mes=sugestao.vigencia_mes,
        e_primeiro_preco=sugestao.e_primeiro_preco,
    )
