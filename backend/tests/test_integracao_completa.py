"""Integração da pilha inteira, com JWT real atravessando tudo.

POR QUE ESTE ARQUIVO EXISTE
    Os testes em ``test_api_*.py`` substituem a autenticação para focar na regra
    de negócio, e os de ``test_autenticacao.py`` validam o JWT isoladamente.
    Nenhum dos dois cobria o caminho completo: **credencial real atravessando
    autenticação, router, serviço, repositório e banco**.

    Sem isto, a substituição da autenticação criaria ilusão de cobertura ponta a
    ponta — o defeito só apareceria em produção.

O QUE É REAL AQUI
    Token assinado com chave EC, validado contra JWKS pela dependência de
    produção; roteamento, serviço, repositório e Postgres reais.

O QUE É SUBSTITUÍDO
    Apenas a busca HTTP do JWKS (``fetch_data``) e o endereço do banco. São as
    duas fronteiras externas; a lógica toda permanece sob teste.
"""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.erros import CodigoErro
from app.core.seguranca import Autenticado, limpar_cache_jwks, usuario_atual
from app.main import criar_app
from tests.conftest import AMBIENTE_DE_TESTE

ISSUER = AMBIENTE_DE_TESTE["SUPABASE_JWT_ISSUER"]
AUDIENCIA = AMBIENTE_DE_TESTE["SUPABASE_JWT_AUDIENCE"]
KID = "chave-integracao-001"


