"""Testes da validação de JWT (tarefa 10 e 11).

ESTRATÉGIA
    Geramos um par de chaves EC (P-256) próprio nos testes, assinamos tokens com
    a chave privada e servimos um JWKS falso com a chave pública. Assim testamos
    o nosso código de validação por completo, sem depender de rede nem de
    credencial real do Supabase.

    Os valores de ``iss``/``aud`` usados aqui são os mesmos confirmados no
    projeto real (design §18, item 1).
"""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from jwt import PyJWKClient

from app.core.erros import CodigoErro, nao_autenticado
from app.core.seguranca import Autenticado, limpar_cache_jwks
from app.main import ROTA_PUBLICA_SAUDE, app, criar_app
from tests.conftest import AMBIENTE_DE_TESTE

ISSUER = AMBIENTE_DE_TESTE["SUPABASE_JWT_ISSUER"]
AUDIENCIA = AMBIENTE_DE_TESTE["SUPABASE_JWT_AUDIENCE"]
KID = "chave-de-teste-001"

# mensagem única devolvida em toda falha de autenticação (Req 1.5)
MENSAGEM_GENERICA = nao_autenticado().mensagem


# ---------------------------------------------------------------------------
# Infraestrutura de chaves
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def par_de_chaves() -> tuple[ec.EllipticCurvePrivateKey, str]:
    """Par EC P-256 (mesma curva do ES256 usado pelo Supabase) e o JWKS público."""
    privada = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(privada.public_key()))
    jwk.update({"kid": KID, "use": "sig", "alg": "ES256"})
    return privada, json.dumps({"keys": [jwk]})


