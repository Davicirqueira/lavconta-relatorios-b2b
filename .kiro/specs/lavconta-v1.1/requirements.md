# Requisitos — Lavconta v1.1

## Introdução

A v1 está em produção. Ao usar, o cliente (Lavandix) levantou quatro pontos:

1. Achou que precisaria trocar o preço dos itens todo mês. **Não precisa**: o preço
   já persiste até ser alterado. O que passou essa impressão foi a tela de Preços
   (seletor de mês e o texto "vigência do dia 1 ao fim do mês").
2. Quer definir o preço já no Catálogo, sem ir para outra tela.
3. Quer um relatório com **todos os clientes** do período.
4. Quer um PDF mais bem acabado: logo, tabela e distribuição das informações.

Esta versão também muda uma regra: a alteração de preço passa a valer **no dia em
que é feita**, e não mais no mês seguinte.

**Princípio condutor (mantido da v1):** o valor cobrado é rastreável e estável.
Nenhuma alteração de preço muda um pedido já registrado nem um relatório passado.

**Prioridades de abordagem:** experiência do usuário, segurança e arquitetura
modular (`engineering.md`, "Prioridades de abordagem").

**Fonte da verdade:** `.kiro/steering/business-rules.md` (seção Preços, já
atualizada). Estes requisitos substituem o Requisito 4 da v1 e ajustam os
Requisitos 3 (catálogo), 5 (lançamento), 7 (relatório) e 8 (exportação).

---

## Glossário

| Termo | Significado |
|---|---|
| **Preço** | Valor por peça de um item para um cliente, válido a partir de uma **data de início** até a próxima alteração. |
| **Data de início** | Dia a partir do qual um preço vale. Definida pelo sistema (hoje, em São Paulo). |
| **Preço vigente** | Para um pedido, o preço com a maior data de início menor ou igual à data do pedido. |
| **Valor congelado** | Preço gravado na linha do pedido quando ele é criado. Não muda depois. |
| **Relatório geral** | Relatório do período com todos os clientes que tiveram pedidos. |

---

## Requisito 1 — Preço válido por data

**História:** Como operador, quero alterar o preço de um item e que ele valha a
partir de hoje, sem precisar redefinir preços a cada mês.

### Critérios de aceitação

1. Um preço definido DEVE continuar valendo até ser alterado, independentemente da
   virada de mês.
2. QUANDO o operador alterar o preço de um item, ENTÃO a data de início do novo preço
   DEVE ser a data de hoje no fuso de São Paulo, **calculada pela API**. O operador
   NÃO DEVE informar data de início, e a API NÃO DEVE aceitar data de início vinda
   do cliente HTTP.
3. QUANDO o sistema resolver o preço de um pedido, ENTÃO ele DEVE usar o preço com a
   maior data de início menor ou igual à **data do pedido** (não a data em que o
   pedido foi digitado).
4. QUANDO o operador alterar o mesmo preço mais de uma vez no mesmo dia, ENTÃO a
   última alteração DEVE substituir a anterior daquele dia, sem criar histórico novo.
5. Pedidos já registrados DEVEM manter seus valores congelados após qualquer
   alteração de preço, inclusive a do item 4.
6. QUANDO a alteração do item 4 ocorrer e já existirem pedidos de hoje com o valor
   anterior, ENTÃO o sistema DEVE informar quantos pedidos mantêm o valor antigo,
   em linguagem simples.
7. O **primeiro** preço de um item DEVE valer também para datas anteriores à sua
   criação (não há preço anterior a preservar). Assim, um item novo pode entrar em
   pedido retroativo sem ficar "sem preço".
8. O histórico de preços DEVE ser preservado no banco. A interface NÃO exibe o
   histórico nesta versão.
9. Mantidas da v1: valor positivo, exatamente duas casas decimais, precisão decimal
   (sem ponto flutuante), recusa com mensagem clara (Req 4.9, 4.11–4.13 da v1).
10. Removidos da v1: escolha de mês de vigência, preço programado para mês futuro e
    sugestão de "mês seguinte" (Req 4.3, 4.5, 4.14–4.16 da v1).

### Correção de erro de digitação (decidido: opção b)

11. Ao editar o preço de um item, o operador DEVE escolher entre duas ações,
    descritas em linguagem simples:
    - **"Mudar o preço a partir de hoje"** — cria um novo preço com início hoje
      (critérios 2 e 4);
    - **"Corrigir o preço atual"** — substitui o valor do preço atual **desde o dia
      em que ele foi definido**, sem criar histórico novo.
12. A correção DEVE alcançar apenas o preço atual do item (o histórico não é exibido
    nesta versão, critério 8).
13. QUANDO o operador corrigir o preço atual, ENTÃO o sistema DEVE avisar, antes de
    confirmar, que os pedidos já registrados **não** mudam e informar quantos pedidos
    mantêm o valor anterior. A correção vale para pedidos lançados depois, inclusive
    os retroativos (equivale ao Req 4.17–4.18 da v1).
14. Quando o preço atual tiver início hoje, as duas ações têm o mesmo efeito; a
    interface PODE oferecer só uma.

---

## Requisito 2 — Migração dos preços existentes

**História:** Como responsável pelo sistema, quero que os preços já cadastrados em
produção passem para a nova regra sem perda nem alteração de cobrança.

### Critérios de aceitação

1. Cada preço existente DEVE receber como data de início o dia 1 do mês em que
   valia (`vigencia_mes` atual).
