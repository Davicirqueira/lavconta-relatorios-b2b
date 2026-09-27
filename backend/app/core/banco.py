"""Conexão com o banco e sessão por requisição.

FRONTEIRA DE TRANSAÇÃO
    Uma transação por requisição. A dependência ``obter_sessao`` confirma no fim
    do tratamento bem-sucedido e desfaz em qualquer exceção. Assim um lançamento
    e suas linhas nunca ficam parcialmente gravados.

CONEXÃO
    Usamos o Session pooler do Supabase (verificado: a conexão direta só publica
    IPv6). ``pool_pre_ping`` evita usar conexão morta depois de hibernação do
    plano gratuito.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obter_configuracao

_motor = None
_fabrica_de_sessao: sessionmaker[Session] | None = None


def obter_motor():  # noqa: ANN201
    """Motor único da aplicação, criado sob demanda."""
    global _motor  # noqa: PLW0603
    if _motor is None:
        _motor = create_engine(
            obter_configuracao().DATABASE_URL,
            # descarta conexão morta antes de usar: o serviço hiberna
            pool_pre_ping=True,
            # pool pequeno: uso interno, um usuário
            pool_size=5,
            max_overflow=5,
            pool_recycle=1800,
        )
    return _motor


def obter_fabrica_de_sessao() -> sessionmaker[Session]:
    global _fabrica_de_sessao  # noqa: PLW0603
    if _fabrica_de_sessao is None:
        _fabrica_de_sessao = sessionmaker(
            bind=obter_motor(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _fabrica_de_sessao


def reiniciar_conexao() -> None:
    """Descarta motor e fábrica (usado pelos testes)."""
    global _motor, _fabrica_de_sessao  # noqa: PLW0603
    if _motor is not None:
        _motor.dispose()
    _motor = None
    _fabrica_de_sessao = None


def obter_sessao() -> Iterator[Session]:
    """Sessão por requisição, com transação confirmada ou desfeita ao final."""
    with obter_fabrica_de_sessao()() as sessao:
        try:
            yield sessao
            sessao.commit()
        except Exception:
            sessao.rollback()
            raise


SessaoBanco = Annotated[Session, Depends(obter_sessao)]


def nome_da_constraint_violada(erro: IntegrityError) -> str | None:
    """Extrai o nome da constraint de um ``IntegrityError`` do Postgres.

    Permite traduzir a violação em erro de domínio específico em vez de um 500
    genérico. A validação prévia no service dá a mensagem amigável; a constraint
    é a garantia real contra condição de corrida. As duas juntas resolvem.
    """
    diagnostico = getattr(getattr(erro, "orig", None), "diag", None)
    return getattr(diagnostico, "constraint_name", None)
