"""Base declarativa e colunas comuns dos modelos.

Convenção de nomes de constraint definida explicitamente para que o Alembic gere
nomes estáveis e previsíveis — sem isso, renomear uma constraint em migração
futura fica arriscado porque o nome gerado pelo banco pode variar.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Uuid, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CONVENCAO_DE_NOMES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_DE_NOMES)


class IdentificadorMixin:
    """Chave primária UUID gerada pelo banco.

    UUID em vez de sequencial: o identificador aparece em URL da aplicação e o
    UUID não permite inferir volume de registros nem enumerar recursos.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class AuditoriaMixin:
    """Carimbos de auditoria.

    São instantes reais, portanto ``timestamptz`` — diferente da data de negócio
    do lançamento, que é data de calendário sem fuso (Req 11.1 e 11.8).
    """

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
