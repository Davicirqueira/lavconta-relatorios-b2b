"""Testes da configuração (Req 9.2).

Verificam que a aplicação falha ruidosamente na ausência de variável obrigatória,
nomeando a chave, e que nunca cai em default inseguro.
"""

import pytest

from app.core.config import Configuracao, ErroDeConfiguracao, obter_configuracao
from tests.conftest import AMBIENTE_DE_TESTE


class TestConfiguracaoObrigatoria:
    def test_carrega_quando_todas_as_variaveis_existem(self) -> None:
        obter_configuracao.cache_clear()
        configuracao = obter_configuracao()

        assert configuracao.SUPABASE_JWT_AUDIENCE == "authenticated"
        assert configuracao.origens_cors == ["http://localhost:5173"]

    @pytest.mark.parametrize("chave_ausente", list(AMBIENTE_DE_TESTE.keys()))
    def test_falha_nomeando_a_chave_ausente(
        self, ambiente_limpo: pytest.MonkeyPatch, chave_ausente: str
    ) -> None:
        """A ausência de qualquer chave obrigatória impede a aplicação de subir."""
        for chave, valor in AMBIENTE_DE_TESTE.items():
            if chave != chave_ausente:
                ambiente_limpo.setenv(chave, valor)

        with pytest.raises(ErroDeConfiguracao) as excecao:
            obter_configuracao()

        # a mensagem precisa nomear a chave para o diagnóstico ser imediato
        assert chave_ausente in str(excecao.value)

    def test_erro_nao_expoe_valor_de_segredo(self, ambiente_limpo: pytest.MonkeyPatch) -> None:
        """A mensagem de erro cita nomes de chave, nunca valores."""
        segredo = "senha-super-secreta-que-nao-deve-aparecer"
        ambiente_limpo.setenv("DATABASE_URL", segredo)
        # demais chaves ausentes de propósito, para provocar o erro

        with pytest.raises(ErroDeConfiguracao) as excecao:
            obter_configuracao()

        assert segredo not in str(excecao.value)


class TestCorsSemCoringa:
    def test_recusa_coringa_em_cors(self) -> None:
        """Coringa em CORS com credencial é proibido (Req 9.5)."""
        with pytest.raises(ValueError, match=r"\*"):
            Configuracao(
                DATABASE_URL="postgresql+psycopg://u:s@localhost:5432/d",
                SUPABASE_JWKS_URL="https://exemplo.supabase.co/jwks",
                SUPABASE_JWT_ISSUER="https://exemplo.supabase.co/auth/v1",
                SUPABASE_JWT_AUDIENCE="authenticated",
                CORS_ORIGENS="*",
            )

    def test_separa_multiplas_origens(self) -> None:
        configuracao = Configuracao(
            DATABASE_URL="postgresql+psycopg://u:s@localhost:5432/d",
            SUPABASE_JWKS_URL="https://exemplo.supabase.co/jwks",
            SUPABASE_JWT_ISSUER="https://exemplo.supabase.co/auth/v1",
            SUPABASE_JWT_AUDIENCE="authenticated",
            CORS_ORIGENS="http://localhost:5173, https://lavconta.netlify.app",
        )

        assert configuracao.origens_cors == [
            "http://localhost:5173",
            "https://lavconta.netlify.app",
        ]
