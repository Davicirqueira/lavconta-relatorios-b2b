# Requisitos — Lavconta v1

## Introdução

A Lavconta é uma aplicação web de relatórios B2B para a Lavandix, lavanderia
profissional que atende empresas em São Paulo. O trabalho acontece diariamente e
pulverizado ao longo do mês, mas a cobrança é mensal e consolidada. Hoje esse
fechamento é feito em planilha manual, o que é frágil: erro de digitação, preço
errado, fórmula quebrada e dificuldade de manter preços diferentes por cliente.

Esta v1 substitui a planilha. O sistema registra os pedidos diários por cliente,
aplica o preço vigente do mês, **congela** o valor no momento do lançamento e gera o
relatório de fechamento detalhado, exportável em PDF e Excel.

**Princípio condutor:** o valor cobrado precisa ser rastreável e estável. Nenhuma
alteração futura de preço pode mudar um relatório passado.

**Escopo:** usuário único (equipe interna Lavandix). Clientes-empresa não acessam o
sistema.

---

## Glossário

| Termo | Significado |
|---|---|
| **Cliente** | Empresa atendida pela Lavandix. |
| **Item** | Tipo de peça do catálogo (lençol, fronha, toalha...). Pertence a um cliente. |
| **Preço** | Valor unitário de um item para um cliente, com vigência de um mês/ano. |
| **Lançamento** | Pedido diário de um cliente numa data. Identificado por (cliente, data). |
| **Linha de lançamento** | Item + quantidade + valor unitário congelado + total da linha. |
| **Valor congelado** | Preço unitário gravado na linha no momento da criação do lançamento. |
| **Fechamento** | Relatório consolidado de um período, detalhado por dia. |

---

## Requisito 1 — Autenticação e proteção de acesso

**História:** Como equipe interna da Lavandix, quero acessar o sistema com login
próprio, para que os dados de faturamento dos clientes não fiquem públicos.

### Critérios de aceitação

1. QUANDO um usuário não autenticado tentar acessar qualquer tela de dados, ENTÃO o
   sistema DEVE redirecioná-lo para a tela de login.
2. QUANDO o usuário informar credenciais válidas, ENTÃO o sistema DEVE autenticá-lo
   via Supabase Auth e obter um JWT.
3. QUANDO o frontend chamar qualquer rota de dados da API, ENTÃO ele DEVE enviar o
   JWT no cabeçalho `Authorization`.
4. QUANDO a API receber uma requisição em rota de dados, ENTÃO ela DEVE validar o JWT
   completamente (assinatura contra o JWKS do Supabase, `exp`, `iss` e `aud`) antes de
   executar qualquer lógica.
5. SE o JWT estiver ausente, expirado, malformado ou com assinatura inválida, ENTÃO a
   API DEVE responder `401` sem revelar detalhes internos da validação.
6. QUANDO a sessão do usuário expirar durante o uso, ENTÃO o sistema DEVE informar
   que a sessão expirou e solicitar novo login, sem perder dados já salvos.
7. O sistema NÃO DEVE expor nenhuma rota de dados sem autenticação.

### Criação de usuário e recuperação de senha

8. A aplicação NÃO DEVE oferecer tela nem rota de auto-cadastro (signup). O usuário é
   criado manualmente no painel do Supabase pela equipe responsável.
9. O signup DEVE estar desabilitado na configuração do projeto Supabase, de modo que
   nem a aplicação nem a API pública do provedor permitam criar conta.
10. O sistema DEVE oferecer o fluxo de recuperação de senha por e-mail do Supabase
    Auth, acessível a partir da tela de login.
11. QUANDO o usuário solicitar recuperação de senha, ENTÃO o sistema DEVE responder de
    forma idêntica independentemente do e-mail existir ou não, para não revelar quais
    contas estão cadastradas.
