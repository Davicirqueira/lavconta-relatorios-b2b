"""Ambiente de migração do Alembic.

A URL do banco vem de ``app.core.config`` (variável de ambiente), nunca de
string neste arquivo nem no alembic.ini — os dois são versionados.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import obter_configuracao

# importa todos os modelos para que Base.metadata conheça o schema completo
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# injeta a URL da configuração validada
config.set_main_option("sqlalchemy.url", obter_configuracao().DATABASE_URL)


def executar_migracoes_offline() -> None:
    """Gera o SQL sem conectar ao banco (``--sql``).

    Usado para revisar o que será aplicado antes de tocar no banco real.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def executar_migracoes_online() -> None:
    """Aplica as migrações conectando ao banco."""
    conectavel = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with conectavel.connect() as conexao:
        context.configure(
            connection=conexao,
            target_metadata=target_metadata,
            # detecta mudança de tipo e de default na autogeração
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executar_migracoes_offline()
else:
    executar_migracoes_online()
