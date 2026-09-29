"""Controle de taxa de requisições (rate limiting) com slowapi.

Protege rotas de escrita e exportação contra abuso (engineering.md §4, design §12).
No free tier do Render, o armazenamento é em memória da instância única.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
