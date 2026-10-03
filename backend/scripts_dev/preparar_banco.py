"""Cria o ``lavconta_dev``, aplica as migrações e popula dados fictícios.

Uso (na pasta backend):
    .\\.venv\\Scripts\\python.exe -m scripts_dev.preparar_banco
    .\\.venv\\Scripts\\python.exe -m scripts_dev.preparar_banco --recriar

Sem ``--recriar``: só popula se o banco estiver sem clientes (seguro repetir).
Com ``--recriar``: apaga e recria o ``lavconta_dev`` do zero. Afeta apenas esse
banco local — a trava de host em ``banco_dev`` impede apontar para fora.

OS DADOS PASSAM PELAS REGRAS DE NEGÓCIO
    Clientes, itens, preços e lançamentos são criados pelos serviços da
    aplicação, não por SQL direto. Assim o valor congelado de cada lançamento é
    o que o sistema calcularia de verdade, e o relatório exibido é coerente.

Todos os nomes são fictícios (sugeridos em prototipo/regras-interface.md).
"""

import argparse
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from scripts_dev.banco_dev import (
    NOME_BANCO_DEV,
    RAIZ_BACKEND,
    url_banco_administrativo,
    url_banco_dev,
)

# --------------------------------------------------------------------------
# Dados fictícios
# --------------------------------------------------------------------------

JUNHO = date(2026, 6, 1)
# meio do mês de propósito: exercita a regra v1.1 (preço vale a partir do dia)
REAJUSTE_EM = date(2026, 9, 15)

# cliente -> itens (nome, preço desde junho ou None para "sem preço")
CATALOGOS: dict[str, list[tuple[str, str | None]]] = {
    "Hotel Aurora": [
        ("Lençol", "4.50"),
        ("Fronha", "3.50"),
        ("Toalha de banho", "5.50"),
        ("Toalha de rosto", "2.80"),
        ("Roupão", "9.00"),
        ("Tapete", "7.00"),
        # sem preço de propósito: mostra o "Sem preço" no catálogo e no pedido
        ("Edredom", None),
    ],
    "Restaurante Bom Prato": [
        ("Toalha de mesa", "6.00"),
        ("Guardanapo", "1.20"),
        ("Avental", "3.80"),
    ],
    "Clínica São Lucas": [
        ("Lençol", "4.20"),
        ("Fronha", "3.30"),
        ("Avental", "4.00"),
    ],
    "Pousada Vista Verde": [
        ("Lençol", "4.60"),
        ("Toalha de banho", "5.80"),
    ],
}

# reajuste em 15/09: pedidos até 14/09 e a partir de 15/09 ficam com valores
# congelados diferentes para o mesmo item, dentro do mesmo mês
REAJUSTES = {("Hotel Aurora", "Lençol"): (REAJUSTE_EM, "4.80")}

# faixa de quantidade por item, por pedido
FAIXAS: dict[str, tuple[int, int]] = {
    "Lençol": (25, 60),
    "Fronha": (20, 50),
    "Toalha de banho": (15, 45),
    "Toalha de rosto": (10, 30),
    "Roupão": (2, 10),
    "Tapete": (2, 6),
    "Toalha de mesa": (10, 30),
    "Guardanapo": (40, 120),
    "Avental": (5, 15),
}

INICIO_HISTORICO = date(2026, 8, 1)


def _log(mensagem: str) -> None:
    print(f"  · {mensagem}")


# --------------------------------------------------------------------------
# Banco
# --------------------------------------------------------------------------


def criar_banco(recriar: bool) -> None:
    motor = create_engine(url_banco_administrativo(), isolation_level="AUTOCOMMIT")
    with motor.connect() as conexao:
        existe = conexao.execute(
            text("select 1 from pg_database where datname = :nome"), {"nome": NOME_BANCO_DEV}
        ).scalar()
        if existe and recriar:
            conexao.execute(text(f'drop database "{NOME_BANCO_DEV}" with (force)'))
            _log(f"banco {NOME_BANCO_DEV} apagado")
            existe = False
        if not existe:
            conexao.execute(text(f'create database "{NOME_BANCO_DEV}"'))
            _log(f"banco {NOME_BANCO_DEV} criado")
        else:
            _log(f"banco {NOME_BANCO_DEV} já existe")
    motor.dispose()


def migrar() -> None:
    configuracao = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ_BACKEND / "migrations"))
    configuracao.set_main_option("sqlalchemy.url", url_banco_dev())
    command.upgrade(configuracao, "head")
    _log("migrações aplicadas")


# --------------------------------------------------------------------------
# Dados
# --------------------------------------------------------------------------


