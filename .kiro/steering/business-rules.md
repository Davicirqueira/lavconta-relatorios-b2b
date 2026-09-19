---
inclusion: always
---

# Regras de negócio — Lavandix

Estas regras são a **fonte da verdade** do domínio. Foram confirmadas com o cliente.
Não deduzir regras novas a partir de imagens/planilhas sem confirmação.

## Clientes

- O sistema gerencia **vários clientes-empresa**.
- Cada cliente tem seu **próprio catálogo de itens** e sua **própria tabela de preços**.
  Nada de catálogo ou preço global.

## Catálogo de itens (flexibilidade)

- Tipos de item são **cadastrados/editados livremente por cliente**.
- "Flexibilidade" significa **exatamente**: cadastrar/editar tipos de item e definir
  preços por cliente. **Não** inclui campos extras arbitrários por lançamento.

## Preços

- Preço é **por cliente + item**.
- **Vigência mensal**: o preço definido para um mês vale do dia 1 ao último dia
  daquele mês.
- Se o preço for alterado no meio do mês (ex: dia 15/08), o valor que valia naquele
  mês **permanece até o fim do mês**; a alteração só passa a valer **a partir do mês
  seguinte**.
- Indexação lógica do preço: **(cliente, item, mês/ano)**.

## Lançamento diário (pedido)

- A unidade de registro é o **pedido diário de um cliente**.
- Cada empresa faz **um único pedido por dia**. **Não** existe mais de um lançamento
  por cliente na mesma data.
- **Regra de unicidade (forte):** para um mesmo cliente, existe **no máximo um
  lançamento por data**. O sistema **deve impedir** criar um segundo lançamento para
  o mesmo cliente na mesma data.
- Identificador natural do lançamento: **(cliente, data)** — sempre presente.
- Cada lançamento tem **uma data** (data do serviço/pedido). Vários clientes
  diferentes podem ter lançamento na mesma data; o mesmo cliente, não.

## Número de comanda

- O **campo comanda existe sempre** na interface.
- O **preenchimento é opcional** (alguns clientes não usam comanda).
- Quando preenchido, é digitado **manualmente** pela equipe da Lavandix (normalmente
  sequencial).
- Quando preenchido, deve ser **único por cliente**.
- A comanda **não é** o identificador principal do lançamento — o identificador é
  (cliente, data). A comanda é um atributo opcional.

## Cálculo de valores

- Cobrança **sempre por peça**.
- **Total do item** = preço unitário do item × quantidade do item.
- **Total do lançamento (R$)** = soma dos totais de todos os itens do lançamento.
- **Total de peças do lançamento** = soma das quantidades de todos os itens.
- **Sem** impostos, taxas, mínimos ou descontos.

## Congelamento de valor (estabilidade histórica)

- No momento em que um lançamento é criado, o **valor unitário de cada item é
  gravado (congelado) no próprio lançamento**, com base no preço vigente daquele mês.
- Consequência: alterar o preço depois **não altera** lançamentos/relatórios
  passados. Relatórios antigos permanecem estáveis.

## Fechamento e relatório

- O relatório é **detalhado por dia/lançamento**.
- Colunas do relatório (espelham a planilha atual): **data**, **comanda** (quando
  houver), **quantidade por tipo de item**, **total de peças** da linha, **total R$**
  da linha.
- Quando o lançamento **não** tem comanda, o layout é o mesmo, apenas sem valor no
  campo comanda (o campo não deixa de existir).
- **Totais do período:** total de peças e total em R$ (mesmos totais da planilha atual).
- **Período de fechamento é customizável** via seleção de datas (dd/mm/yyyy).
  - **Default:** 1º dia do mês vigente até o último dia do mês vigente.
  - O usuário pode modificar o intervalo livremente (inclusive cruzando meses).
- Como o preço tem vigência mensal e o período pode cruzar meses, cada lançamento
  entra no relatório com **seu próprio valor congelado** (o preço do mês em que foi
  criado). O relatório soma lançamentos, não reaplica um preço único do período.

## Exportação

- O relatório pode ser exportado em **PDF** e em **Excel**. O usuário escolhe o formato.
