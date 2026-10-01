# Avaliação do protótipo v1 (UX Pilot)

Ponte entre o protótipo visual e o design técnico. Registra o que da primeira versão
do UX Pilot **entra** no produto e o que é **descartado por estar fora do escopo**
confirmado. Serve para evitar que features inventadas pela ferramenta vazem para o
`design.md` e virem código.

Regra de leitura: o protótipo vale como **direção visual**, não como fonte de escopo.
Escopo é definido por `product.md`, `business-rules.md` e `requirements.md`. Em conflito,
essas fontes vencem o protótipo.

---

## Parte A — Aprovado (manter no design)

Direção visual e de layout que atende o brief e deve ser preservada.

1. **Sidebar escura com gradiente, ícones e item ativo destacado.** Navegação com os
   cinco itens corretos: Lançamentos, Relatório, Clientes, Catálogo, Preços.
2. **Login limpo e correto:** sem cadastro, com "esqueceu a senha" e aviso de acesso
   restrito a funcionários. Alinhado ao Requisito 1.
3. **Relatório com faixa de cartões de resumo no topo + gráfico + tabela.** A estrutura
   está certa (ver correções de conteúdo na Parte B).
4. **Gráfico de volume por dia** acima da tabela de fechamento. Manter, respeitando a
   paleta azul e sem depender só de cor para distinguir séries.
5. **Barra de totais fixa no rodapé do lançamento**, com peças e R$ atualizando ao
   digitar. É o momento de deleite do produto. Manter.
6. **Cartões de cliente e de item** com iniciais/ícone, situação (Ativo/Inativo) como
   badge, e ação de editar. Bom para a gestão. Manter a estrutura.
7. **Comanda marcada como opcional** no formulário de lançamento. Correto.
8. **Estados de situação (Ativo/Inativo)** visíveis em clientes e itens. Alinhado aos
   Requisitos 2 e 3.
9. **Paleta, tipografia, profundidade e acabamento geral.** Aprovados.

---

## Parte B — Descartado ou corrigido (fora do escopo v1)

Cada item traz o problema, a regra que ele contraria e a ação.

### B1. Total divergente no relatório — CORREÇÃO CRÍTICA

- **No protótipo:** cartão "Total Bruto" mostra R$ 1.380,00; a linha de totais da tabela
  mostra R$ 1.695,00 (este é o correto: soma das linhas).
- **Problema:** dois totais diferentes para a mesma coisa, na tela cujo propósito é
  cobrança auditável. Destrói a confiança que o produto existe para criar.
- **Regra:** `product.md` — valor rastreável e estável; Requisito 6 — cálculo
  autoritativo no backend.
- **Ação:** fonte única de verdade para o total, calculada no backend; todos os
  elementos da tela leem desse mesmo valor. Nunca recalcular no frontend.

### B2. Ticket Médio e variação "+12,5%"

- **No protótipo:** cartões de "Ticket Médio" e um indicador de variação percentual.
- **Problema:** analítica comparativa (média de faturamento, comparação entre períodos).
- **Regra:** `product.md`, "Fora de escopo na v1" — o relatório consolida peças e reais
  do período, sem inteligência de negócio. Não há período anterior para comparar.
- **Ação:** remover. Substituir o conteúdo dos quatro cartões pelos totais reais que a
  Lavandix audita: **Total de Peças, Total R$, Nº de Lançamentos, Média Diária de Peças**
  (operacional, não financeira).

### B3. Campo "Notas adicionais / observações sobre manchas, rasgos, urgência"

- **No protótipo:** textarea livre no formulário de lançamento.
- **Problema:** campo arbitrário por lançamento.
- **Regra:** `business-rules.md` — a flexibilidade se limita a cadastrar/editar itens e
  definir preços; **sem campos personalizados arbitrários por lançamento**. Requisito
  3.5.
- **Ação:** remover da v1.

### B4. "Margem s/ base" (-5,4%, +6,6%) na tela de preços

