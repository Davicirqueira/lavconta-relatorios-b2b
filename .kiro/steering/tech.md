---
inclusion: always
---

# Arquitetura técnica — Lavandix

## Stack (definida e confirmada)

| Camada        | Tecnologia                                  |
|---------------|---------------------------------------------|
| Frontend      | React + Vite                                |
| Backend / API | Python + FastAPI                            |
| Banco         | PostgreSQL (Supabase)                       |
| Autenticação  | Supabase Auth                               |
| Hospedagem FE | Netlify                                     |
| Hospedagem API| Render (free web service)                   |
| Custo inicial | US$ 0                                        |

## Autenticação (Supabase)

- O **frontend autentica no Supabase** e recebe um **JWT**.
- O **FastAPI valida o JWT do Supabase** em cada requisição protegida.
- Na v1 há **usuário único** (equipe interna). Ainda assim, toda rota de dados
  exige um token válido.

## Banco de dados

- **PostgreSQL do próprio Supabase** (não usar Neon; banco e auth no mesmo provedor
  para reduzir peças a gerenciar).
- Toda a **lógica de negócio fica no FastAPI**. **Não** depender de RLS nem das APIs
  auto-geradas do Supabase para regras de negócio. O Supabase é usado como
  **provedor de auth + Postgres gerenciado**.

## Divisão de responsabilidades

- **Frontend (React + Vite):** UI, seleção de datas, formulários de lançamento,
  telas de cliente/catálogo/preço, disparo de exportação. Não contém regra de
  cálculo autoritativa — exibe o que a API retorna.
- **Backend (FastAPI):** autoridade sobre as regras de negócio — cálculo de totais,
  congelamento de valor no lançamento, resolução do preço vigente por mês, validação
  da unicidade (cliente, data) e (cliente, comanda), geração de relatório e dos
  arquivos PDF/Excel.
- **Banco (Postgres):** persistência. Restrições de integridade (unicidade,
  chaves estrangeiras) reforçam as regras críticas no nível do banco.

## Trade-off conhecido: cold start

- O free tier do Render **hiberna após inatividade** (~15 min). A primeira
  requisição após hibernar pode levar de ~30s a ~1 min para "acordar".
- **Aceitável na v1** (uso interno, equipe pequena). Mitigações futuras se necessário:
  plano pago do Render ou ping periódico para manter o serviço ativo.

## Regras de implementação derivadas do negócio

- **Congelar o valor unitário** de cada item no lançamento no momento da criação
  (com base no preço vigente do mês). Relatórios passados nunca mudam.
- **Resolução de preço** por (cliente, item, mês/ano). Alteração de preço no meio do
  mês só vale a partir do mês seguinte.
- **Unicidade (cliente, data)**: reforçar tanto na API quanto por constraint no banco.
- **Comanda opcional, única por cliente quando preenchida**: reforçar por constraint
  parcial no banco (unicidade que ignora valores nulos).
- Relatório de período pode **cruzar meses**; soma lançamentos com seus valores
  congelados, sem reaplicar preço único.
