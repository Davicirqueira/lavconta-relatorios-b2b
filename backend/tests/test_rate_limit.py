"""Testes de rate limiting (tarefa 34).

Verifica que:
- O limiter está registrado no app.state (sem isso, qualquer request limitado
  lança AttributeError em produção).
- Endpoints de escrita retornam 429 após exceder o limite, no envelope de erro
  padrão da API.
- A rota /previa tem limite mais permissivo que as rotas de escrita.
- O corpo do 429 segue o envelope { "erro": { "codigo", "mensagem" } }.

ESTRATÉGIA
    Criar um app de teste com limite minúsculo ("1/minute") para que o segundo
    request já dispare o 429, sem precisar fazer dezenas de chamadas. A fixture
    usa ``create_autospec`` para não precisar de banco real.

    Os testes de rate limit NÃO usam a fixture ``api`` do conftest (que
    sobrescreve o banco) porque precisam que o ``app.state.limiter`` real esteja
    presente. Cria-se um mini-app isolado aqui.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from app.core.erros import CodigoErro
from app.core.rate_limit import limiter
from app.main import criar_app


class TestLimiterRegistradoNoApp:
    """Garantia estrutural: o limiter está no app.state antes de qualquer request."""

    def test_app_tem_limiter_no_state(self) -> None:
        aplicacao = criar_app()
        assert hasattr(aplicacao.state, "limiter"), (
            "app.state.limiter não encontrado. "
            "Sem isso os endpoints com @limiter.limit() levantam AttributeError em produção."
        )
        assert aplicacao.state.limiter is limiter

    def test_handler_429_registrado(self) -> None:
        """RateLimitExceeded precisa ter handler registrado no app."""
        aplicacao = criar_app()
        # exception_handlers é um dict de tipo -> callable
        handlers = getattr(aplicacao, "exception_handlers", {})
        assert RateLimitExceeded in handlers, (
            "Handler para RateLimitExceeded não encontrado. "
            "Sem ele, o 429 retorna o formato padrão do slowapi, não o envelope da API."
        )


class TestEnvelope429:
    """Quando o limite é excedido, a resposta segue o envelope padrão da API."""

    def test_429_segue_o_envelope_de_erro(self) -> None:
        """Cria app com limite de 1/minute e dispara o segundo request."""
        aplicacao = FastAPI()
        aplicacao.state.limiter = limiter

        from fastapi import Request
        from fastapi.responses import JSONResponse
        from slowapi.errors import RateLimitExceeded

        from app.core.erros import muitas_requisicoes

        @aplicacao.exception_handler(RateLimitExceeded)
        async def _handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
            return JSONResponse(
                status_code=429,
                content=muitas_requisicoes(str(exc.detail)).como_envelope(),
            )

        @aplicacao.get("/api/recurso-limitado")
        @limiter.limit("1/minute")
        async def _endpoint(request: Request) -> dict:  # noqa: ARG001
            return {"ok": True}

        with TestClient(aplicacao, raise_server_exceptions=False) as cliente:
            r1 = cliente.get("/api/recurso-limitado")
            r2 = cliente.get("/api/recurso-limitado")

        assert r1.status_code == 200
        assert r2.status_code == 429

        corpo = r2.json()
        assert "erro" in corpo
        assert corpo["erro"]["codigo"] == CodigoErro.MUITAS_REQUISICOES.value
        assert "mensagem" in corpo["erro"]
        # não vaza stack trace
        assert "traceback" not in str(corpo).lower()
        assert "exception" not in str(corpo).lower()


class TestLimitesDistintos:
    """Prévia tem limite mais permissivo que as rotas de escrita (design §9.3)."""

    def test_previa_tem_limite_maior_que_escrita(self) -> None:
        """Verifica indiretamente pela string do decorator no OpenAPI/schema."""
        # Os limites estão nos decorators dos endpoints; verificamos via
        # os limites registrados no Limiter após o import dos routers.
        from app.routers.lancamentos import calcular_previa, criar_lancamento

        # A maneira canônica: inspecionar os limites registrados no Limiter
        nome_previa = f"{calcular_previa.__module__}.{calcular_previa.__qualname__}"
        nome_criar = f"{criar_lancamento.__module__}.{criar_lancamento.__qualname__}"

        limites_previa = limiter._route_limits.get(nome_previa, [])
        limites_criar = limiter._route_limits.get(nome_criar, [])

        assert limites_previa, "Prévia não tem limite registrado no limiter"
        assert limites_criar, "Criar lançamento não tem limite registrado no limiter"

        # O amount (número de requests) da prévia é maior
        amount_previa = max(lim.limit.amount for lim in limites_previa)
        amount_criar = max(lim.limit.amount for lim in limites_criar)
        assert amount_previa > amount_criar, (
            f"Prévia deveria ter limite maior que criar lançamento, "
            f"mas prévia={amount_previa} e criar={amount_criar}"
        )

    def test_exportacao_tem_limite_registrado(self) -> None:
        from app.routers.relatorio import exportar_excel, exportar_pdf

        nome_excel = f"{exportar_excel.__module__}.{exportar_excel.__qualname__}"
        nome_pdf = f"{exportar_pdf.__module__}.{exportar_pdf.__qualname__}"

        assert limiter._route_limits.get(nome_excel), "Excel não tem limite registrado"
        assert limiter._route_limits.get(nome_pdf), "PDF não tem limite registrado"

    def test_exportacao_geral_tem_limite_registrado(self) -> None:
        from app.routers.relatorio import exportar_excel_geral, exportar_pdf_geral

        for rota in (exportar_excel_geral, exportar_pdf_geral):
            nome = f"{rota.__module__}.{rota.__qualname__}"
            limites = limiter._route_limits.get(nome)
            assert limites, f"{rota.__name__} não tem limite registrado"
            assert max(lim.limit.amount for lim in limites) == 30


class TestLimiteNasRotasDeCatalogoEPreco:
    """v1.1 (tarefa 9): escritas de item e de preço limitadas a 60/min.

    Usa item inexistente: o limite é contado antes de o endpoint executar, então
    cada chamada conta mesmo respondendo 404, sem gravar nada no banco.
    """

    ITEM_INEXISTENTE = "11111111-2222-3333-4444-555555555555"

    @pytest.mark.parametrize(
        ("metodo", "caminho", "corpo"),
        [
            ("delete", "/api/itens/{id}", None),
            ("post", "/api/itens/{id}/inativar", None),
            ("patch", "/api/itens/{id}", {"nome": "Lençol"}),
            ("put", "/api/itens/{id}/preco", {"valor_unitario": "4.50"}),
        ],
    )
    def test_61a_chamada_recebe_429(
        self, api, metodo: str, caminho: str, corpo: dict | None
    ) -> None:  # noqa: ANN001
        url = caminho.format(id=self.ITEM_INEXISTENTE)
        chamar = getattr(api, metodo)
        argumentos = {"json": corpo} if corpo is not None else {}

        respostas = [chamar(url, **argumentos).status_code for _ in range(60)]
        excedente = chamar(url, **argumentos)

        assert set(respostas) == {404}
        assert excedente.status_code == 429
        assert excedente.json()["erro"]["codigo"] == CodigoErro.MUITAS_REQUISICOES.value

    def test_criar_item_e_limitado(self, api) -> None:  # noqa: ANN001
        url = f"/api/clientes/{self.ITEM_INEXISTENTE}/itens"
        corpo = {"nome": "Lençol", "valor_unitario": "4.50"}

        respostas = [api.post(url, json=corpo).status_code for _ in range(60)]

        assert set(respostas) == {404}
        assert api.post(url, json=corpo).status_code == 429
