"""Regra de negócio de Cliente (Req 2).

Única autoridade sobre as decisões: normalização de nome, unicidade, situação
ativo/inativo e a regra de exclusão em dois níveis. O router só transporta.

EXCLUSÃO EM DOIS NÍVEIS
    Cliente sem lançamento pode ser excluído de verdade, levando catálogo e
    preços (Req 2.10). Cliente com lançamento não pode: o histórico de cobrança
    precisa continuar existindo, e a alternativa é inativar (Req 2.11).

VALIDAÇÃO DUPLA DE UNICIDADE
    Consultamos antes para dar mensagem amigável e traduzimos a violação de
    constraint como rede de segurança. Só a consulta estaria sujeita a condição
    de corrida; só a constraint daria mensagem ruim.
"""

import uuid

from sqlalchemy.exc import IntegrityError

from app.core.banco import nome_da_constraint_violada
from app.core.erros import (
    ErroDeDominio,
    campo_obrigatorio,
    exclusao_com_historico,
    nao_encontrado,
    nome_duplicado,
)
from app.models.cliente import Cliente
from app.repositories.cliente_repo import RepositorioCliente

# Índice único do nome (migração inicial). Usado para traduzir a violação.
INDICE_NOME_UNICO = "ix_clientes_nome_unico"


class ServicoCliente:
    def __init__(self, repositorio: RepositorioCliente) -> None:
        self._repositorio = repositorio

    # --- consultas --------------------------------------------------------

    def listar(self, *, incluir_inativos: bool = False) -> list[Cliente]:
        return self._repositorio.listar(incluir_inativos=incluir_inativos)

    def obter(self, cliente_id: uuid.UUID) -> Cliente:
        cliente = self._repositorio.obter_por_id(cliente_id)
        if cliente is None:
            raise nao_encontrado("Cliente")
        return cliente

    # --- escrita ----------------------------------------------------------

    def criar(self, nome: str) -> Cliente:
        nome_limpo = self._normalizar_nome(nome)

        if self._repositorio.buscar_por_nome(nome_limpo) is not None:
            raise nome_duplicado("cliente", nome_limpo)

        try:
            return self._repositorio.inserir(nome_limpo)
        except IntegrityError as erro:
            raise self._traduzir(erro, nome_limpo) from erro

    def renomear(self, cliente_id: uuid.UUID, nome: str) -> Cliente:
        """Renomeia sem tocar em lançamentos ou valores já registrados (Req 2.3).

        O nome vive só no cadastro; o valor cobrado está congelado na linha do
        lançamento. Por isso renomear é seguro.
        """
        cliente = self.obter(cliente_id)
        nome_limpo = self._normalizar_nome(nome)

        existente = self._repositorio.buscar_por_nome(nome_limpo)
        if existente is not None and existente.id != cliente.id:
            raise nome_duplicado("cliente", nome_limpo)

        cliente.nome = nome_limpo
        try:
            self._repositorio.sincronizar()
        except IntegrityError as erro:
            raise self._traduzir(erro, nome_limpo) from erro
        return cliente

    def inativar(self, cliente_id: uuid.UUID) -> Cliente:
        """Remove da seleção de novos lançamentos, preservando o histórico."""
        cliente = self.obter(cliente_id)
        cliente.ativo = False
        self._repositorio.sincronizar()
        return cliente

    def reativar(self, cliente_id: uuid.UUID) -> Cliente:
        cliente = self.obter(cliente_id)
        cliente.ativo = True
        self._repositorio.sincronizar()
        return cliente

    def excluir(self, cliente_id: uuid.UUID) -> None:
        cliente = self.obter(cliente_id)

        if self._repositorio.tem_lancamentos(cliente.id):
            raise exclusao_com_historico("cliente")

        try:
            self._repositorio.excluir(cliente)
        except IntegrityError as erro:
            # rede de segurança: ON DELETE RESTRICT barra o que a consulta não viu
            raise exclusao_com_historico("cliente") from erro

    # --- apoio ------------------------------------------------------------

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        """Remove espaços nas pontas e recusa nome vazio (Req 2.2)."""
        limpo = (nome or "").strip()
        if not limpo:
            raise campo_obrigatorio("nome", "O nome do cliente é obrigatório.")
        return limpo

    @staticmethod
    def _traduzir(erro: IntegrityError, nome: str) -> ErroDeDominio:
        """Converte violação de constraint em erro de domínio, ou repassa."""
        if nome_da_constraint_violada(erro) == INDICE_NOME_UNICO:
            return nome_duplicado("cliente", nome)
        raise erro
