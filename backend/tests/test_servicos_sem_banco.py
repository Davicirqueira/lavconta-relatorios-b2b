"""Testes de regra de negócio SEM banco de dados.

Usam repositórios em memória que satisfazem os protocolos da camada de dados.
Isso concretiza a justificativa da camada de repositório declarada no design:
a regra fica testável sem I/O.

Complementam, e não substituem, as outras suítes:
  - ``test_constraints.py`` verifica o que só o Postgres garante.
  - ``test_api_*.py`` verifica a pilha completa com banco real.
  - estes verificam a DECISÃO de negócio isolada, rápido e sem infraestrutura.

Também servem de verificação de que os protocolos são satisfazíveis por outra
implementação — se o serviço passar a depender de detalhe do ORM, estes testes
quebram primeiro.
"""

import uuid

import pytest

from app.core.erros import CodigoErro, ErroDeDominio
from app.repositories.protocolos import (
    RepositorioClienteProtocolo,
    RepositorioItemProtocolo,
)
from app.services.servico_cliente import ServicoCliente
from app.services.servico_item import ServicoItem
from tests.repositorios_falsos import RepositorioClienteFalso, RepositorioItemFalso

ID_INEXISTENTE = uuid.UUID("11111111-2222-3333-4444-555555555555")


def codigo(excecao: pytest.ExceptionInfo[ErroDeDominio]) -> str:
    return excecao.value.codigo.value


class TestProtocolosSaoSatisfeitos:
    """Os falsos cumprem o contrato — verificado por tipo em tempo de execução."""

    def test_repositorio_cliente_falso_satisfaz_o_protocolo(self) -> None:
        falso: RepositorioClienteProtocolo = RepositorioClienteFalso()

        assert isinstance(falso, RepositorioClienteFalso)

    def test_repositorio_item_falso_satisfaz_o_protocolo(self) -> None:
        falso: RepositorioItemProtocolo = RepositorioItemFalso()

        assert isinstance(falso, RepositorioItemFalso)


class TestServicoClienteSemBanco:
    @pytest.fixture
    def repositorio(self) -> RepositorioClienteFalso:
        return RepositorioClienteFalso()

    @pytest.fixture
    def servico(self, repositorio: RepositorioClienteFalso) -> ServicoCliente:
        return ServicoCliente(repositorio)

    # --- normalização -----------------------------------------------------

    def test_remove_espacos_nas_pontas(self, servico: ServicoCliente) -> None:
        cliente = servico.criar("   Hotel Aurora   ")

        assert cliente.nome == "Hotel Aurora"

    @pytest.mark.parametrize("entrada", ["", "   ", "\t", "\n  "])
    def test_recusa_nome_em_branco(self, servico: ServicoCliente, entrada: str) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(entrada)

        assert codigo(excecao) == CodigoErro.VALIDACAO.value
        assert excecao.value.detalhes["campos"] == ["nome"]

    # --- unicidade --------------------------------------------------------

    def test_recusa_nome_duplicado_ignorando_caixa(self, servico: ServicoCliente) -> None:
        servico.criar("Hotel Aurora")

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar("HOTEL aurora")

        assert codigo(excecao) == CodigoErro.NOME_DUPLICADO.value

    def test_renomear_permite_manter_o_proprio_nome(self, servico: ServicoCliente) -> None:
        cliente = servico.criar("Hotel Aurora")

        atualizado = servico.renomear(cliente.id, "  Hotel Aurora  ")

        assert atualizado.nome == "Hotel Aurora"

    def test_renomear_recusa_nome_de_outro(self, servico: ServicoCliente) -> None:
        primeiro = servico.criar("Hotel Aurora")
        servico.criar("Pousada Vista Verde")

        with pytest.raises(ErroDeDominio) as excecao:
            servico.renomear(primeiro.id, "pousada vista verde")

        assert codigo(excecao) == CodigoErro.NOME_DUPLICADO.value

    # --- situação ---------------------------------------------------------

    def test_inativar_e_reativar(self, servico: ServicoCliente) -> None:
        cliente = servico.criar("Hotel Aurora")

        assert servico.inativar(cliente.id).ativo is False
        assert servico.reativar(cliente.id).ativo is True

    def test_listagem_oculta_inativos_por_padrao(
        self, servico: ServicoCliente, repositorio: RepositorioClienteFalso
    ) -> None:
        repositorio.semear("Hotel Aurora", ativo=False)
        repositorio.semear("Pousada Vista Verde")

        assert [c.nome for c in servico.listar()] == ["Pousada Vista Verde"]
        assert len(servico.listar(incluir_inativos=True)) == 2

    def test_listagem_em_ordem_alfabetica_ignorando_caixa(
        self, servico: ServicoCliente, repositorio: RepositorioClienteFalso
    ) -> None:
        for nome in ("Toalha Ltda", "aurora", "Bom Prato"):
            repositorio.semear(nome)

        assert [c.nome for c in servico.listar()] == ["aurora", "Bom Prato", "Toalha Ltda"]

    # --- exclusão em dois níveis ------------------------------------------

    def test_exclui_cliente_sem_lancamento(
        self, servico: ServicoCliente, repositorio: RepositorioClienteFalso
    ) -> None:
        cliente = repositorio.semear("Hotel Aurora")

        servico.excluir(cliente.id)

        assert repositorio.registros == {}

    def test_recusa_excluir_cliente_com_lancamento(
        self, servico: ServicoCliente, repositorio: RepositorioClienteFalso
    ) -> None:
        cliente = repositorio.semear("Hotel Aurora", com_lancamento=True)

        with pytest.raises(ErroDeDominio) as excecao:
            servico.excluir(cliente.id)

        assert codigo(excecao) == CodigoErro.EXCLUSAO_COM_HISTORICO.value
        assert "inativ" in excecao.value.mensagem.lower()
        assert cliente.id in repositorio.registros

    # --- não encontrado ---------------------------------------------------

    @pytest.mark.parametrize("operacao", ["obter", "inativar", "reativar", "excluir"])
    def test_404_para_id_inexistente(self, servico: ServicoCliente, operacao: str) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            getattr(servico, operacao)(ID_INEXISTENTE)

        assert codigo(excecao) == CodigoErro.NAO_ENCONTRADO.value


