# Plano de implementação — Lavconta v1.1

Ordem pensada para que cada etapa seja verificável antes da próxima. A regra de
negócio é construída e testada **antes** da interface que a consome. Nada vai para
produção antes da Fase 6.

Referências: `_Req X.Y_` → `requirements.md`; `§N` → `design.md`.

Em toda tarefa: build e testes passando antes de marcar; teste novo provado por
sabotagem quando for detector ou regra crítica (skill `estrategia-de-teste`); tela
conferida no navegador com `lavconta_dev` quando houver UI (skill `design-de-interface`).

---

## Fase 1 — Preço por data (backend)

- [x] 1. Escrever a migração de fase 1 (expand)
  - Revisão `v11_preco_por_data` sobre `54016f7a3787`: coluna `vigencia_inicio`
    preenchida com `vigencia_mes` e `NOT NULL`; `uq_precos_cliente_item_inicio`;
    `ix_precos_resolucao_inicio`; remover `uq_precos_cliente_item_mes`;
    `vigencia_mes` passa a aceitar nulo
  - Downgrade conforme §2, com a limitação documentada no próprio arquivo
  - Atualizar o modelo `Preco` (coluna nova, constraints novas, `vigencia_mes` opcional)
  - Aplicar no `lavconta_teste` e no `lavconta_dev`: `upgrade`, `downgrade`, `upgrade`
  - _Req 2.1, 2.3, 2.4 · §1.1, §2_

- [x] 2. Reescrever a resolução no repositório
  - `resolver_vigentes(cliente, itens, data)` com a regra do §1.2 (vigente mais
    recente ≤ data; senão o primeiro; senão sem preço), em uma consulta
  - `obter_atual(cliente, item, hoje)` e `listar_na_data(cliente, data, incluir_inativos)`
  - Remover `obter_do_mes` e `existe_algum`; atualizar `RepositorioPrecoProtocolo`
    e `RepositorioPrecoFalso` (mesma regra, para os testes sem banco)
  - `PrecoVigente.vigencia_origem` → `desde`
  - _Req 1.1, 1.3, 1.7 · §1.2_

- [x] 3. Reescrever as operações do `ServicoPreco`
  - Relógio injetado `hoje: Callable[[], date]` (padrão `hoje_sp`)
  - `mudar_a_partir_de_hoje`, `corrigir_atual`, `definir_primeiro`, `impacto`
    (§1.4); manter `_validar_valor`
  - Remover `vigencia_sugerida`, `listar_do_mes` e a tradução de `ck_..._primeiro_dia`;
    traduzir `uq_precos_cliente_item_inicio`
  - _Req 1.2, 1.4, 1.6, 1.9, 1.11–1.13 · §1.3, §1.4_

- [x] 4. Ajustar o lançamento à resolução por data
  - `ServicoLancamento` passa a data do pedido (não mais o mês) à resolução
  - `itens_sem_preco` sem mês: mensagem nova do §4; `detalhes` sem `mes_referencia`
  - Remover `_mes_em_portugues`, `mes_de_referencia` e helpers de mês sem uso
    (`primeiro_dia_do_mes`, `mes_seguinte`, `mes_como_texto`, `texto_para_mes`) se não
    restar consumidor
  - _Req 1.3, 1.5, 4.3 · §1.2, §4_

- [x] 5. Reescrever os testes de preço e congelamento
  - Substituir os testes de mês/vigência sugerida/dia 1 pelos casos do §7 (resolução,
    escrita, congelamento, constraint) — com banco real e sem banco
  - Teste de que um campo de data enviado no corpo é ignorado
  - Teste de migração: contagem e valores preservados, `vigencia_inicio = vigencia_mes`
  - Sabotar a regra "primeiro preço vale para trás" e confirmar que o teste acusa
  - _Req 1, 2 · §7_

- [x] 6. Atualizar o seed de desenvolvimento
  - `preparar_banco.py` com relógio fixo: preço inicial em junho, reajuste do Lençol
    (Hotel Aurora) em 15/09, Edredom sem preço
  - Recriar `lavconta_dev` e conferir
  - _§8_

---

## Fase 2 — Preço no Catálogo (API)

- [x] 7. Expor o preço atual na listagem de itens
  - `ItemResposta.preco_atual: PrecoAtual | null` (`valor_unitario`, `desde`, `e_hoje`),
    resolvido em uma consulta para a lista toda
  - _Req 3.4, 3.5, 3.7 · §3.1_

- [x] 8. Criar item com preço de forma atômica
  - `ServicoCatalogo.criar_item_com_preco` orquestrando `ServicoItem` e `ServicoPreco`
  - `POST /api/clientes/{id}/itens` exige `nome` e `valor_unitario`
  - Teste: preço inválido → item não existe no banco
  - _Req 3.1, 3.3 · §3.2_

