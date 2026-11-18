# Scripts auxiliares

Scripts utilitários que não fazem parte da aplicação FastAPI principal.

## `keep_alive.py`

Mantém o projeto Supabase ativo no plano Free executando uma query mínima
(`SELECT 1`) periodicamente.

**Uso local (teste):**
```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://..."
python scripts/keep_alive.py
```

**Uso em produção:**
Executado automaticamente pelo GitHub Actions (`.github/workflows/keep-alive.yml`)
a cada 5 dias. Requer o secret `DATABASE_URL` configurado no repositório.

**Dependências:**
```powershell
pip install -r requirements-scripts.txt
```
