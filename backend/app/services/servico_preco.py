"""Regra de negócio de Preço e resolução da vigência (Req 4).

A REGRA EM UMA FRASE
    O preço definido para um mês vale daquele mês em diante, até que outro seja
    definido.

    Consequência prática: não há redigitação na virada do mês. E alteração feita
    no meio do mês não afeta o mês corrente — ela é registrada com vigência no mês
    seguinte (Req 4.5).

POR QUE A DATA DE REFERÊNCIA É A DO LANÇAMENTO
    A resolução usa o mês da **data do pedido**, nunca a data corrente (Req 4.7).
    Sem isso, um lançamento retroativo — registrado em setembro para um pedido de
    agosto — receberia o preço de setembro e cobraria valor errado.

ITEM SEM PREÇO
    Se nenhum preço existe até o mês de referência, o item é reportado como sem
    preço. Não existe valor zero implícito: cobrar zero por engano é pior que
    recusar a operação (Req 4.8 e 5.14).
"""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import NoReturn

from sqlalchemy.exc import IntegrityError

from app.core.banco import nome_da_constraint_violada
from app.core.datas import mes_seguinte, primeiro_dia_do_mes
from app.core.erros import CodigoErro, ErroDeDominio, nao_encontrado
from app.dominio import PrecoVigente, ResolucaoDePrecos, SugestaoDeVigencia
from app.models.preco import Preco
from app.repositories.protocolos import (
    RepositorioClienteProtocolo,
    RepositorioItemProtocolo,
    RepositorioPrecoProtocolo,
)

CONSTRAINT_UNICA_POR_MES = "uq_precos_cliente_item_mes"
CONSTRAINT_VALOR_POSITIVO = "ck_precos_valor_positivo"
CONSTRAINT_PRIMEIRO_DIA = "ck_precos_vigencia_primeiro_dia"

# Duas casas: padrão monetário, sem fração de centavo (Req 4.12)
CASAS_DECIMAIS = 2