12. QUANDO o usuário abrir o link de redefinição, ENTÃO o sistema DEVE permitir definir
    nova senha e, ao concluir, direcioná-lo ao login.

---

## Requisito 2 — Gestão de clientes

**História:** Como operador, quero cadastrar e manter as empresas atendidas, para que
cada uma tenha seu próprio catálogo, preços e lançamentos.

### Critérios de aceitação

1. QUANDO o operador cadastrar um cliente com nome válido, ENTÃO o sistema DEVE
   persistir o cliente e exibi-lo na listagem.
2. QUANDO o operador tentar cadastrar um cliente sem nome, ENTÃO o sistema DEVE
   recusar e informar qual campo é obrigatório.
3. QUANDO o operador editar o nome de um cliente, ENTÃO o sistema DEVE atualizar o
   cadastro sem alterar lançamentos ou valores já registrados.
4. QUANDO o operador listar clientes, ENTÃO o sistema DEVE exibi-los em ordem
   alfabética por nome.
5. QUANDO o operador tentar cadastrar um cliente com nome já existente, ENTÃO o sistema
   DEVE recusar e informar a duplicidade, comparando os nomes **sem diferenciar
   maiúsculas e minúsculas** e desconsiderando espaços nas pontas.
6. O sistema NÃO DEVE permitir catálogo ou preço global — todo item e todo preço
   pertencem a um cliente específico.

### Situação do cliente (ativo/inativo) e exclusão

7. Todo cliente DEVE possuir uma situação **ativo** ou **inativo**, iniciando como ativo.
8. QUANDO o operador inativar um cliente, ENTÃO ele DEVE deixar de aparecer na seleção
   padrão de novos lançamentos, preservando integralmente o histórico e permanecendo
   disponível para consulta e geração de relatórios de períodos passados.
9. QUANDO o operador reativar um cliente inativo, ENTÃO ele DEVE voltar a aparecer na
   seleção, sem criar registro duplicado.
10. QUANDO o operador solicitar a exclusão de um cliente **sem nenhum lançamento**,
    ENTÃO o sistema DEVE permitir a exclusão definitiva, removendo também seu catálogo
    de itens e preços.
11. QUANDO o operador solicitar a exclusão de um cliente **com lançamentos**, ENTÃO o
    sistema DEVE recusar a exclusão, explicar que existem registros históricos
    vinculados e oferecer a inativação como alternativa.

---

## Requisito 3 — Catálogo de itens por cliente

**História:** Como operador, quero cadastrar livremente os tipos de item de cada
cliente, para refletir o que aquela empresa efetivamente envia.

### Critérios de aceitação

1. QUANDO o operador cadastrar um item informando cliente e nome, ENTÃO o sistema
   DEVE persistir o item vinculado àquele cliente.
2. QUANDO o operador tentar cadastrar, para o mesmo cliente, um item com nome já
   existente, ENTÃO o sistema DEVE recusar e informar a duplicidade.
3. QUANDO o operador editar o nome de um item, ENTÃO o sistema DEVE atualizar o
   catálogo sem alterar o valor congelado de lançamentos anteriores.
4. QUANDO o operador listar os itens, ENTÃO o sistema DEVE exibir apenas os itens do
   cliente selecionado.
5. O sistema NÃO DEVE oferecer campos personalizados arbitrários por lançamento —
   a flexibilidade se limita a cadastrar/editar itens e definir seus preços.

### Situação do item (ativo/inativo) e exclusão

6. Todo item DEVE possuir uma situação **ativo** ou **inativo**, iniciando como ativo.
7. QUANDO o operador inativar um item, ENTÃO ele DEVE deixar de aparecer na seleção
   padrão de itens de novos lançamentos, preservando integralmente o histórico.
8. QUANDO o operador reativar um item inativo, ENTÃO ele DEVE voltar a aparecer na
   seleção, sem criar registro duplicado.
