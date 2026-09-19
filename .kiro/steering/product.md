---
inclusion: always
---

# Produto — Lavconta (Relatórios B2B)

**Nome da aplicação:** Lavconta — Relatórios B2B
**Cliente inicial (v1):** Lavandix (lavanderia profissional em São Paulo).

## Contexto do negócio

A **Lavandix** é uma lavanderia profissional que atende **empresas** (clientes B2B)
em São Paulo. As empresas enviam itens (lençol, fronha, toalha, roupão, etc.) para
serem tratados (lavagem, secagem, dobra) e devolvidos. A cobrança é **mensal e
consolidada**.

## Por que este processo existe

Existe um descompasso entre **quando o trabalho acontece** (diário, pulverizado ao
longo do mês) e **quando ele é cobrado** (uma vez, no fechamento mensal). O processo
de "relação de valores" fecha esse descompasso e cumpre três funções:

1. **Registro fiel** do que foi feito a cada dia (itens, quantidades, preço aplicado).
2. **Cobrança confiável e auditável** — o cliente recebe uma relação detalhada
   (dia a dia, item a item) que ele consegue conferir contra os próprios pedidos.
   Isso evita disputa e torna a fatura defensável.
3. **Consolidação para faturar** — no fechamento, tudo vira um total cobrável.

Hoje isso é feito em planilha manual, o que é frágil (erro de digitação, preço
errado, fórmula quebrada, retrabalho, dificuldade de manter preços diferentes por
cliente). O app existe para **garantir que o valor cobrado seja sempre coerente com
o preço vigente e o que foi registrado**, e para gerar a relação pronta para envio.

## Princípio de design derivado do processo

O valor cobrado precisa ser **rastreável e estável**: não pode mudar retroativamente.
Essa é a função central do processo (cobrança confiável). Todas as decisões de
modelagem devem preservar isso.

## Escopo da versão 1 (v1)

- **Usuário único**, equipe interna da Lavandix. Clientes-empresa **não** acessam.
- Web app completo com API e banco Postgres.
- Gestão de **clientes**, **catálogo de itens por cliente**, **preços por cliente/mês**
  e **lançamentos diários**.
- Geração de **relatório de fechamento** (detalhado por dia) com exportação em
  **PDF e Excel**.

## Fora de escopo na v1

- Múltiplos usuários / perfis de acesso (admin vs. operador).
- Acesso de clientes-empresa ao sistema.
- Campos personalizados arbitrários por lançamento.
- Importação de histórico (começamos do zero).
- Cobrança por peso/lote (cobrança é sempre **por peça**).
- Impostos, taxas ou descontos no cálculo.
