"""Repositórios em memória que satisfazem os protocolos da camada de dados.

Permitem testar a regra de negócio **sem banco**: rápido, sem I/O, e falha por
defeito de regra em vez de por indisponibilidade de infraestrutura.

Funciona porque modelo declarativo do SQLAlchemy pode ser instanciado sem sessão.
O que o falso emula é apenas o contrato: busca por nome normalizado, presença de
histórico e atribuição de identificador na inserção.

Não substituem os testes contra Postgres: constraint, índice parcial e coluna
gerada só existem no banco real e têm suíte própria em ``test_constraints.py``.
"""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from app.dominio import LinhaDeFechamento, LinhaDoResumoGeral, PrecoVigente
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.lancamento import Lancamento, LancamentoLinha
from app.models.preco import Preco


def _normalizar(nome: str) -> str:
    """Espelha o que o índice único faz: lower(btrim(nome))."""
    return nome.strip().lower()


class RepositorioClienteFalso:
    """Emula ``RepositorioClienteProtocolo`` em memória."""

    def __init__(self) -> None:
        self.registros: dict[uuid.UUID, Cliente] = {}
        # ids marcados como tendo histórico de cobrança
        self.com_lancamentos: set[uuid.UUID] = set()
        self.sincronizacoes = 0

    # --- apoio para os testes ---------------------------------------------

    def semear(self, nome: str, *, ativo: bool = True, com_lancamento: bool = False) -> Cliente:
        cliente = Cliente(nome=nome, ativo=ativo)
        cliente.id = uuid.uuid4()
        self.registros[cliente.id] = cliente
        if com_lancamento:
            self.com_lancamentos.add(cliente.id)
        return cliente

    # --- contrato ---------------------------------------------------------

    def obter_por_id(self, cliente_id: uuid.UUID) -> Cliente | None:
        return self.registros.get(cliente_id)

    def listar(self, *, incluir_inativos: bool = False) -> list[Cliente]:
        clientes = [
            cliente for cliente in self.registros.values() if incluir_inativos or cliente.ativo
        ]
        return sorted(clientes, key=lambda cliente: cliente.nome.lower())

    def buscar_por_nome(self, nome: str) -> Cliente | None:
        alvo = _normalizar(nome)
        for cliente in self.registros.values():
            if _normalizar(cliente.nome) == alvo:
                return cliente
        return None

    def tem_lancamentos(self, cliente_id: uuid.UUID) -> bool:
        return cliente_id in self.com_lancamentos

    def inserir(self, nome: str) -> Cliente:
        cliente = Cliente(nome=nome, ativo=True)
        cliente.id = uuid.uuid4()
        self.registros[cliente.id] = cliente
        return cliente

    def excluir(self, cliente: Cliente) -> None:
        self.registros.pop(cliente.id, None)

    def sincronizar(self) -> None:
        self.sincronizacoes += 1


class RepositorioItemFalso:
    """Emula ``RepositorioItemProtocolo`` em memória."""

    def __init__(self) -> None:
        self.registros: dict[uuid.UUID, Item] = {}
        self.com_lancamentos: set[uuid.UUID] = set()
        self.sincronizacoes = 0

    # --- apoio para os testes ---------------------------------------------

    def semear(
        self,
        cliente_id: uuid.UUID,
        nome: str,
        *,
        ativo: bool = True,
        com_lancamento: bool = False,
    ) -> Item:
        item = Item(cliente_id=cliente_id, nome=nome, ativo=ativo)
        item.id = uuid.uuid4()
        self.registros[item.id] = item
        if com_lancamento:
            self.com_lancamentos.add(item.id)
        return item

    # --- contrato ---------------------------------------------------------

    def obter_por_id(self, item_id: uuid.UUID) -> Item | None:
        return self.registros.get(item_id)

    def listar_por_cliente(
        self, cliente_id: uuid.UUID, *, incluir_inativos: bool = False
    ) -> list[Item]:
        itens = [
            item
            for item in self.registros.values()
            if item.cliente_id == cliente_id and (incluir_inativos or item.ativo)
        ]
        return sorted(itens, key=lambda item: item.nome.lower())

    def buscar_por_nome(self, cliente_id: uuid.UUID, nome: str) -> Item | None:
        alvo = _normalizar(nome)
        for item in self.registros.values():
            if item.cliente_id == cliente_id and _normalizar(item.nome) == alvo:
                return item
        return None

    def tem_lancamentos(self, item_id: uuid.UUID) -> bool:
        return item_id in self.com_lancamentos

    def inserir(self, cliente_id: uuid.UUID, nome: str) -> Item:
        item = Item(cliente_id=cliente_id, nome=nome, ativo=True)
        item.id = uuid.uuid4()
        self.registros[item.id] = item
        return item

    def excluir(self, item: Item) -> None:
        self.registros.pop(item.id, None)

    def sincronizar(self) -> None:
        self.sincronizacoes += 1