9. QUANDO o operador editar um lançamento que já contém um item inativo, ENTÃO o
   sistema DEVE permitir a edição normalmente, inclusive alterar a quantidade daquela
   linha.
10. O sistema DEVE permitir incluir item inativo em um lançamento por ação explícita do
    operador (ex.: controle "incluir itens inativos"), para viabilizar registro
    retroativo de pedidos antigos.
11. QUANDO o operador solicitar a exclusão de um item **nunca usado** em nenhum
    lançamento, ENTÃO o sistema DEVE permitir a exclusão definitiva.
12. QUANDO o operador solicitar a exclusão de um item **já usado** em algum lançamento,
    ENTÃO o sistema DEVE recusar a exclusão, explicar que há histórico vinculado e
    oferecer a inativação como alternativa.
13. A situação (ativo/inativo) do item NÃO DEVE influenciar relatórios de períodos
    passados: itens inativos que ocorreram no período DEVEM continuar compondo colunas
    e totais normalmente.

---

## Requisito 4 — Preços com vigência mensal

**História:** Como operador, quero definir o preço de cada item por cliente e por
mês, para que a cobrança use sempre o valor acordado naquele período.

### Critérios de aceitação

1. QUANDO o operador definir um preço, ENTÃO o sistema DEVE registrá-lo indexado por
   (cliente, item, mês/ano).
2. QUANDO já existir preço para a mesma combinação (cliente, item, mês/ano), ENTÃO o
   sistema DEVE tratar a operação como atualização daquele preço, não criar duplicata.
3. O preço definido para um mês DEVE valer do dia 1 ao último dia daquele mês.
4. O preço definido para um mês DEVE permanecer vigente nos meses seguintes até que um
   novo preço seja definido para aquele cliente e item. O sistema NÃO DEVE exigir
   redigitação de preços a cada virada de mês.
5. QUANDO o operador alterar o preço de um item no meio de um mês (ex.: dia 15/08),
   ENTÃO o valor vigente naquele mês DEVE permanecer até o fim do mês, e a alteração
   DEVE passar a valer a partir do mês seguinte.
6. QUANDO o sistema resolver o preço vigente, ENTÃO ele DEVE usar o preço mais recente
   definido para aquele cliente e item cujo mês/ano seja igual ou anterior ao mês/ano
   de referência.
7. A resolução de preço DEVE usar sempre o mês/ano da **data do lançamento**, nunca a
   data corrente. Um lançamento retroativo DEVE receber o preço vigente na data do
   pedido.
8. SE não existir nenhum preço definido para o cliente e item em mês/ano igual ou
   anterior ao da data de referência, ENTÃO o item DEVE ser considerado sem preço.
9. QUANDO o operador informar preço com valor negativo ou zero, ENTÃO o sistema DEVE
   recusar e informar que o valor deve ser positivo.
10. QUANDO o operador consultar a tabela de preços de um cliente para um mês, ENTÃO o
    sistema DEVE indicar quais itens estão sem preço definido.
11. O sistema DEVE armazenar e calcular valores monetários com precisão decimal,
    nunca com ponto flutuante binário.
12. O preço unitário DEVE ter exatamente **duas casas decimais** (padrão monetário,
    ex.: R$ 2,50). O sistema NÃO DEVE aceitar fração de centavo.
13. QUANDO o operador informar preço com mais de duas casas decimais, ENTÃO o sistema
    DEVE recusar e informar o formato esperado.

### Mês de vigência e correção de preço

14. O operador DEVE poder escolher o mês/ano de início de vigência ao definir um preço,
    podendo programar um preço para um mês futuro.
15. QUANDO o operador **alterar** o preço de um item que já possui preço vigente, ENTÃO
    o sistema DEVE sugerir como padrão o **mês seguinte** ao corrente, em coerência com
    a regra de que alteração só passa a valer no mês seguinte.
