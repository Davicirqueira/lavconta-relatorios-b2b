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

from app.dominio import LinhaDeFechamento, PrecoVigente
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

    A resolução replica em Python o que o ``DISTINCT ON`` faz no banco: entre os
    preços com vigência até o mês de referência, vence o de vigência mais recente.

    Reimplementar a regra aqui é intencional. Se a consulta SQL e esta versão
    divergirem, os testes contra Postgres em ``test_constraints.py`` e os de API
    acusam — e a divergência aponta defeito em uma das duas.
    """

    def __init__(self) -> None:
        # (cliente_id, item_id, vigencia_mes) -> Preco
        self.registros: dict[tuple[uuid.UUID, uuid.UUID, date], Preco] = {}
        self.sincronizacoes = 0

    # --- apoio para os testes ---------------------------------------------

    def semear(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_mes: date,
        valor: str,
    ) -> Preco:
        return self.inserir(cliente_id, item_id, vigencia_mes, Decimal(valor))

    # --- contrato ---------------------------------------------------------

    def resolver_vigentes(
        self,
        cliente_id: uuid.UUID,
        item_ids: Sequence[uuid.UUID],
        mes_referencia: date,
    ) -> dict[uuid.UUID, PrecoVigente]:
        if not item_ids:
            return {}

        procurados = set(item_ids)
        candidatos: dict[uuid.UUID, Preco] = {}

        for (cli, item, vigencia), preco in self.registros.items():
            if cli != cliente_id or item not in procurados or vigencia > mes_referencia:
                continue
            atual = candidatos.get(item)
            if atual is None or vigencia > atual.vigencia_mes:
                candidatos[item] = preco

        return {
            item_id: PrecoVigente(
                item_id=item_id,
                valor_unitario=preco.valor_unitario,
                vigencia_origem=preco.vigencia_mes,
            )
            for item_id, preco in candidatos.items()
        }

    def obter_do_mes(
        self, cliente_id: uuid.UUID, item_id: uuid.UUID, vigencia_mes: date
    ) -> Preco | None:
        return self.registros.get((cliente_id, item_id, vigencia_mes))

    def existe_algum(self, cliente_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        return any(cli == cliente_id and item == item_id for cli, item, _ in self.registros)

    def inserir(
        self,
        cliente_id: uuid.UUID,
        item_id: uuid.UUID,
        vigencia_mes: date,
        valor_unitario: Decimal,
    ) -> Preco:
        preco = Preco(
            cliente_id=cliente_id,
            item_id=item_id,
            vigencia_mes=vigencia_mes,
            valor_unitario=valor_unitario,
        )
        preco.id = uuid.uuid4()
        self.registros[(cliente_id, item_id, vigencia_mes)] = preco
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
