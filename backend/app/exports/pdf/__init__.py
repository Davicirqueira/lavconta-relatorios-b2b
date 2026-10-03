"""Exportação dos relatórios em PDF (reportlab, A4 paisagem).

- ``estilo``: cores, fontes, formatação e moldura comum das tabelas.
- ``marca``: logo da Lavandix com a proporção real.
- ``pagina``: formato do documento, cabeçalho e rodapé "Página X de Y".
- ``colunas``: larguras e tipografia da tabela por dia (funções puras).
- ``resumo``: tabelas item · por peça · peças · subtotal.
- ``fechamento``: ``gerar_pdf(relatorio)``, por cliente.
- ``geral``: ``gerar_pdf_geral(relatorio_geral)``, todos os clientes.
"""

from app.exports.pdf.estilo import formatar_moeda
from app.exports.pdf.fechamento import gerar_pdf
from app.exports.pdf.geral import gerar_pdf_geral

# Nome antigo, mantido para os consumidores existentes.
_formatar_moeda = formatar_moeda

__all__ = ["formatar_moeda", "gerar_pdf", "gerar_pdf_geral"]