16. QUANDO o operador definir o **primeiro** preço de um item, ENTÃO o sistema DEVE
    sugerir como padrão o **mês corrente**, para que o item possa ser lançado
    imediatamente.
17. O operador DEVE poder corrigir um preço de mês já passado (ex.: erro de digitação).
18. QUANDO o operador corrigir um preço de mês passado, ENTÃO o sistema DEVE avisar
    explicitamente que os lançamentos já registrados **não** serão alterados, pois seus
    valores estão congelados, e que a correção afeta apenas resoluções futuras e
    lançamentos retroativos criados a partir dali.

---

## Requisito 5 — Lançamento diário (pedido)

**História:** Como operador, quero registrar o pedido diário de cada cliente com os
itens e quantidades, para que o fechamento reflita fielmente o que foi feito.

### Critérios de aceitação

1. QUANDO o operador criar um lançamento, ENTÃO o sistema DEVE exigir cliente e data,
   e DEVE aceitar uma ou mais linhas de item com quantidade.
2. O sistema DEVE impedir a criação de um segundo lançamento para o mesmo cliente na
   mesma data, informando que já existe lançamento para aquele dia.
3. A unicidade (cliente, data) DEVE ser garantida tanto na API quanto por constraint
   no banco de dados.
4. QUANDO clientes diferentes tiverem lançamento na mesma data, ENTÃO o sistema DEVE
   permitir normalmente.
5. O campo comanda DEVE existir sempre na interface, com preenchimento opcional.
6. A comanda DEVE aceitar texto (números e letras, ex.: `1042` ou `A-1042`).
7. QUANDO a comanda for informada, ENTÃO o sistema DEVE remover espaços no início e no
   fim antes de validar e gravar.
8. QUANDO a comanda for informada apenas com espaços, ENTÃO o sistema DEVE tratá-la
   como não preenchida (nula), não como texto vazio.
9. QUANDO a comanda for preenchida, ENTÃO ela DEVE ser única para aquele cliente,
   **ignorando maiúsculas e minúsculas** (`a100` e `A100` são a mesma comanda), e o
   sistema DEVE recusar repetição informando o conflito.
10. A unicidade da comanda por cliente DEVE ignorar lançamentos sem comanda, e DEVE ser
    reforçada por constraint parcial no banco, também insensível a caixa.
11. A quantidade de uma linha DEVE ser um número **inteiro positivo** (cobrança por
    peça, peças são contáveis). QUANDO o operador informar quantidade zero, negativa ou
    fracionada, ENTÃO o sistema DEVE recusar e informar o formato esperado.
12. QUANDO o operador informar o mesmo item duas vezes no mesmo lançamento, ENTÃO o
    sistema DEVE recusar e informar a duplicidade.
13. QUANDO o operador selecionar itens, ENTÃO o sistema DEVE oferecer apenas itens do
    catálogo do cliente do lançamento.
14. SE algum item do lançamento não tiver preço vigente resolvível para o mês da data
    do lançamento, ENTÃO o sistema DEVE recusar a operação e informar **nominalmente
    quais itens** estão sem preço, orientando o operador a cadastrá-los.

### Data do lançamento

15. SE a data informada for posterior a "hoje" (em America/Sao_Paulo), ENTÃO o sistema
    DEVE recusar o lançamento e informar que não é possível registrar pedido com data
    futura, pois o serviço é registrado após ocorrer.
16. QUANDO o operador abrir o formulário de novo lançamento, ENTÃO a data DEVE vir
    preenchida com a data corrente em America/Sao_Paulo.

### Edição de lançamento

17. O operador DEVE poder editar um lançamento já salvo: alterar comanda, alterar
    quantidades, adicionar linhas e remover linhas.
18. QUANDO uma linha existente for editada, ENTÃO o sistema DEVE preservar o valor
    unitário congelado original, recalculando apenas o total da linha pela nova
    quantidade.