class RepositorioPrecoFalso:
    """Emula ``RepositorioPrecoProtocolo`` em memória.

    A resolução replica em Python a regra da consulta SQL (``preco_repo``):

    1. entre os preços com início até a data, o de início mais recente;
    2. se não houver, o de início mais antigo (o primeiro vale para trás);
    3. sem nenhum preço: ausente do retorno.

    Reimplementar a regra aqui é intencional. Se a consulta SQL e esta versão
    divergirem, os testes de API contra Postgres acusam — e a divergência aponta
    defeito em uma das duas.

    ``pedidos`` simula as linhas de pedido gravadas, só para
    ``contar_pedidos_afetados``.
    """

    def __init__(self) -> None:
        # (cliente_id, item_id, vigencia_inicio) -> Preco
        self.registros: dict[tuple[uuid.UUID, uuid.UUID, date], Preco] = {}
        # (lancamento_id, cliente_id, item_id, data, valor congelado)
        self.pedidos: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID, date, Decimal]] = []
        self.sincronizacoes = 0

    # --- apoio para os testes ---------------------------------------------

    def semear(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_inicio: date,
        valor: str,
    ) -> Preco:
        return self.inserir(cliente_id, item_id, vigencia_inicio, Decimal(valor))

    def semear_pedido(
        self, cliente_id: uuid.UUID, item_id: uuid.UUID, data: date, valor: str
    ) -> uuid.UUID:
        lancamento_id = uuid.uuid4()
        self.pedidos.append((lancamento_id, cliente_id, item_id, data, Decimal(valor)))
        return lancamento_id

    # --- contrato ---------------------------------------------------------

    def _escolher(self, cliente_id: uuid.UUID, item_id: uuid.UUID, data: date) -> Preco | None:
        do_item = [
            preco
            for (cli, item, _), preco in self.registros.items()
            if cli == cliente_id and item == item_id
        ]
        if not do_item:
            return None
        vigentes = [p for p in do_item if p.vigencia_inicio <= data]
        if vigentes:
            return max(vigentes, key=lambda p: p.vigencia_inicio)
        return min(do_item, key=lambda p: p.vigencia_inicio)

    def resolver_vigentes(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        data: date,
    ) -> dict[uuid.UUID, PrecoVigente]:
        resultado: dict[uuid.UUID, PrecoVigente] = {}
        for item_id in dict.fromkeys(item_ids):
            preco = self._escolher(cliente_id, item_id, data)
            if preco is not None:
                resultado[item_id] = PrecoVigente(
                    item_id=item_id,
                    valor_unitario=preco.valor_unitario,
                    desde=preco.vigencia_inicio,
                )
        return resultado

    def obter_vigente(self, cliente_id: uuid.UUID, item_id: uuid.UUID, data: date) -> Preco | None:
        return self._escolher(cliente_id, item_id, data)

    def obter_no_dia(self, cliente_id: uuid.UUID, item_id: uuid.UUID, dia: date) -> Preco | None:
        return self.registros.get((cliente_id, item_id, dia))

    def inicios(self, cliente_id: uuid.UUID, item_id: uuid.UUID) -> list[date]:
        return sorted(
            inicio for cli, item, inicio in self.registros if cli == cliente_id and item == item_id
        )

    def contar_pedidos_afetados(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        *,
        desde: date | None,
        ate_exclusivo: date | None,
        valor_diferente_de: Decimal,
    ) -> int:
        return len(
            {
                lancamento
                for lancamento, cli, item, data, valor in self.pedidos
                if cli == cliente_id
                and item == item_id
                and valor != valor_diferente_de
                and (desde is None or data >= desde)
                and (ate_exclusivo is None or data < ate_exclusivo)
            }
        )

    def inserir(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_inicio: date,
        valor_unitario: Decimal,
    ) -> Preco:
        chave = (cliente_id, item_id, vigencia_inicio)
        if chave in self.registros:
            # espelha uq_precos_cliente_item_inicio: o serviço nunca deve chegar aqui
            raise AssertionError(f"preço duplicado no mesmo dia: {chave}")
        preco = Preco(
            cliente_id=cliente_id,
            item_id=item_id,
            vigencia_inicio=vigencia_inicio,
            valor_unitario=valor_unitario,
        )
        preco.id = uuid.uuid4()
        self.registros[chave] = preco
        return preco

    def sincronizar(self) -> None:
        self.sincronizacoes += 1


