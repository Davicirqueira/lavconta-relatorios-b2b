---
inclusion: fileMatch
fileMatchPattern: 'frontend/**'
---

# Lavconta — Relatórios B2B · Identidade visual

Aplicação web de relatórios B2B da **Lavandix** (lavanderia e toalheria profissional, zona sul de São Paulo).

- **Direção:** paleta consistente e objetiva, com derivações proporcionais de azul, branco e gelo.
- **Tipografia:** Poppins.
- **Estados:** sucesso (verde), alerta (amarelo) e erro (vermelho), todos em tons médios: nem muito intensos, nem fracos.

> **Observação:** a paleta não foi extraída do logo atual da Lavandix. O site institucional foi consultado apenas pelo conteúdo, sem acesso ao CSS nem à imagem do logo. Se o logo tiver um azul próprio, ajustar o matiz da escala azul (mantendo os mesmos degraus de luminosidade) para alinhar.

---

## 1. Princípios

1. **Uma família de cor só.** Toda a interface nasce de azul + gelo. Sem cores de marca extras.
2. **Proporção, não improviso.** As escalas usam matiz fixo e degraus regulares de luminosidade, com saturação acompanhando.
3. **Cor de estado comunica estado.** Verde, amarelo e vermelho aparecem só para sucesso, alerta e erro, nunca como decoração.
4. **Regra 60/30/10.** Cerca de 60% branco e gelo, 30% neutros (texto e bordas), 10% azul.
5. **Acessibilidade primeiro.** Todo par texto/fundo de uso corrente atende WCAG AA (4,5:1 para texto normal).

---

## 2. Tipografia

Duas famílias, cada uma para a tarefa em que é melhor:

- **Poppins — interface.** Títulos, rótulos, botões, navegação e corpo de texto.
  Comunica a marca (geométrica, limpa, moderna).
- **Inter — números.** Toda coluna/valor numérico em tabelas e relatórios
  (valores em R$, quantidades, totais). Inter tem **numerais tabulares** nativos,
  garantindo que as colunas de dinheiro alinhem a vírgula. Pareia bem com Poppins
  e é gratuita.

**Motivo:** o núcleo do produto é uma tabela de valores em R$ que o cliente audita.
Poppins não tem numerais tabulares por padrão, então os dígitos "dançam" nas colunas.
Inter resolve isso sem trocar a identidade da interface.

| Uso | Família | Peso |
|---|---|---|
| Títulos | Poppins | 600 (SemiBold) |
| Rótulos, botões, cabeçalho de tabela | Poppins | 500 (Medium) |
| Corpo de texto | Poppins | 400 (Regular) |
| Valores numéricos em tabelas/relatórios | Inter | 400/500 |

**Implementação dos números:** aplicar a família Inter **e**
`font-variant-numeric: tabular-nums` nas células numéricas, para alinhamento
vertical consistente dos dígitos.

---

## 3. Paleta

### 3.1 Azul (marca)

| Token | Hex | Uso |
|---|---|---|
| `azul-50` | `#F1F7FF` | Fundo de destaque, hover de linha |
| `azul-100` | `#DEEDFF` | Fundo de item selecionado |
| `azul-200` | `#C1DCFE` | Bordas de foco, faixas |
| `azul-300` | `#9EC6F9` | Ícones em fundo escuro |
| `azul-400` | `#76ACF1` | Gráficos, estados hover |
| `azul-500` | `#4F91E2` | Gráficos e elementos decorativos |
| **`azul-600`** | **`#2D74CA`** | **Primária: botões, links, foco** |
| `azul-700` | `#1C5CA6` | Botão pressionado, texto de ênfase |
| `azul-800` | `#13457E` | Títulos de destaque |
| `azul-900` | `#0B2F58` | Sidebar e cabeçalho |

### 3.2 Gelo e branco (superfícies e texto)

| Token | Hex | Uso |
|---|---|---|
| `branco` | `#FFFFFF` | Cartões, tabelas |
| `gelo-50` | `#F8FAFD` | Fundo do app |
| `gelo-100` | `#F0F4F9` | Cabeçalho de tabela, campos |
| `gelo-200` | `#E0E7EE` | Bordas e divisórias |
| `gelo-300` | `#CDD5DF` | Bordas de input |
| `gelo-400` | `#A2ACB7` | Placeholder, ícones inativos |
| `gelo-500` | `#76828E` | Apenas texto grande ou decorativo |
| `gelo-600` | `#56626F` | Texto secundário |
| `gelo-700` | `#3D4955` | Corpo de texto |
| `gelo-800` | `#252F3A` | Títulos |
| `gelo-900` | `#141B24` | Texto de máximo contraste |

### 3.3 Estados (tons médios)

Cada estado tem quatro variações:

- **Base:** preenchimento e ícone.
- **Suave:** fundo de alerta e badge.
- **Borda:** contorno de alertas e badges.
- **Forte:** texto sobre o fundo suave.

| Estado | Base | Suave | Borda | Forte |
|---|---|---|---|---|
| Sucesso | `#1E8650` | `#E5FAEB` | `#B4DDC0` | `#005E31` |
| Alerta | `#E7B643` | `#FDF2DD` | `#E4CFA2` | `#6A4500` |
| Erro | `#D03739` | `#FFE9E5` | `#FFBCB5` | `#98181F` |

O **info** é o próprio `azul-600`; não há quarta cor de estado.

---

## 4. Contraste (WCAG)

| Par | Razão | Resultado |
|---|---|---|
| Branco sobre `azul-600` | 4,71:1 | AA |
| Branco sobre `azul-700` | 6,71:1 | AA |
| Branco sobre `azul-900` | 13,45:1 | AAA |
| `azul-300` sobre `azul-900` | 7,62:1 | AAA |
| `gelo-700` sobre branco | 9,2:1 | AAA |
| `gelo-600` sobre `gelo-50` | 5,96:1 | AA |
| Branco sobre base de sucesso | 4,58:1 | AA |
| Branco sobre base de erro | 4,90:1 | AA |
| Texto "forte" sobre "suave" (3 estados) | 7,3:1 a 7,7:1 | AAA |

**Atenção:**

- **Amarelo:** branco sobre a base de alerta dá só 1,88:1. Em botões e badges de alerta preenchidos, usar texto `gelo-900` (9,2:1), nunca branco.
- **`gelo-500`:** sobre `gelo-50` dá 3,75:1. Não usar para texto pequeno.

---

## 5. Aplicação na interface

| Elemento | Especificação |
|---|---|
| Fundo do app | `gelo-50` |
| Cartões e tabelas | `branco`, borda `gelo-200` |
| Cabeçalho de tabela | `gelo-100`, texto `gelo-600` (Poppins 500) |
| Sidebar | `azul-900`, texto branco, ícones `azul-300`, item ativo `azul-800` |
| Botão primário | Fundo `azul-600`, texto branco; hover `azul-500`; pressionado `azul-700` |
| Botão secundário | Fundo branco, borda `gelo-300`, texto `azul-700` |
| Link | `azul-600`, sublinhado no hover |
| Foco | Anel de 2px em `azul-200` com borda `azul-600` |
| Badge de estado | Fundo "suave", borda "borda", texto "forte" |
| Alerta (banner) | Fundo "suave", borda "borda", ícone "base", texto "forte" |

---

## 6. Gráficos e relatórios

- **Volume e variação:** rampa sequencial de azul (`azul-100` a `azul-800`).
- **Metas, atrasos e desvios:** verde, amarelo e vermelho, reservados a esse significado.
- Nunca depender só da cor: usar rótulos, ícones ou padrões nas séries.

---

## 7. Tokens (CSS)

```css
:root {
  /* Azul (marca) */
  --azul-50: #F1F7FF;
  --azul-100: #DEEDFF;
  --azul-200: #C1DCFE;
  --azul-300: #9EC6F9;
  --azul-400: #76ACF1;
  --azul-500: #4F91E2;
  --azul-600: #2D74CA;
  --azul-700: #1C5CA6;
  --azul-800: #13457E;
  --azul-900: #0B2F58;

  /* Gelo e branco */
  --branco: #FFFFFF;
  --gelo-50: #F8FAFD;
  --gelo-100: #F0F4F9;
  --gelo-200: #E0E7EE;
  --gelo-300: #CDD5DF;
  --gelo-400: #A2ACB7;
  --gelo-500: #76828E;
  --gelo-600: #56626F;
  --gelo-700: #3D4955;
  --gelo-800: #252F3A;
  --gelo-900: #141B24;

  /* Estados */
  --sucesso-base: #1E8650;
  --sucesso-suave: #E5FAEB;
  --sucesso-borda: #B4DDC0;
  --sucesso-forte: #005E31;

  --alerta-base: #E7B643;
  --alerta-suave: #FDF2DD;
  --alerta-borda: #E4CFA2;
  --alerta-forte: #6A4500;

  --erro-base: #D03739;
  --erro-suave: #FFE9E5;
  --erro-borda: #FFBCB5;
  --erro-forte: #98181F;

  /* Tipografia */
  --fonte: "Poppins", system-ui, -apple-system, "Segoe UI", sans-serif;
  --fonte-numeros: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
}

/* Células numéricas: alinhamento consistente dos dígitos */
.num,
td.num,
.valor {
  font-family: var(--fonte-numeros);
  font-variant-numeric: tabular-nums;
}
```