19. QUANDO uma linha nova for adicionada em uma edição, ENTÃO o sistema DEVE congelar
    seu valor unitário pelo preço vigente no **mês da data do lançamento**, não pelo
    mês corrente.
20. QUANDO a data ou o cliente de um lançamento for alterado, ENTÃO o sistema DEVE
    revalidar a unicidade (cliente, data) e recusar se houver conflito.

### Exclusão de lançamento

21. O operador DEVE poder excluir um lançamento.
22. QUANDO o operador solicitar exclusão, ENTÃO o sistema DEVE exibir confirmação
    explícita ("Tem certeza?") identificando cliente e data, antes de executar.
23. QUANDO a exclusão for confirmada, ENTÃO o sistema DEVE remover o lançamento e suas
    linhas, e o registro DEVE deixar de compor relatórios do período.

---

## Requisito 6 — Congelamento de valor e cálculo de totais

**História:** Como responsável pela cobrança, quero que o valor de cada lançamento
fique gravado no momento do registro, para que relatórios passados nunca mudem.

### Critérios de aceitação

1. QUANDO um lançamento for criado, ENTÃO o sistema DEVE gravar em cada linha o valor
   unitário vigente do item naquele mês, congelando-o na própria linha.
2. QUANDO o preço de um item for alterado depois, ENTÃO os lançamentos já criados e os
   relatórios que os incluem NÃO DEVEM sofrer alteração de valor.
3. QUANDO um lançamento existente for editado, ENTÃO o valor unitário congelado das
   linhas preexistentes NÃO DEVE ser recalculado pelo preço atual. A edição corrige o
   registro do pedido, não renegocia o preço praticado.
4. O total de uma linha DEVE ser o valor unitário congelado multiplicado pela
   quantidade daquela linha.
5. O total em R$ do lançamento DEVE ser a soma dos totais de todas as suas linhas.
6. O total de peças do lançamento DEVE ser a soma das quantidades de todas as suas
   linhas.
7. A cobrança DEVE ser sempre por peça; o sistema NÃO DEVE aplicar impostos, taxas,
   valores mínimos ou descontos.
8. O cálculo autoritativo DEVE ocorrer no backend; o frontend DEVE exibir os valores
   retornados pela API, sem recalcular regra de negócio.
9. O sistema DEVE aplicar arredondamento monetário explícito e consistente.

---

## Requisito 7 — Relatório de fechamento

**História:** Como responsável pela cobrança, quero gerar a relação de valores de um
período, detalhada por dia, para que o cliente consiga auditar a fatura.

### Critérios de aceitação

1. QUANDO o operador gerar um relatório, ENTÃO o sistema DEVE exigir um cliente e um
   período com data inicial e final.
2. O relatório DEVE ser sempre de um único cliente. O sistema NÃO DEVE misturar dados
   de clientes diferentes num mesmo fechamento.
3. QUANDO a tela de relatório for aberta, ENTÃO o período DEVE vir preenchido por
   padrão do primeiro ao último dia do mês vigente.
4. O operador DEVE poder alterar livremente o intervalo de datas, inclusive cruzando
   meses.
5. SE a data inicial for posterior à data final, ENTÃO o sistema DEVE recusar e
   informar o erro.
6. O relatório DEVE apresentar uma linha por lançamento, contendo: data, comanda
   (quando houver), quantidade por tipo de item, total de peças da linha e total em R$
   da linha.
7. As colunas de tipo de item DEVEM conter **apenas os itens que aparecem em pelo menos
   um lançamento do período selecionado**. Itens do catálogo sem ocorrência no período
   NÃO DEVEM gerar coluna.
8. QUANDO um item existir nas colunas mas não aparecer em determinado lançamento,
   ENTÃO a célula correspondente DEVE ficar vazia (sem quantidade).
9. As linhas DEVEM ser ordenadas por data crescente.
10. QUANDO um lançamento não tiver comanda, ENTÃO o layout DEVE permanecer o mesmo,
    apenas sem valor no campo comanda.
