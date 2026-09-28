"""Objetos de valor do domínio.

Estruturas simples, sem ORM e sem I/O, trocadas entre repositório e serviço
quando uma entidade não é a resposta certa. Ficam separadas dos modelos porque
não representam linha de tabela, e separadas dos schemas porque não são contrato
de API.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PrecoVigente:
    """Preço aplicável a um item num mês de referência.

    ``vigencia_origem`` é o mês em que esse preço foi **definido**, que pode ser
    anterior ao mês consultado — a vigência se propaga até que um novo preço
    exista (Req 4.4).

    Expor a origem dá transparência à regra: o operador vê que o preço de
    setembro veio de junho, em vez de precisar deduzir.
    """

    item_id: uuid.UUID
    valor_unitario: Decimal
    vigencia_origem: date


@dataclass(frozen=True, slots=True)
class SugestaoDeVigencia:
    """Mês a propor na interface ao definir preço, e por quê.

    ``e_primeiro_preco`` vem da consulta ao repositório, não de comparar o mês
    sugerido com o corrente. Derivar por comparação funcionaria hoje e quebraria
    em silêncio se a regra de sugestão mudasse.
    """

    vigencia_mes: date
    e_primeiro_preco: bool


@dataclass(frozen=True, slots=True)
class ResolucaoDePrecos:
    """Resultado de resolver preços para um conjunto de itens.

    Separa explicitamente o que foi resolvido do que **não tem preço**. Quem
    consome decide o que fazer com a ausência: o lançamento recusa (Req 5.14), a
    prévia de totais apenas informa.
    """

    vigentes: dict[uuid.UUID, PrecoVigente]
    sem_preco: tuple[uuid.UUID, ...]

    @property
    def completa(self) -> bool:
        return not self.sem_preco


@dataclass(frozen=True, slots=True)
class LinhaSolicitada:
    """Uma linha como o operador a informa: item e quantidade.

    Nunca traz valor. O preço é resolvido e congelado pelo servidor — aceitar
    valor do cliente seria permitir que o navegador definisse quanto custa.
    """

    item_id: uuid.UUID
    quantidade: int


@dataclass(frozen=True, slots=True)
class LinhaCalculada:
    """Uma linha com o valor já congelado e o total.

    ``valor_unitario`` é o preço vigente no mês da data do lançamento, capturado
    no momento do cálculo. Uma vez gravado, não é recalculado (Req 6.1 a 6.3).
    """

    item_id: uuid.UUID
    quantidade: int
    valor_unitario: Decimal
    total: Decimal
    vigencia_origem: date


@dataclass(frozen=True, slots=True)
class CalculoDeLancamento:
    """Resultado do cálculo, compartilhado por criar, editar e prévia.

    Existe uma só implementação de cálculo no sistema. Se houvesse duas, uma
    divergiria — e a divergência apareceria como fatura errada.

    ``itens_sem_preco`` é devolvido em vez de levantar erro aqui: quem chama
    decide. A criação recusa (Req 5.14); a prévia apenas informa, para não ser
    hostil no meio da digitação.
    """

    linhas: tuple[LinhaCalculada, ...]
    total_pecas: int
    total_valor: Decimal
    itens_sem_preco: tuple[uuid.UUID, ...]

    @property
    def completo(self) -> bool:
        return not self.itens_sem_preco


# ---------------------------------------------------------------------------
# Relatório de fechamento (Req 7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LinhaDeFechamento:
    """Uma linha de lançamento como o banco a devolve para o relatório.

    Estrutura achatada, um registro por (lançamento, item): é o formato natural
    do ``join`` da consulta única do relatório. O serviço agrupa por lançamento.

    ``total`` vem da coluna gerada do banco, não de multiplicação em Python — é o
    mesmo valor que a linha do lançamento sempre teve.
    """

    lancamento_id: uuid.UUID
    data: date
    comanda: str | None
    item_id: uuid.UUID
    item_nome: str
    quantidade: int
    valor_unitario_congelado: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class ColunaDeItem:
    """Uma coluna de tipo de item no relatório.

    Só existe coluna para item com **ocorrência no período** (Req 7.7). Item do
    catálogo que ninguém pediu naquele intervalo não vira coluna vazia.
    """

    item_id: uuid.UUID
    nome: str


@dataclass(frozen=True, slots=True)
class LinhaDoRelatorio:
    """Uma linha do fechamento: um lançamento, com quantidade por item.

    ``quantidades`` é **mapa** de ``item_id``, não lista posicional. Item ausente
    no mapa significa célula vazia (Req 7.8), sem precisar enviar zeros e sem
    risco de desalinhar valores e colunas.
    """

    lancamento_id: uuid.UUID
    data: date
    comanda: str | None
    quantidades: dict[uuid.UUID, int]
    total_pecas: int
    total_valor: Decimal


@dataclass(frozen=True, slots=True)
class TotaisDoRelatorio:
    """Rodapé da tabela: total por item e totais do período (Req 7.11)."""

    por_item: dict[uuid.UUID, int]
    total_pecas: int
    total_valor: Decimal


@dataclass(frozen=True, slots=True)
class ResumoDoRelatorio:
    """Cartões do topo da tela.

    Derivado de ``TotaisDoRelatorio``, nunca recalculado a partir das linhas. É a
    correção estrutural do defeito B1 do protótipo, em que os cartões e o rodapé
    da tabela exibiam totais diferentes.

    ``media_diaria_pecas`` é métrica operacional de exibição: é a única divisão do
    sistema e **não participa de valor cobrado**. Arredondada para inteiro.
    """

    total_pecas: int
    total_valor: Decimal
    quantidade_lancamentos: int
    media_diaria_pecas: int


@dataclass(frozen=True, slots=True)
class Relatorio:
    """Fechamento de um período para um cliente.

    Estrutura única consumida por tela, PDF e Excel. Os módulos de exportação
    **não recalculam nada** — se recalculassem, o documento enviado ao cliente
    poderia divergir do que o operador viu.
    """

    cliente_id: uuid.UUID
    cliente_nome: str
    inicio: date
    fim: date
    colunas_itens: tuple[ColunaDeItem, ...]
    linhas: tuple[LinhaDoRelatorio, ...]
    totais: TotaisDoRelatorio
    resumo: ResumoDoRelatorio

    @property
    def vazio(self) -> bool:
        """Período sem nenhum lançamento (Req 7.13)."""
        return not self.linhas
