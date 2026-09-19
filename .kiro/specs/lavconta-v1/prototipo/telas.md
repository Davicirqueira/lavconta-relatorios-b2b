# Inventário de telas — Lavconta

Aplicação web interna de uso diário, operada em desktop por uma pessoa da equipe.
Português do Brasil em toda a interface. Sem cadastro público: quem acessa já tem conta.

## Estrutura base

Layout com **sidebar fixa e colapsável à esquerda** e área de conteúdo à direita.

- Sidebar: gradiente azul escuro, marca "Lavconta" no topo, itens de navegação com
  **ícone e rótulo**. Item ativo destacado com barra indicadora na borda esquerda.
- Navegação: Lançamentos, Relatório, Clientes, Catálogo, Preços — cada um com seu ícone
  (ver `brief-design.md` para o conjunto e a escolha de cada ícone).
- **Colapso:** botão no rodapé alterna entre 240px (ícone e rótulo) e 68px (só ícone,
  com tooltip no hover). O estado persiste entre sessões.
- Topo da área de conteúdo: título da página, ação primária à direita quando houver
  (ex.: "Novo lançamento").
- Rodapé da sidebar: controle de colapso, usuário logado e sair. No estado colapsado,
  permanece apenas o avatar com a inicial.

## 1. Login

Tela centralizada, cartão único sobre fundo gelo.

- Campos: e-mail, senha.
- Botão primário: Entrar.
- Link discreto: "Esqueci minha senha".
- **Não existe** link ou botão de criar conta.
- Estado de erro: mensagem única acima do formulário ("E-mail ou senha inválidos").

## 2. Esqueci minha senha / Redefinir senha

Duas telas simples, mesmo formato do login.

- Esqueci: campo e-mail, botão Enviar link. Após envio, mensagem neutra confirmando
  que, se o e-mail existir, o link foi enviado.
- Redefinir: campos nova senha e confirmar nova senha, botão Salvar.

## 3. Lançamentos (tela principal de uso diário)

É a tela mais usada. Lista de lançamentos com filtro e acesso rápido ao cadastro.

**Lista:**
- Filtros no topo: cliente (seleção) e intervalo de datas.
- Tabela: Data, Cliente, Comanda, Total de peças, Total R$, ações (editar, excluir).
- Ação primária no topo: "Novo lançamento".
- Estado vazio: mensagem orientando a criar o primeiro lançamento.

**Formulário de lançamento (novo/editar):**
- Cabeçalho do formulário: cliente (seleção), data (dd/mm/yyyy, preenchida com hoje),
  comanda (texto, opcional, com rótulo indicando "opcional").
- Bloco de itens: linhas com item (seleção do catálogo do cliente), quantidade
  (inteiro), valor unitário (somente leitura, vindo da API) e total da linha
  (somente leitura).
- Botão "Adicionar item" abaixo das linhas; cada linha tem ação de remover.
- Rodapé fixo do formulário com os totais: **Total de peças** e **Total R$**, em
  destaque.
- Caixa de seleção discreta: "incluir itens inativos" na seleção de item.
- Botões: Salvar (primário) e Cancelar (secundário).

**Estados de erro a representar:**
- Já existe lançamento para esse cliente nessa data.
- Comanda já usada para esse cliente.
- Itens sem preço cadastrado (listando os nomes dos itens).

**Exclusão:** diálogo de confirmação com "Tem certeza?", identificando cliente e data,
botão destrutivo Excluir e botão Cancelar.

## 4. Relatório de fechamento

Tela de saída do produto: gera a relação que vai para o cliente.

- Filtros no topo: cliente (seleção, obrigatório), data inicial e data final
  (dd/mm/yyyy, já preenchidas do primeiro ao último dia do mês atual), botão
  "Gerar relatório".
- Ações de exportação à direita: **Exportar PDF** e **Exportar Excel**.
- Corpo: a tabela de fechamento (ver `layout-relatorio.md`).
- Estado vazio: relatório sem lançamentos no período, com totais zerados e aviso.

## 5. Clientes

- Lista: Nome, Situação (ativo/inativo), ações (editar, inativar/reativar, excluir).
- Filtro simples por nome e alternância para mostrar inativos.
- Formulário: nome (obrigatório). Modal ou painel lateral.
- Cliente inativo aparece com marcação visual discreta de estado neutro.
- Exclusão: permitida só quando não há lançamentos; caso contrário, mensagem
  explicando e sugerindo inativar.

## 6. Catálogo de itens

- Seleção de cliente no topo (o catálogo é sempre de um cliente).
- Lista: Nome do item, Situação (ativo/inativo), ações (editar,
  inativar/reativar, excluir).
- Alternância para mostrar itens inativos.
- Formulário: nome do item (obrigatório).
- Mesma lógica de exclusão dos clientes: só se nunca usado.

## 7. Preços

- Seleção de cliente e de mês/ano no topo.
- Tabela: Item, Preço vigente (R$), ação de editar.
- **Destaque visual** para itens sem preço definido (estado de alerta), porque isso
  bloqueia lançamentos.
- Formulário de preço: item, valor (R$, duas casas), mês/ano de início de vigência.
- Aviso informativo ao corrigir preço de mês passado: lançamentos já registrados
  permanecem com o valor congelado e não mudam.

## Comportamentos gerais

- Toda ação de escrita mostra estado de carregamento; a API pode demorar alguns
  segundos na primeira chamada (hospedagem hiberna quando ociosa).
- Mensagens de erro em português, apontando o campo envolvido.
- Datas sempre dd/mm/yyyy.
- Valores monetários no formato R$ 1.234,56.
