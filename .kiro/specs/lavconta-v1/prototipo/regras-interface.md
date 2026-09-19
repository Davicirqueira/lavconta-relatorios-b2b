# Regras de interface — Lavconta

Restrições que o protótipo deve respeitar. São regras de comportamento da interface,
não de visual (visual em `id-visual.md`).

## Papel da interface

A interface **exibe** valores calculados pelo servidor. Ela não recalcula preço, total
de linha, total de peças nem total em R$. No protótipo, esses valores podem ser
estáticos ou simulados, mas devem ser apresentados como vindos do servidor — campos de
valor unitário e totais são **somente leitura**.

## Formatos

- **Datas:** sempre dd/mm/yyyy, na entrada e na exibição.
- **Dinheiro:** R$ com duas casas decimais, vírgula como separador decimal e ponto como
  separador de milhar (R$ 1.234,56).
- **Quantidades:** números inteiros, sem casas decimais.
- Colunas numéricas com dígitos de largura fixa, para alinhamento vertical.

## Idioma

Todo texto visível em português do Brasil: rótulos, botões, mensagens de erro, estados
vazios, tooltips e títulos. Sem termos em inglês na interface.

## Mensagens e erros

Erros aparecem em português, explicando o motivo e apontando o campo. Exemplos de
mensagens que o protótipo deve representar:

- "Já existe um lançamento para este cliente nesta data."
- "Esta comanda já foi usada para este cliente."
- "Os itens Roupão e Tapete não têm preço cadastrado para setembro/2026."
- "A data inicial não pode ser posterior à data final."
- "Não é possível registrar lançamento com data futura."
- "Não é possível excluir: existem lançamentos vinculados. Você pode inativar."

Erros de formulário aparecem junto ao campo; erros da operação inteira aparecem em
banner no topo do formulário.

## Estados obrigatórios

Cada tela de dados precisa representar quatro estados:

1. **Carregando** — inclusive um estado mais demorado: a hospedagem hiberna quando
   ociosa e a primeira requisição pode levar dezenas de segundos. Mostrar progresso e
   uma mensagem tranquilizadora, nunca dar impressão de falha.
2. **Vazio** — sem registros, com orientação do próximo passo.
3. **Com dados** — o estado normal.
4. **Erro** — falha ao carregar, com opção de tentar novamente.

## Confirmações

Ações destrutivas pedem confirmação explícita em diálogo, identificando o registro
("Excluir o lançamento de Hotel Aurora em 03/09/2026?"), com botão destrutivo e opção
de cancelar. Inativar **não** é destrutivo e não precisa de diálogo.

## Ativo e inativo

Registros inativos (clientes e itens) não aparecem nas seleções por padrão. Listas têm
uma alternância para exibi-los, e eles recebem marcação visual discreta de estado
neutro — não de erro nem de alerta.

## Acessibilidade

- Todo campo com rótulo visível associado; não usar apenas placeholder como rótulo.
- Foco de teclado sempre visível, com anel de foco destacado.
- Navegação completa por teclado, especialmente no formulário de lançamento, que é
  preenchido todos os dias e se beneficia de tabulação rápida entre item e quantidade.
- Informação nunca transmitida só por cor: usar também texto ou ícone.
- Contraste de texto e fundo atendendo WCAG AA no uso corrente.

## Dados de exemplo

Usar apenas dados fictícios no protótipo. Nomes sugeridos: Hotel Aurora, Restaurante
Bom Prato, Clínica São Lucas, Pousada Vista Verde. Itens: lençol, fronha, toalha,
roupão, tapete, toalha de mesa.