- [x] 9. Rotas de preço do item
  - **Adiantado no bloco 2–5** (os testes de lançamento e relatório precisavam de um
    caminho de API para definir preço): `PUT /api/itens/{id}/preco` (`modo`, 60/min),
    `GET /api/itens/{id}/preco/impacto`, `GET /api/clientes/{id}/precos?data=`,
    rotas antigas removidas, relógio `hoje_de_negocio` como dependência
  - Concluído na Fase 2: rate limit 60/min nas escritas de item (criar, renomear,
    inativar, reativar, excluir) e teste de 429 nas rotas reais
  - Conferir no OpenAPI que nenhuma rota nova ficou sem autenticação (teste estrutural
    existente)
  - _Req 1.2, 1.6, 1.13, 3.2 · §3.1_

---

## Fase 3 — Preço no Catálogo (interface) e textos

- [x] 10. Conversão de dinheiro sem ponto flutuante
  - Utilitário em `lib/dinheiro.ts`: texto com vírgula → texto decimal com duas casas,
    recusando formato inválido; testes de borda (`4,5`, `4,50`, `1.234,56`, `0`, `-1`,
    `4,555`)
  - _§3.3_

- [x] 11. Formulário de item com preço
  - Campos nome e preço; criar exige os dois
  - Editar: escolha "Mudar a partir de hoje" / "Corrigir o preço atual" só quando o
    preço mudou e `e_hoje` é falso; aviso de impacto antes de confirmar
  - Textos do §3.3 e §4; foco, rótulos, erro associado ao campo
  - _Req 1.6, 1.11–1.14, 3.1, 3.2, 4.1 · §3.3_

- [x] 12. Cartão do item com preço
  - Linha "R$ X por peça"; sem preço: badge "Sem preço" e ação "Definir preço"
  - Medir rodapé e altura dos cartões em 1024, 1280, 1366, 1600, 1920 e ~700
  - _Req 3.4, 3.5 · §3.3_

- [x] 13. Remover a tela de Preços
  - Apagar `features/precos/` e `pages/Precos.tsx`; rota `/precos` →
    `<Navigate to="/catalogo" replace />`; tirar "Preços" do menu
  - `usePrecosNaData` em `features/catalogo/hooks.ts` para o formulário de lançamento
  - Atualizar `types/api.ts`
  - _Req 3.6 · §3.3_

- [x] 14. Revisar os textos
  - Aplicar a tabela do §4 (lançamento, catálogo, mensagem da API)
  - Ajustar `logica.test.ts` e `api.test.ts` ao novo `detalhes`
  - Busca final por "vigência", "vigente", "mês" em `frontend/src` e nas mensagens
    de `backend/app`: nenhum resto ligado a preço
  - _Req 4.1–4.4 · §4_

---

## Fase 4 — Relatório geral

- [x] 15. Domínio e consulta do relatório geral
  - `LinhaResumoItem`, `SecaoDoCliente`, `RelatorioGeral`; `Relatorio.resumo_por_item`
  - `buscar_resumo_geral(inicio, fim)` agrupado (§5.2); montagem e totais no serviço
  - Testes: inativo com pedido aparece; sem pedido não aparece; dois valores = duas
    linhas; total geral = soma dos relatórios por cliente
  - _Req 5.2–5.5, 5.8, 6.4 · §5.1, §5.2, §5.6_

- [x] 16. Rotas do relatório geral
  - `GET /api/relatorio/geral` e `/geral/excel` (30/min na exportação); `/geral/pdf`
    fica para a tarefa 22, junto com o PDF geral;
    `resumo_por_item` também na resposta por cliente
  - _Req 5.6, 5.9 · §5.3_

- [x] 17. Excel do relatório geral
  - Aba "Resumo" e uma aba por cliente; nomes de aba válidos e únicos
  - Teste de paridade com a tela
  - _Req 5.6, 5.7 · §5.5_

- [x] 18. Interface do relatório geral
  - Opção "Todos os clientes" (`?cliente=todos`); componente `RelatorioGeral`;
    exportação pelas rotas `/geral/*`; estado vazio
  - Conferir no navegador com `lavconta_dev`
  - _Req 5.1, 5.2, 5.3 · §5.4_

---

## Fase 5 — PDF

- [x] 19. Organizar o pacote `exports/pdf/`
  - Separar `estilo`, `marca`, `pagina`, `colunas`, `fechamento`, `geral` (§6.1)
    mantendo a assinatura de `gerar_pdf`; testes existentes verdes sem mudança
  - Feito: `estilo`, `marca`, `pagina`, `colunas`, `fechamento`; `geral.py` nasce
    na tarefa 22. Texto, imagens e página dos PDFs (1, 3, 12, 18 itens) idênticos
    antes/depois, com comparação provada por sabotagem
  - _§6.1_

- [x] 20. Logo com proporção real
  - Ver o original antes; recortar a margem com Pillow e versionar o PNG novo
  - Altura calculada pela proporção do arquivo
  - Feito: original é só o emblema (círculo + "LAVANDIX" + "LAVANDERIA", fundo
    transparente). `lavandix-marca-emblema.png` (600×538) já era o recorte dele
    (diferença média zero) e passou a ser o asset; `lavandix-marca.png` removido.
    Desenhado com 120 pt de largura, altura pela proporção (~107,6 pt). Teste em
    `test_pdf_marca.py`, provado por sabotagem (altura fixa 28 → falha).
    Conferir no PDF renderizado se a altura do cabeçalho ficou boa: tarefa 23
  - _Req 6.1 · §6.2_