class ServicoPreco:
    def __init__(
        self,
        repositorio: RepositorioPrecoProtocolo,
        repositorio_cliente: RepositorioClienteProtocolo,
        repositorio_item: RepositorioItemProtocolo,
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_cliente = repositorio_cliente
        self._repositorio_item = repositorio_item

    # --- resolução --------------------------------------------------------

    def resolver(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        data_referencia: date,
    ) -> ResolucaoDePrecos:
        """Resolve o preço vigente de cada item na data informada.

        ``data_referencia`` é a data do lançamento. Qualquer dia do mês resolve o
        mesmo preço, porque a vigência é mensal.
        """
        mes = primeiro_dia_do_mes(data_referencia)
        vigentes = self._repositorio.resolver_vigentes(cliente_id, item_ids, mes)

        # preserva a ordem pedida, útil para mensagem de erro previsível
        sem_preco = tuple(item_id for item_id in dict.fromkeys(item_ids) if item_id not in vigentes)
        return ResolucaoDePrecos(vigentes=vigentes, sem_preco=sem_preco)

    def resolver_um(
        self, cliente_id: uuid.UUID, item_id: uuid.UUID, data_referencia: date
    ) -> PrecoVigente | None:
        """Atalho para um único item. Devolve ``None`` quando não há preço."""
        return self.resolver(cliente_id, [item_id], data_referencia).vigentes.get(item_id)

    # --- consulta para a tela de preços -----------------------------------

    def listar_do_mes(
        self, cliente_id: uuid.UUID, mes: date, *, incluir_inativos: bool = False
    ) -> list[tuple[uuid.UUID, str, PrecoVigente | None]]:
        """Itens do cliente com o preço vigente naquele mês.

        Devolve ``None`` no lugar do preço para item sem valor definido, para a
        tela poder destacá-lo: item sem preço **bloqueia lançamento**, então o
        operador precisa ver isso antes de tentar (Req 4.10).
        """
        self._exigir_cliente(cliente_id)
        mes_normalizado = primeiro_dia_do_mes(mes)

        itens = self._repositorio_item.listar_por_cliente(
            cliente_id, incluir_inativos=incluir_inativos
        )
        vigentes = self._repositorio.resolver_vigentes(
            cliente_id, [item.id for item in itens], mes_normalizado
        )
        return [(item.id, item.nome, vigentes.get(item.id)) for item in itens]

    # --- escrita ----------------------------------------------------------

    def definir(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_mes: date,
        valor_unitario: Decimal,
    ) -> Preco:
        """Define ou atualiza o preço de um item para um mês.

        Repetir a mesma combinação (cliente, item, mês) é **atualização**, não
        duplicata (Req 4.2). Permite mês futuro, para programar preço acordado com
        antecedência, e mês passado, para corrigir erro de digitação (Req 4.14 e
        4.17).

        Correção de mês passado **não altera lançamentos já criados** — eles estão
        congelados. Quem chama deve avisar isso ao operador (Req 4.18).
        """
        self._exigir_cliente(cliente_id)
        item = self._exigir_item_do_cliente(cliente_id, item_id)

        valor = self._validar_valor(valor_unitario)
        mes = primeiro_dia_do_mes(vigencia_mes)

        existente = self._repositorio.obter_do_mes(cliente_id, item.id, mes)
        try:
            if existente is not None:
                existente.valor_unitario = valor
                self._repositorio.sincronizar()
                return existente
            return self._repositorio.inserir(cliente_id, item.id, mes, valor)
        except IntegrityError as erro:
            self._relancar_traduzido(erro)

    def vigencia_sugerida(
        self, cliente_id: uuid.UUID, item_id: uuid.UUID, hoje: date
    ) -> SugestaoDeVigencia:
        """Mês de vigência a sugerir na interface.

        **Primeiro** preço de um item: mês corrente, senão o item recém-cadastrado
        não poderia ser lançado hoje — cairia na regra de item sem preço.

        **Alteração** de preço existente: mês seguinte, em coerência com a regra de
        que alteração no meio do mês só passa a valer no mês seguinte.

        (Req 4.15 e 4.16, decisão 18.)
        """
        self._exigir_cliente(cliente_id)
        self._exigir_item_do_cliente(cliente_id, item_id)

        ja_tem_preco = self._repositorio.existe_algum(cliente_id, item_id)
        return SugestaoDeVigencia(
            vigencia_mes=mes_seguinte(hoje) if ja_tem_preco else primeiro_dia_do_mes(hoje),
            e_primeiro_preco=not ja_tem_preco,
        )

    # --- validação --------------------------------------------------------

    @staticmethod
    def _validar_valor(valor: Decimal) -> Decimal:
        """Exige valor positivo com no máximo duas casas decimais."""
        if valor <= 0:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "O preço deve ser maior que zero.",
                {"campos": ["valor_unitario"]},
            )

        expoente = valor.as_tuple().exponent
        if isinstance(expoente, int) and expoente < -CASAS_DECIMAIS:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "O preço deve ter no máximo duas casas decimais.",
                {"campos": ["valor_unitario"]},
            )

        # normaliza para duas casas, para que 4.5 e 4.50 sejam o mesmo valor
        return valor.quantize(Decimal("0.01"))

    def _exigir_cliente(self, cliente_id: uuid.UUID) -> None:
        if self._repositorio_cliente.obter_por_id(cliente_id) is None:
            raise nao_encontrado("Cliente")

    def _exigir_item_do_cliente(self, cliente_id: uuid.UUID, item_id: uuid.UUID):  # noqa: ANN202
        """Garante que o item existe E pertence ao cliente.

        O banco também impede, pela chave estrangeira composta. Aqui a checagem
        existe para devolver 404 com mensagem clara em vez de erro de constraint.
        """
        item = self._repositorio_item.obter_por_id(item_id)
        if item is None or item.cliente_id != cliente_id:
            raise nao_encontrado("Item")
        return item

    @staticmethod
    def _relancar_traduzido(erro: IntegrityError) -> NoReturn:
        constraint = nome_da_constraint_violada(erro)
        if constraint == CONSTRAINT_VALOR_POSITIVO:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "O preço deve ser maior que zero.",
                {"campos": ["valor_unitario"]},
            ) from erro
        if constraint == CONSTRAINT_PRIMEIRO_DIA:
            raise ErroDeDominio(
                CodigoErro.VALIDACAO,
                "A vigência do preço deve ser o primeiro dia do mês.",
                {"campos": ["vigencia_mes"]},
            ) from erro
        raise erro