class RepositorioLancamentoFalso:
    """Emula o repositório de lançamento em memória.

    Emula também as duas regras de unicidade que no banco são constraints, para
    que o serviço possa ser testado sem Postgres. A garantia real continua sendo
    a do banco, verificada em ``test_constraints.py``.
    """

    def __init__(self) -> None:
        self.registros: dict[uuid.UUID, Lancamento] = {}
        self.linhas: dict[uuid.UUID, list[LancamentoLinha]] = {}
        self.sincronizacoes = 0

    # --- contrato ---------------------------------------------------------

    def obter_por_id(self, lancamento_id: uuid.UUID) -> Lancamento | None:
        lancamento = self.registros.get(lancamento_id)
        if lancamento is not None:
            # emula o carregamento das linhas
            lancamento.linhas = self.linhas.get(lancamento_id, [])
        return lancamento

    def buscar_por_cliente_e_data(self, cliente_id: uuid.UUID, data: date) -> Lancamento | None:
        for lancamento in self.registros.values():
            if lancamento.cliente_id == cliente_id and lancamento.data == data:
                return lancamento
        return None

    def buscar_por_comanda(self, cliente_id: uuid.UUID, comanda: str) -> Lancamento | None:
        alvo = _normalizar(comanda)
        for lancamento in self.registros.values():
            if (
                lancamento.cliente_id == cliente_id
                and lancamento.comanda is not None
                and _normalizar(lancamento.comanda) == alvo
            ):
                return lancamento
        return None

    def listar_por_periodo(
        self, cliente_id: uuid.UUID, inicio: date, fim: date
    ) -> list[Lancamento]:
        encontrados = [
            self.obter_por_id(lancamento.id)
            for lancamento in self.registros.values()
            if lancamento.cliente_id == cliente_id and inicio <= lancamento.data <= fim
        ]
        return sorted(
            [lancamento for lancamento in encontrados if lancamento is not None],
            key=lambda lancamento: lancamento.data,
        )

    def inserir(self, cliente_id: uuid.UUID, data: date, comanda: str | None) -> Lancamento:
        lancamento = Lancamento(cliente_id=cliente_id, data=data, comanda=comanda)
        lancamento.id = uuid.uuid4()
        lancamento.linhas = []
        self.registros[lancamento.id] = lancamento
        self.linhas[lancamento.id] = []
        return lancamento

    def inserir_linha(
        self,
        lancamento_id: uuid.UUID,
        item_id: uuid.UUID,
        quantidade: int,
        valor_unitario_congelado: Decimal,
    ) -> LancamentoLinha:
        linha = LancamentoLinha(
            lancamento_id=lancamento_id,
            item_id=item_id,
            quantidade=quantidade,
            valor_unitario_congelado=valor_unitario_congelado,
        )
        linha.id = uuid.uuid4()
        self.linhas.setdefault(lancamento_id, []).append(linha)
        self._recalcular_totais()
        return linha

    def excluir_linha(self, linha: LancamentoLinha) -> None:
        for lista in self.linhas.values():
            if linha in lista:
                lista.remove(linha)

    def excluir(self, lancamento: Lancamento) -> None:
        self.registros.pop(lancamento.id, None)
        self.linhas.pop(lancamento.id, None)

    def recarregar_linhas(self, lancamento: Lancamento) -> None:
        """Reassocia a lista de linhas, como o refresh do ORM faria."""
        lancamento.linhas = self.linhas.get(lancamento.id, [])

    def sincronizar(self) -> None:
        self.sincronizacoes += 1
        self._recalcular_totais()

    def _recalcular_totais(self) -> None:
        """Emula a coluna gerada ``total`` do banco.

        No Postgres, ``total`` é ``GENERATED ALWAYS AS (valor × quantidade)`` e o
        servidor o recalcula a cada escrita. O serviço nunca grava esse campo — e
        não deve, porque em produção o banco recusaria.

        Sem este recálculo o falso divergiria do banco justamente na edição de
        quantidade, dando falso negativo.
        """
        for lista in self.linhas.values():
            for linha in lista:
                linha.total = linha.valor_unitario_congelado * linha.quantidade


