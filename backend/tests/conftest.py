"""Configuração compartilhada dos testes.

Define variáveis de ambiente fictícias antes de qualquer import da aplicação, para
que a configuração valide sem depender de um ``.env`` real. Nenhum valor aqui é
credencial verdadeira.
"""

import os

import pytest

# Valores fictícios, definidos antes de importar app.* (a configuração é lida na
# importação do main).
AMBIENTE_DE_TESTE = {
    "DATABASE_URL": "postgresql+psycopg://usuario:senha@localhost:5432/lavconta_teste",
    "SUPABASE_JWKS_URL": "https://exemplo.supabase.co/auth/v1/.well-known/jwks.json",
    "SUPABASE_JWT_ISSUER": "https://exemplo.supabase.co/auth/v1",
    "SUPABASE_JWT_AUDIENCE": "authenticated",
    "CORS_ORIGENS": "http://localhost:5173",
}

for chave, valor in AMBIENTE_DE_TESTE.items():
    os.environ.setdefault(chave, valor)


@pytest.fixture
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch):
    """Remove as variáveis de ambiente e o cache da configuração.

    Usado pelos testes que verificam a falha na ausência de variável obrigatória.
    """
    from app.core.config import obter_configuracao

    obter_configuracao.cache_clear()
    for chave in AMBIENTE_DE_TESTE:
        monkeypatch.delenv(chave, raising=False)
    yield monkeypatch
    obter_configuracao.cache_clear()
