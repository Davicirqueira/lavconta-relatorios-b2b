"""Regra de negócio de Lançamento — o congelamento do valor (Req 5 e 6).

O QUE O CONGELAMENTO É
    A tabela de preços responde "quanto esse item custa agora". O lançamento
    responde "quanto foi cobrado naquele dia". O valor unitário é copiado para a
    linha no momento da criação, e nunca recalculado.

    Isso transforma o lançamento numa afirmação histórica, como um recibo já
    emitido: o cliente confere a relação contra os próprios pedidos e os números
    batem, hoje e daqui a seis meses. É a função central do produto — cobrança
    defensável.

    Se a edição recalculasse pelo preço atual, um relatório de agosto já enviado
    ao cliente poderia exibir outro total em outubro. A fatura deixaria de ser
    auditável.

UMA SÓ IMPLEMENTAÇÃO DE CÁLCULO
    ``_resolver_e_calcular`` é usado por criar, editar e prévia. Duas
    implementações divergiriam, e a divergência apareceria como fatura errada.
"""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import NoReturn

from sqlalchemy.exc import IntegrityError

from app.core.banco import nome_da_constraint_violada
from app.core.datas import hoje_sp, mes_como_texto
from app.core.erros import (
    CodigoErro,
    ErroDeDominio,
    campo_obrigatorio,
    comanda_duplicada,
    data_futura,
    item_duplicado_no_lancamento,
    itens_sem_preco,
    lancamento_duplicado,
    nao_encontrado,
    periodo_invalido,
)
from app.dominio import (
    CalculoDeLancamento,
    LinhaCalculada,
    LinhaSolicitada,
)
from app.models.item import Item
from app.models.lancamento import Lancamento
from app.repositories.lancamento_repo import RepositorioLancamento
from app.repositories.protocolos import (
    RepositorioClienteProtocolo,
    RepositorioItemProtocolo,
)
from app.services.servico_preco import ServicoPreco

CONSTRAINT_CLIENTE_DATA = "uq_lancamentos_cliente_data"
INDICE_COMANDA_UNICA = "ix_lancamentos_comanda_unica_por_cliente"

MESES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def _mes_em_portugues(referencia: date) -> str:
    """Formata o mês para a mensagem ao operador: ``setembro/2026``."""
    return f"{MESES[referencia.month - 1]}/{referencia.year}"


def _data_em_portugues(referencia: date) -> str:
    return referencia.strftime("%d/%m/%Y")


