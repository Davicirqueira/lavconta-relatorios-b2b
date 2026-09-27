"""Datas de negócio e fuso horário (Req 11).

DUAS COISAS DIFERENTES CHAMADAS "DATA"
    **Data de calendário** é um rótulo, sem hora e sem fuso — "o pedido é do dia
    15/08". É o caso da data do lançamento e da vigência do preço. Tipo ``date``.

    **Instante** é um ponto na linha do tempo global, e tem fuso — "criado em
    19/09 às 14h32". É o caso dos carimbos de auditoria. Tipo ``datetime`` com
    fuso.

    Confundir os dois causa o pior tipo de bug neste produto: um lançamento de
    31/08 escorregando para 01/09 muda o mês de fechamento **e** o preço aplicado,
    porque a vigência é mensal. Um deslize de três horas na virada do mês corrompe
    o valor cobrado.

POR QUE O FUSO É EXPLÍCITO
    O servidor de hospedagem roda em UTC (verificado). Se "hoje" viesse do fuso do
    servidor, às 21h do dia 31 em São Paulo já seria dia 1 do mês seguinte. A
    noção de "hoje" precisa ser do fuso do negócio, não da máquina.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO_NEGOCIO = ZoneInfo("America/Sao_Paulo")


def hoje_sp() -> date:
    """Data corrente no fuso do negócio.

    Única fonte de "hoje" no backend. Usada para recusar lançamento com data
    futura (Req 5.15) e para o período padrão do relatório (Req 7.3).
    """
    return datetime.now(FUSO_NEGOCIO).date()


def agora_sp() -> datetime:
    """Instante corrente no fuso do negócio (para exibição de auditoria)."""
    return datetime.now(FUSO_NEGOCIO)


def primeiro_dia_do_mes(referencia: date) -> date:
    """Normaliza uma data para o primeiro dia do seu mês.

    A vigência de preço é sempre o dia 1 — há ``CHECK`` no banco garantindo isso.
    Normalizar aqui evita depender de o chamador lembrar.
    """
    return referencia.replace(day=1)


def mes_como_texto(referencia: date) -> str:
    """Formata como ``YYYY-MM``, usado no contrato da API."""
    return f"{referencia.year:04d}-{referencia.month:02d}"


def texto_para_mes(texto: str) -> date:
    """Converte ``YYYY-MM`` no primeiro dia daquele mês.

    Raises:
        ValueError: quando o texto não está no formato esperado.
    """
    partes = texto.strip().split("-")
    if len(partes) != 2:
        raise ValueError("Mês deve estar no formato YYYY-MM.")
    try:
        ano, mes = int(partes[0]), int(partes[1])
    except ValueError as erro:
        raise ValueError("Mês deve estar no formato YYYY-MM.") from erro
    if not 1 <= mes <= 12:
        raise ValueError("Mês deve estar entre 01 e 12.")
    if not 2000 <= ano <= 2999:
        raise ValueError("Ano fora da faixa aceita.")
    return date(ano, mes, 1)


def mes_seguinte(referencia: date) -> date:
    """Primeiro dia do mês seguinte ao da referência.

    Serve à sugestão de vigência ao ALTERAR um preço existente: a alteração só
    passa a valer no mês seguinte (Req 4.5 e 4.15).
    """
    primeiro = primeiro_dia_do_mes(referencia)
    if primeiro.month == 12:
        return date(primeiro.year + 1, 1, 1)
    return date(primeiro.year, primeiro.month + 1, 1)
