"""Regra de negócio de Item — catálogo por cliente (Req 3).

ESCOPO DA "FLEXIBILIDADE"
    Cadastrar e editar tipos de item por cliente, e definir seus preços. Nada
    mais: o sistema não oferece campo personalizado arbitrário por lançamento
    (Req 3.5). Essa fronteira é deliberada e foi confirmada com o cliente.

ATIVO E INATIVO
    Item inativo sai da seleção padrão de novos lançamentos, mas continua
    existindo. Isso resolve o efeito colateral de proibir exclusão: sem a
    inativação, o catálogo só cresceria e a lista de seleção ficaria poluída
    com itens que o cliente parou de enviar.

    A situação NÃO afeta relatórios passados: item inativo que ocorreu no
    período continua compondo colunas e totais (Req 3.13).
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
from app.models.item import Item
from app.repositories.cliente_repo import RepositorioCliente
from app.repositories.item_repo import RepositorioItem

INDICE_NOME_UNICO_POR_CLIENTE = "ix_itens_nome_unico_por_cliente"


class ServicoItem:
    def __init__(
        self, repositorio: RepositorioItem, repositorio_cliente: RepositorioCliente
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_cliente = repositorio_cliente

    # --- consultas --------------------------------------------------------

    def listar(self, cliente_id: uuid.UUID, *, incluir_inativos: bool = False) -> list[Item]:
        self._exigir_cliente(cliente_id)
        return self._repositorio.listar_por_cliente(cliente_id, incluir_inativos=incluir_inativos)

    def obter(self, item_id: uuid.UUID) -> Item:
        item = self._repositorio.obter_por_id(item_id)
        if item is None:
            raise nao_encontrado("Item")
        return item

    # --- escrita ----------------------------------------------------------

    def criar(self, cliente_id: uuid.UUID, nome: str) -> Item:
        self._exigir_cliente(cliente_id)
        nome_limpo = self._normalizar_nome(nome)

        if self._repositorio.buscar_por_nome(cliente_id, nome_limpo) is not None:
            raise nome_duplicado("item", nome_limpo)

        try:
            return self._repositorio.inserir(cliente_id, nome_limpo)
        except IntegrityError as erro:
            raise self._traduzir(erro, nome_limpo) from erro

    def renomear(self, item_id: uuid.UUID, nome: str) -> Item:
        """Renomeia sem afetar o valor congelado de lançamentos anteriores.

        O congelamento protege o VALOR, não o rótulo: relatórios passados passam
        a exibir o nome novo, com os valores inalterados (Req 3.3, decisão 14).
        """
        item = self.obter(item_id)
        nome_limpo = self._normalizar_nome(nome)

        existente = self._repositorio.buscar_por_nome(item.cliente_id, nome_limpo)
        if existente is not None and existente.id != item.id:
            raise nome_duplicado("item", nome_limpo)

        item.nome = nome_limpo
        try:
            self._repositorio.sincronizar()
        except IntegrityError as erro:
            raise self._traduzir(erro, nome_limpo) from erro
        return item

    def inativar(self, item_id: uuid.UUID) -> Item:
        item = self.obter(item_id)
        item.ativo = False
        self._repositorio.sincronizar()
        return item

    def reativar(self, item_id: uuid.UUID) -> Item:
        """Reativa sem criar registro duplicado (Req 3.8)."""
        item = self.obter(item_id)
        item.ativo = True
        self._repositorio.sincronizar()
        return item

    def excluir(self, item_id: uuid.UUID) -> None:
        """Exclui apenas item nunca usado; com histórico, sugere inativar."""
        item = self.obter(item_id)

        if self._repositorio.tem_lancamentos(item.id):
            raise exclusao_com_historico("item")

        try:
            self._repositorio.excluir(item)
        except IntegrityError as erro:
            # rede de segurança: ON DELETE RESTRICT barra o que a consulta não viu
            raise exclusao_com_historico("item") from erro

    # --- apoio ------------------------------------------------------------

    def _exigir_cliente(self, cliente_id: uuid.UUID) -> None:
        if self._repositorio_cliente.obter_por_id(cliente_id) is None:
            raise nao_encontrado("Cliente")

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        limpo = (nome or "").strip()
        if not limpo:
            raise campo_obrigatorio("nome", "O nome do item é obrigatório.")
        return limpo

    @staticmethod
    def _traduzir(erro: IntegrityError, nome: str) -> ErroDeDominio:
        if nome_da_constraint_violada(erro) == INDICE_NOME_UNICO_POR_CLIENTE:
            return nome_duplicado("item", nome)
        raise erro