- **No protótipo:** coluna de margem percentual sobre um preço-base.
- **Problema:** pressupõe um preço-base global e expõe cálculo de margem.
- **Regra:** `business-rules.md` — preço é por (cliente, item, mês/ano); **não existe
  catálogo nem preço global**. Requisito 2.6.
- **Ação:** remover a coluna de margem. A tela de preços mostra item e preço vigente do
  mês, e destaca itens sem preço.

### B5. "Categoria" de item (Cama, Banho, Uniforme)

- **No protótipo:** itens agrupados por categoria, com abas de filtro.
- **Problema:** categoria é um agrupamento que não existe no modelo de domínio.
- **Regra:** entidade Item = nome + cliente + situação. Sem categoria.
- **Ação:** remover na v1. Candidato a versão futura, se a Lavandix pedir.

### B6. Vocabulário fora do domínio

- **No protótipo:** "Total de Itens", "Resumo da Carga", "Lançamento Bruto", "entrada de
  peças para processamento", "Tarifário", "Novo Acordo", "Contrato Premium".
- **Problema:** mistura vocabulário industrial ("carga", "processamento") e comercial
  ("tarifário", "acordo", "contrato") que não corresponde ao trabalho real.
- **Regra:** glossário do `requirements.md` e `structure.md` — idioma e nomes de domínio
  padronizados. Termos corretos: **peças, lançamento, preço, relação de valores,
  cliente**.
- **Ação:** padronizar a terminologia da interface pelo glossário. Palavra é interface.

### B7. Endereço de cliente

- **No protótipo:** card de cliente com endereço ("Av. Atlântica, 1402").
- **Problema:** cliente na v1 é apenas nome (+ situação ativo/inativo).
- **Regra:** Requisito 2 — cadastro de cliente com nome; sem outros campos definidos.
- **Ação:** remover endereço, salvo decisão explícita de adicionar o campo aos
  requisitos.

### B8. Vigência de preço como rótulo anual/pontual ("DEZ/2026", "MAR/2027")

- **No protótipo:** vigência exibida como um mês/ano solto associado ao "contrato".
- **Problema:** sugere vigência pontual, não a vigência **mensal que se propaga**.
- **Regra:** Requisito 4 — preço indexado por (cliente, item, mês/ano), vigente até novo
  preço ser definido.
- **Ação:** a tela de preços é sempre de um cliente para um mês/ano selecionado, listando
  o preço vigente resolvido para cada item naquele mês.

---

## Parte C — Refinamentos de UX (manter, ajustar no design)

Não são erros de escopo; são melhorias a especificar.

1. **Stepper +/- na quantidade:** boa ideia para ajuste rápido, mas deve **conviver com
   entrada direta por teclado** (digitar o número). O operador preenche todo dia e
   precisa tabular e digitar. Manter os dois.
2. **Colunas dinâmicas de item no relatório:** confirmar que seguem a regra — só itens
   com ocorrência no período geram coluna, célula vazia quando o item não aparece no dia
   (Requisitos 7.7 e 7.8). No mock isso apareceu coerente; manter explícito no design.
3. **Estado de "servidor acordando"** (cold start): não apareceu no protótipo. Precisa
   existir na implementação (brief-design, seção de carregamento).
4. **Data no formato dd/mm/yyyy:** o protótipo usou dd/mm/yyyy corretamente. Manter.

---

## Resumo para o design técnico

O `design.md` deve herdar a **direção visual da Parte A** e ignorar tudo da **Parte B**.
Os quatro cartões do relatório passam a conter Total de Peças, Total R$, Nº de
Lançamentos e Média Diária de Peças. Nenhum campo de nota, margem, categoria ou endereço
entra no modelo de dados. A terminologia segue o glossário. Qualquer item da Parte B que
o cliente venha a querer é tratado como mudança de escopo: atualiza-se `requirements.md`
primeiro.