class ServicoLancamento:
    def __init__(
        self,
        repositorio: RepositorioLancamento,
        repositorio_cliente: RepositorioClienteProtocolo,
        repositorio_item: RepositorioItemProtocolo,
        servico_preco: ServicoPreco,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_cliente = repositorio_cliente
        self._repositorio_item = repositorio_item
        self._servico_preco = servico_preco

    # ------------------------------------------------------------------
    # Cálculo compartilhado (tarefa 21)
    # ------------------------------------------------------------------

    def _resolver_e_calcular(
        self,
        cliente_id: uuid.UUID,
        data: date,
        solicitadas: Sequence[LinhaSolicitada],
        *,
        congelados: dict[uuid.UUID, Decimal] | None = None,
    ) -> CalculoDeLancamento:
        """Resolve preços e calcula linhas e totais.

        Args:
            data: data do lançamento. **É ela** que define o mês da resolução,
                nunca a data corrente — senão um lançamento retroativo receberia
                o preço do mês errado (Req 4.7).
            congelados: valores já congelados de linhas preexistentes. Quando
                informado para um item, o preço **não é resolvido de novo**: a
                edição corrige o registro do pedido, não renegocia o preço
                praticado (Req 6.3).

        Não levanta erro por item sem preço: devolve a lista. Quem chama decide.
        """
        congelados = congelados or {}
        item_ids = [linha.item_id for linha in solicitadas]

        # Itens que precisam de resolução: os que ainda não têm valor congelado.
        a_resolver = [item_id for item_id in item_ids if item_id not in congelados]
        resolucao = self._servico_preco.resolver(cliente_id, a_resolver, data)

        linhas: list[LinhaCalculada] = []
        faltantes: list[uuid.UUID] = []

        for solicitada in solicitadas:
            if solicitada.item_id in congelados:
                valor = congelados[solicitada.item_id]
                # linha preexistente: a origem da vigência não é reconsultada
                origem = data.replace(day=1)
            else:
                vigente = resolucao.vigentes.get(solicitada.item_id)
                if vigente is None:
                    faltantes.append(solicitada.item_id)
                    continue
                valor = vigente.valor_unitario
                origem = vigente.vigencia_origem

            # numeric(10,2) × inteiro é exato: não há dízima nem arredondamento
            total = valor * solicitada.quantidade
            linhas.append(
                LinhaCalculada(
                    item_id=solicitada.item_id,
                    quantidade=solicitada.quantidade,
                    valor_unitario=valor,
                    total=total,
                    vigencia_origem=origem,
                )
            )

        return CalculoDeLancamento(
            linhas=tuple(linhas),
            total_pecas=sum(linha.quantidade for linha in linhas),
            total_valor=sum((linha.total for linha in linhas), Decimal("0.00")),
            itens_sem_preco=tuple(faltantes),
        )

    # ------------------------------------------------------------------
    # Criação (tarefa 22)
    # ------------------------------------------------------------------

    def criar(
        self,
        cliente_id: uuid.UUID,
        data: date,
        solicitadas: Sequence[LinhaSolicitada],
        comanda: str | None = None,
    ) -> Lancamento:
        """Cria o lançamento congelando o valor de cada linha.

        Ordem das validações escolhida para dar o erro mais útil primeiro: o que
        depende só da entrada vem antes do que depende de consulta.
        """
        self._exigir_cliente(cliente_id)
        self._validar_data(data)
        comanda_normalizada = self._normalizar_comanda(comanda)
        self._validar_solicitadas(solicitadas)

        itens = self._carregar_itens_do_cliente(cliente_id, solicitadas)

        calculo = self._resolver_e_calcular(cliente_id, data, solicitadas)
        if not calculo.completo:
            nomes = [itens[item_id].nome for item_id in calculo.itens_sem_preco]
            raise itens_sem_preco(nomes, _mes_em_portugues(data))

        # Validação prévia dá mensagem amigável; a constraint é a garantia real
        # contra condição de corrida. As duas juntas resolvem.
        if self._repositorio.buscar_por_cliente_e_data(cliente_id, data) is not None:
            raise lancamento_duplicado(_data_em_portugues(data))
        if (
            comanda_normalizada is not None
            and self._repositorio.buscar_por_comanda(cliente_id, comanda_normalizada) is not None
        ):
            raise comanda_duplicada(comanda_normalizada)

        try:
            lancamento = self._repositorio.inserir(cliente_id, data, comanda_normalizada)
            for linha in calculo.linhas:
                self._repositorio.inserir_linha(
                    lancamento.id,
                    linha.item_id,
                    linha.quantidade,
                    linha.valor_unitario,
                )
            self._repositorio.sincronizar()
        except IntegrityError as erro:
            self._relancar_traduzido(erro, data, comanda_normalizada)

        self._repositorio.recarregar_linhas(lancamento)
        return lancamento

    # ------------------------------------------------------------------
    # Edição (tarefa 23)
    # ------------------------------------------------------------------

    def editar(
        self,
        lancamento_id: uuid.UUID,
        data: date,
        solicitadas: Sequence[LinhaSolicitada],
        comanda: str | None = None,
        cliente_id: uuid.UUID | None = None,
    ) -> Lancamento:
        """Edita um lançamento preservando o congelamento das linhas existentes.

        A DISTINÇÃO QUE IMPORTA
            Linha que já existia mantém o valor unitário original, mesmo que o
            preço tenha mudado desde então: a edição **corrige o registro do
            pedido**, não renegocia o preço praticado (Req 5.18 e 6.3).

            Linha nova é congelada pelo preço vigente no **mês da data do
            lançamento**, não pelo mês corrente (Req 5.19). Um pedido de agosto
            editado em outubro recebe preço de agosto na linha nova, ficando
            coerente com as demais linhas do mesmo pedido.
        """
        lancamento = self.obter(lancamento_id)
        cliente_final = cliente_id or lancamento.cliente_id

        self._exigir_cliente(cliente_final)
        self._validar_data(data)
        comanda_normalizada = self._normalizar_comanda(comanda)
        self._validar_solicitadas(solicitadas)

        itens = self._carregar_itens_do_cliente(cliente_final, solicitadas)

        # Mapa dos valores já congelados, por item. É o que impede o recálculo.
        congelados = {linha.item_id: linha.valor_unitario_congelado for linha in lancamento.linhas}
        # Trocar de cliente invalida o congelado: o preço é por cliente, então o
        # valor anterior não se aplica ao novo.
        if cliente_final != lancamento.cliente_id:
            congelados = {}

        calculo = self._resolver_e_calcular(cliente_final, data, solicitadas, congelados=congelados)
        if not calculo.completo:
            nomes = [itens[item_id].nome for item_id in calculo.itens_sem_preco]
            raise itens_sem_preco(nomes, _mes_em_portugues(data))

        self._validar_unicidade_na_edicao(lancamento, cliente_final, data, comanda_normalizada)

        try:
            lancamento.cliente_id = cliente_final
            lancamento.data = data
            lancamento.comanda = comanda_normalizada

            self._substituir_linhas(lancamento, calculo)
            self._repositorio.sincronizar()
        except IntegrityError as erro:
            self._relancar_traduzido(erro, data, comanda_normalizada)

        # a coleção carregada no início não reflete as linhas inseridas/removidas
        self._repositorio.recarregar_linhas(lancamento)
        return lancamento

    def _substituir_linhas(self, lancamento: Lancamento, calculo: CalculoDeLancamento) -> None:
        """Ajusta as linhas para o conjunto calculado.

        Linha que permanece é **atualizada**, não recriada: recriar perderia o
        valor congelado e a data de criação.
        """
        existentes = {linha.item_id: linha for linha in lancamento.linhas}
        desejados = {linha.item_id for linha in calculo.linhas}

        for item_id, linha in existentes.items():
            if item_id not in desejados:
                self._repositorio.excluir_linha(linha)

        for calculada in calculo.linhas:
            existente = existentes.get(calculada.item_id)
            if existente is None:
                self._repositorio.inserir_linha(
                    lancamento.id,
                    calculada.item_id,
                    calculada.quantidade,
                    calculada.valor_unitario,
                )
            else:
                # só a quantidade muda; o valor congelado permanece
                existente.quantidade = calculada.quantidade

    def _validar_unicidade_na_edicao(
        self,
        lancamento: Lancamento,
        cliente_id: uuid.UUID,
        data: date,
        comanda: str | None,
    ) -> None:
        """Revalida (cliente, data) e comanda, ignorando o próprio registro.

        Sem ignorar a si mesmo, salvar um lançamento sem alterar data acusaria
        conflito com ele próprio (Req 5.20).
        """
        conflito_data = self._repositorio.buscar_por_cliente_e_data(cliente_id, data)
        if conflito_data is not None and conflito_data.id != lancamento.id:
            raise lancamento_duplicado(_data_em_portugues(data))

        if comanda is not None:
            conflito_comanda = self._repositorio.buscar_por_comanda(cliente_id, comanda)
            if conflito_comanda is not None and conflito_comanda.id != lancamento.id:
                raise comanda_duplicada(comanda)

    # ------------------------------------------------------------------
    # Exclusão (tarefa 24)
    # ------------------------------------------------------------------

    def excluir(self, lancamento_id: uuid.UUID) -> None:
        """Exclui o lançamento e suas linhas (Req 5.21 e 5.23).

        A confirmação "Tem certeza?" é responsabilidade da interface (Req 5.22):
        a API não tem como confirmar intenção, e exigir um parâmetro de
        confirmação seria teatro de segurança.
        """
        lancamento = self.obter(lancamento_id)
        self._repositorio.excluir(lancamento)

    # ------------------------------------------------------------------
    # Prévia de totais (tarefa 25)
    # ------------------------------------------------------------------

    def calcular_previa(
        self,
        cliente_id: uuid.UUID,
        data: date,
        solicitadas: Sequence[LinhaSolicitada],
        lancamento_id: uuid.UUID | None = None,
    ) -> CalculoDeLancamento:
        """Calcula totais sem persistir, para a barra de totais da interface.

        TRÊS CARACTERÍSTICAS DELIBERADAS
            **Não persiste nada.** Só leitura de preços e aritmética; pode ser
            chamada a cada pausa na digitação sem efeito colateral.

            **Não falha por item sem preço.** Devolve ``itens_sem_preco`` e
            calcula o total com o resto. Erro no meio da digitação seria hostil;
            a tela usa a lista para avisar em linha. A recusa dura continua no
            salvamento (Req 5.14).

            **Não valida unicidade nem data futura.** Prévia trata de valor;
            conflito é verificado ao salvar.

        Usa o MESMO ``_resolver_e_calcular`` de criar e editar. É o que garante
        que a prévia e o valor salvo não divirjam.

        MODO EDIÇÃO (``lancamento_id``)
            Na edição, linhas que já existiam mantêm o valor congelado. Sem
            saber disso, a prévia resolveria o preço vigente e a barra de
            totais mostraria um valor diferente do que será salvo — a mesma
            divergência que o defeito B1 tinha no relatório. Informando o
            lançamento, a prévia aplica exatamente a regra de ``editar``:
            congelados por item, descartados se o cliente mudou.
        """
        self._exigir_cliente(cliente_id)
        self._validar_solicitadas(solicitadas)
        self._carregar_itens_do_cliente(cliente_id, solicitadas)

        congelados: dict[uuid.UUID, Decimal] | None = None
        if lancamento_id is not None:
            existente = self.obter(lancamento_id)
            # mesma regra de editar: trocar de cliente invalida o congelado
            if existente.cliente_id == cliente_id:
                congelados = {
                    linha.item_id: linha.valor_unitario_congelado for linha in existente.linhas
                }

        return self._resolver_e_calcular(cliente_id, data, solicitadas, congelados=congelados)

    # ------------------------------------------------------------------
    # Validações
    # ------------------------------------------------------------------

    def _exigir_cliente(self, cliente_id: uuid.UUID) -> None:
        """Exige cliente existente.

        Cliente inativo **não** é recusado aqui. Inativar remove da seleção padrão
        (Req 2.8), não proíbe registrar: o mesmo tratamento dado a item inativo,
        que é explicitamente permitido para lançamento retroativo (Req 3.10).
        Quem restringe é a interface, não a regra.
        """
        if self._repositorio_cliente.obter_por_id(cliente_id) is None:
            raise nao_encontrado("Cliente")

    @staticmethod
    def _validar_data(data: date) -> None:
        """Recusa data futura (Req 5.15).

        Compara com "hoje" em America/Sao_Paulo, não no fuso do servidor — que
        roda em UTC e, às 21h em São Paulo, já está no dia seguinte.
        """
        if data > hoje_sp():
            raise data_futura()

    @staticmethod
    def _normalizar_comanda(comanda: str | None) -> str | None:
        """Remove espaços nas pontas; só-espaços vira nulo (Req 5.7 e 5.8).

        Texto vazio no banco colidiria com outro texto vazio no índice único,
        impedindo dois lançamentos "sem comanda". Nulo não colide.
        """
        if comanda is None:
            return None
        limpa = comanda.strip()
        return limpa or None

    @staticmethod
    def _validar_solicitadas(solicitadas: Sequence[LinhaSolicitada]) -> None:
        """Exige ao menos uma linha, quantidade positiva e item sem repetição."""
        if not solicitadas:
            raise campo_obrigatorio("linhas", "Informe ao menos um item no lançamento.")

        for linha in solicitadas:
            if linha.quantidade <= 0:
                raise ErroDeDominio(
                    CodigoErro.VALIDACAO,
                    "A quantidade deve ser um número inteiro positivo.",
                    {"campos": ["quantidade"], "item_id": str(linha.item_id)},
                )

    def _carregar_itens_do_cliente(
        self, cliente_id: uuid.UUID, solicitadas: Sequence[LinhaSolicitada]
    ) -> dict[uuid.UUID, Item]:
        """Carrega os itens, exigindo que pertençam ao cliente e não repitam.

        Uma única passagem serve a três propósitos: detectar item repetido,
        validar a propriedade e obter os nomes para a mensagem de item sem preço.
        """
        itens: dict[uuid.UUID, Item] = {}

        for linha in solicitadas:
            if linha.item_id in itens:
                raise item_duplicado_no_lancamento(itens[linha.item_id].nome)

            item = self._repositorio_item.obter_por_id(linha.item_id)
            if item is None or item.cliente_id != cliente_id:
                raise nao_encontrado("Item")
            itens[linha.item_id] = item

        return itens

    @staticmethod
    def _relancar_traduzido(erro: IntegrityError, data: date, comanda: str | None) -> NoReturn:
        """Traduz violação de constraint em erro de domínio específico."""
        constraint = nome_da_constraint_violada(erro)
        if constraint == CONSTRAINT_CLIENTE_DATA:
            raise lancamento_duplicado(_data_em_portugues(data)) from erro
        if constraint == INDICE_COMANDA_UNICA and comanda is not None:
            raise comanda_duplicada(comanda) from erro
        raise erro

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obter(self, lancamento_id: uuid.UUID) -> Lancamento:
        lancamento = self._repositorio.obter_por_id(lancamento_id)
        if lancamento is None:
            raise nao_encontrado("Lançamento")
        return lancamento

    def listar(self, cliente_id: uuid.UUID, inicio: date, fim: date) -> list[Lancamento]:
        self._exigir_cliente(cliente_id)
        if inicio > fim:
            raise periodo_invalido()
        return self._repositorio.listar_por_periodo(cliente_id, inicio, fim)

    def mes_de_referencia(self, data: date) -> str:
        """Mês usado na resolução de preço, no formato do contrato da API."""
        return mes_como_texto(data)
