"""Configuração compartilhada dos testes.

Define variáveis de ambiente fictícias antes de qualquer import da aplicação, para
que a configuração valide sem depender de um ``.env`` real. Nenhum valor aqui é
credencial verdadeira.

Também expõe as fixtures de banco usadas pelos testes de constraint, que exigem
Postgres real — recursos como índice único parcial e coluna gerada não existem em
SQLite, então testar em outro banco daria falsa cobertura.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import Connection, Engine, create_engine, text

RAIZ_BACKEND = Path(__file__).resolve().parent.parent

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
    """Isola a configuração: sem variáveis de ambiente e sem ler o arquivo .env.

    Usado pelos testes que verificam a falha na ausência de variável obrigatória.

    Desabilitar o ``env_file`` é essencial: em máquina de desenvolvimento existe
    um ``backend/.env`` preenchido, e sem isso o Pydantic leria os valores dele,
    o erro esperado não aconteceria e o teste passaria a depender de o arquivo
    existir ou não.
    """
    from app.core.config import Configuracao, obter_configuracao

    obter_configuracao.cache_clear()
    monkeypatch.setitem(Configuracao.model_config, "env_file", None)
    for chave in AMBIENTE_DE_TESTE:
        monkeypatch.delenv(chave, raising=False)
    yield monkeypatch
    obter_configuracao.cache_clear()


# ---------------------------------------------------------------------------
# Banco de dados real (Postgres local)
# ---------------------------------------------------------------------------

HOSTS_LOCAIS = ("localhost", "127.0.0.1", "::1")


def _url_do_banco_de_teste() -> str | None:
    """URL do banco local de testes, de ``.env.teste`` ou do ambiente.

    Em CI a variável vem do serviço Postgres do workflow; localmente vem do
    arquivo ``.env.teste`` (não versionado).
    """
    arquivo = RAIZ_BACKEND / ".env.teste"
    if arquivo.exists():
        load_dotenv(arquivo, override=False)

    url = os.environ.get("DATABASE_URL_TESTE", "").strip()
    if not url or "SUA_SENHA" in url:
        return None
    return url


@pytest.fixture(scope="session")
def url_banco_teste() -> str:
    """URL validada do banco de teste.

    Sem banco configurado: pula localmente (conveniência de quem ainda não
    montou o ambiente) ou **falha** quando ``EXIGIR_BANCO_DE_TESTE=1``.

    O CI define essa variável de propósito. Sem ela haveria um ponto cego:
    teste pulado também deixa o CI verde, e a suíte de constraints poderia
    deixar de rodar sem ninguém perceber.
    """
    url = _url_do_banco_de_teste()
    if not url:
        recado = (
            "Banco de teste não configurado. Crie backend/.env.teste a partir de "
            ".env.teste.example (o banco é criado por "
            "scripts/redefinir-senha-postgres-local.ps1)."
        )
        if os.environ.get("EXIGIR_BANCO_DE_TESTE") == "1":
            pytest.fail(
                f"EXIGIR_BANCO_DE_TESTE=1 mas o banco não está acessível. {recado}",
                pytrace=False,
            )
        pytest.skip(recado)

    # TRAVA DE SEGURANÇA: a suíte cria e remove tabelas. Apontar para um host
    # remoto (ex.: Supabase de produção) seria destrutivo.
    if not any(host in url for host in HOSTS_LOCAIS):
        pytest.fail(
            "DATABASE_URL_TESTE aponta para um host que não é local. "
            "Os testes criam e removem tabelas e só podem rodar em banco local."
        )
    return url


@pytest.fixture(scope="session")
def engine_teste(url_banco_teste: str) -> Iterator[Engine]:
    """Engine do banco local com a migração aplicada.

    Aplicar a migração aqui verifica algo que o banco de produção já não pode
    verificar: que ela funciona **a partir do zero**.
    """
    from alembic import command
    from alembic.config import Config

    engine = create_engine(url_banco_teste, pool_pre_ping=True)

    configuracao = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ_BACKEND / "migrations"))
    configuracao.set_main_option("sqlalchemy.url", url_banco_teste)
    command.upgrade(configuracao, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def conexao(engine_teste: Engine) -> Iterator[Connection]:
    """Conexão dentro de uma transação revertida ao final de cada teste.

    Isolamento sem recriar o schema: cada teste vê um banco limpo e nada do que
    ele escreve permanece.
    """
    with engine_teste.connect() as conexao:
        transacao = conexao.begin()
        try:
            yield conexao
        finally:
            transacao.rollback()


# ---------------------------------------------------------------------------
# Auxiliares de domínio para os testes
# ---------------------------------------------------------------------------


def criar_cliente(conexao: Connection, nome: str) -> str:
    return conexao.execute(
        text("insert into clientes (nome) values (:nome) returning id"),
        {"nome": nome},
    ).scalar_one()


def criar_item(conexao: Connection, cliente_id: str, nome: str) -> str:
    return conexao.execute(
        text("insert into itens (cliente_id, nome) values (:cliente, :nome) returning id"),
        {"cliente": cliente_id, "nome": nome},
    ).scalar_one()


def criar_lancamento(
    conexao: Connection, cliente_id: str, data: str, comanda: str | None = None
) -> str:
    return conexao.execute(
        text(
            "insert into lancamentos (cliente_id, data, comanda)"
            " values (:cliente, :data, :comanda) returning id"
        ),
        {"cliente": cliente_id, "data": data, "comanda": comanda},
    ).scalar_one()
