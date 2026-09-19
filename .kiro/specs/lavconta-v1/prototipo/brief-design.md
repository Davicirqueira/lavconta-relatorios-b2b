# Brief de design — Lavconta

Estende `id-visual.md`. Aquele arquivo define **tokens**; este define **expressão**:
profundidade, aplicação de cor, movimento e o acabamento dos componentes.

## 1. Direção de produto

Lavconta é uma ferramenta de trabalho diário que produz um documento financeiro. A
personalidade certa é **precisa e confiante**, não corporativa e apagada. A referência
mental é software de produto moderno — Linear, Stripe Dashboard, Vercel — aplicada a um
contexto de lavanderia B2B: superfícies limpas, profundidade sutil, tipografia com
hierarquia clara, movimento que responde à ação do operador.

Três qualidades a perseguir:

**Densa sem ser apertada.** A tela de relatório mostra muitos números. Densidade se
resolve com ritmo de espaçamento e hierarquia tipográfica, não encolhendo tudo.

**Viva sem ser inquieta.** O movimento confirma ações e orienta transições. Nada anima
sozinho, nada pisca, nada chama atenção sem motivo.

**Colorida com propósito.** Cor estrutura a informação: agrupa, destaca, indica estado.

## 2. Reinterpretando a regra 60/30/10

A regra original suprimiu a cor. A leitura correta: **60/30/10 governa a cor de marca
saturada como acento, não proíbe superfícies tingidas.**

O que passa a ser explicitamente permitido e desejado:

- **Superfícies tingidas** de azul muito claro (`azul-50`, `azul-100`) em painéis
  informativos, linhas selecionadas, hover de linha e containers de ícone.
- **Gradientes sutis** dentro da mesma família — sidebar de `azul-900` para `azul-800`,
  no sentido vertical, quase imperceptível.
- **Sombras tingidas de azul** em vez de preto. Sombra preta suja a paleta; sombra
  derivada de `azul-900` em alfa baixo mantém tudo coerente.
- **A escala azul inteira em dados.** Barras, rampas e realces usam de `azul-200` a
  `azul-800` livremente.
- **Acentos diferenciados entre cartões de resumo.** Cartões vizinhos podem usar
  degraus diferentes da escala azul, gerando variação sem sair da família.

O que continua valendo: **verde, amarelo e vermelho só comunicam estado.** Nunca
decoram. Essa restrição protege a confiança no documento financeiro.

## 3. Profundidade e forma

### Elevação (sombras tingidas)

```css
:root {
  --sombra-1: 0 1px 2px rgba(11, 47, 88, 0.06),
              0 1px 3px rgba(11, 47, 88, 0.04);
  --sombra-2: 0 2px 4px rgba(11, 47, 88, 0.06),
              0 4px 12px rgba(11, 47, 88, 0.08);
  --sombra-3: 0 8px 16px rgba(11, 47, 88, 0.08),
              0 16px 32px rgba(11, 47, 88, 0.12);
  --sombra-foco: 0 0 0 3px rgba(45, 116, 202, 0.18);
}
```

- **Nível 1:** cartões e tabelas em repouso.
- **Nível 2:** cartão em hover, dropdown, barra de totais fixa.
- **Nível 3:** modal e diálogo de confirmação.

### Raio de canto

```css
--raio-sm: 6px;   /* chips, badges, células editáveis */
--raio-md: 10px;  /* inputs, botões, seleções */
--raio-lg: 14px;  /* cartões, containers de tabela */
--raio-xl: 20px;  /* modais */
--raio-full: 999px; /* pílulas e avatar */
```

### Espaçamento

Escala de 4px: 4, 8, 12, 16, 24, 32, 48, 64. Padding interno de cartão 24px. Célula de
tabela 12px vertical por 16px horizontal. Respiro entre seções 32px.

### Tipografia aplicada

