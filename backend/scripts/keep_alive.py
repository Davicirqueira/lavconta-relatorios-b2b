#!/usr/bin/env python3
"""Script para manter o projeto Supabase ativo.

Executa uma query mínima (SELECT 1) para registrar atividade no banco e impedir
que o Supabase pause o projeto por inatividade no plano Free.

Este script é executado pelo GitHub Actions a cada 5 dias.

Uso:
    DATABASE_URL=<connection-string> python keep_alive.py

Variáveis de ambiente:
    DATABASE_URL: string de conexão do Postgres (obrigatória, sensível).

Exit codes:
    0: sucesso — conexão estabelecida e query executada.
    1: falha — erro de conexão, query ou configuração.
"""

import os
import sys
from datetime import datetime, timezone


def main() -> int:
    """Executa ping no banco e retorna código de saída."""
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        print("❌ ERRO: variável DATABASE_URL não definida", file=sys.stderr)
        print("Configure o secret no GitHub Actions.", file=sys.stderr)
        return 1
    
    print(f"🔄 Iniciando ping no banco Supabase...")
    print(f"⏰ Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    try:
        # Importar psycopg apenas quando necessário (permite validar env antes)
        import psycopg
        
        # Conectar ao banco
        print("🔌 Conectando ao Postgres...")
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                # Query mínima para registrar atividade
                cur.execute("SELECT 1")
                resultado = cur.fetchone()
                
                if resultado and resultado[0] == 1:
                    print("✅ Ping executado com sucesso!")
                    print("✅ Projeto Supabase permanece ativo.")
                    return 0
                else:
                    print("⚠️  Query retornou resultado inesperado", file=sys.stderr)
                    return 1
    
    except ImportError as erro:
        print(f"❌ ERRO: biblioteca psycopg não instalada: {erro}", file=sys.stderr)
        print("Execute: pip install psycopg[binary]", file=sys.stderr)
        return 1
    
    except Exception as erro:
        print(f"❌ ERRO ao conectar ou executar query: {erro}", file=sys.stderr)
        print("Verifique se DATABASE_URL está correto e se o banco está acessível.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