11. O relatório DEVE apresentar os totais do período: total de peças e total em R$.
12. QUANDO o período cruzar mais de um mês, ENTÃO cada lançamento DEVE entrar com seu
    próprio valor congelado, e o sistema NÃO DEVE reaplicar um preço único ao período.
13. QUANDO não houver lançamentos no período, ENTÃO o sistema DEVE exibir o relatório
    vazio com totais zerados, informando a ausência de registros.
14. As datas DEVEM ser exibidas no formato dd/mm/yyyy.

---

## Requisito 8 — Exportação em PDF e Excel

**História:** Como responsável pela cobrança, quero exportar o relatório em PDF ou
Excel, para enviar ao cliente e arquivar.

### Critérios de aceitação

1. QUANDO o operador solicitar exportação, ENTÃO o sistema DEVE permitir escolher
   entre PDF e Excel.
2. O arquivo exportado DEVE conter as mesmas linhas, colunas e totais exibidos no
   relatório em tela.
3. O arquivo exportado DEVE identificar o cliente e o período do fechamento.
4. QUANDO o arquivo for gerado, ENTÃO o sistema DEVE entregá-lo como download com
   nome descritivo e `content-type` correto para o formato.
5. A geração dos arquivos DEVE ocorrer no backend, a partir dos mesmos dados
   calculados para o relatório em tela.
6. No Excel, os valores monetários e as quantidades DEVEM ser células numéricas,
   permitindo conferência e soma pelo destinatário.

---

## Requisito 9 — Segurança, configuração e qualidade

**História:** Como responsável pelo projeto, quero que dados e credenciais estejam
protegidos, para não expor o faturamento dos clientes nem as chaves de acesso.

### Critérios de aceitação

1. O sistema NÃO DEVE conter segredos (chaves, senhas, tokens, string de conexão)
   no código-fonte nem versionados no repositório.
2. A configuração sensível DEVE ser lida de variáveis de ambiente, validada na
   inicialização, falhando com erro claro pelo nome da chave quando ausente.
3. O repositório DEVE conter `.env.example` com as chaves sem valores reais, e
   `.gitignore` cobrindo arquivos de segredo antes de sua criação.
4. A chave `service_role` do Supabase DEVE ser usada apenas no backend, nunca no
   bundle do frontend nem em URL.
5. A API DEVE restringir CORS às origens do frontend, sem usar coringa com
   credenciais.
6. A API DEVE validar toda entrada externa e usar consultas parametrizadas no banco.
7. QUANDO ocorrer erro interno, ENTÃO a API DEVE responder com mensagem útil e sem
   stack trace nem detalhe de implementação.
8. O sistema NÃO DEVE registrar valores de segredos em log.
9. As dependências DEVEM ter versão fixada, com lockfile versionado.
10. A suíte de testes DEVE cobrir prioritariamente: cálculo de totais, resolução de
    preço vigente por mês, congelamento de valor, unicidade (cliente, data),
    unicidade parcial de comanda e validação de JWT.

---

## Requisito 10 — Usabilidade e apresentação

**História:** Como operador que lança pedidos todos os dias, quero uma interface
rápida e legível, para registrar sem erro e conferir valores com facilidade.

### Critérios de aceitação

1. A interface DEVE usar a identidade visual definida (paleta azul/gelo, Poppins na
   interface, Inter com numerais tabulares nos valores numéricos).
2. As colunas de valores monetários e quantidades DEVEM alinhar os dígitos
   verticalmente nas tabelas e relatórios.
3. As datas DEVEM ser informadas e exibidas no formato dd/mm/yyyy.
4. QUANDO uma operação for recusada por regra de negócio, ENTÃO o sistema DEVE exibir
   mensagem em português explicando o motivo e o campo envolvido.