| Papel | Tamanho / Peso | Família |
|---|---|---|
| Título de página | 28px / 600 | Poppins |
| Título de cartão | 16px / 600 | Poppins |
| Número de destaque (stat) | 32px / 600 | Inter |
| Corpo | 14px / 400 | Poppins |
| Rótulo e cabeçalho de tabela | 12px / 500, letter-spacing 0.02em, maiúsculas | Poppins |
| Valor em tabela | 14px / 400, tabular-nums | Inter |
| Total em destaque | 20px / 600, tabular-nums | Inter |

## 4. Sistema de movimento

```css
:root {
  --dur-rapida: 120ms;   /* hover, mudança de cor */
  --dur-padrao: 200ms;   /* entrada de componente, modal */
  --dur-lenta: 320ms;    /* transição de painel, indicador */

  --ease-padrao: cubic-bezier(0.2, 0, 0, 1);   /* ênfase, entradas */
  --ease-saida: cubic-bezier(0.4, 0, 1, 1);    /* saídas */
  --ease-suave: cubic-bezier(0.4, 0, 0.2, 1);  /* transições neutras */
}
```

Princípio: **movimento responde a uma causa.** Toda animação tem um gatilho do usuário
ou uma mudança de dado real.

### Catálogo de animações

| Componente | Comportamento |
|---|---|
| Linha de tabela | Fundo para `azul-50` em hover, 120ms |
| Botão | Escala 0,98 ao pressionar, 100ms; cor de fundo em 120ms |
| Botão primário | Sombra cresce de nível 1 para 2 em hover, 160ms |
| Input | Borda para `azul-600` e anel de foco expandindo de 0 para 3px, 160ms |
| Cartão em lista | Entrada com fade e translateY de 8px, 240ms, **escalonado 40ms** entre cartões |
| Modal | Backdrop fade 160ms; painel escala 0,96 para 1 com fade, 200ms, `--ease-padrao` |
| Diálogo de exclusão | Mesma entrada do modal, botão destrutivo com hover em 120ms |
| Indicador da sidebar | Barra vertical de 3px em `azul-300` que **desliza** entre itens, 320ms |
| Item de navegação | Fundo e ícone em 160ms no hover |
| Colapso da sidebar | Rótulos em fade 80ms, depois largura de 240px para 68px em 240ms, `--ease-suave`; conteúdo acompanha na mesma curva |
| Tooltip do rail colapsado | Fade com translateX de 4px, 120ms, após 400ms de atraso no hover |
| Barra de totais | Ao recalcular, os números fazem contagem de 400ms e o fundo dá um flash suave em `azul-50` que decai em 600ms |
| Toast | Entra deslizando 12px do topo com fade, 200ms; sai com fade 160ms |
| Skeleton | Shimmer horizontal em loop de 1,6s |
| Chip de item | Escala 0,9 para 1 com fade ao ser adicionado, 180ms |
| Linha adicionada no lançamento | Expande a altura com fade, 240ms |
| Linha removida | Colapsa com fade, 180ms, `--ease-saida` |
| Troca de aba ou painel | Fade cruzado 200ms, sem deslocamento lateral |

### Acessibilidade do movimento

Com `prefers-reduced-motion: reduce`, todas as transições caem para 0ms ou viram
apenas opacidade. Nenhuma informação depende de animação para ser compreendida.

## 5. Componentes com acabamento moderno

### Sidebar

Gradiente vertical de `azul-900` para `azul-800`. Três zonas: marca no topo, navegação
no meio, usuário e controle de colapso no rodapé.

Itens com **ícone à esquerda** e rótulo em Poppins 500, altura de 44px, raio
`--raio-md`. Item ativo com fundo `azul-800` mais claro, texto branco, ícone branco e
**barra indicadora de 3px em `azul-300` na borda esquerda** que desliza na troca de
rota. Itens inativos com texto e ícone em `azul-300`; no hover, fundo sutil e texto
branco.

