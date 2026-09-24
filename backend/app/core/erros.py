"""Exceções de domínio e o mapa de códigos de erro da API.

Os serviços levantam estas exceções; o handler global em ``main.py`` as traduz no
envelope de erro da API. Nenhum service conhece código HTTP — essa tradução é
responsabilidade da camada de transporte.

Regra de saída segura: a mensagem é útil ao operador e **não** revela detalhe de
implementação, stack trace ou valor de segredo.
"""

from enum import StrEnum
from typing import Any


class CodigoErro(StrEnum):
    """Códigos estáveis de erro, consumidos pelo frontend para decidir a mensagem."""

    NAO_AUTENTICADO = "NAO_AUTENTICADO"
    VALIDACAO = "VALIDACAO"
    LANCAMENTO_DUPLICADO = "LANCAMENTO_DUPLICADO"
    COMANDA_DUPLICADA = "COMANDA_DUPLICADA"
    ITENS_SEM_PRECO = "ITENS_SEM_PRECO"
    ITEM_DUPLICADO_NO_LANCAMENTO = "ITEM_DUPLICADO_NO_LANCAMENTO"
    DATA_FUTURA = "DATA_FUTURA"
    PERIODO_INVALIDO = "PERIODO_INVALIDO"
    NOME_DUPLICADO = "NOME_DUPLICADO"
    EXCLUSAO_COM_HISTORICO = "EXCLUSAO_COM_HISTORICO"
    NAO_ENCONTRADO = "NAO_ENCONTRADO"
    ERRO_INTERNO = "ERRO_INTERNO"


# Código de domínio → status HTTP. Mantido aqui para existir um só lugar de verdade.
STATUS_HTTP_POR_CODIGO: dict[CodigoErro, int] = {
    CodigoErro.NAO_AUTENTICADO: 401,
    CodigoErro.VALIDACAO: 422,
    CodigoErro.LANCAMENTO_DUPLICADO: 409,
    CodigoErro.COMANDA_DUPLICADA: 409,
    CodigoErro.ITENS_SEM_PRECO: 422,
    CodigoErro.ITEM_DUPLICADO_NO_LANCAMENTO: 422,
    CodigoErro.DATA_FUTURA: 422,
    CodigoErro.PERIODO_INVALIDO: 422,
    CodigoErro.NOME_DUPLICADO: 409,
    CodigoErro.EXCLUSAO_COM_HISTORICO: 409,
    CodigoErro.NAO_ENCONTRADO: 404,
    CodigoErro.ERRO_INTERNO: 500,
}


class ErroDeDominio(Exception):
    """Erro previsto de regra de negócio.

    Args:
        codigo: código estável consumido pelo frontend.
        mensagem: texto em português, voltado ao operador.
        detalhes: dados estruturados úteis à interface (ex.: nomes dos itens sem
            preço), para a tela destacar exatamente o que falhou.
    """

    def __init__(
        self,
        codigo: CodigoErro,
        mensagem: str,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes or {}

    @property
    def status_http(self) -> int:
        return STATUS_HTTP_POR_CODIGO[self.codigo]

    def como_envelope(self) -> dict[str, Any]:
        """Serializa no envelope de erro da API (design §8.1)."""
        corpo: dict[str, Any] = {"codigo": self.codigo.value, "mensagem": self.mensagem}
        if self.detalhes:
            corpo["detalhes"] = self.detalhes
        return {"erro": corpo}


# --- Atalhos de uso frequente ---------------------------------------------
# Construtores nomeados evitam repetir mensagem em vários serviços e mantêm o
# texto ao usuário consistente.


def nao_encontrado(recurso: str) -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.NAO_ENCONTRADO,
        f"{recurso} não encontrado.",
    )


def nome_duplicado(recurso: str, nome: str) -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.NOME_DUPLICADO,
        f"Já existe {recurso} com o nome “{nome}”.",
        {"nome": nome},
    )


def exclusao_com_historico(recurso: str) -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.EXCLUSAO_COM_HISTORICO,
        f"Não é possível excluir: existem lançamentos vinculados a este {recurso}. "
        f"Você pode inativá-lo.",
    )


def lancamento_duplicado(data_br: str) -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.LANCAMENTO_DUPLICADO,
        f"Já existe um lançamento para este cliente em {data_br}.",
        {"data": data_br},
    )


def comanda_duplicada(comanda: str) -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.COMANDA_DUPLICADA,
        f"A comanda “{comanda}” já foi usada para este cliente.",
        {"comanda": comanda},
    )


def itens_sem_preco(nomes: list[str], mes_ref: str) -> ErroDeDominio:
    """Erro de item sem preço, nomeando os itens (Req 5.14)."""
    lista = " e ".join(nomes) if len(nomes) <= 2 else ", ".join(nomes[:-1]) + f" e {nomes[-1]}"
    plural = "os itens" if len(nomes) > 1 else "o item"
    verbo = "têm" if len(nomes) > 1 else "tem"
    return ErroDeDominio(
        CodigoErro.ITENS_SEM_PRECO,
        f"Não foi possível salvar: {plural} {lista} não {verbo} preço cadastrado para {mes_ref}.",
        {"itens": nomes, "mes_referencia": mes_ref},
    )


def data_futura() -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.DATA_FUTURA,
        "Não é possível registrar lançamento com data futura: o serviço é registrado após ocorrer.",
    )


def periodo_invalido() -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.PERIODO_INVALIDO,
        "A data inicial não pode ser posterior à data final.",
    )


def item_duplicado_no_lancamento(nome: str) -> ErroDeDominio:
    return ErroDeDominio(
        CodigoErro.ITEM_DUPLICADO_NO_LANCAMENTO,
        f"O item “{nome}” está repetido no lançamento.",
        {"item": nome},
    )


def nao_autenticado() -> ErroDeDominio:
    """Falha de autenticação.

    Mensagem deliberadamente genérica: não revela se o token expirou, se a
    assinatura é inválida ou se a audiência está errada (Req 1.5).
    """
    return ErroDeDominio(
        CodigoErro.NAO_AUTENTICADO,
        "Sessão inválida ou expirada. Faça login novamente.",
    )