class RepositorioFechamentoFalso:
    """Emula ``RepositorioFechamentoProtocolo`` em memória.

    Devolve linhas achatadas (lançamento × item), como o ``join`` da consulta
    real. O que está sob teste com este falso é a **agregação em Python** —
    colunas presentes, mapa de quantidades, coincidência entre ``totais`` e
    ``resumo`` — que não depende de recurso de banco.

    O SQL de verdade tem cobertura própria em ``test_api_relatorio.py``, contra
    Postgres. Sem aquela suíte, este falso daria cobertura ilusória da consulta.
    """

    def __init__(self) -> None:
        self.registros: list[LinhaDeFechamento] = []
        self.geral: list[LinhaDoResumoGeral] = []
        self._ids: dict[str, uuid.UUID] = {}

    # --- apoio para os testes ---------------------------------------------

    def semear(
        self,
        lancamento_id: uuid.UUID,
        data: date,
        comanda: str | None,
        item_id: uuid.UUID,
        item_nome: str,
        quantidade: int,
        valor_unitario: str,
    ) -> LinhaDeFechamento:
        valor = Decimal(valor_unitario)
        registro = LinhaDeFechamento(
            lancamento_id=lancamento_id,
            data=data,
            comanda=comanda,
            item_id=item_id,
            item_nome=item_nome,
            quantidade=quantidade,
            valor_unitario_congelado=valor,
            # emula a coluna gerada do banco
            total=valor * quantidade,
        )
        self.registros.append(registro)
        return registro

    # --- contrato ---------------------------------------------------------

    def buscar_linhas_do_periodo(
        self, cliente_id: uuid.UUID, inicio: date, fim: date
    ) -> list[LinhaDeFechamento]:
        del cliente_id  # o falso guarda os registros de um cliente só
        encontrados = [registro for registro in self.registros if inicio <= registro.data <= fim]
        return sorted(encontrados, key=lambda registro: (registro.data, registro.item_nome))

    def buscar_resumo_geral(self, inicio: date, fim: date) -> list[LinhaDoResumoGeral]:
        """Devolve as linhas já agrupadas semeadas com ``semear_geral``.

        O agrupamento em SQL (``GROUP BY``) é coberto contra Postgres em
        ``test_api_relatorio_geral.py``; aqui está sob teste a montagem das seções.
        """
        del inicio, fim
        return list(self.geral)

    def semear_geral(
        self,
        cliente_nome: str,
        item_nome: str,
        valor: str,
        quantidade: int,
        *,
        cliente_id: uuid.UUID | None = None,
    ) -> LinhaDoResumoGeral:
        unitario = Decimal(valor)
        linha = LinhaDoResumoGeral(
            cliente_id=cliente_id or self._ids.setdefault(cliente_nome, uuid.uuid4()),
            cliente_nome=cliente_nome,
            item_id=self._ids.setdefault(f"{cliente_nome}/{item_nome}", uuid.uuid4()),
            item_nome=item_nome,
            valor_unitario=unitario,
            quantidade=quantidade,
            subtotal=unitario * quantidade,
        )
        self.geral.append(linha)
        return linha