#### Ícones da navegação

Conjunto **Lucide** — traço de 1,5px a 2px, geometria limpa, pareia bem com Poppins.
Tamanho 20px na navegação, 18px em ações secundárias.

| Item | Ícone | Motivo |
|---|---|---|
| Lançamentos | `ClipboardList` | Registro diário de pedido, metáfora de prancheta |
| Relatório | `FileBarChart2` | Documento com números, é o que o fechamento é |
| Clientes | `Building2` | São empresas, não pessoas — evitar ícone de usuário |
| Catálogo | `Shirt` | Peças de roupa, liga direto ao domínio da lavanderia |
| Preços | `Tag` | Etiqueta de preço |
| Sair | `LogOut` | Convenção |
| Colapsar / expandir | `PanelLeftClose` / `PanelLeftOpen` | Indica a direção da ação |

Ícone nunca aparece sozinho no estado expandido — sempre acompanha o rótulo. Ícone é
reforço de reconhecimento, não substituto do texto.

#### Sidebar colapsável

Dois estados, com largura como única dimensão que muda:

- **Expandida:** 240px, ícone e rótulo.
- **Colapsada:** 68px, só ícone centralizado (rail).

**Comportamento do colapso:**

1. Os **rótulos somem primeiro** — opacidade para 0 em 80ms — e só então a largura
   contrai em 240ms com `--ease-suave`. Fazer as duas coisas juntas amassa o texto no
   meio da transição, e é exatamente o que denuncia implementação descuidada.
2. Ao expandir, a ordem inverte: largura primeiro, rótulos aparecem em fade nos últimos
   120ms.
3. Rótulos com `white-space: nowrap` e `overflow: hidden`, para nunca quebrarem linha
   durante a animação.
4. A **área de conteúdo acompanha** com a mesma duração e curva, senão a sidebar desliza
   e o conteúdo dá um salto atrasado.
5. A **barra indicadora do item ativo permanece visível** no estado colapsado. Sem ela,
   o operador perde a única pista de onde está.
6. A marca vira **monograma "L"** no estado colapsado, com fade cruzado de 160ms.
7. No rodapé, o e-mail do usuário desaparece e fica apenas o avatar com a inicial.

**Tooltip no estado colapsado.** Hover sobre o ícone abre tooltip à direita após 400ms
de atraso, com fundo `azul-900`, texto branco de 12px, raio `--raio-sm` e sombra nível
2. Entra com fade e translateX de 4px em 120ms. Sem o tooltip, o rail colapsado é
adivinhação.

**Controle.** Botão no rodapé da sidebar, acima do bloco de usuário, com o ícone de
painel e rótulo "Recolher" quando expandida. No estado colapsado, só o ícone, girado
para indicar a ação inversa. Atalho opcional de teclado: `[`.

**Persistência.** O estado escolhido sobrevive ao recarregamento da página. Quem
trabalha em tela menor recolhe uma vez e não toca mais.

**Acessibilidade.** O botão expõe `aria-expanded` e rótulo textual. Os tooltips precisam
ser anunciáveis por leitor de tela. Com `prefers-reduced-motion`, a largura muda
instantaneamente e os rótulos apenas aparecem ou desaparecem.

**Responsivo.** Abaixo de 1024px a sidebar inicia colapsada. O alvo é desktop, então não
há necessidade de gaveta sobreposta na v1.

### Cartões de resumo (novo, no relatório)

Faixa de quatro cartões acima da tabela de fechamento, cada um com rótulo pequeno em
maiúsculas, número grande em Inter e um container de ícone com fundo tingido:

| Cartão | Acento do ícone |
|---|---|
| Total em R$ | `azul-100` de fundo, `azul-700` de ícone |
| Total de peças | `azul-50` de fundo, `azul-600` de ícone |
| Lançamentos no período | `gelo-100` de fundo, `gelo-600` de ícone |
| Média diária de peças | `azul-50` de fundo, `azul-500` de ícone |