- [x] 21. Tabela, resumo e moldura do PDF por cliente
  - Larguras 48–96 pt sem esticar (função pura com teste para 1, 3 e 20 itens);
    alinhamentos; `repeatRows=1`
  - Bloco "Resumo por item"; rodapé "Página X de Y" (conferir a documentação do
    reportlab 5.0.1 para o padrão de duas passadas)
  - Testes com `pypdf`: "Página 1 de", resumo, totais
  - Feito: `colunas.larguras_por_dia` (medidor injetado), `resumo.py`,
    `CanvasComRodape` (receita `canvasmaker`; a 5.0.1 não tem recurso pronto),
    estado vazio, escape de `&`/`<` nos nomes, milhar "1.234". Testes em
    `test_pdf_acabamento.py`; sabotagens acusadas: `repeatRows=0`, total de
    páginas fixo, sem teto de 96 pt, resumo vazio, encolher sem mínimo por palavra
  - _Req 6.2–6.5, 6.7 · §6.3, §6.4_

- [x] 22. PDF do relatório geral
  - Mesmo padrão visual; bloco por cliente; total geral; teste de paridade
  - Feito: `geral.py`, `GET /api/relatorio/geral/pdf` (30/min, teste de limite);
    paridade com a tela em `test_api_relatorio_geral.py`
  - _Req 5.6, 5.7, 6.6 · §5.5_

- [x] 23. Verificação visual dos PDFs
  - Gerar com `lavconta_dev`: poucos itens, muitos itens, várias páginas, geral
  - Conferir a imagem renderizada de cada um antes de marcar
  - Feito com `scripts_dev/visualizar_pdf.py` (`pypdfium2` em requirements-dev;
    "muitos itens" é sintético, 18 itens). Achados e correções: títulos partidos
    no meio da palavra com 18 itens → largura mínima por palavra; logo de 120 pt
    roubava 5 linhas da página 1 → 80 pt
  - _Req 6 · §6.5_

---

## Fase 6 — Ensaio e deploy

- [ ] 24. Verificação completa local
  - Lint, testes de backend (`EXIGIR_BANCO_DE_TESTE=1`) e frontend, build
  - Fluxo no navegador: criar item com preço, mudar a partir de hoje, corrigir o atual,
    lançar pedido retroativo, relatório por cliente e geral, exportar PDF e Excel,
    conferir totais iguais
  - _Req 1–6_

- [x] 25. Preparar a migração de produção (só leitura)
  - `SELECT version();` → escolher `pg_dump` da versão certa
  - Consulta de preços futuros (§1.5) e contagem de preços; se houver preço futuro,
    parar e decidir com o usuário
  - 02/10: servidor **Postgres 17.6** → backup exige `pg_dump` 17 (o local é 16).
    **46 preços**, dos quais **4 com início futuro** (01/11/2026), todos com o
    mesmo valor do preço anterior (BONEVILE Lençol 1,90; PAULISTA Lençol, Piso e
    Toalha 2,10), criados em 02/10 pela tela da v1. Não alteravam cobrança.
    Apagados a pedido do usuário em 02/10, após a migração e o deploy (DELETE
    com trava de exatamente 4): 46 → 42 preços, nenhum com início futuro. `pg_dump` 17.11 instalado via winget (só
    ferramentas). Backup: `C:\Users\Pichau\lavconta-backup\antes-v11-20261002-2100.dump`
    (371 KB, `pg_restore -l` lista clientes, lancamentos e precos)
  - _Req 2.5 · §1.5, §2_

- [x] 26. Backup e migração em produção (confirmar com o usuário antes)
  - 02/10 ~21h: `upgrade 54016f7a3787 -> 9c4e1a7b2d60` aplicado; 46 preços,
    46 com `vigencia_inicio`. Backup da tarefa 25
  - `pg_dump` para arquivo fora da pasta do projeto
  - `alembic upgrade head` contra produção; conferir contagem e `vigencia_inicio`
  - Combinar a janela: não editar preços até o deploy terminar
  - _Req 2.5, 2.6 · §2_

- [x] 27. Deploy do código
  - 02/10 21h05: commit `6f2188c`, CI verde, Netlify publicado. Conferido de fora:
    saúde 200, rotas novas da v1.1 respondem 401, CORS aceita só o Netlify.
  - 02/10 (fix): commit `9cfe512` — botão "Exportar PDF" escondido no relatório
    geral (`{!geral && ...}`, placeholder da Fase 5 não removido). Corrigido.

- [ ] 28. Migração de fase 2 (contract) — depois do código estável
  - Revisão `v11_remove_vigencia_mes` (remove `vigencia_mes`, CHECK e índice antigos)
  - Destrutiva: confirmar com o usuário e fazer novo backup antes
  - _Req 2.4 · §2_
