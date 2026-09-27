"""Confere a configuração de autenticação do Supabase SEM usar credencial.

O que verifica:
  1. Descoberta OIDC (endpoint público): issuer, URL do JWKS e algoritmos.
  2. JWKS: chaves de assinatura publicadas.
  3. /auth/v1/settings: se o auto-cadastro está desabilitado (Req 1.9) e se o
     projeto exige confirmação de e-mail.
  4. Compara tudo com o que está em backend/.env.

Não precisa de senha de usuário. A chave publicável (pública por definição) é
exigida apenas pelo item 3.

USO
    backend\\.venv\\Scripts\\python.exe scripts_verificacao\\conferir_config_auth.py
"""

import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
RAIZ_PROJETO = RAIZ_BACKEND.parent

backend_env = dotenv_values(RAIZ_BACKEND / ".env")
frontend_env = dotenv_values(RAIZ_PROJETO / "frontend" / ".env")

jwks_configurado = (backend_env.get("SUPABASE_JWKS_URL") or "").strip()
iss_configurado = (backend_env.get("SUPABASE_JWT_ISSUER") or "").strip()
aud_configurado = (backend_env.get("SUPABASE_JWT_AUDIENCE") or "").strip()
url_projeto = (frontend_env.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
chave_publicavel = (frontend_env.get("VITE_SUPABASE_PUBLISHABLE_KEY") or "").strip()

if not url_projeto:
    print("FALHA: VITE_SUPABASE_URL ausente em frontend/.env")
    sys.exit(1)

problemas: list[str] = []
pendentes: list[str] = []


def conferir(descricao: str, condicao: bool, detalhe: str = "") -> None:
    if condicao:
        print(f"  [OK      ] {descricao}")
    else:
        problemas.append(descricao)
        print(f"  [PROBLEMA] {descricao}")
        if detalhe:
            print(f"             {detalhe}")


print("=" * 72)
print("CONFIGURACAO DE AUTENTICACAO (sem credenciais)")
print("=" * 72)
print(f"Projeto: {url_projeto}")
print()

# --- 1. descoberta OIDC ----------------------------------------------------
print("-" * 72)
print("1. DESCOBERTA OIDC (endpoint publico)")
print("-" * 72)
try:
    descoberta = httpx.get(
        f"{url_projeto}/auth/v1/.well-known/openid-configuration", timeout=30
    ).raise_for_status()
except httpx.HTTPError as erro:
    print(f"  FALHA ao consultar: {erro}")
    sys.exit(1)

dados = descoberta.json()
issuer_real = dados.get("issuer", "")
jwks_real = dados.get("jwks_uri", "")
algoritmos = dados.get("id_token_signing_alg_values_supported", [])

print(f"  issuer declarado : {issuer_real}")
print(f"  jwks_uri         : {jwks_real}")
print(f"  algoritmos       : {', '.join(algoritmos)}")
print()
conferir(
    "SUPABASE_JWT_ISSUER confere com o issuer declarado",
    issuer_real == iss_configurado,
    f"configurado: {iss_configurado} | real: {issuer_real}",
)
conferir(
    "SUPABASE_JWKS_URL confere com o jwks_uri declarado",
    jwks_real == jwks_configurado,
    f"configurado: {jwks_configurado} | real: {jwks_real}",
)

# --- 2. JWKS ---------------------------------------------------------------
print()
print("-" * 72)
print("2. CHAVES DE ASSINATURA (JWKS)")
print("-" * 72)
try:
    jwks = httpx.get(jwks_real, timeout=30).raise_for_status().json()
except httpx.HTTPError as erro:
    print(f"  FALHA ao consultar: {erro}")
    sys.exit(1)

chaves = jwks.get("keys", [])
conferir("o JWKS publica ao menos uma chave", len(chaves) > 0)
for chave in chaves:
    print(f"    alg={chave.get('alg')}  kty={chave.get('kty')}  kid={chave.get('kid')}")
    print(f"    uso={chave.get('use')}  operacoes={chave.get('key_ops')}")

assimetricas = {"ES256", "ES384", "RS256", "RS384", "RS512"}
usa_assimetrica = any(chave.get("alg") in assimetricas for chave in chaves)
conferir(
    "assinatura assimetrica (backend guarda apenas a chave publica)",
    usa_assimetrica,
    "chave simetrica exigiria guardar segredo capaz de EMITIR tokens",
)
tem_privada = any("d" in chave for chave in chaves)
conferir(
    "o JWKS NAO expoe componente de chave privada",
    not tem_privada,
    "campo 'd' presente indica chave privada exposta",
)

# --- 3. ajustes do Auth ----------------------------------------------------
print()
print("-" * 72)
print("3. AJUSTES DO AUTH (/auth/v1/settings)")
print("-" * 72)

if not chave_publicavel:
    print("  IGNORADO: VITE_SUPABASE_PUBLISHABLE_KEY vazia em frontend/.env")
    print("            (Project Settings > API Keys > publishable key)")
    pendentes.append("verificar disable_signup e confirmacao de e-mail")
else:
    try:
        ajustes = (
            httpx.get(
                f"{url_projeto}/auth/v1/settings",
                headers={"apikey": chave_publicavel},
                timeout=30,
            )
            .raise_for_status()
            .json()
        )
    except httpx.HTTPError as erro:
        print(f"  FALHA: {erro}")
        print("  Verifique se a chave publicavel esta correta.")
        sys.exit(1)

    signup_desabilitado = bool(ajustes.get("disable_signup", False))
    autoconfirm = bool(ajustes.get("mailer_autoconfirm", False))
    provedores = {nome: ativo for nome, ativo in (ajustes.get("external") or {}).items() if ativo}

    print(f"  disable_signup     : {signup_desabilitado}")
    print(f"  mailer_autoconfirm : {autoconfirm}")
    print(f"  provedores ativos  : {', '.join(sorted(provedores)) or 'nenhum'}")
    print()
    conferir(
        "auto-cadastro DESABILITADO (Req 1.9)",
        signup_desabilitado,
        "com signup aberto, qualquer pessoa cria conta e acessa o faturamento",
    )
    conferir(
        "apenas o provedor de e-mail esta ativo",
        set(provedores) <= {"email"},
        f"provedores inesperados: {sorted(set(provedores) - {'email'})}",
    )
    if not autoconfirm:
        print("  [NOTA    ] o projeto EXIGE confirmacao de e-mail")
        print("             usuario criado por convite fica sem senha ate confirmar,")
        print("             e o login retorna 'invalid_credentials'")

# --- 4. o que so um token real confirma ------------------------------------
print()
print("-" * 72)
print("4. NAO VERIFICAVEL SEM TOKEN")
print("-" * 72)
print(f"  SUPABASE_JWT_AUDIENCE configurado: {aud_configurado}")
print("  O 'aud' existe apenas dentro de um token emitido. Confirmar exige")
print("  autenticar com uma credencial conhecida (ver confirmar_claims_jwt.py).")
print("  Mitigacao no codigo: divergencia de 'aud' e registrada no log do")
print("  servidor com os valores esperado e recebido, mantendo 401 generico")
print("  para o cliente (Req 1.5).")
pendentes.append("confirmar SUPABASE_JWT_AUDIENCE com um token real")

# --- resultado -------------------------------------------------------------
print()
print("=" * 72)
if problemas:
    print(f"{len(problemas)} PROBLEMA(S):")
    for item in problemas:
        print(f"  - {item}")
else:
    print("Nenhum problema na configuracao verificavel.")
if pendentes:
    print()
    print("Pendente(s):")
    for item in pendentes:
        print(f"  - {item}")
print("=" * 72)
sys.exit(1 if problemas else 0)
