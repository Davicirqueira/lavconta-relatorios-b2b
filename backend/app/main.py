"""Aplicação FastAPI do Lavconta.

Monta o app, a borda de segurança (CORS restrito e cabeçalhos) e os handlers que
traduzem erro de domínio no envelope da API.

Regra de saída segura: nenhuma resposta de erro expõe stack trace ou detalhe de
implementação. O rastreamento completo vai apenas para o log do servidor.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import obter_configuracao
from app.core.erros import CodigoErro, ErroDeDominio

logger = logging.getLogger("lavconta")

# Rota pública: não devolve dado de negócio. Referenciada pelo teste estrutural
# que exige autenticação em todas as demais rotas sob /api.
ROTA_PUBLICA_SAUDE = "/api/saude"


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    """Adiciona cabeçalhos de segurança a toda resposta."""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001, ANN201
        resposta = await call_next(request)
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        return resposta


async def tratar_erro_de_dominio(_: Request, erro: ErroDeDominio) -> JSONResponse:
    """Erro previsto de negócio: devolve código, mensagem e detalhes."""
    return JSONResponse(status_code=erro.status_http, content=erro.como_envelope())


async def tratar_erro_de_validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
    """Entrada malformada.

    Informa apenas quais campos falharam, sem ecoar os valores recebidos — um
    valor inválido pode conter dado sensível.
    """
    campos = [
        ".".join(str(parte) for parte in item["loc"][1:])
        for item in erro.errors()
        if item.get("loc")
    ]
    return JSONResponse(
        status_code=422,
        content={
            "erro": {
                "codigo": CodigoErro.VALIDACAO.value,
                "mensagem": "Dados inválidos na requisição.",
                "detalhes": {"campos": campos},
            }
        },
    )


async def tratar_erro_inesperado(request: Request, erro: Exception) -> JSONResponse:
    """Falha não prevista.

    O detalhe fica no log do servidor; o cliente recebe mensagem genérica.
    """
    logger.exception("Erro inesperado em %s %s", request.method, request.url.path, exc_info=erro)
    return JSONResponse(
        status_code=500,
        content={
            "erro": {
                "codigo": CodigoErro.ERRO_INTERNO.value,
                "mensagem": "Ocorreu um erro inesperado. Tente novamente.",
            }
        },
    )


def criar_app() -> FastAPI:
    """Monta a aplicação com borda de segurança e handlers de erro.

    Fábrica em vez de instância global para que os testes possam criar apps
    isolados — um teste que registra rota própria não contamina a aplicação real
    nem o teste estrutural de autenticação.
    """
    configuracao = obter_configuracao()

    aplicacao = FastAPI(
        title="Lavconta — API",
        description="API de relatórios B2B da Lavandix.",
        version="1.0.0",
    )

    # CORS com origens explícitas, sem coringa (a configuração recusa "*").
    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=configuracao.origens_cors,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    aplicacao.add_middleware(CabecalhosDeSeguranca)

    aplicacao.add_exception_handler(ErroDeDominio, tratar_erro_de_dominio)  # type: ignore[arg-type]
    aplicacao.add_exception_handler(RequestValidationError, tratar_erro_de_validacao)  # type: ignore[arg-type]
    aplicacao.add_exception_handler(Exception, tratar_erro_inesperado)

    @aplicacao.get(ROTA_PUBLICA_SAUDE, tags=["infraestrutura"])
    async def saude() -> dict[str, str]:
        """Verificação de disponibilidade.

        Única rota pública da API: não devolve dado de negócio, apenas confirma
        que o serviço está no ar. Serve também para acordar a instância após
        hibernação do plano gratuito.
        """
        return {"situacao": "ok"}

    return aplicacao


app = criar_app()
