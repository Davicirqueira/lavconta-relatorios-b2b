"""Datas de negócio e fuso horário (Req 11).

DUAS COISAS DIFERENTES CHAMADAS "DATA"
    **Data de calendário** é um rótulo, sem hora e sem fuso — "o pedido é do dia
    15/08". É o caso da data do pedido e do início de um preço. Tipo ``date``.

    **Instante** é um ponto na linha do tempo global, e tem fuso — "criado em
    19/09 às 14h32". É o caso dos carimbos de auditoria. Tipo ``datetime`` com
    fuso.

    Confundir os dois causa o pior tipo de bug neste produto: um pedido de 31/08
    escorregando para 01/09 muda o período de fechamento **e** pode mudar o preço
    aplicado, porque o preço é escolhido pela data do pedido.

POR QUE O FUSO É EXPLÍCITO
    O servidor de hospedagem roda em UTC (verificado). Se "hoje" viesse do fuso do
    servidor, às 21h em São Paulo já seria o dia seguinte — e um preço alterado à
    noite começaria a valer um dia depois do combinado. A noção de "hoje" precisa
    ser do fuso do negócio, não da máquina.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO_NEGOCIO = ZoneInfo("America/Sao_Paulo")


def hoje_sp() -> date:
    """Data corrente no fuso do negócio.

    Única fonte de "hoje" no backend. Usada para recusar pedido com data futura
    (Req 5.15), para o período padrão do relatório (Req 7.3) e para o início de
    um preço alterado (v1.1, Req 1.2).
    """
    return datetime.now(FUSO_NEGOCIO).date()


def agora_sp() -> datetime:
    """Instante corrente no fuso do negócio (para exibição de auditoria)."""
    return datetime.now(FUSO_NEGOCIO)