Isso resolve duas coisas ao mesmo tempo: dá ao operador a leitura imediata do
fechamento e abre espaço legítimo para cor sem tocar na tabela.

### Volume diário (novo, no relatório)

Gráfico de barras compacto, uma barra por dia do período, altura proporcional ao total
de peças. Rampa de `azul-300` a `azul-700` conforme o volume. Altura total de 80px,
sem eixos, com tooltip no hover. Comunica sazonalidade da semana de forma instantânea.

### Tabela de fechamento

Container com raio `--raio-lg`, borda `gelo-200` e sombra nível 1, com overflow
escondido para o cabeçalho respeitar o canto arredondado. Cabeçalho `gelo-100` com
rótulos em maiúsculas de 12px. Hover de linha em `azul-50`. Cabeçalho fixo ao rolar.
Colunas de item recebem um chip discreto de cor no cabeçalho, variando na escala azul,
para o olho acompanhar a coluna até o rodapé. Linha de totais com fundo `gelo-50`,
borda superior de 2px em `gelo-300` e números em peso 600.

### Formulário de lançamento

Duas zonas: cabeçalho do pedido (cliente, data, comanda) em um cartão, e a lista de
itens em outro. Cada linha de item é uma faixa com seleção de item, campo de quantidade,
valor unitário em cinza (somente leitura) e total da linha à direita. Remover linha é um
ícone que aparece no hover da faixa.

**Barra de totais fixa no rodapé**, com sombra nível 2, exibindo total de peças e total
em R$. É o momento de deleite do produto: a cada mudança de quantidade os números fazem
contagem animada e o fundo dá um flash suave. O operador vê o pedido crescer enquanto
digita.

### Botões

Primário: fundo `azul-600`, texto branco, raio `--raio-md`, sombra nível 1 que cresce em
hover, escala 0,98 ao pressionar. Secundário: fundo branco, borda `gelo-300`, texto
`azul-700`, hover com fundo `gelo-50`. Destrutivo: base de erro, usado só em
confirmação de exclusão. Fantasma: só texto `azul-700`, para ações terciárias.

### Estados vazios

Cartão centralizado com ilustração simples em traço de `azul-200` e `azul-400`, título
em Poppins 600, uma linha de orientação e o botão da ação principal. Nunca uma tabela
vazia com uma frase solta.

### Carregamento

**Skeleton, não spinner.** Linhas de tabela e cartões viram blocos `gelo-100` com
shimmer. O spinner fica reservado para ações dentro de botão.

**Estado de servidor acordando:** a hospedagem hiberna quando ociosa, e a primeira
requisição pode levar dezenas de segundos. Depois de 3 segundos de espera, aparece um
painel com fundo `azul-50`, borda `azul-200`, ícone animado e o texto "Reativando o
servidor, isso leva alguns segundos na primeira vez". Transformar a limitação técnica em
comunicação tranquila, em vez de deixar o operador achando que travou.

### Chips e badges

Item no formulário e no cabeçalho de coluna aparece como chip: fundo `azul-50`, texto
`azul-700`, borda `azul-200`, raio total. Situação inativa usa `gelo-100` com texto
`gelo-600` — neutro, porque inativo não é erro.

### Toast

Canto superior direito, fundo branco, sombra nível 2, barra colorida de 3px à esquerda
indicando o tipo, ícone, texto e fechar. Sucesso usa verde, erro usa vermelho — aqui a
cor de estado é apropriada porque comunica estado.

## 6. Onde a cor NÃO entra

Para o documento continuar auditável:

- Números de valor sempre em `gelo-800` ou `gelo-900`. Dinheiro não é colorido.
- Sem cor de fundo em células de valor, exceto o hover neutro da linha.
- Sem gradiente atrás de texto de leitura.
- Máximo de dois acentos de cor competindo na mesma tela.