@pytest.fixture(scope="module")
def chave_privada() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def _jwks(
    chave_privada: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Serve a chave pública no lugar da busca HTTP do JWKS."""
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(chave_privada.public_key()))
    jwk.update({"kid": KID, "use": "sig", "alg": "ES256"})
    conjunto = {"keys": [jwk]}

    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda _self: conjunto)
    limpar_cache_jwks()
    yield
    limpar_cache_jwks()


@pytest.fixture
def token_valido(chave_privada: ec.EllipticCurvePrivateKey) -> str:
    agora = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iss": ISSUER,
            "aud": AUDIENCIA,
            "role": "authenticated",
            "email": "gilson@exemplo.local",
            "iat": agora,
            # 60 minutos: mesmo tempo de vida medido no projeto real
            "exp": agora + timedelta(minutes=60),
        },
        chave_privada,
        algorithm="ES256",
        headers={"kid": KID},
    )


@pytest.fixture
def app_autenticada(sessao: Session) -> Iterator[FastAPI]:
    """Aplicação real: só a sessão de banco é redirecionada ao Postgres local.

    A dependência de autenticação NÃO é substituída — é ela que está sob teste.
    """
    aplicacao = criar_app()
    aplicacao.dependency_overrides[obter_sessao] = lambda: sessao
    yield aplicacao
    aplicacao.dependency_overrides.clear()


@pytest.fixture
def api_autenticada(app_autenticada: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_autenticada, raise_server_exceptions=False) as cliente:
        yield cliente


class TestFluxoCompletoComTokenReal:
    def test_cria_e_le_cliente_com_token_valido(
        self, api_autenticada: TestClient, token_valido: str
    ) -> None:
        cabecalho = {"Authorization": f"Bearer {token_valido}"}

        criacao = api_autenticada.post(
            "/api/clientes", json={"nome": "Hotel Aurora"}, headers=cabecalho
        )
        assert criacao.status_code == 201
        identificador = criacao.json()["id"]

        leitura = api_autenticada.get(f"/api/clientes/{identificador}", headers=cabecalho)
        assert leitura.status_code == 200
        assert leitura.json()["nome"] == "Hotel Aurora"

    def test_fluxo_de_cliente_e_catalogo(
        self, api_autenticada: TestClient, token_valido: str
    ) -> None:
        """Percurso que o operador faz de verdade, com credencial real."""
        cabecalho = {"Authorization": f"Bearer {token_valido}"}

        cliente_id = api_autenticada.post(
            "/api/clientes", json={"nome": "Hotel Aurora"}, headers=cabecalho
        ).json()["id"]

        for nome in ("Lençol", "Fronha", "Toalha"):
            resposta = api_autenticada.post(
                f"/api/clientes/{cliente_id}/itens",
                json={"nome": nome, "valor_unitario": "4.50"},
                headers=cabecalho,
            )
            assert resposta.status_code == 201

        itens = api_autenticada.get(f"/api/clientes/{cliente_id}/itens", headers=cabecalho).json()

        assert [item["nome"] for item in itens] == ["Fronha", "Lençol", "Toalha"]
        assert {item["preco_atual"]["valor_unitario"] for item in itens} == {"4.50"}

    def test_regra_de_negocio_vale_com_token_real(
        self, api_autenticada: TestClient, token_valido: str
    ) -> None:
        """A unicidade continua valendo — autenticar não contorna regra."""
        cabecalho = {"Authorization": f"Bearer {token_valido}"}
        api_autenticada.post("/api/clientes", json={"nome": "Hotel Aurora"}, headers=cabecalho)

        repetido = api_autenticada.post(
            "/api/clientes", json={"nome": "hotel aurora"}, headers=cabecalho
        )

        assert repetido.status_code == 409
        assert repetido.json()["erro"]["codigo"] == CodigoErro.NOME_DUPLICADO.value


class TestTokenInvalidoNaPilhaReal:
    """Token recusado não chega ao banco: a barreira é antes da regra."""

    def test_sem_token_nao_cria_cliente(self, api_autenticada: TestClient) -> None:
        resposta = api_autenticada.post("/api/clientes", json={"nome": "Invasor Ltda"})

        assert resposta.status_code == 401
        # e nada foi gravado
        assert api_autenticada.get("/api/clientes").status_code == 401

    def test_token_expirado_nao_cria_cliente(
        self, api_autenticada: TestClient, chave_privada: ec.EllipticCurvePrivateKey
    ) -> None:
        agora = datetime.now(UTC)
        expirado = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "iss": ISSUER,
                "aud": AUDIENCIA,
                "iat": agora - timedelta(hours=2),
                "exp": agora - timedelta(hours=1),
            },
            chave_privada,
            algorithm="ES256",
            headers={"kid": KID},
        )

        resposta = api_autenticada.post(
            "/api/clientes",
            json={"nome": "Invasor Ltda"},
            headers={"Authorization": f"Bearer {expirado}"},
        )

        assert resposta.status_code == 401

    def test_token_de_outra_chave_nao_cria_cliente(self, api_autenticada: TestClient) -> None:
        """Assinado por chave que não está no JWKS do projeto."""
        intrusa = ec.generate_private_key(ec.SECP256R1())
        agora = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "iss": ISSUER,
                "aud": AUDIENCIA,
                "iat": agora,
                "exp": agora + timedelta(minutes=60),
            },
            intrusa,
            algorithm="ES256",
            headers={"kid": KID},
        )

        resposta = api_autenticada.post(
            "/api/clientes",
            json={"nome": "Invasor Ltda"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resposta.status_code == 401


class TestIdentidadeDoToken:
    def test_a_identidade_validada_chega_ao_endpoint(
        self,
        app_autenticada: FastAPI,
        chave_privada: ec.EllipticCurvePrivateKey,
    ) -> None:
        """O endpoint recebe o usuário do token, não um valor fictício.

        Registramos uma rota que devolve a identidade recebida — sem ela, o teste
        só confirmaria o status, e o nome prometeria mais do que verifica.
        """
        router = APIRouter(prefix="/api", dependencies=[Depends(usuario_atual)])

        @router.get("/_identidade")
        async def _identidade(usuario: Autenticado) -> dict[str, str | None]:
            return {"id": usuario.id, "email": usuario.email, "papel": usuario.papel}

        app_autenticada.include_router(router)

        identificador = str(uuid.uuid4())
        agora = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": identificador,
                "iss": ISSUER,
                "aud": AUDIENCIA,
                "role": "authenticated",
                "email": "gilson@exemplo.local",
                "iat": agora,
                "exp": agora + timedelta(minutes=60),
            },
            chave_privada,
            algorithm="ES256",
            headers={"kid": KID},
        )

        with TestClient(app_autenticada, raise_server_exceptions=False) as cliente:
            resposta = cliente.get("/api/_identidade", headers={"Authorization": f"Bearer {token}"})

        assert resposta.status_code == 200
        assert resposta.json() == {
            "id": identificador,
            "email": "gilson@exemplo.local",
            "papel": "authenticated",
        }
