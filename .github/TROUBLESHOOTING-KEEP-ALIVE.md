# Troubleshooting — Keep-Alive do Supabase

Problemas comuns e soluções para o workflow de keep-alive.

## ❌ Workflow falha: "DATABASE_URL não definida"

**Causa:** O secret `DATABASE_URL` não está configurado no repositório GitHub.

**Solução:**
1. Vá em **Settings** → **Secrets and variables** → **Actions**
2. Clique em **New repository secret**
3. Nome: `DATABASE_URL`
4. Valor: copie a string de conexão do `backend/.env` (Session Pooler do Supabase)

---

## ❌ Workflow falha: "ERRO ao conectar ou executar query"

**Causas possíveis:**

### 1. Banco Supabase pausado manualmente
- **Solução:** Retome o projeto no painel do Supabase

### 2. DATABASE_URL incorreta
- **Solução:** Verifique se:
  - Usa o **Session Pooler** (porta 5432), não Transaction pooler (6543)
  - Prefixo é `postgresql+psycopg://`, não só `postgresql://`
  - Senha está correta
  - Formato: `postgresql+psycopg://postgres.<ref>:senha@aws-N-<regiao>.pooler.supabase.com:5432/postgres`

### 3. Firewall/rede do GitHub Actions bloqueada
- **Solução:** Verifique no Supabase se há restrições de IP configuradas
- GitHub Actions usa IPs dinâmicos; evite whitelist de IP específico

---

## ⚠️ Workflow não executa automaticamente

**Causa:** Repositório privado pode ter limitações de cron no plano free do GitHub.

**Soluções:**
1. **Executar manualmente:** Actions → Keep Supabase Active → Run workflow
2. **Verificar permissões:** Settings → Actions → General → "Allow all actions"
3. **Repositório inativo:** GitHub desabilita workflows após 60 dias sem commit

---

## ✅ Como testar o script localmente

```powershell
cd backend

# Instalar dependências
pip install -r requirements-scripts.txt

# Definir DATABASE_URL (temporário, só nesta sessão)
$env:DATABASE_URL = "postgresql+psycopg://postgres.xxx:senha@aws-N-sa-east-1.pooler.supabase.com:5432/postgres"

# Executar
python scripts/keep_alive.py
```

**Resultado esperado:**
```
🔄 Iniciando ping no banco Supabase...
⏰ Timestamp: 2026-11-18T19:37:00.000000+00:00
🔌 Conectando ao Postgres...
✅ Ping executado com sucesso!
✅ Projeto Supabase permanece ativo.
```

---

## 📊 Monitoramento

### Ver histórico de execuções
1. **Actions** → **Keep Supabase Active**
2. Veja todos os runs anteriores (sucesso/falha)

### Notificações
- GitHub envia email automaticamente se o workflow falhar
- Configure em: Settings → Notifications → GitHub Actions

### Badge no README (opcional)
Adicione ao README.md:
```markdown
![Keep-Alive Status](https://github.com/<USUARIO>/<REPO>/actions/workflows/keep-alive.yml/badge.svg)
```

---

## 🔧 Ajustar frequência

Editar `.github/workflows/keep-alive.yml`:

```yaml
schedule:
  # A cada 3 dias (mais frequente)
  - cron: '0 12 */3 * *'
  
  # A cada 6 dias (menos frequente, mas arriscado)
  - cron: '0 12 */6 * *'
```

**Recomendado:** manter 5 dias (margem de 2 dias antes da pausa aos 7 dias).

---

## 🆘 Projeto pausou mesmo com keep-alive

**Investigar:**
1. Workflow estava realmente executando? (ver histórico no Actions)
2. Última execução bem-sucedida foi há quanto tempo?
3. Há algum erro nos logs do último run?

**Ação imediata:**
1. Retomar projeto no Supabase
2. Executar workflow manualmente para confirmar que funciona
3. Corrigir o problema identificado nos logs

---

## 💡 Alternativas

Se o keep-alive não atende suas necessidades:

### Opção 1: Upgrade para plano Pro
- Custo: US$ 25/mês
- Projetos pagos **nunca pausam**
- Inclui backups diários

### Opção 2: Uso regular pela equipe
- Se a equipe usa o sistema toda semana, o keep-alive é redundante
- Cada lançamento/consulta/exportação conta como atividade

### Opção 3: Ping externo (alternativo)
- Serviços como [cron-job.org](https://cron-job.org) (gratuito)
- Fazem requisições HTTP periodicamente
- Requer endpoint público na API
