"""Gera os PDFs com dados do ``lavconta_dev`` e renderiza cada página em PNG.

Uso (na pasta backend):
    .\\.venv\\Scripts\\python.exe -m scripts_dev.visualizar_pdf [pasta_de_saida]

Sem pasta, grava em ``%TEMP%/lavconta-pdf`` (fora do projeto: as imagens não
devem ser versionadas). Serve para a verificação visual (design §6.5): poucos
itens, vários itens, várias páginas, muitos itens e o relatório geral.

"Muitos itens" usa um relatório sintético de 18 itens, porque o seed tem no
máximo 6 itens por cliente. Só leitura no banco; a URL nunca é impressa.
"""

import os
import sys
import tempfile
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from scripts_dev.banco_dev import url_banco_dev

os.environ["DATABASE_URL"] = url_banco_dev()  # antes de qualquer import do app

ESCALA = 1.5  # ~108 dpi: suficiente para conferir layout


def _renderizar(nome: str, conteudo: bytes, pasta: Path) -> None:
    import pypdfium2 as pdfium

    (pasta / f"{nome}.pdf").write_bytes(conteudo)
    documento = pdfium.PdfDocument(conteudo)
    try:
        for indice in range(len(documento)):
            imagem = documento[indice].render(scale=ESCALA).to_pil()
            imagem.save(pasta / f"{nome}-p{indice + 1}.png")
        print(f"  · {nome}: {len(documento)} página(s)")
    finally:
        documento.close()


def _muitos_itens() -> "object":
    from app.dominio import (
        ColunaDeItem,
        LinhaDoRelatorio,
        LinhaResumoItem,
        Relatorio,
        ResumoDoRelatorio,
        TotaisDoRelatorio,
    )

    nomes = [
        "Lençol casal", "Lençol solteiro", "Fronha", "Toalha de banho", "Toalha de rosto",
        "Toalha de piso", "Roupão", "Edredom", "Cobertor", "Colcha", "Travesseiro",
        "Capa de colchão", "Cortina", "Toalha de mesa", "Guardanapo", "Avental",
        "Jaleco", "Uniforme camareira",
    ]  # fmt: skip
    colunas = tuple(ColunaDeItem(uuid.uuid4(), n) for n in nomes)
    valor = Decimal("3.75")
    linhas = tuple(
        LinhaDoRelatorio(
            uuid.uuid4(),
            date(2026, 9, dia),
            str(2000 + dia),
            {c.item_id: 5 + (dia + i) % 20 for i, c in enumerate(colunas)},
            sum(5 + (dia + i) % 20 for i in range(len(colunas))),
            valor * sum(5 + (dia + i) % 20 for i in range(len(colunas))),
        )
        for dia in range(1, 21)
    )
    por_item = {c.item_id: sum(linha.quantidades[c.item_id] for linha in linhas) for c in colunas}
    pecas = sum(por_item.values())
    return Relatorio(
        cliente_id=uuid.uuid4(),
        cliente_nome="Hotel Sintético (18 itens)",
        inicio=date(2026, 9, 1),
        fim=date(2026, 9, 30),
        colunas_itens=colunas,
        linhas=linhas,
        totais=TotaisDoRelatorio(por_item, pecas, valor * pecas),
        resumo=ResumoDoRelatorio(pecas, valor * pecas, len(linhas), pecas // len(linhas)),
        resumo_por_item=tuple(
            LinhaResumoItem(
                c.item_id, c.nome, valor, por_item[c.item_id], valor * por_item[c.item_id]
            )
            for c in colunas
        ),
    )


def main() -> int:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.exports.pdf import gerar_pdf, gerar_pdf_geral
    from app.repositories.cliente_repo import RepositorioCliente
    from app.repositories.lancamento_repo import RepositorioLancamento
    from app.services.servico_relatorio import ServicoRelatorio

    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "lavconta-pdf"
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*.p*"):
        antigo.unlink()

    setembro = (date(2026, 9, 1), date(2026, 9, 30))
    agosto_a_setembro = (date(2026, 8, 1), date(2026, 9, 30))

    with Session(create_engine(url_banco_dev())) as sessao:
        repo_cliente = RepositorioCliente(sessao)
        servico = ServicoRelatorio(RepositorioLancamento(sessao), repo_cliente)

        def cliente(nome: str) -> uuid.UUID:
            encontrado = repo_cliente.buscar_por_nome(nome)
            if encontrado is None:
                raise SystemExit(f"Cliente {nome!r} não está no lavconta_dev (rode preparar_banco)")
            return encontrado.id

        print(f"PDFs em {pasta}")
        _renderizar(
            "poucos-itens",
            gerar_pdf(servico.gerar(cliente("Pousada Vista Verde"), *setembro)),
            pasta,
        )
        _renderizar(
            "aurora-setembro", gerar_pdf(servico.gerar(cliente("Hotel Aurora"), *setembro)), pasta
        )
        _renderizar(
            "varias-paginas",
            gerar_pdf(servico.gerar(cliente("Hotel Aurora"), *agosto_a_setembro)),
            pasta,
        )
        _renderizar("geral-setembro", gerar_pdf_geral(servico.gerar_geral(*setembro)), pasta)
    _renderizar("muitos-itens", gerar_pdf(_muitos_itens()), pasta)  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
