"""Acesso a dados de Cliente.

Concentra as consultas. Os serviços dependem desta camada, não do ORM
diretamente (engineering.md §1), o que mantém a regra de negócio testável sem
banco e as consultas num só lugar.

Toda consulta é parametrizada pelo SQLAlchemy — nenhuma concatenação de entrada.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.lancamento import Lancamento


class RepositorioCliente:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # --- leitura ----------------------------------------------------------

    def obter_por_id(self, cliente_id: uuid.UUID) -> Cliente | None:
        return self._sessao.get(Cliente, cliente_id)

    def listar(self, *, incluir_inativos: bool = False) -> list[Cliente]:
        """Clientes em ordem alfabética (Req 2.4).

        Ordena por nome normalizado para que a caixa não interfira: "aurora"
        e "Aurora" ficam juntos onde o leitor espera.
        """
        consulta = select(Cliente)
        if not incluir_inativos:
            consulta = consulta.where(Cliente.ativo.is_(True))
        consulta = consulta.order_by(func.lower(Cliente.nome))
        return list(self._sessao.scalars(consulta))

    def buscar_por_nome(self, nome: str) -> Cliente | None:
        """Busca ignorando caixa e espaços nas pontas (espelha o índice único)."""
        consulta = select(Cliente).where(
            func.lower(func.btrim(Cliente.nome)) == nome.strip().lower()
        )
        return self._sessao.scalars(consulta).first()

    def tem_lancamentos(self, cliente_id: uuid.UUID) -> bool:
        """Se há histórico de cobrança vinculado (Req 2.11)."""
        consulta = select(Lancamento.id).where(Lancamento.cliente_id == cliente_id).limit(1)
        return self._sessao.scalars(consulta).first() is not None

    # --- escrita ----------------------------------------------------------

    def inserir(self, nome: str) -> Cliente:
        cliente = Cliente(nome=nome)
        self._sessao.add(cliente)
        self._sessao.flush()  # materializa id e dispara constraints agora
        return cliente

    def excluir(self, cliente: Cliente) -> None:
        self._sessao.delete(cliente)
        self._sessao.flush()

    def sincronizar(self) -> None:
        """Aplica as alterações pendentes, disparando as constraints."""
        self._sessao.flush()