5. Os pares de texto e fundo em uso corrente DEVEM atender contraste WCAG AA.
6. QUANDO a API estiver reativando após hibernação do plano free, ENTÃO a interface
   DEVE indicar que a requisição está em andamento, evitando a impressão de falha.
7. Toda a terminologia visível ao usuário DEVE estar em português.

---

## Requisito 11 — Tratamento de datas e fuso horário

**História:** Como responsável pela cobrança, quero que a data de um lançamento seja
exatamente o dia informado, para que nenhum pedido mude de dia ou de mês por conversão
de fuso e acabe no fechamento errado.

### Critérios de aceitação

1. A data do lançamento DEVE ser tratada como **data de calendário**, sem hora e sem
   fuso horário, e armazenada como tipo `DATE` no Postgres.
2. A data do lançamento DEVE trafegar na API no formato `YYYY-MM-DD`, como texto, sem
   componente de hora e sem deslocamento de fuso.
3. O frontend NÃO DEVE converter a data de negócio para objeto de data/hora local ao
   exibi-la. A conversão para dd/mm/yyyy DEVE ser reformatação de texto.
4. O sistema NÃO DEVE aplicar nenhuma conversão de fuso horário sobre a data do
   lançamento, em nenhum ponto da cadeia (frontend, API ou banco).
5. QUANDO o operador informar uma data, ENTÃO o dia, mês e ano persistidos e exibidos
   DEVEM ser idênticos aos informados, inclusive em lançamentos no primeiro e no último
   dia do mês.
6. A noção de "hoje" DEVE ser calculada no fuso **America/Sao_Paulo**, e não no fuso do
   servidor de hospedagem.
7. QUANDO o sistema sugerir o período padrão do relatório (mês vigente) ou a data
   padrão de um novo lançamento, ENTÃO ele DEVE usar a data corrente em
   America/Sao_Paulo.
8. Os carimbos de auditoria (criação e atualização de registros) DEVEM ser instantes
   armazenados com fuso (`timestamptz`) e, se exibidos, apresentados em horário de
   America/Sao_Paulo.

---

## Decisões esclarecidas (confirmadas nesta especificação)

Estes pontos não estavam cobertos pelas regras de negócio originais e foram decididos
e confirmados. Ficam registrados aqui como fonte da verdade.

1. **Vigência do preço se propaga.** O preço definido para um mês permanece vigente nos
   meses seguintes até que um novo preço seja definido. A "vigência mensal" governa
   *quando uma alteração passa a valer* (a partir do mês seguinte), e não obriga um
   registro de preço por mês. Não há redigitação de preços na virada de mês.
   → Requisito 4.4 e 4.6.
2. **Item sem preço bloqueia o lançamento.** Se nenhum preço houver sido definido para
   o cliente e item até o mês da data do lançamento, o sistema recusa a operação e
   informa nominalmente quais itens estão sem preço. Não existe lançamento com valor
   zero implícito. → Requisito 5.11.
3. **Resolução pela data do lançamento.** O preço é resolvido pelo mês/ano da data do
   pedido, nunca pela data corrente, para que lançamentos retroativos recebam o valor
   correto. → Requisito 4.7.
4. **Edição permitida, congelamento preservado.** O lançamento pode ser editado. Linhas
   preexistentes mantêm o valor unitário congelado original — a edição corrige o
   registro do pedido, não renegocia o preço praticado. Linhas novas adicionadas em uma
   edição são congeladas pelo preço vigente no mês da data do lançamento.
   → Requisitos 5.12–5.15 e 6.3.
5. **Exclusão permitida com confirmação.** O lançamento pode ser excluído, mediante
   confirmação explícita que identifica cliente e data. → Requisitos 5.16–5.18.
6. **Relatório sempre de um cliente.** Sem relatório consolidado de múltiplos clientes
   na v1. → Requisito 7.2.
