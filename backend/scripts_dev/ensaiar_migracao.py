"""Ensaio de migração no ``lavconta_dev``: upgrade, check, downgrade, upgrade.

Uso (a partir de ``backend/``)::

    .\\.venv\\Scripts\\python.exe -m scripts_dev.ensaiar_migracao

Só roda contra o banco local de desenvolvimento (``banco_dev`` recusa host
remoto). Imprime contagem e soma de preços antes e depois de cada passo, para
provar que nenhum dado foi perdido. A URL (com senha) nunca é impressa.
"""

import os
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from scripts_dev.banco_dev import RAIZ_BACKEND, url_banco_dev

# app.models importa a configuração da aplicação; aponta para o banco local
# antes de qualquer import do app (variável de ambiente vence o .env)
os.environ["DATABASE_URL"] = url_banco_dev()


def _config() -> Config:
    configuracao = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ_BACKEND / "migrations"))
    configuracao.set_main_option("sqlalchemy.url", url_banco_dev())
    return configuracao


def _retrato(rotulo: str) -> tuple:
    motor = create_engine(url_banco_dev())
    with motor.connect() as conexao:
        versao = conexao.execute(text("select version_num from alembic_version")).scalar_one()
        contagem, soma = conexao.execute(
            text("select count(*), coalesce(sum(valor_unitario), 0) from precos")
        ).one()
        linhas = conexao.execute(
            text("select count(*), coalesce(sum(total), 0) from lancamento_linhas")
        ).one()
    motor.dispose()
    print(f"[{rotulo}] revisão={versao} preços={contagem} soma={soma} linhas={tuple(linhas)}")
    return contagem, soma, tuple(linhas)


def _diferencas_em(tabela: str) -> list:
    """Diferenças entre o modelo ORM e o banco, só na tabela informada."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.models import Base

    motor = create_engine(url_banco_dev())
    with motor.connect() as conexao:
        contexto = MigrationContext.configure(conexao, opts={"compare_type": True})
        diferencas = compare_metadata(contexto, Base.metadata)
    motor.dispose()

    def _da_tabela(diferenca) -> bool:  # noqa: ANN001
        texto = repr(diferenca)
        return f"'{tabela}'" in texto or f"table={tabela}" in texto or f"<{tabela}>" in texto

    return [d for d in diferencas if _da_tabela(d)]


def main() -> int:
    configuracao = _config()
    antes = _retrato("antes")

    command.upgrade(configuracao, "head")
    depois_upgrade = _retrato("upgrade")

    motor = create_engine(url_banco_dev())
    with motor.connect() as conexao:
        divergentes = conexao.execute(
            text("select count(*) from precos where vigencia_inicio <> vigencia_mes")
        ).scalar_one()
    motor.dispose()
    print(f"[upgrade] preços com vigencia_inicio <> vigencia_mes: {divergentes}")

    # Modelo ORM idêntico ao banco na tabela migrada. Restrito a "precos" porque
    # há uma divergência anterior à v1.1 em "clientes" (uq_clientes_id declarada
    # no modelo e na migração inicial, ausente no banco; redundante com a PK).
    diferencas = _diferencas_em("precos")
    print(f"[check] diferenças modelo x banco em precos: {diferencas or 'nenhuma'}")

    command.downgrade(configuracao, "-1")
    depois_downgrade = _retrato("downgrade")

    command.upgrade(configuracao, "head")
    final = _retrato("upgrade de novo")

    iguais = (
        antes == depois_upgrade == depois_downgrade == final and divergentes == 0 and not diferencas
    )
    print("RESULTADO:", "ok" if iguais else "DIVERGÊNCIA")
    return 0 if iguais else 1


if __name__ == "__main__":
    sys.exit(main())
