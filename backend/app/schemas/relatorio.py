"""Schemas de saída do Relatório de Fechamento

DINHEIRO COMO TEXTO
    Todos os valores monetários saem como string decimal ("395.00"), nunca como
    número float. Isso preserva a precisão decimal no JavaScript do frontend e
    evita discrepâncias de arredondamento.

ESTRUTURA CONFORME CONTRATO DA API (Design §8.2)
    - cliente: identificação básica (id, nome).
    - periodo: data de início e fim no formato YYYY-MM-DD.
    - colunas_itens: lista ordenada de itens presentes no período.
    - linhas: cada lançamento com quantidades em mapa {item_id: quantidade}.
    - totais: fechamento do rodapé da tabela.
    - resumo: cartões de topo da tela (derivado dos mesmos totais).

"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.dominio import Relatorio

# Dinheiro na saída: sempre duas casas decimais como string (ex: "395.00").
DinheiroTexto = Annotated[Decimal, PlainSerializer(lambda valor: f"{valor:.2f}", return_type=str)]


class ClienteIdentificacao(BaseModel):
    """Identificação do cliente no cabeçalho do fechamento"""

    model_config = ConfigDict(frozen=True)
    id: uuid.UUID
    nome: str


class PeriodoResposta(BaseModel):
    """Intervalo de datas do fechamento."""

    model_config = ConfigDict(frozen=True)
    inicio: date
    fim: date


class ColunaDeItemResposta(BaseModel):
    """Coluna de item no fechamento (apenas itens com ocorrência no período)."""

    model_config = ConfigDict(frozen=True)
    item_id: uuid.UUID
    nome: str


class LinhaDoRelatorioResposta(BaseModel):
    """Uma linha da tabela de fechamento correspondente a um lançamento."""

    model_config = ConfigDict(frozen=True)
    lancamento_id: uuid.UUID
    data: date
    comanda: str | None = None
    quantidades: dict[uuid.UUID, int] = Field(
        description="Mapa de item_id -> quantidade. Itens ausentes não entram no mapa."
    )
    total_pecas: int
    total_valor: DinheiroTexto


class TotaisDoRelatorioResposta(BaseModel):
    """Rodapé da tabela de fechamento: soma por item e totais gerais."""

    model_config = ConfigDict(frozen=True)
    por_item: dict[uuid.UUID, int] = Field(
        description="Soma das quantidades no período por item_id."
    )
    total_pecas: int
    total_valor: DinheiroTexto


class ResumoDoRelatorioResposta(BaseModel):
    """Cartões do topo da tela de fechamento."""

    model_config = ConfigDict(frozen=True)
    total_pecas: int
    total_valor: DinheiroTexto
    quantidade_lancamentos: int
    media_diaria_pecas: int


class RelatorioResposta(BaseModel):
    """Contrato completo de resposta do endpoint GET /api/relatorio."""

    model_config = ConfigDict(frozen=True)
    cliente: ClienteIdentificacao
    periodo: PeriodoResposta
    colunas_itens: list[ColunaDeItemResposta]
    linhas: list[LinhaDoRelatorioResposta]
    totais: TotaisDoRelatorioResposta
    resumo: ResumoDoRelatorioResposta

    @classmethod
    def do_dominio(cls, relatorio: Relatorio) -> "RelatorioResposta":
        """Converte o objeto de valor do domínio para o schema de saída da API."""
        return cls(
            cliente=ClienteIdentificacao(
                id=relatorio.cliente_id,
                nome=relatorio.cliente_nome,
            ),
            periodo=PeriodoResposta(
                inicio=relatorio.inicio,
                fim=relatorio.fim,
            ),
            colunas_itens=[
                ColunaDeItemResposta(item_id=col.item_id, nome=col.nome)
                for col in relatorio.colunas_itens
            ],
            linhas=[
                LinhaDoRelatorioResposta(
                    lancamento_id=linha.lancamento_id,
                    data=linha.data,
                    comanda=linha.comanda,
                    quantidades=linha.quantidades,
                    total_pecas=linha.total_pecas,
                    total_valor=linha.total_valor,
                )
                for linha in relatorio.linhas
            ],
            totais=TotaisDoRelatorioResposta(
                por_item=relatorio.totais.por_item,
                total_pecas=relatorio.totais.total_pecas,
                total_valor=relatorio.totais.total_valor,
            ),
            resumo=ResumoDoRelatorioResposta(
                total_pecas=relatorio.resumo.total_pecas,
                total_valor=relatorio.resumo.total_valor,
                quantidade_lancamentos=relatorio.resumo.quantidade_lancamentos,
                media_diaria_pecas=relatorio.resumo.media_diaria_pecas,
            ),
        )
