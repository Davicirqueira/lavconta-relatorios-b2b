"""Testes da borda da API: rota de saúde, envelope de erro e cabeçalhos."""

from fastapi.testclient import TestClient

from app.core.erros import CodigoErro, ErroDeDominio, itens_sem_preco
from app.main import app, criar_app

cliente = TestClient(app, raise_server_exceptions=False)


class TestRotaDeSaude:
    def test_responde_ok(self) -> None:
        resposta = cliente.get("/api/saude")

        assert resposta.status_code == 200
        assert resposta.json() == {"situacao": "ok"}

    def test_envia_cabecalhos_de_seguranca(self) -> None:
        resposta = cliente.get("/api/saude")

        assert resposta.headers["X-Content-Type-Options"] == "nosniff"
        assert resposta.headers["Referrer-Policy"] == "no-referrer"

    def test_content_type_json(self) -> None:
        resposta = cliente.get("/api/saude")

        assert resposta.headers["content-type"].startswith("application/json")


class TestEnvelopeDeErro:
    """Usa app isolado: registrar rota de teste no app real contaminaria o teste
    estrutural de autenticação (tarefa 11)."""

    def test_erro_de_dominio_vira_envelope_com_codigo_e_detalhes(self) -> None:
        """O handler traduz erro de domínio no envelope do design §8.1."""
        app_isolado = criar_app()

        @app_isolado.get("/api/_erro_dominio")
        async def _rota_de_teste() -> None:
            raise itens_sem_preco(["Roupão", "Tapete"], "setembro/2026")

        resposta = TestClient(app_isolado, raise_server_exceptions=False).get("/api/_erro_dominio")

        assert resposta.status_code == 422
        corpo = resposta.json()["erro"]
        assert corpo["codigo"] == CodigoErro.ITENS_SEM_PRECO.value
        assert corpo["detalhes"]["itens"] == ["Roupão", "Tapete"]
        # a mensagem nomeia os itens, para a tela poder exibi-la direto
        assert "Roupão" in corpo["mensagem"]

    def test_erro_inesperado_nao_vaza_detalhe_interno(self) -> None:
        """Falha não prevista devolve mensagem genérica (Req 9.7)."""
        detalhe_interno = "conexao falhou em servidor-interno-db-01"
        app_isolado = criar_app()

        @app_isolado.get("/api/_erro_inesperado")
        async def _rota_que_explode() -> None:
            raise RuntimeError(detalhe_interno)

        resposta = TestClient(app_isolado, raise_server_exceptions=False).get(
            "/api/_erro_inesperado"
        )

        assert resposta.status_code == 500
        corpo = resposta.text
        assert detalhe_interno not in corpo
        assert "RuntimeError" not in corpo
        assert resposta.json()["erro"]["codigo"] == CodigoErro.ERRO_INTERNO.value


class TestIsolamentoDoAppReal:
    def test_app_real_expoe_apenas_a_rota_de_saude(self) -> None:
        """Garante que nenhum teste poluiu o app real com rota extra.

        Precursor do teste estrutural de autenticação da tarefa 11.
        """
        rotas_api = {
            rota.path  # type: ignore[attr-defined]
            for rota in app.routes
            if hasattr(rota, "path") and rota.path.startswith("/api")  # type: ignore[attr-defined]
        }

        assert rotas_api == {"/api/saude"}


class TestMapeamentoDeStatus:
    def test_cada_codigo_tem_status_http(self) -> None:
        """Nenhum código de erro fica sem status mapeado."""
        for codigo in CodigoErro:
            erro = ErroDeDominio(codigo, "mensagem de teste")
            assert 400 <= erro.status_http <= 599

    def test_conflitos_usam_409(self) -> None:
        for codigo in (
            CodigoErro.LANCAMENTO_DUPLICADO,
            CodigoErro.COMANDA_DUPLICADA,
            CodigoErro.NOME_DUPLICADO,
            CodigoErro.EXCLUSAO_COM_HISTORICO,
        ):
            assert ErroDeDominio(codigo, "x").status_http == 409
