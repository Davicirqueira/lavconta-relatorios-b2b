# Plano de implementação — Lavconta v1

Ordem de construção pensada para que cada etapa seja verificável antes da próxima. A
regra de negócio é construída e testada **antes** da interface que a consome.

Referências `_Requisitos: X.Y_` apontam para `requirements.md`.

---

## Fase 1 — Fundação e segurança do repositório

- [ ] 1. Configurar barreira de segredos antes de qualquer arquivo sensível
  - Criar `.gitignore` na raiz cobrindo `.env`, `.env.*` (preservando `!.env.example`),
    `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `secrets/`, `__pycache__/`,
    `node_modules/`, `dist/`, `.venv/`
  - Criar `backend/.env.example` e `frontend/.env.example` apenas com nomes de chaves e
    comentário do que cada uma faz, sem valores reais
  - Verificar com `git status` que nenhum arquivo de segredo é rastreável
  - _Requisitos: 9.1, 9.3_

- [ ] 2. Criar a estrutura de pastas do monorepo
  - `backend/app/{core,models,schemas,repositories,services,exports,routers}`,
    `backend/migrations`, `backend/tests`
  - `frontend/src/{lib,features,components,pages,types}`
  - Arquivos `__init__.py` nos pacotes Python
  - _Requisitos: estrutura definida em `structure.md` e `design.md` §14_

- [ ] 3. Configurar o backend com dependências fixadas
  - Criar `backend/requirements.txt` com versões **pinadas**, conferindo cada pacote na
    página oficial do PyPI no momento da instalação
  - Conferir nome exato de cada pacote (`reportlab`, `openpyxl`, `pyjwt`) contra
    typosquatting
  - _Requisitos: 9.9_

- [ ] 4. Implementar configuração validada na inicialização
  - `app/core/config.py` com Pydantic `Settings` lendo `DATABASE_URL`,
    `SUPABASE_JWKS_URL`, `SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUDIENCE`, `CORS_ORIGENS`
  - Falha na ausência de variável obrigatória com erro que nomeia a chave, sem default
    inseguro
  - Teste: instanciar sem variável obrigatória levanta erro citando o nome da chave
  - _Requisitos: 9.2_

- [ ] 5. Criar o app FastAPI com borda configurada
  - `app/main.py` com CORS restrito às origens da configuração, rota `GET /api/saude`
    (única pública) e handler global de erros
  - `app/core/erros.py` com as exceções de domínio e o mapa de códigos do design §8.1
  - Handler devolve o envelope `{ "erro": { codigo, mensagem, detalhes } }` e nunca
    stack trace
  - _Requisitos: 9.5, 9.7_

- [ ] 6. Configurar CI no GitHub Actions
  - Workflow com lint, testes e build de backend e frontend
  - `pip-audit` e `npm audit`; scanner de segredos (gitleaks)
  - _Requisitos: 9.9, 9.10_

---

## Fase 2 — Banco de dados

- [ ] 7. Implementar os modelos ORM
  - `app/models/` com `Cliente`, `Item`, `Preco`, `Lancamento`, `LancamentoLinha`
  - `Numeric(10,2)` para preço, `Numeric(12,2)` para total, `Integer` para quantidade,
    `Date` para data de negócio, `DateTime(timezone=True)` para auditoria
  - _Requisitos: 4.11, 5.11, 11.1_

- [ ] 8. Criar a migração inicial com todas as constraints
  - Configurar Alembic e gerar a migração com o DDL do design §3.1
  - Incluir explicitamente: `clientes_nome_unico` (lower+btrim), FK composta
    `precos_item_do_cliente`, `precos_vigencia_primeiro_dia`, `precos_unico_por_mes`,
    `lancamentos_cliente_data_unico`, índice parcial
    `lancamentos_comanda_unica_por_cliente` sobre `lower(btrim(comanda))`,
    `linhas_item_unico_por_lancamento`, coluna gerada `total`, `on delete restrict` em
    cliente e item de lançamento
  - _Requisitos: 2.5, 5.3, 5.10, 5.12, 6.4_

- [ ] 9. Escrever testes de constraint contra Postgres
  - Segundo lançamento em (cliente, data) é rejeitado pelo banco
  - Comanda repetida com caixa diferente (`a100` vs `A100`) é rejeitada
  - Dois lançamentos sem comanda do mesmo cliente são aceitos
  - Item repetido no mesmo lançamento é rejeitado
  - Excluir cliente ou item com histórico é rejeitado pelo banco
  - Coluna `total` sempre igual a `valor_unitario_congelado × quantidade`
  - _Requisitos: 2.11, 3.12, 5.3, 5.10, 5.12_

---

## Fase 3 — Autenticação

- [ ] 10. Implementar validação completa de JWT
  - `app/core/seguranca.py` com busca de JWKS via `httpx`, cache em memória com TTL e
    recarga sob `kid` desconhecido
  - Validar assinatura, `exp`, `iss` e `aud`; falha → `401` com mensagem genérica
  - Dependência `usuario_atual` aplicada no nível do `APIRouter` de dados
  - _Requisitos: 1.3, 1.4, 1.5, 1.7_

- [ ] 11. Escrever testes de autenticação, incluindo o teste estrutural
  - Token válido passa; ausente, expirado, assinatura inválida, `aud` errado e `iss`
    errado retornam `401`
  - **Teste estrutural:** varrer as rotas registradas no app e falhar se alguma rota sob
    `/api` (exceto `/api/saude`) não exigir a dependência de autenticação
  - _Requisitos: 1.5, 1.7, 9.10_

---

## Fase 4 — Clientes e catálogo

- [ ] 12. Implementar repositório e serviço de clientes
  - `repositories/cliente_repo.py` com queries parametrizadas
  - `services/servico_cliente.py`: criar, renomear, listar ordenado por nome, inativar,
    reativar, excluir só sem lançamentos
  - Nome duplicado (ignorando caixa e espaços) → `NOME_DUPLICADO`
  - Exclusão com histórico → `EXCLUSAO_COM_HISTORICO` sugerindo inativação
  - _Requisitos: 2.1–2.11_

- [ ] 13. Expor os endpoints de clientes
  - Router com GET (com `incluir_inativos`), POST, PATCH, inativar, reativar, DELETE
  - Schemas Pydantic de entrada e saída separados dos modelos ORM
  - _Requisitos: 2.1–2.11_

- [ ] 14. Implementar repositório e serviço de itens
  - Item vinculado a cliente; nome único por cliente ignorando caixa
  - Inativar, reativar; exclusão apenas de item nunca usado
  - _Requisitos: 3.1–3.13_

- [ ] 15. Expor os endpoints de itens
  - GET/POST em `/api/clientes/{cliente_id}/itens`; PATCH, inativar, reativar e DELETE em
    `/api/itens/{id}`
  - _Requisitos: 3.1–3.13_

---

## Fase 5 — Preços e resolução de vigência

- [ ] 16. Implementar a resolução de preço vigente
  - `repositories/preco_repo.py` com a consulta `DISTINCT ON` em lote do design §5
  - `services/servico_preco.py` com `resolver_precos(cliente_id, item_ids, data)`
    devolvendo preços encontrados e itens sem preço
  - Normalizar `vigencia_mes` para o primeiro dia do mês
  - _Requisitos: 4.4, 4.6, 4.7, 4.8_

- [ ] 17. Escrever os testes de resolução de preço
  - Propagação: preço de junho vale em setembro e em dezembro
  - Mês com vigência própria sobrepõe a propagação
  - Lançamento retroativo recebe o preço do mês do pedido, não do mês corrente
  - Sem preço anterior algum → item classificado como sem preço
  - Fronteiras: primeiro e último dia do mês resolvem o mesmo preço
  - _Requisitos: 4.4, 4.6, 4.7, 4.8_

- [ ] 18. Implementar definição e correção de preço
  - Upsert por (cliente, item, mês); recusar valor ≤ 0 e mais de duas casas decimais
  - Permitir correção de mês passado
  - _Requisitos: 4.2, 4.9, 4.12, 4.13, 4.14, 4.17_

- [ ] 19. Expor os endpoints de preços
  - `GET /api/clientes/{id}/precos?mes=YYYY-MM` devolvendo preço resolvido por item,
    `vigencia_origem` e sinalizador `sem_preco`
  - `PUT /api/clientes/{id}/precos` para upsert
  - _Requisitos: 4.10, 4.14_

---

## Fase 6 — Lançamentos e congelamento

- [ ] 20. Implementar utilitário de data de negócio
  - `app/core/datas.py` com `FUSO_NEGOCIO = ZoneInfo("America/Sao_Paulo")` e `hoje_sp()`
  - Única fonte de "hoje" no backend
  - Teste: `hoje_sp()` independe do fuso do processo
  - _Requisitos: 11.6, 11.7_

- [ ] 21. Implementar o cálculo compartilhado de lançamento
  - `_resolver_e_calcular` em `servico_lancamento`: resolve preços pelo mês da data,
    calcula total por linha, total de peças e total em R$ com `Decimal`
  - Usado por criar, editar e prévia — implementação única de cálculo
  - _Requisitos: 6.1, 6.4, 6.5, 6.6_

- [ ] 22. Implementar criação de lançamento com congelamento
  - Validar data não futura, comanda normalizada, itens do cliente, sem repetição
  - Recusar com `ITENS_SEM_PRECO` nomeando os itens faltantes
  - Transação única inserindo lançamento e linhas com `valor_unitario_congelado`
  - Traduzir violações de constraint em `LANCAMENTO_DUPLICADO` e `COMANDA_DUPLICADA`
  - _Requisitos: 5.1–5.16, 6.1_

- [ ] 23. Implementar edição de lançamento preservando o congelamento
  - Linha existente: mantém valor congelado, atualiza só quantidade
  - Linha nova: congela pelo preço vigente do **mês da data do lançamento**
  - Alteração de cliente ou data revalida unicidade e data futura
  - _Requisitos: 5.17–5.20, 6.3_

- [ ] 24. Implementar exclusão de lançamento
  - Remoção do lançamento e das linhas em cascata
  - _Requisitos: 5.21, 5.23_

- [ ] 25. Implementar a prévia de totais
  - `calcular_previa` reutilizando `_resolver_e_calcular`, sem persistir
  - Devolve `itens_sem_preco` como lista, sem levantar erro
  - Não valida data futura, unicidade nem comanda
  - _Requisitos: 6.8; design §8.2 e §9.3_

- [ ] 26. Escrever os testes de congelamento e cálculo
  - Criação grava o preço vigente do mês da data
  - Alterar preço depois não muda lançamento nem total já criado
  - Edição preserva o congelado da linha existente
  - Linha nova em edição usa o mês da data do lançamento, não o mês corrente
  - Totais de linha, de peças e em R$ conferem
  - **Prévia e salvamento produzem totais idênticos** para a mesma entrada
  - Prévia com item sem preço devolve a lista; salvamento da mesma entrada é recusado
  - Lançamento em 31 e em 01 não muda de mês; data futura recusada
  - _Requisitos: 5.15, 6.1–6.6, 11.5_

- [ ] 27. Expor os endpoints de lançamentos
  - GET com filtro de cliente e período, POST, `POST /previa`, GET por id, PUT, DELETE
  - _Requisitos: 5.1–5.23_

---

## Fase 7 — Relatório e exportação

- [ ] 28. Implementar a geração do relatório
  - `servico_relatorio.gerar` com a consulta única do design §9.4
  - Validar `inicio <= fim` → `PERIODO_INVALIDO`
  - Colunas apenas dos itens presentes no período, em ordem alfabética
  - Quantidades como mapa `item_id → quantidade`; item ausente não entra no mapa
  - `totais` e `resumo` derivados da **mesma** agregação
  - _Requisitos: 7.1–7.14_

- [ ] 29. Escrever os testes de relatório
  - Colunas só de itens com ocorrência; item do catálogo sem ocorrência não gera coluna
  - Lançamento sem comanda mantém a estrutura da linha
  - Período cruzando meses soma valores congelados distintos, sem reaplicar preço
  - Período sem lançamentos devolve totais zerados
  - Ordenação por data crescente
  - **`resumo` e `totais` coincidem sempre** (regressão do defeito B1)
  - _Requisitos: 7.7, 7.8, 7.9, 7.12, 7.13_

- [ ] 30. Expor o endpoint de relatório
  - `GET /api/relatorio` com cliente e período obrigatórios
  - _Requisitos: 7.1, 7.2_

- [ ] 31. Implementar a exportação Excel
  - `exports/excel.py` com `openpyxl`, consumindo a estrutura já calculada
  - Quantidades como inteiro e valores como número com formato monetário — células
    numéricas reais
  - Cabeçalho com cliente e período; linha de totais destacada; primeira linha congelada
  - _Requisitos: 8.2, 8.3, 8.5, 8.6_

- [ ] 32. Implementar a exportação PDF
  - `exports/pdf.py` com `reportlab` em A4 paisagem, tabela via `platypus`
  - Cabeçalho com cliente, período e data de geração; linha de totais destacada
  - Degradar fonte e largura das colunas de item quando houver muitas, preservando Data,
    Total de peças e Total R$
  - _Requisitos: 8.2, 8.3, 8.5_

- [ ] 33. Expor os endpoints de exportação
  - `GET /api/relatorio/pdf` e `/excel` com `Content-Disposition`, nome descritivo do
    arquivo e `content-type` correto
  - Teste: ambos os formatos reproduzem os mesmos totais do relatório em tela
  - _Requisitos: 8.1, 8.4_

- [ ] 34. Aplicar rate limiting
  - `slowapi` nas rotas de escrita e exportação; limite próprio, mais permissivo, para
    `/api/lancamentos/previa`
  - _Requisitos: definido em `engineering.md` §4; design §12_

---

## Fase 8 — Fundação do frontend

- [ ] 35. Configurar o projeto Vite com os tokens visuais
  - Projeto React + TypeScript; dependências com versão exata e lockfile versionado
  - CSS global com os tokens de `id-visual.md`: cores, tipografia, sombras tingidas,
    raios, durações e curvas, e o bloco `prefers-reduced-motion`
  - Fontes Poppins e Inter; classe utilitária de numerais tabulares
  - _Requisitos: 9.9, 10.1, 10.2_

- [ ] 36. Implementar os utilitários de data e dinheiro
  - `lib/datas.ts` com `paraExibicao`, `paraIso` e `hojeSp` — sem `new Date()` em data de
    negócio
  - `lib/dinheiro.ts` formatando a partir de string decimal com `Intl.NumberFormat('pt-BR')`
  - Testes: data 31/08 e 01/09 não mudam de dia em nenhuma conversão
  - _Requisitos: 10.3, 11.2, 11.3, 11.5_

- [ ] 37. Implementar o cliente de API
  - `lib/api.ts` injetando o JWT, traduzindo o envelope de erro em mensagens em
    português e expondo sinal de requisição lenta acima de 3s
  - _Requisitos: 1.3, 10.4, 10.6_

- [ ] 38. Construir a biblioteca de componentes base
  - `Botao` (primário, secundário, destrutivo, fantasma), `Campo`, `Selecao`,
    `CampoData`, `Tabela`, `Modal`, `DialogoConfirmacao`, `Toast`, `Skeleton`, `Chip`,
    `Badge`, `EstadoVazio`, `PainelServidorAcordando`
  - Animações conforme o catálogo de movimento do brief; foco visível; rótulos associados
  - _Requisitos: 10.1, 10.4, 10.5, 10.6_

- [ ] 39. Construir o layout com sidebar colapsável
  - Sidebar com gradiente, ícones Lucide (`ClipboardList`, `FileBarChart2`, `Building2`,
    `Shirt`, `Tag`), barra indicadora deslizante do item ativo
  - Colapso 240px ↔ 68px: rótulos em fade antes de contrair a largura, conteúdo
    acompanhando na mesma curva, tooltip no rail, estado persistido
  - `aria-expanded` no controle; movimento respeitando `prefers-reduced-motion`
  - _Requisitos: 10.1, 10.5_

- [ ] 40. Implementar autenticação no frontend
  - Cliente Supabase, tela de login, recuperação e redefinição de senha
  - **Sem rota ou link de cadastro**; rotas protegidas redirecionando para login; aviso de
    sessão expirada
  - _Requisitos: 1.1, 1.2, 1.6, 1.8, 1.10, 1.11, 1.12_

---

## Fase 9 — Telas de gestão

- [ ] 41. Implementar a tela de clientes
  - Lista com situação, busca, alternância de inativos; formulário de nome
  - Inativar e reativar; exclusão com diálogo de confirmação e mensagem explicativa
    quando houver histórico
  - Sem campo de endereço (avaliação B7)
  - _Requisitos: 2.1–2.11_

- [ ] 42. Implementar a tela de catálogo
  - Seleção de cliente, lista de itens com situação, alternância de inativos, formulário
  - Sem categoria de item (avaliação B5)
  - _Requisitos: 3.1–3.13_

- [ ] 43. Implementar a tela de preços
  - Seleção de cliente e mês; lista de itens com preço vigente e `vigencia_origem`
  - Destaque de alerta para itens sem preço
  - Formulário com valor de duas casas e mês de vigência, sugerindo mês seguinte na
    alteração e mês corrente no primeiro preço
  - Aviso ao corrigir mês passado: lançamentos já registrados não mudam
  - Sem coluna de margem (avaliação B4)
  - _Requisitos: 4.9–4.18_

---

## Fase 10 — Lançamento e relatório

- [ ] 44. Implementar a lista de lançamentos
  - Filtros de cliente e período; tabela com data, cliente, comanda, peças e total
  - Ações de editar e excluir com confirmação identificando cliente e data
  - _Requisitos: 5.21, 5.22, 10.3_

- [ ] 45. Implementar o formulário de lançamento
  - Cabeçalho com cliente, data (padrão hoje em SP) e comanda marcada como opcional
  - Linhas de item com seleção do catálogo do cliente, quantidade aceitando **digitação
    direta e stepper**, valor unitário e total de linha somente leitura
  - Alternância "incluir itens inativos"
  - Sem campo de notas ou observações (avaliação B3)
  - Mensagens de erro em linha para data duplicada, comanda duplicada e itens sem preço
  - _Requisitos: 5.1–5.16, 6.8, 10.4; avaliação C1_

- [ ] 46. Implementar a barra de totais animada
  - Barra fixa no rodapé com total de peças e total em R$
  - Chamada a `POST /api/lancamentos/previa` com debounce de 400ms e cancelamento de
    requisição em voo
  - Contagem animada dos números e flash suave de fundo ao recalcular
  - Valores anteriores permanecem visíveis durante a prévia em voo; falha da prévia não
    bloqueia o salvamento
  - `itens_sem_preco` marca as linhas envolvidas antes de tentar salvar
  - _Requisitos: 6.8, 10.6; design §11_

- [ ] 47. Implementar a tela de relatório
  - Filtros de cliente e período, com padrão do primeiro ao último dia do mês vigente em SP
  - Quatro cartões de resumo: **Total de Peças, Total R$, Nº de Lançamentos e Média
    Diária de Peças** — sem ticket médio e sem variação percentual (avaliação B2)
  - Gráfico de volume diário em CSS puro com a rampa azul
  - Tabela de fechamento com colunas dinâmicas de item, célula vazia quando ausente,
    cabeçalho fixo ao rolar e linha de totais destacada
  - Estado vazio com totais zerados
  - _Requisitos: 7.1–7.14, 10.1, 10.2_

- [ ] 48. Implementar a exportação no frontend
  - Botões de PDF e Excel acionando o download com indicação de progresso
  - _Requisitos: 8.1, 8.4_

- [ ] 49. Padronizar a terminologia da interface
  - Revisar todos os textos visíveis contra o glossário: **peças, lançamento, preço,
    relação de valores, cliente**
  - Remover vocabulário de "carga", "processamento", "tarifário", "acordo" e "contrato"
    (avaliação B6)
  - _Requisitos: 10.7_

---

## Fase 11 — Deploy e verificação final

- [ ] 50. Versionar a configuração de deploy
  - `render.yaml` para a API e `netlify.toml` para o frontend, sem nenhum segredo
    embutido
  - Documentar no `README` quais variáveis configurar em cada plataforma
  - _Requisitos: 9.1, 9.3, 9.4_

- [ ] 51. Verificação final ponta a ponta
  - Rodar build e a suíte completa de backend e frontend
  - Conferir manualmente o fluxo crítico: cadastrar cliente, item e preço; lançar pedido;
    gerar relatório; exportar PDF e Excel
  - Conferir que o total dos cartões, o da tabela, o do PDF e o do Excel são idênticos
  - Revisar o diff completo procurando segredo antes do commit final
  - _Requisitos: 6.4, 8.2, 9.1_
