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
- **O preço persiste:** depois de definido, vale até ser alterado, mesmo que o mês
  vire. O usuário **não** precisa redefinir preços a cada mês (a troca real acontece
  cerca de 1 a 2 vezes por ano).
- **A alteração vale a partir do dia em que é feita** (data de hoje no fuso de São
  Paulo, definida pelo sistema; o usuário não informa data de início).
  - Pedidos com data **anterior** ao dia da alteração continuam com o preço antigo.
  - Pedidos com data **igual ou posterior** usam o preço novo.
- **O preço é escolhido pela data do pedido**, nunca pela data em que o pedido foi
  digitado. Ex.: preço alterado no dia 10; um pedido do dia 5 lançado no dia 12 usa
  o preço antigo.
- **Duas alterações no mesmo dia:** a segunda corrige a primeira (não cria histórico
  novo para aquele dia).
- **O primeiro preço de um item vale também para datas anteriores** à sua criação
  (não há preço anterior a preservar). Assim, item novo pode entrar em pedido
  retroativo.
- **Correção de erro de digitação:** o operador pode **corrigir o preço atual**
  desde o dia em que ele foi definido (em vez de criar um novo a partir de hoje).
  Pedidos já registrados **não** mudam; o sistema avisa quantos mantêm o valor
  anterior antes de confirmar.
- O histórico de preços é **preservado** no banco. Exibir esse histórico na
  interface está **fora do escopo** até decisão do cliente.
- Indexação lógica do preço: **(cliente, item, data de início)**.
- **Onde o preço é definido:** no **Catálogo**, junto com o item (ao criar e ao
  editar). Não existe tela separada de preços.

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
  gravado (congelado) no próprio lançamento**, com base no preço vigente na **data do
  pedido**.
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
- Como o preço pode mudar dentro do período, cada lançamento entra no relatório com
  **seu próprio valor congelado** (o preço vigente na data do pedido). O relatório
  soma lançamentos, não reaplica um preço único do período.

## Exportação

- O relatório pode ser exportado em **PDF** e em **Excel**. O usuário escolhe o formato.
