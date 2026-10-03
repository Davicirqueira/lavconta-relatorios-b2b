"""Configuração compartilhada dos testes.

Define variáveis de ambiente fictícias antes de qualquer import da aplicação, para
que a configuração valide sem depender de um ``.env`` real. Nenhum valor aqui é
credencial verdadeira.

Também expõe as fixtures de banco usadas pelos testes de constraint, que exigem
Postgres real — recursos como índice único parcial e coluna gerada não existem em
SQLite, então testar em outro banco daria falsa cobertura.
"""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session

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


@pytest.fixture
def sessao(engine_teste: Engine) -> Iterator[Session]:
    """Sessão ORM isolada, mesmo quando o código sob teste faz ``commit``.

    A sessão participa de uma transação externa com
    ``join_transaction_mode="create_savepoint"``: um ``commit`` dentro do
    endpoint libera um savepoint em vez de confirmar a transação externa. Ao
    final, o rollback externo descarta tudo.

    Sem isso, o ``commit`` da dependência de requisição gravaria de verdade e os
    testes de API contaminariam uns aos outros.
    """
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    sessao = Session(
        bind=conexao,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        autoflush=False,
    )
    try:
        yield sessao
    finally:
        sessao.close()
        transacao.rollback()
        conexao.close()


@pytest.fixture(autouse=True)
def _limites_zerados() -> Iterator[None]:
    """Zera os contadores do rate limit a cada teste.

    O limiter guarda os contadores em memória do processo. Sem zerar, a suíte
    inteira (que cria dezenas de itens em segundos) bateria nos 60/min e os
    testes falhariam por 429 conforme a ordem de execução. O limite continua
    ativo: ``test_rate_limit.py`` prova o 429 nas rotas reais.
    """
    from app.core.rate_limit import limiter

    limiter.reset()
    yield


@pytest.fixture
def api(sessao: Session) -> Iterator[TestClient]:
    """Cliente HTTP com o banco de teste e um usuário autenticado fictício.

    Substituímos duas dependências: a sessão, para apontar ao Postgres local em
    vez do Supabase; e a autenticação, porque o que está sob teste aqui é a regra
    de negócio — a validação de JWT tem sua própria suíte.
    """
    from app.core.banco import obter_sessao
    from app.core.seguranca import UsuarioAutenticado, usuario_atual
    from app.main import criar_app

    aplicacao = criar_app()
    aplicacao.dependency_overrides[obter_sessao] = lambda: sessao
    aplicacao.dependency_overrides[usuario_atual] = lambda: UsuarioAutenticado(
        id="00000000-0000-0000-0000-000000000001",
        email="teste@lavconta.local",
        papel="authenticated",
    )
    with TestClient(aplicacao, raise_server_exceptions=False) as cliente:
        yield cliente
    aplicacao.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auxiliares de domínio para os testes
# ---------------------------------------------------------------------------


@contextmanager
def hoje_fixado(api: TestClient, em: str) -> Iterator[None]:
    """Durante o bloco, o "hoje" da API é ``em`` (``YYYY-MM-DD``).

    A API decide o início do preço pelo relógio de negócio (v1.1, Req 1.2). O
    teste fixa esse relógio sobrescrevendo a dependência ``hoje_de_negocio``,
    para montar histórico em datas passadas pelo caminho real da API.
    """
    from app.core.relogio import hoje_de_negocio

    dia = date.fromisoformat(em)
    sobrescritas = api.app.dependency_overrides  # type: ignore[attr-defined]
    anterior = sobrescritas.get(hoje_de_negocio)
    sobrescritas[hoje_de_negocio] = lambda: dia
    try:
        yield
    finally:
        if anterior is None:
            sobrescritas.pop(hoje_de_negocio, None)
        else:
            sobrescritas[hoje_de_negocio] = anterior


def definir_preco(
    api: TestClient,
    item_id: str,
    valor: str,
    *,
    em: str,
    modo: str = "a_partir_de_hoje",
):  # noqa: ANN201
    """Altera o preço pela API como se "hoje" fosse ``em``."""
    with hoje_fixado(api, em):
        return api.put(f"/api/itens/{item_id}/preco", json={"valor_unitario": valor, "modo": modo})


def criar_item_api(
    api: TestClient,
    cliente_id: str,
    nome: str,
    valor: str = "1.00",
    *,
    em: str = "2026-06-01",
):  # noqa: ANN201
    """Cria item com o primeiro preço pela API, como se "hoje" fosse ``em``.

    Devolve a resposta (para testes que verificam status); use ``.json()["id"]``.
    """
    with hoje_fixado(api, em):
        return api.post(
            f"/api/clientes/{cliente_id}/itens", json={"nome": nome, "valor_unitario": valor}
        )


def criar_item_sem_preco(sessao: Session, cliente_id: str, nome: str) -> str:
    """Item sem nenhum preço, gravado direto na sessão do teste.

    Pela API isso não é mais possível (o preço é obrigatório ao criar, Req 3.1);
    o caso continua existindo em dado legado e precisa de cobertura (Req 3.5).
    """
    from app.models.item import Item

    item = Item(cliente_id=uuid.UUID(cliente_id), nome=nome)
    sessao.add(item)
    sessao.flush()
    return str(item.id)


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