def _dias_de_pedido(inicio: date, fim: date, sorteio: random.Random) -> list[date]:
    """Dias úteis com alguns sábados — um pedido por dia, no máximo."""
    dias = []
    atual = inicio
    while atual <= fim:
        if atual.weekday() < 5 or (atual.weekday() == 5 and sorteio.random() < 0.4):
            dias.append(atual)
        atual += timedelta(days=1)
    return dias


def popular(sessao: Session) -> None:
    # imports aqui: só depois de DATABASE_URL estar definido no ambiente
    from app.core.datas import hoje_sp
    from app.dominio import LinhaSolicitada
    from app.repositories.cliente_repo import RepositorioCliente
    from app.repositories.item_repo import RepositorioItem
    from app.repositories.lancamento_repo import RepositorioLancamento
    from app.repositories.preco_repo import RepositorioPreco
    from app.services.servico_cliente import ServicoCliente
    from app.services.servico_item import ServicoItem
    from app.services.servico_lancamento import ServicoLancamento
    from app.services.servico_preco import ServicoPreco

    repo_cliente = RepositorioCliente(sessao)
    repo_item = RepositorioItem(sessao)
    servico_cliente = ServicoCliente(repo_cliente)
    servico_item = ServicoItem(repo_item, repo_cliente)
    repo_preco = RepositorioPreco(sessao)

    def preco_em(dia: date) -> ServicoPreco:
        """Serviço com o relógio fixado: o preço "é alterado" naquele dia."""
        return ServicoPreco(repo_preco, repo_cliente, repo_item, hoje=lambda: dia)

    servico_preco = ServicoPreco(repo_preco, repo_cliente, repo_item)
    servico_lancamento = ServicoLancamento(
        RepositorioLancamento(sessao), repo_cliente, repo_item, servico_preco
    )

    if repo_cliente.listar(incluir_inativos=True):
        _log("o banco já tem clientes — nada a popular (use --recriar para refazer)")
        return

    # determinístico: mesma massa a cada recriação. Não é uso criptográfico.
    sorteio = random.Random(20260901)  # noqa: S311
    hoje = hoje_sp()
    comanda = 1201

    for nome_cliente, catalogo in CATALOGOS.items():
        cliente = servico_cliente.criar(nome_cliente)
        itens_com_preco = []
        for nome_item, preco in catalogo:
            item = servico_item.criar(cliente.id, nome_item)
            if preco is not None:
                preco_em(JUNHO).mudar_a_partir_de_hoje(item.id, Decimal(preco))
                itens_com_preco.append(item)
            reajuste = REAJUSTES.get((nome_cliente, nome_item))
            if reajuste:
                preco_em(reajuste[0]).mudar_a_partir_de_hoje(item.id, Decimal(reajuste[1]))

        # Hotel Aurora tem histórico diário; os demais, mais espaçado
        dias = _dias_de_pedido(INICIO_HISTORICO, hoje, sorteio)
        if nome_cliente != "Hotel Aurora":
            dias = [d for d in dias if sorteio.random() < 0.45]

        for dia in dias:
            sorteados = [i for i in itens_com_preco if sorteio.random() < 0.8]
            escolhidos = sorteados or itens_com_preco[:1]
            linhas = [
                LinhaSolicitada(i.id, sorteio.randint(*FAIXAS.get(i.nome, (5, 20))))
                for i in escolhidos
            ]
            # cerca de 1 em 6 pedidos chega sem comanda
            numero = None if sorteio.random() < 0.17 else str(comanda)
            if numero:
                comanda += 1
            servico_lancamento.criar(cliente.id, dia, linhas, numero)

        _log(f"{nome_cliente}: {len(catalogo)} itens, {len(dias)} lançamentos")

    # situação inativa com histórico: aparece marcada nas telas, sem sumir do relatório
    pousada = repo_cliente.buscar_por_nome("Pousada Vista Verde")
    if pousada:
        servico_cliente.inativar(pousada.id)
        _log("Pousada Vista Verde inativada (mantém o histórico)")

    aurora = repo_cliente.buscar_por_nome("Hotel Aurora")
    tapete = repo_item.buscar_por_nome(aurora.id, "Tapete") if aurora else None
    if tapete:
        servico_item.inativar(tapete.id)
        _log("item Tapete do Hotel Aurora inativado")

    sessao.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--recriar",
        action="store_true",
        help="apaga e recria o lavconta_dev antes de popular",
    )
    argumentos = parser.parse_args()

    url = url_banco_dev()  # valida host local antes de qualquer ação
    os.environ["DATABASE_URL"] = url

    print(f"Preparando {NOME_BANCO_DEV} (Postgres local)")
    criar_banco(argumentos.recriar)
    migrar()

    motor = create_engine(url)
    with Session(motor) as sessao:
        popular(sessao)
    motor.dispose()
    print("Pronto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
