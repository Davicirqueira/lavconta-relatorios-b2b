"""Banco local de desenvolvimento (``lavconta_dev``).

POR QUE UM BANCO SEPARADO
    O banco ``lavconta_teste`` é da suíte de testes, que exige nomes únicos de
    cliente ("Hotel Aurora" etc.). Dados de visualização ali quebrariam testes
    por conflito. O ``lavconta_dev`` fica no mesmo servidor Postgres local, com
    as mesmas credenciais de ``.env.teste`` — só o nome do banco muda.

SEGURANÇA
    A URL é derivada de ``DATABASE_URL_TESTE`` e recusada se o host não for
    local: estes scripts criam banco e gravam dados, e jamais podem tocar o
    Supabase. A URL (que contém senha) nunca é impressa.
"""

import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
NOME_BANCO_DEV = "lavconta_dev"
HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1"}


class ErroAmbienteDev(RuntimeError):
    """Configuração local ausente ou apontando para fora da máquina."""


def url_banco_dev() -> str:
    """URL do ``lavconta_dev``, validada como local."""
    arquivo = RAIZ_BACKEND / ".env.teste"
    base = os.environ.get("DATABASE_URL_TESTE") or dotenv_values(arquivo).get("DATABASE_URL_TESTE")
    if not base:
        raise ErroAmbienteDev(
            "DATABASE_URL_TESTE não encontrada. Crie backend/.env.teste a partir de "
            ".env.teste.example."
        )

    url = make_url(base)
    if url.host not in HOSTS_LOCAIS:
        raise ErroAmbienteDev(
            "DATABASE_URL_TESTE não aponta para um host local. Os scripts de "
            "desenvolvimento só rodam contra Postgres na própria máquina."
        )
    return url.set(database=NOME_BANCO_DEV).render_as_string(hide_password=False)


def url_banco_administrativo() -> str:
    """Mesma conexão, no banco ``postgres``, para poder criar o ``lavconta_dev``."""
    return make_url(url_banco_dev()).set(database="postgres").render_as_string(hide_password=False)