2. O primeiro preço de cada item DEVE seguir o Requisito 1.7.
3. A migração NÃO DEVE alterar nenhum valor congelado de pedido.
4. A migração DEVE ser feita em duas fases, cada uma com rollback testado:
   - fase 1: adicionar e preencher a estrutura nova, mantendo a antiga;
   - fase 2 (separada, após o código novo estável): remover a estrutura antiga.
5. Antes de aplicar em produção, DEVE haver backup do banco (`pg_dump`) e a
   migração DEVE ter sido aplicada e verificada no banco de desenvolvimento.
6. A migração DEVE ser aplicada em produção **antes** do push do código que
   depende dela (o Render publica automaticamente após CI verde).

---

## Requisito 3 — Preço definido no Catálogo

**História:** Como operador, quero informar o preço ao cadastrar ou editar o item,
para não precisar ir a outra tela.

### Critérios de aceitação

1. QUANDO o operador cadastrar um item, ENTÃO o formulário DEVE pedir nome e preço
   por peça, e o preço DEVE ser obrigatório.
2. QUANDO o operador editar um item, ENTÃO ele DEVE poder alterar nome e preço no
   mesmo formulário.
3. A criação do item com seu primeiro preço DEVE ser atômica: ou os dois são
   gravados, ou nenhum.
4. O cartão do item DEVE exibir o preço atual por peça (ex.: "R$ 4,50 por peça").
5. Itens existentes sem preço DEVEM aparecer com indicação "Sem preço" e uma ação
   direta para definir o preço.
6. A tela de Preços DEVE sair do menu, e a rota `/precos` DEVE redirecionar para
   `/catalogo`.
7. O valor exibido no cartão DEVE vir da API; a interface não calcula preço vigente.
8. As demais regras de item da v1 permanecem (nome único por cliente, ativo/inativo,
   exclusão só sem histórico).

---

## Requisito 4 — Textos de interface

**História:** Como operador, quero entender o que o sistema faz com o preço só de
ler a tela, sem termos técnicos.

### Critérios de aceitação

1. Os textos sobre preço DEVEM dizer o que acontece em linguagem simples. Referência:
   "O preço vale a partir de hoje e continua valendo até você mudar." e "Pedidos
   anteriores mantêm o preço da época."
2. A interface NÃO DEVE usar "vigência", "mês de referência" ou códigos de erro em
   textos para o operador.
3. Mensagens de "item sem preço" no lançamento DEVEM orientar a ação ("Defina o
   preço deste item no Catálogo"), sem citar mês.
4. Todos os textos que mencionam preço por mês DEVEM ser revisados (telas,
   mensagens da API exibidas ao operador, estados vazios, confirmações).

---

## Requisito 5 — Relatório geral (todos os clientes)

**História:** Como operador, quero ver no mesmo relatório todos os clientes do
período, com itens e valores, para ter a visão consolidada do faturamento.

### Critérios de aceitação

1. O seletor de cliente do relatório DEVE oferecer a opção "Todos os clientes".
2. QUANDO "Todos os clientes" for escolhido, ENTÃO o relatório DEVE mostrar uma
   seção por cliente com: item, quantidade de peças, valor por peça e subtotal; e
   o total de peças e em R$ do cliente.
3. O relatório DEVE terminar com o **total geral** de peças e em R$ do período.
4. QUANDO um item tiver mais de um valor congelado no período, ENTÃO ele DEVE
   aparecer em uma linha por valor, sem reaplicar preço.
5. Clientes sem pedidos no período NÃO DEVEM aparecer. Clientes inativos com
   pedidos no período DEVEM aparecer.
6. O relatório geral DEVE ser exportável em PDF e Excel (Excel: aba de resumo e uma
   aba por cliente).
7. Os totais da tela, do PDF e do Excel DEVEM ser idênticos, com teste de paridade
   como na v1.
8. O período segue as regras da v1 (padrão: mês corrente; pode cruzar meses).
9. A geração DEVE usar consultas agrupadas (sem uma consulta por cliente), exigir
   autenticação e ter o mesmo limite de requisições das exportações da v1.
10. O relatório por cliente da v1 permanece inalterado em conteúdo.

---

## Requisito 6 — PDF com melhor acabamento

**História:** Como operador, quero enviar ao cliente um PDF limpo e fácil de
conferir.

### Critérios de aceitação

1. O logo DEVE manter a proporção original e ficar nítido na impressão. (Hoje a
   imagem de 348×300 px é desenhada em 110×28 pt, achatada.) Usar o original de
   861×742 px recortado, ou versão vetorial se o cliente fornecer.
2. As colunas de item DEVEM ter largura proporcional ao conteúdo, com limite
   máximo, sem espaços vazios grandes entre colunas quando houver poucos itens.
3. O alinhamento DEVE ser consistente entre cabeçalho e valores (texto à esquerda,
   números à direita). Algarismos tabulares valem para a interface web; no PDF não
   são viáveis com a biblioteca atual (o reportlab não aplica recursos OpenType
   como `tnum`), e o alinhamento à direita cumpre o papel.
4. O PDF por cliente DEVE incluir um **resumo por item** (quantidade, valor por peça,
   subtotal), para o cliente conferir preço × quantidade.
5. O PDF DEVE ter rodapé com número da página ("Página 1 de 2") e repetir o
   cabeçalho da tabela nas páginas seguintes.
6. O mesmo padrão visual DEVE valer para o PDF do relatório geral.
7. Os valores do PDF continuam vindo da mesma estrutura de relatório da tela, sem
   recalcular.

---

## Fora de escopo nesta versão

- Data de revisão de preço e aviso de revisão.
- Exibir histórico de preços na interface.
- Preço programado para data futura.
- Ação de reaplicar o preço atual a um pedido já gravado.
- Notificação por e-mail.