@pytest.fixture(autouse=True)
def _jwks_local(
    par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Substitui APENAS a busca HTTP do JWKS pelo nosso conjunto de chaves.

    Interceptamos ``PyJWKClient.fetch_data``, o ponto exato onde a rede é
    acessada. Todo o resto do caminho real permanece sob teste: procura da chave
    por ``kid``, cache, recarga sob ``kid`` desconhecido e a validação em si.

    Servir o JWKS por arquivo não funcionaria: o PyJWKClient recusa esquema
    ``file://`` por segurança, aceitando apenas ``http`` e ``https``.
    """
    _, jwks_json = par_de_chaves
    conjunto = json.loads(jwks_json)

    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda _self: conjunto)

    limpar_cache_jwks()
    yield
    limpar_cache_jwks()


def gerar_token(
    privada: ec.EllipticCurvePrivateKey,
    *,
    issuer: str = ISSUER,
    audiencia: str = AUDIENCIA,
    expira_em: timedelta = timedelta(minutes=60),
    sub: str | None = None,
    algoritmo: str = "ES256",
    kid: str | None = KID,
    omitir: tuple[str, ...] = (),
    chave_de_assinatura: Any = None,  # noqa: ANN401
) -> str:
    """Monta um token assinado, com desvios controlados para cada cenário."""
    agora = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": sub or str(uuid.uuid4()),
        "iss": issuer,
        "aud": audiencia,
        "role": "authenticated",
        "email": "verificacao@lavconta.local",
        "iat": agora,
        "exp": agora + expira_em,
    }
    for claim in omitir:
        payload.pop(claim, None)

    cabecalho = {"kid": kid} if kid else {}
    return jwt.encode(
        payload,
        chave_de_assinatura or privada,
        algorithm=algoritmo,
        headers=cabecalho,
    )


@pytest.fixture
def app_protegido() -> FastAPI:
    """App isolado com uma rota de dados protegida pela dependência real."""
    aplicacao = criar_app()
    router = APIRouter(prefix="/api")

    @router.get("/recurso-protegido")
    async def recurso(usuario: Autenticado) -> dict[str, str]:
        return {"id": usuario.id, "papel": usuario.papel or ""}

    aplicacao.include_router(router)
    return aplicacao


@pytest.fixture
def cliente(app_protegido: FastAPI) -> TestClient:
    return TestClient(app_protegido, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Token válido
# ---------------------------------------------------------------------------


class TestTokenValido:
    def test_aceita_token_valido(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        privada, _ = par_de_chaves
        identificador = str(uuid.uuid4())
        token = gerar_token(privada, sub=identificador)

        resposta = cliente.get(
            "/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"}
        )

        assert resposta.status_code == 200
        assert resposta.json() == {"id": identificador, "papel": "authenticated"}

    def test_esquema_bearer_e_insensivel_a_caixa(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada)

        resposta = cliente.get(
            "/api/recurso-protegido", headers={"Authorization": f"bearer {token}"}
        )

        assert resposta.status_code == 200


# ---------------------------------------------------------------------------
# Token recusado
# ---------------------------------------------------------------------------


class TestTokenRecusado:
    """Req 1.5 — toda falha resulta em 401 com mensagem genérica."""

    def _assert_401_generico(self, resposta) -> None:  # noqa: ANN001
        """Exige 401 com a mensagem EXATAMENTE igual em todos os cenários.

        Comparar com a mensagem canônica é mais forte que procurar termos
        proibidos: prova que nenhuma falha se distingue das outras pela resposta,
        que é a propriedade de segurança do Req 1.5.
        """
        assert resposta.status_code == 401
        corpo = resposta.json()["erro"]
        assert corpo["codigo"] == CodigoErro.NAO_AUTENTICADO.value
        assert corpo["mensagem"] == MENSAGEM_GENERICA
        # nem detalhes estruturados podem diferenciar os casos
        assert "detalhes" not in corpo

    def test_recusa_sem_cabecalho(self, cliente: TestClient) -> None:
        self._assert_401_generico(cliente.get("/api/recurso-protegido"))

    def test_recusa_token_vazio(self, cliente: TestClient) -> None:
        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": "Bearer "})
        )

    def test_recusa_esquema_diferente_de_bearer(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada)

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Basic {token}"})
        )

    def test_recusa_token_malformado(self, cliente: TestClient) -> None:
        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": "Bearer nao-e-um-jwt"})
        )

    def test_recusa_token_expirado(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada, expira_em=timedelta(minutes=-5))

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )

    def test_recusa_assinatura_de_outra_chave(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        """Token bem formado, assinado por chave que não está no JWKS."""
        privada, _ = par_de_chaves
        intrusa = ec.generate_private_key(ec.SECP256R1())
        token = gerar_token(privada, chave_de_assinatura=intrusa)

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )

    def test_recusa_audiencia_errada(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada, audiencia="outra-audiencia")

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )

    def test_recusa_emissor_errado(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada, issuer="https://invasor.example.com/auth/v1")

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )

    @pytest.mark.parametrize("claim", ["exp", "aud", "iss", "sub"])
    def test_recusa_claim_obrigatorio_ausente(
        self,
        cliente: TestClient,
        par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str],
        claim: str,
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada, omitir=(claim,))

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )

    def test_recusa_kid_desconhecido(
        self, cliente: TestClient, par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str]
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada, kid="kid-que-nao-existe")

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )

    def test_recusa_algoritmo_none(self, cliente: TestClient) -> None:
        """Confusão de algoritmo: token sem assinatura não pode ser aceito."""
        payload = {
            "sub": str(uuid.uuid4()),
            "iss": ISSUER,
            "aud": AUDIENCIA,
            "exp": datetime.now(UTC) + timedelta(minutes=60),
        }
        token = jwt.encode(payload, key="", algorithm="none")

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )

    def test_recusa_algoritmo_simetrico(self, cliente: TestClient) -> None:
        """HS256 é recusado: só aceitamos assinatura assimétrica.

        Defesa contra confusão de algoritmo: um atacante que descobrisse a chave
        pública poderia usá-la como segredo HMAC se aceitássemos HS256.
        """
        payload = {
            "sub": str(uuid.uuid4()),
            "iss": ISSUER,
            "aud": AUDIENCIA,
            "exp": datetime.now(UTC) + timedelta(minutes=60),
        }
        # 32+ bytes para não disparar aviso de chave curta do PyJWT
        segredo = "segredo-de-teste-com-tamanho-suficiente-para-hmac-sha256"
        token = jwt.encode(payload, key=segredo, algorithm="HS256", headers={"kid": KID})

        self._assert_401_generico(
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})
        )


# ---------------------------------------------------------------------------
# Diagnóstico no log
# ---------------------------------------------------------------------------


class TestDiagnosticoNoLog:
    """A mensagem ao cliente é genérica, mas o log nomeia a causa real."""

    def test_audiencia_errada_registra_a_chave_de_configuracao(
        self,
        cliente: TestClient,
        par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada, audiencia="errada")

        with caplog.at_level("ERROR", logger="lavconta.seguranca"):
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})

        registro = caplog.text
        assert "SUPABASE_JWT_AUDIENCE" in registro
        assert AUDIENCIA in registro

    def test_emissor_errado_registra_a_chave_de_configuracao(
        self,
        cliente: TestClient,
        par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        privada, _ = par_de_chaves
        token = gerar_token(privada, issuer="https://errado.example.com")

        with caplog.at_level("ERROR", logger="lavconta.seguranca"):
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})

        assert "SUPABASE_JWT_ISSUER" in caplog.text

    def test_log_nunca_contem_o_token(
        self,
        cliente: TestClient,
        par_de_chaves: tuple[ec.EllipticCurvePrivateKey, str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Token é credencial portadora: não pode vazar em log."""
        privada, _ = par_de_chaves
        token = gerar_token(privada, audiencia="errada")

        with caplog.at_level("DEBUG"):
            cliente.get("/api/recurso-protegido", headers={"Authorization": f"Bearer {token}"})

        assert token not in caplog.text
        # nem a parte da assinatura isoladamente
        assert token.rsplit(".", 1)[-1] not in caplog.text


# ---------------------------------------------------------------------------
# Teste estrutural (tarefa 11)
# ---------------------------------------------------------------------------


METODOS_HTTP = ("get", "post", "put", "patch", "delete")

# valor válido para qualquer parâmetro de caminho, para que a requisição chegue à
# verificação de autenticação em vez de parar na validação de tipo
UUID_FICTICIO = "00000000-0000-0000-0000-000000000000"


def rotas_da_api(aplicacao: FastAPI) -> list[tuple[str, str]]:
    """Lista (método, caminho) das rotas sob ``/api``, a partir do OpenAPI.

    Usamos o esquema OpenAPI, que é contrato público do FastAPI, em vez de
    percorrer ``app.routes``. Motivo concreto: a partir da versão 0.141 o
    ``include_router`` não achata as rotas em ``app.routes`` — ele guarda um
    objeto ``_IncludedRouter``. Um detector baseado em estrutura interna passou a
    ignorar todas as rotas incluídas e dava falsa segurança.
    """
    esquema = aplicacao.openapi()
    rotas: list[tuple[str, str]] = []
    for caminho, operacoes in esquema.get("paths", {}).items():
        if not caminho.startswith("/api"):
            continue
        for metodo in operacoes:
            if metodo.lower() in METODOS_HTTP:
                rotas.append((metodo.upper(), caminho))
    return rotas


def _preencher_parametros(caminho: str) -> str:
    """Substitui ``{param}`` por um UUID válido."""
    resultado = caminho
    while "{" in resultado:
        inicio = resultado.index("{")
        fim = resultado.index("}", inicio)
        resultado = resultado[:inicio] + UUID_FICTICIO + resultado[fim + 1 :]
    return resultado


class TestProtecaoEstruturalDasRotas:
    """Impede que uma rota de dados seja publicada sem autenticação.

    Verificação COMPORTAMENTAL: para cada rota declarada no OpenAPI, faz a
    requisição sem token e exige 401. Testa a propriedade de segurança de fato,
    e não uma estrutura interna da biblioteca que pode mudar de versão.
    """

    def test_toda_rota_de_dados_exige_autenticacao(self) -> None:
        cliente_sem_token = TestClient(app, raise_server_exceptions=False)
        desprotegidas: list[str] = []

        rotas = rotas_da_api(app)
        assert rotas, "nenhuma rota /api encontrada — o detector não está enxergando nada"

        for metodo, caminho in rotas:
            if caminho == ROTA_PUBLICA_SAUDE:
                continue
            resposta = cliente_sem_token.request(metodo, _preencher_parametros(caminho), json={})
            if resposta.status_code != 401:
                desprotegidas.append(f"{metodo} {caminho} -> {resposta.status_code}")

        assert not desprotegidas, (
            "Rotas de dados que responderam sem autenticação: "
            + "; ".join(desprotegidas)
            + ". Aplique a dependência de autenticação no APIRouter."
        )

    def test_encontra_as_rotas_de_clientes(self) -> None:
        """Garante que o detector realmente enxerga rotas de router incluído."""
        caminhos = {caminho for _, caminho in rotas_da_api(app)}

        assert "/api/clientes" in caminhos
        assert "/api/clientes/{cliente_id}" in caminhos

    def test_a_rota_publica_de_saude_permanece_acessivel(self) -> None:
        resposta = TestClient(app).get(ROTA_PUBLICA_SAUDE)

        assert resposta.status_code == 200

    def test_o_detector_acusa_rota_desprotegida(self) -> None:
        """Verifica o próprio detector com uma rota sem autenticação.

        Sem este teste, um detector cego passaria silenciosamente e daria falsa
        segurança — que é pior que não ter detector.
        """
        aplicacao = criar_app()
        router_sem_protecao = APIRouter(prefix="/api")

        @router_sem_protecao.get("/esquecida")
        async def _sem_protecao() -> dict[str, bool]:
            return {"vazou": True}

        # incluído por include_router, exatamente como as rotas reais
        aplicacao.include_router(router_sem_protecao)

        cliente_sem_token = TestClient(aplicacao, raise_server_exceptions=False)
        resposta = cliente_sem_token.get("/api/esquecida")

        assert ("GET", "/api/esquecida") in rotas_da_api(aplicacao), (
            "o detector não enxergou a rota incluída"
        )
        assert resposta.status_code == 200, "a rota de teste deveria estar desprotegida"
