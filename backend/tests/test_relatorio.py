"""Testes da agregação do relatório de fechamento (tarefa 29).

Rodam **sem banco**, contra repositório em memória: o que está sob teste aqui é a
agregação em Python, não a consulta SQL. A consulta real é exercitada em
``test_api_relatorio.py``, contra Postgres.

O teste mais importante do arquivo é ``test_resumo_e_totais_sempre_coincidem``: é
a regressão direta do defeito B1 do protótipo, em que os cartões do topo e o
rodapé da tabela exibiam totais diferentes no mesmo fechamento.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.erros import CodigoErro, ErroDeDominio
from app.dominio import Relatorio
from app.services.servico_relatorio import ServicoRelatorio
from tests.repositorios_falsos import RepositorioClienteFalso, RepositorioFechamentoFalso

SETEMBRO_INICIO = date(2026, 9, 1)
SETEMBRO_FIM = date(2026, 9, 30)


@pytest.fixture
def fechamento() -> RepositorioFechamentoFalso:
    return RepositorioFechamentoFalso()


@pytest.fixture
def clientes() -> RepositorioClienteFalso:
    repositorio = RepositorioClienteFalso()
    repositorio.semear("Hotel Aurora")
    return repositorio


@pytest.fixture
def cliente_id(clientes: RepositorioClienteFalso) -> uuid.UUID:
    return next(iter(clientes.registros))


@pytest.fixture
def servico(
    fechamento: RepositorioFechamentoFalso, clientes: RepositorioClienteFalso
) -> ServicoRelatorio:
    return ServicoRelatorio(fechamento, clientes)


# ids de item estáveis, para as asserções serem legíveis
LENCOL = uuid.uuid4()
FRONHA = uuid.uuid4()
TOALHA = uuid.uuid4()
ROUPAO = uuid.uuid4()

NOMES = {LENCOL: "Lençol", FRONHA: "Fronha", TOALHA: "Toalha", ROUPAO: "Roupão"}


def semear_lancamento(
    fechamento: RepositorioFechamentoFalso,
    data: date,
    itens: dict[uuid.UUID, tuple[int, str]],
    comanda: str | None = None,
) -> uuid.UUID:
    """Semeia um lançamento com ``item -> (quantidade, valor unitário)``."""
    lancamento_id = uuid.uuid4()
    for item_id, (quantidade, valor) in itens.items():
        fechamento.semear(
            lancamento_id=lancamento_id,
            data=data,
            comanda=comanda,
            item_id=item_id,
            item_nome=NOMES[item_id],
            quantidade=quantidade,
            valor_unitario=valor,
        )
    return lancamento_id


class TestColunasDeItem:
    """Req 7.7 — coluna só para item com ocorrência no período."""

    def test_cria_coluna_apenas_para_item_presente(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50")})
        semear_lancamento(fechamento, date(2026, 9, 2), {FRONHA: (30, "3.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [coluna.item_id for coluna in relatorio.colunas_itens] == [FRONHA, LENCOL]

    def test_item_do_catalogo_sem_ocorrencia_nao_gera_coluna(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """O catálogo tem Roupão, mas ninguém pediu Roupão no período."""
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert ROUPAO not in {coluna.item_id for coluna in relatorio.colunas_itens}
        assert ROUPAO not in relatorio.totais.por_item

    def test_item_fora_do_periodo_nao_gera_coluna(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Item pedido em agosto não vira coluna no fechamento de setembro."""
        semear_lancamento(fechamento, date(2026, 8, 20), {TOALHA: (10, "6.00")})
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [coluna.item_id for coluna in relatorio.colunas_itens] == [LENCOL]

    def test_ordena_ignorando_acento(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """ "Roupão" fica entre Lençol e Toalha, não depois do Z."""
        semear_lancamento(
            fechamento,
            date(2026, 9, 1),
            {TOALHA: (5, "6.00"), ROUPAO: (5, "9.00"), LENCOL: (5, "4.50"), FRONHA: (5, "3.50")},
        )

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [coluna.nome for coluna in relatorio.colunas_itens] == [
            "Fronha",
            "Lençol",
            "Roupão",
            "Toalha",
        ]

    def test_ordem_das_colunas_nao_depende_da_ordem_de_chegada(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Previsibilidade: dois fechamentos iguais saem na mesma ordem."""
        semear_lancamento(fechamento, date(2026, 9, 1), {TOALHA: (5, "6.00")})
        semear_lancamento(fechamento, date(2026, 9, 2), {FRONHA: (5, "3.50")})
        semear_lancamento(fechamento, date(2026, 9, 3), {LENCOL: (5, "4.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [coluna.nome for coluna in relatorio.colunas_itens] == [
            "Fronha",
            "Lençol",
            "Toalha",
        ]


class TestLinhas:
    def test_uma_linha_por_lancamento_com_mapa_de_quantidades(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        semear_lancamento(
            fechamento,
            date(2026, 9, 1),
            {LENCOL: (40, "4.50"), FRONHA: (30, "3.50")},
            comanda="1201",
        )

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert len(relatorio.linhas) == 1
        linha = relatorio.linhas[0]
        assert linha.comanda == "1201"
        assert linha.quantidades == {LENCOL: 40, FRONHA: 30}
        assert linha.total_pecas == 70
        # 40 × 4,50 + 30 × 3,50
        assert linha.total_valor == Decimal("285.00")

    def test_item_ausente_no_lancamento_fica_fora_do_mapa(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Req 7.8 — ausência no mapa é a célula vazia, não um zero."""
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50")})
        semear_lancamento(fechamento, date(2026, 9, 2), {FRONHA: (30, "3.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        primeira, segunda = relatorio.linhas
        assert FRONHA not in primeira.quantidades
        assert LENCOL not in segunda.quantidades

    def test_lancamento_sem_comanda_mantem_a_estrutura(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Req 7.10 — o campo não deixa de existir, só fica sem valor."""
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50")}, comanda="1201")
        semear_lancamento(fechamento, date(2026, 9, 2), {LENCOL: (10, "4.50")}, comanda=None)

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        com_comanda, sem_comanda = relatorio.linhas
        assert com_comanda.comanda == "1201"
        assert sem_comanda.comanda is None
        # mesma estrutura: quantidades, peças e valor presentes nas duas
        assert sem_comanda.quantidades == {LENCOL: 10}
        assert sem_comanda.total_pecas == 10
        assert sem_comanda.total_valor == Decimal("45.00")

    def test_ordena_por_data_crescente(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Req 7.9 — inclusive quando o repositório devolve fora de ordem."""
        for dia in (12, 3, 27, 1):
            semear_lancamento(fechamento, date(2026, 9, dia), {LENCOL: (10, "4.50")})
        # embaralha para provar que a ordenação é do serviço, não da fonte
        fechamento.registros.reverse()

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [linha.data.day for linha in relatorio.linhas] == [1, 3, 12, 27]

    def test_fronteiras_do_periodo_sao_inclusivas(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Primeiro e último dia entram; o dia seguinte ao fim não."""
        semear_lancamento(fechamento, date(2026, 8, 31), {LENCOL: (1, "4.50")})
        semear_lancamento(fechamento, SETEMBRO_INICIO, {LENCOL: (2, "4.50")})
        semear_lancamento(fechamento, SETEMBRO_FIM, {LENCOL: (3, "4.50")})
        semear_lancamento(fechamento, date(2026, 10, 1), {LENCOL: (4, "4.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [linha.total_pecas for linha in relatorio.linhas] == [2, 3]


class TestTotais:
    def test_soma_por_item_e_totais_do_periodo(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        semear_lancamento(
            fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50"), FRONHA: (30, "3.50")}
        )
        semear_lancamento(
            fechamento, date(2026, 9, 3), {LENCOL: (50, "4.50"), FRONHA: (40, "3.50")}
        )

        totais = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM).totais

        assert totais.por_item == {LENCOL: 90, FRONHA: 70}
        assert totais.total_pecas == 160
        # (40+50) × 4,50 + (30+40) × 3,50
        assert totais.total_valor == Decimal("650.00")

    def test_periodo_cruzando_meses_soma_congelados_distintos(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Req 7.12 — cada lançamento entra com o preço do seu mês.

        O mesmo item aparece a 4,50 em agosto e a 4,80 em setembro. O relatório
        soma os dois valores congelados; NÃO reaplica um preço único ao período.
        Reaplicar daria 100 × 4,80 = 480,00 em vez de 465,00.
        """
        semear_lancamento(fechamento, date(2026, 8, 20), {LENCOL: (50, "4.50")})
        semear_lancamento(fechamento, date(2026, 9, 5), {LENCOL: (50, "4.80")})

        relatorio = servico.gerar(cliente_id, date(2026, 8, 1), SETEMBRO_FIM)

        assert relatorio.totais.total_pecas == 100
        assert relatorio.totais.total_valor == Decimal("465.00")
        assert [linha.total_valor for linha in relatorio.linhas] == [
            Decimal("225.00"),
            Decimal("240.00"),
        ]

    def test_total_do_periodo_e_a_soma_das_linhas_exibidas(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """O rodapé tem de ser aritmeticamente a soma do que a tabela mostra."""
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (37, "4.50")})
        semear_lancamento(fechamento, date(2026, 9, 2), {FRONHA: (23, "3.50")})
        semear_lancamento(fechamento, date(2026, 9, 3), {TOALHA: (11, "6.15")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert relatorio.totais.total_valor == sum(linha.total_valor for linha in relatorio.linhas)
        assert relatorio.totais.total_pecas == sum(linha.total_pecas for linha in relatorio.linhas)

    def test_total_por_item_e_a_soma_da_coluna(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50")})
        semear_lancamento(fechamento, date(2026, 9, 2), {LENCOL: (15, "4.50"), FRONHA: (7, "3.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        for coluna in relatorio.colunas_itens:
            esperado = sum(linha.quantidades.get(coluna.item_id, 0) for linha in relatorio.linhas)
            assert relatorio.totais.por_item[coluna.item_id] == esperado


class TestResumo:
    def test_resumo_e_totais_sempre_coincidem(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """Regressão do defeito B1: cartões e rodapé nunca podem divergir."""
        semear_lancamento(
            fechamento, date(2026, 9, 1), {LENCOL: (40, "4.50"), FRONHA: (30, "3.50")}
        )
        semear_lancamento(fechamento, date(2026, 9, 3), {LENCOL: (50, "4.50")})
        semear_lancamento(fechamento, date(2026, 9, 7), {TOALHA: (13, "6.15")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert relatorio.resumo.total_pecas == relatorio.totais.total_pecas
        assert relatorio.resumo.total_valor == relatorio.totais.total_valor

    def test_conta_os_lancamentos(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        for dia in (1, 2, 3):
            semear_lancamento(fechamento, date(2026, 9, dia), {LENCOL: (10, "4.50")})

        resumo = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM).resumo

        assert resumo.quantidade_lancamentos == 3

    def test_media_diaria_de_pecas(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """390 peças em 5 lançamentos → 78 por dia."""
        for dia, quantidade in enumerate((100, 80, 90, 60, 60), start=1):
            semear_lancamento(fechamento, date(2026, 9, dia), {LENCOL: (quantidade, "4.50")})

        resumo = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM).resumo

        assert resumo.total_pecas == 390
        assert resumo.media_diaria_pecas == 78

    def test_media_diaria_arredonda_para_o_inteiro_mais_proximo(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        """5 peças em 2 lançamentos → 2,5 → 3 (metade para cima)."""
        semear_lancamento(fechamento, date(2026, 9, 1), {LENCOL: (2, "4.50")})
        semear_lancamento(fechamento, date(2026, 9, 2), {LENCOL: (3, "4.50")})

        resumo = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM).resumo

        assert resumo.media_diaria_pecas == 3


class TestPeriodoVazio:
    """Req 7.13 — relatório vazio, com totais zerados, e não erro."""

    @pytest.fixture
    def vazio(self, servico: ServicoRelatorio, cliente_id: uuid.UUID) -> Relatorio:
        return servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

    def test_devolve_estrutura_completa(self, vazio: Relatorio) -> None:
        assert vazio.vazio
        assert vazio.linhas == ()
        assert vazio.colunas_itens == ()

    def test_totais_zerados(self, vazio: Relatorio) -> None:
        assert vazio.totais.total_pecas == 0
        assert vazio.totais.total_valor == Decimal("0.00")
        assert vazio.totais.por_item == {}

    def test_resumo_zerado_sem_divisao_por_zero(self, vazio: Relatorio) -> None:
        assert vazio.resumo.quantidade_lancamentos == 0
        assert vazio.resumo.media_diaria_pecas == 0
        assert vazio.resumo.total_valor == Decimal("0.00")

    def test_identifica_cliente_e_periodo(self, vazio: Relatorio) -> None:
        """Mesmo vazio, o documento diz de quem e de quando é."""
        assert vazio.cliente_nome == "Hotel Aurora"
        assert (vazio.inicio, vazio.fim) == (SETEMBRO_INICIO, SETEMBRO_FIM)


class TestValidacoes:
    def test_recusa_periodo_invertido(
        self, servico: ServicoRelatorio, cliente_id: uuid.UUID
    ) -> None:
        with pytest.raises(ErroDeDominio) as capturado:
            servico.gerar(cliente_id, SETEMBRO_FIM, SETEMBRO_INICIO)

        assert capturado.value.codigo == CodigoErro.PERIODO_INVALIDO

    def test_aceita_periodo_de_um_unico_dia(
        self,
        servico: ServicoRelatorio,
        fechamento: RepositorioFechamentoFalso,
        cliente_id: uuid.UUID,
    ) -> None:
        semear_lancamento(fechamento, SETEMBRO_INICIO, {LENCOL: (10, "4.50")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_INICIO)

        assert relatorio.resumo.quantidade_lancamentos == 1

    def test_recusa_cliente_inexistente(self, servico: ServicoRelatorio) -> None:
        with pytest.raises(ErroDeDominio) as capturado:
            servico.gerar(uuid.uuid4(), SETEMBRO_INICIO, SETEMBRO_FIM)

        assert capturado.value.codigo == CodigoErro.NAO_ENCONTRADO


# ---------------------------------------------------------------------------
# v1.1 — resumo por item e relatório geral (Req 5 e 6.4)
# ---------------------------------------------------------------------------


class TestResumoPorItem:
    def test_item_a_dois_valores_sai_em_duas_linhas(
        self, servico: ServicoRelatorio, fechamento: RepositorioFechamentoFalso, cliente_id
    ) -> None:  # noqa: ANN001
        semear_lancamento(
            fechamento, date(2026, 9, 10), {LENCOL: (40, "4.50"), FRONHA: (10, "3.50")}
        )
        semear_lancamento(fechamento, date(2026, 9, 20), {LENCOL: (20, "4.80")})
        semear_lancamento(fechamento, date(2026, 9, 21), {LENCOL: (5, "4.80")})

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [
            (linha.item_nome, linha.valor_unitario, linha.quantidade, linha.subtotal)
            for linha in relatorio.resumo_por_item
        ] == [
            ("Fronha", Decimal("3.50"), 10, Decimal("35.00")),
            ("Lençol", Decimal("4.50"), 40, Decimal("180.00")),
            ("Lençol", Decimal("4.80"), 25, Decimal("120.00")),
        ]

    def test_soma_do_resumo_bate_com_os_totais(
        self, servico: ServicoRelatorio, fechamento: RepositorioFechamentoFalso, cliente_id
    ) -> None:  # noqa: ANN001
        semear_lancamento(
            fechamento, date(2026, 9, 10), {LENCOL: (40, "4.50"), ROUPAO: (3, "9.00")}
        )
        semear_lancamento(
            fechamento, date(2026, 9, 20), {LENCOL: (7, "4.80"), TOALHA: (12, "5.50")}
        )

        relatorio = servico.gerar(cliente_id, SETEMBRO_INICIO, SETEMBRO_FIM)

        assert (
            sum(linha.quantidade for linha in relatorio.resumo_por_item)
            == relatorio.totais.total_pecas
        )
        assert (
            sum((linha.subtotal for linha in relatorio.resumo_por_item), Decimal("0"))
            == relatorio.totais.total_valor
        )


class TestRelatorioGeral:
    def test_uma_secao_por_cliente_em_ordem_alfabetica_sem_acento(
        self, servico: ServicoRelatorio, fechamento: RepositorioFechamentoFalso
    ) -> None:
        fechamento.semear_geral("Restaurante Bom Prato", "Guardanapo", "1.20", 100)
        fechamento.semear_geral("Clínica São Lucas", "Lençol", "4.20", 30)
        fechamento.semear_geral("Hotel Aurora", "Lençol", "4.50", 40)

        geral = servico.gerar_geral(SETEMBRO_INICIO, SETEMBRO_FIM)

        assert [s.cliente_nome for s in geral.secoes] == [
            "Clínica São Lucas",
            "Hotel Aurora",
            "Restaurante Bom Prato",
        ]

    def test_totais_da_secao_e_total_geral(
        self, servico: ServicoRelatorio, fechamento: RepositorioFechamentoFalso
    ) -> None:
        fechamento.semear_geral("Hotel Aurora", "Lençol", "4.50", 40)  # 180,00
        fechamento.semear_geral("Hotel Aurora", "Lençol", "4.80", 25)  # 120,00
        fechamento.semear_geral("Hotel Aurora", "Fronha", "3.50", 10)  # 35,00
        fechamento.semear_geral("Clínica São Lucas", "Avental", "4.00", 5)  # 20,00

        geral = servico.gerar_geral(SETEMBRO_INICIO, SETEMBRO_FIM)
        aurora = next(s for s in geral.secoes if s.cliente_nome == "Hotel Aurora")

        assert [(linha.item_nome, linha.valor_unitario) for linha in aurora.linhas] == [
            ("Fronha", Decimal("3.50")),
            ("Lençol", Decimal("4.50")),
            ("Lençol", Decimal("4.80")),
        ]
        assert (aurora.total_pecas, aurora.total_valor) == (75, Decimal("335.00"))
        assert (geral.total_pecas, geral.total_valor) == (80, Decimal("355.00"))

    def test_periodo_sem_pedidos_fica_vazio(self, servico: ServicoRelatorio) -> None:
        geral = servico.gerar_geral(SETEMBRO_INICIO, SETEMBRO_FIM)

        assert geral.vazio
        assert (geral.total_pecas, geral.total_valor) == (0, Decimal("0.00"))

    def test_periodo_invertido_e_recusado(self, servico: ServicoRelatorio) -> None:
        with pytest.raises(ErroDeDominio) as erro:
            servico.gerar_geral(SETEMBRO_FIM, SETEMBRO_INICIO)

        assert erro.value.codigo == CodigoErro.PERIODO_INVALIDO