class TestServicoItemSemBanco:
    @pytest.fixture
    def repositorio_cliente(self) -> RepositorioClienteFalso:
        return RepositorioClienteFalso()

    @pytest.fixture
    def repositorio(self) -> RepositorioItemFalso:
        return RepositorioItemFalso()

    @pytest.fixture
    def servico(
        self, repositorio: RepositorioItemFalso, repositorio_cliente: RepositorioClienteFalso
    ) -> ServicoItem:
        return ServicoItem(repositorio, repositorio_cliente)

    @pytest.fixture
    def cliente_id(self, repositorio_cliente: RepositorioClienteFalso) -> uuid.UUID:
        return repositorio_cliente.semear("Hotel Aurora").id

    @pytest.fixture
    def outro_cliente_id(self, repositorio_cliente: RepositorioClienteFalso) -> uuid.UUID:
        return repositorio_cliente.semear("Pousada Vista Verde").id

    # --- vínculo com cliente ----------------------------------------------

    def test_cria_item_vinculado(self, servico: ServicoItem, cliente_id: uuid.UUID) -> None:
        item = servico.criar(cliente_id, "  Lençol  ")

        assert item.nome == "Lençol"
        assert item.cliente_id == cliente_id

    def test_recusa_cliente_inexistente(self, servico: ServicoItem) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(ID_INEXISTENTE, "Lençol")

        assert codigo(excecao) == CodigoErro.NAO_ENCONTRADO.value

    def test_listar_recusa_cliente_inexistente(self, servico: ServicoItem) -> None:
        with pytest.raises(ErroDeDominio) as excecao:
            servico.listar(ID_INEXISTENTE)

        assert codigo(excecao) == CodigoErro.NAO_ENCONTRADO.value

    # --- unicidade por cliente -------------------------------------------

    def test_recusa_duplicado_no_mesmo_cliente(
        self, servico: ServicoItem, cliente_id: uuid.UUID
    ) -> None:
        servico.criar(cliente_id, "Lençol")

        with pytest.raises(ErroDeDominio) as excecao:
            servico.criar(cliente_id, "LENÇOL")

        assert codigo(excecao) == CodigoErro.NOME_DUPLICADO.value

    def test_aceita_mesmo_nome_em_clientes_diferentes(
        self, servico: ServicoItem, cliente_id: uuid.UUID, outro_cliente_id: uuid.UUID
    ) -> None:
        """A unicidade é POR CLIENTE, não global (Req 3.2)."""
        servico.criar(cliente_id, "Lençol")
        item = servico.criar(outro_cliente_id, "Lençol")

        assert item.cliente_id == outro_cliente_id

    def test_renomear_aceita_nome_usado_em_outro_cliente(
        self, servico: ServicoItem, cliente_id: uuid.UUID, outro_cliente_id: uuid.UUID
    ) -> None:
        item = servico.criar(cliente_id, "Toalha")
        servico.criar(outro_cliente_id, "Lençol")

        assert servico.renomear(item.id, "Lençol").nome == "Lençol"

    # --- listagem ---------------------------------------------------------

    def test_lista_apenas_itens_do_cliente(
        self,
        servico: ServicoItem,
        repositorio: RepositorioItemFalso,
        cliente_id: uuid.UUID,
        outro_cliente_id: uuid.UUID,
    ) -> None:
        repositorio.semear(cliente_id, "Lençol")
        repositorio.semear(outro_cliente_id, "Toalha")

        assert [i.nome for i in servico.listar(cliente_id)] == ["Lençol"]

    def test_inclui_inativos_quando_solicitado(
        self, servico: ServicoItem, repositorio: RepositorioItemFalso, cliente_id: uuid.UUID
    ) -> None:
        repositorio.semear(cliente_id, "Tapete", ativo=False)

        assert servico.listar(cliente_id) == []
        assert len(servico.listar(cliente_id, incluir_inativos=True)) == 1

    # --- exclusão em dois níveis ------------------------------------------

    def test_exclui_item_nunca_usado(
        self, servico: ServicoItem, repositorio: RepositorioItemFalso, cliente_id: uuid.UUID
    ) -> None:
        item = repositorio.semear(cliente_id, "Tapete")

        servico.excluir(item.id)

        assert repositorio.registros == {}

    def test_recusa_excluir_item_com_historico(
        self, servico: ServicoItem, repositorio: RepositorioItemFalso, cliente_id: uuid.UUID
    ) -> None:
        item = repositorio.semear(cliente_id, "Lençol", com_lancamento=True)

        with pytest.raises(ErroDeDominio) as excecao:
            servico.excluir(item.id)

        assert codigo(excecao) == CodigoErro.EXCLUSAO_COM_HISTORICO.value
        assert item.id in repositorio.registros