7. **Colunas de item só do período.** As colunas de tipo de item listam apenas os itens
   com ocorrência no período selecionado, mantendo o relatório compacto e legível no
   PDF. → Requisitos 7.7 e 7.8.
8. **Sem auto-cadastro.** A aplicação não tem tela de signup; o usuário é criado
   manualmente no painel do Supabase e o signup fica desabilitado no projeto. Evita que
   qualquer pessoa crie conta e acesse o faturamento dos clientes.
   → Requisitos 1.8 e 1.9.
9. **Recuperação de senha pelo Supabase.** Usa o fluxo de reset por e-mail do Supabase
   Auth, com resposta uniforme para não revelar quais e-mails existem.
   → Requisitos 1.10–1.12.
10. **Item ativo/inativo.** Item pode ser inativado para sair da seleção de novos
    lançamentos sem perder histórico. Exclusão definitiva só para item nunca usado;
    item com histórico só pode ser inativado. Item inativo pode ser usado por ação
    explícita, para permitir registro retroativo. → Requisitos 3.6–3.13.
11. **Preço com duas casas decimais.** Padrão monetário, sem fração de centavo.
    → Requisitos 4.12 e 4.13.
12. **Comanda em texto, unicidade insensível a caixa.** Aceita números e letras, espaços
    nas pontas removidos, comanda só com espaços tratada como não preenchida, e `a100`
    equivale a `A100` na verificação de unicidade. → Requisitos 5.6–5.10.
13. **Quantidade inteira e positiva.** Cobrança por peça, peças são contáveis.
    → Requisito 5.11.
14. **Renomear item reflete em relatórios antigos.** O congelamento protege o valor, não
    o rótulo. Relatórios passados passam a exibir o nome novo do item, com os valores
    inalterados. → Requisito 3.3.
15. **Data de negócio sem fuso; "hoje" em America/Sao_Paulo.** A data do lançamento é
    data de calendário (`DATE`, texto `YYYY-MM-DD`), sem conversão de fuso em nenhum
    ponto, para que nenhum pedido troque de dia ou de mês. Já a noção de "hoje" (período
    padrão do relatório, data sugerida no lançamento) é calculada em America/Sao_Paulo,
    e carimbos de auditoria são instantes com fuso. → Requisito 11.

---

## Decisões tomadas por consistência (rodada 2)

Decididas pela coerência com as regras já fixadas, sem necessidade de nova consulta.
Registradas para revisão: se alguma não servir à operação real, é ajuste pontual.

16. **Cliente ativo/inativo, igual ao item.** Mesma mecânica e mesma regra de exclusão
    em dois níveis (sem lançamento → exclui; com lançamento → só inativa). Mantém
    simetria e evita lista de seleção poluída. → Requisitos 2.7–2.11.
17. **Nome de cliente único.** Recusa nome repetido ignorando caixa e espaços nas
    pontas, mesmo tratamento já aplicado a nome de item por cliente. Evita ambiguidade
    na seleção e no relatório. → Requisito 2.5.
18. **Mês de vigência escolhível, com padrão inteligente.** O operador escolhe o mês/ano
    de início, podendo programar preço futuro. O padrão sugerido é o **mês seguinte**
    para alteração de preço existente (coerente com a regra de vigência) e o **mês
    corrente** para o primeiro preço de um item (senão o item recém-cadastrado não
    poderia ser lançado hoje). → Requisitos 4.14–4.16.
19. **Correção de preço passado permitida, com aviso.** Permitida para corrigir erro de
    digitação, e a interface avisa que lançamentos já registrados permanecem congelados
    e não mudam — se a cobrança precisa ser corrigida de fato, o caminho é editar os
    lançamentos. → Requisitos 4.17 e 4.18.
20. **Data futura recusada.** O serviço é registrado após ocorrer, então lançamento com
    data posterior a hoje (America/Sao_Paulo) é recusado, e o formulário abre com a data
    de hoje. → Requisitos 5.15 e 5.16.
