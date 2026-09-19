# Layout do relatório de fechamento

Tela mais importante do produto. É a relação de valores que a lavanderia envia ao
cliente-empresa para conferência e cobrança. Precisa ser densa, legível e auditável.

## Cabeçalho do relatório

Acima da tabela, identificando o documento:

- Nome do cliente, em destaque.
- Período: "01/09/2026 a 30/09/2026".
- (No PDF) nome da empresa emissora e data de geração.

## Estrutura da tabela

As colunas do meio são **dinâmicas**: uma coluna por tipo de item, contendo apenas os
itens que apareceram no período. Itens do catálogo sem ocorrência no período **não**
geram coluna.

Ordem das colunas:

1. **Data** (dd/mm/yyyy)
2. **Comanda** (pode estar vazia)
3. **Uma coluna por item** (quantidade)
4. **Total de peças** da linha
5. **Total R$** da linha

Linha final de **totais do período**: soma de cada coluna de item, total de peças e
total em R$.

## Exemplo preenchido (dados fictícios)

Cliente: Hotel Aurora · Período: 01/09/2026 a 05/09/2026

| Data | Comanda | Lençol | Fronha | Toalha | Total de peças | Total R$ |
|---|---|---|---|---|---|---|
| 01/09/2026 | 1201 | 40 | 30 | 20 | 90 | 315,00 |
| 02/09/2026 | 1202 | 35 | 25 | 15 | 75 | 262,50 |
| 03/09/2026 |  | 50 | 40 |  | 90 | 330,00 |
| 04/09/2026 | 1204 | 20 |  | 10 | 30 | 105,00 |
| 05/09/2026 | 1205 | 45 | 35 | 25 | 105 | 367,50 |
| **Totais** |  | **190** | **130** | **70** | **390** | **1.380,00** |

Observe no exemplo:

- A linha de 03/09 **não tem comanda** — a célula fica vazia, a coluna continua
  existindo e o layout não muda.
- Células de item sem quantidade naquele dia ficam **vazias**, não exibem zero.
- Só há três colunas de item porque só três itens apareceram no período, mesmo que o
  catálogo do cliente tenha mais.

## Regras visuais

- Linhas ordenadas por data crescente.
- Números alinhados à direita; datas e comanda alinhadas à esquerda.
- Dígitos com alinhamento tabular, para as colunas de valores casarem verticalmente.
- Cabeçalho de tabela com fundo de tom claro e texto de peso médio.
- Linha de totais visualmente separada (borda superior mais forte e peso maior).
- Alternância suave de cor nas linhas ou hover de linha para facilitar a leitura
  horizontal em tabelas longas.
- Um fechamento mensal tem no máximo 31 linhas: não há paginação.

## Consideração para o PDF

O número de colunas de item varia por cliente e período. O layout deve degradar bem
quando houver muitas colunas: orientação paisagem, fonte um pouco menor e colunas de
item com largura compacta, mantendo Data, Total de peças e Total R$ sempre legíveis.
