"""Relógio de negócio como dependência da API.

O "hoje" que define a partir de quando um preço vale vem daqui, nunca do
cliente HTTP (v1.1, Req 1.2). Ser uma dependência do FastAPI permite que os
testes de API fixem a data (``dependency_overrides``) para provar véspera, dia
e dia seguinte a uma alteração, sem depender da data real da execução.
"""

from datetime import date
from typing import Annotated

from fastapi import Depends

from app.core.datas import hoje_sp


def hoje_de_negocio() -> date:
    """Data de hoje no fuso de São Paulo."""
    return hoje_sp()


HojeDeNegocio = Annotated[date, Depends(hoje_de_negocio)]
