"""Confirma os valores reais de 'iss' e 'aud' emitidos pelo Supabase.

POR QUE ISSO EXISTE
    A validação do JWT confere 'iss' e 'aud' contra valores configurados. Se eles
    estiverem errados no .env, a API rejeitaria TODO token válido — falha difícil
    de diagnosticar depois. Este script confirma os valores na fonte.

    De bônus, valida o token contra o JWKS com PyJWT: é o mesmo caminho que a
    dependência de autenticação vai usar (tarefa 10), testado antes de escrevê-lo.

SEGURANÇA
    - A senha é lida de forma OCULTA (getpass) e nunca é impressa nem gravada.
    - O token NUNCA é impresso: ele é uma credencial portadora e, exposto, daria
      acesso à API até expirar.
    - Só são exibidos valores não sensíveis: alg, kid, iss, aud, expiração e o
      início do 'sub'.

USO
    backend\\.venv\\Scripts\\python.exe scripts_verificacao\\confirmar_claims_jwt.py
"""

import getpass
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import jwt
from dotenv import dotenv_values
from jwt import PyJWKClient

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
RAIZ_PROJETO = RAIZ_BACKEND.parent

# Modo de diagnóstico: exibe a senha enquanto é digitada, para descartar erro de
# digitação. Use apenas em terminal descartável — a senha fica no histórico da
# sessão. O padrão continua sendo entrada oculta.
SENHA_VISIVEL = "--senha-visivel" in sys.argv


def encerrar(mensagem: str) -> None:
    print(f"\nFALHA: {mensagem}")
    sys.exit(1)


# --- configuração ----------------------------------------------------------
frontend_env = dotenv_values(RAIZ_PROJETO / "frontend" / ".env")
url_projeto = (frontend_env.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
chave_publicavel = (frontend_env.get("VITE_SUPABASE_PUBLISHABLE_KEY") or "").strip()

backend_env = dotenv_values(RAIZ_BACKEND / ".env")
jwks_url = (backend_env.get("SUPABASE_JWKS_URL") or "").strip()
iss_esperado = (backend_env.get("SUPABASE_JWT_ISSUER") or "").strip()
aud_esperado = (backend_env.get("SUPABASE_JWT_AUDIENCE") or "").strip()

if not url_projeto:
    encerrar("VITE_SUPABASE_URL não encontrada em frontend/.env")
if not chave_publicavel:
    encerrar(
        "VITE_SUPABASE_PUBLISHABLE_KEY vazia em frontend/.env.\n"
        "  Copie do painel: Project Settings > API Keys > publishable key"
    )

print("=" * 72)
print("CONFIRMACAO DOS CLAIMS DO JWT")
print("=" * 72)
print(f"Projeto : {url_projeto}")
print(f"JWKS    : {jwks_url}")
print()
print("Valores configurados hoje em backend/.env:")
print(f"  iss esperado : {iss_esperado}")
print(f"  aud esperado : {aud_esperado}")
print()

# --- sonda: a chave publicavel e aceita? -----------------------------------
# Isola o problema. Se este endpoint responde 200, a chave esta correta e uma
# falha posterior e de credencial, nao de configuracao.
print("-" * 72)
print("0. SONDA DA CONFIGURACAO (sem credenciais)")
print("-" * 72)
try:
    sonda = httpx.get(
        f"{url_projeto}/auth/v1/settings",
        headers={"apikey": chave_publicavel},
        timeout=30,
    )
except httpx.HTTPError as erro:
    encerrar(f"erro de rede ao consultar /auth/v1/settings: {erro}")

if sonda.status_code != 200:
    print(f"  [FALHA] HTTP {sonda.status_code} — a chave publicavel foi recusada")
    print(f"          {sonda.text[:200]}")
    encerrar("corrija VITE_SUPABASE_PUBLISHABLE_KEY em frontend/.env")

ajustes = sonda.json()
email_habilitado = ajustes.get("external", {}).get("email", True)
exige_confirmacao = not ajustes.get("mailer_autoconfirm", False)
signup_permitido = not ajustes.get("disable_signup", False)

print("  [OK] chave publicavel aceita")
print(f"  login por e-mail/senha habilitado : {email_habilitado}")
print(f"  exige confirmacao de e-mail       : {exige_confirmacao}")
print(f"  auto-cadastro (signup) permitido  : {signup_permitido}")
if signup_permitido:
    print("       ATENCAO: o signup deveria estar desabilitado (Req 1.9)")

# --- credenciais -----------------------------------------------------------
print()
email = input("E-mail do usuario: ").strip()
if not email:
    encerrar("e-mail vazio")

token: str | None = None

if SENHA_VISIVEL:
    print()
    print("  !!! MODO DIAGNOSTICO: a senha sera EXIBIDA ao ser digitada.")
    print("      Use apenas em terminal descartavel.")
    print("      Ao colar a saida em algum lugar, REMOVA a linha da senha.")

for tentativa in range(1, 4):
    if SENHA_VISIVEL:
        senha = input("Senha (VISIVEL): ")
    else:
        senha = getpass.getpass("Senha (digitacao oculta): ")
    if not senha:
        encerrar("senha vazia")

    # Diagnostico SEM revelar a senha: caracteristicas que costumam causar
    # falha silenciosa (captura truncada, espaco invisivel, caractere acentuado
    # mal decodificado pelo terminal).
    tem_nao_ascii = any(ord(caractere) > 127 for caractere in senha)
    print(f"  capturados {len(senha)} caracteres", end="")
    if tem_nao_ascii:
        print(" | contem caractere NAO-ASCII (possivel problema de codificacao)", end="")
    if senha != senha.strip():
        print(" | ATENCAO: ha espaco no inicio ou fim", end="")
    print()

    print("  Autenticando...")
    try:
        resposta = httpx.post(
            f"{url_projeto}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": chave_publicavel},
            json={"email": email, "password": senha},
            timeout=30,
        )
    except httpx.HTTPError as erro:
        encerrar(f"erro de rede: {erro}")
    finally:
        del senha  # nao mantem a senha em memoria alem do necessario

    if resposta.status_code == 200:
        token = resposta.json().get("access_token")
        if not token:
            encerrar("a resposta nao trouxe access_token")
        print("  Login bem-sucedido. (o token NAO sera exibido)")
        break

    # --- falhou: mostra o corpo completo para diagnostico ------------------
    print(f"  [FALHA] HTTP {resposta.status_code}")
    try:
        print(f"          resposta: {resposta.json()}")
    except ValueError:
        print(f"          resposta: {resposta.text[:300]}")

    if tentativa < 3:
        print(f"\n  Tentativa {tentativa + 1} de 3 — digite a senha novamente:")

if not token:
    encerrar(
        "login recusado em 3 tentativas.\n"
        "  Se os 'caracteres capturados' correspondem ao tamanho real da senha,\n"
        "  o problema esta na credencial (senha diferente da cadastrada no painel,\n"
        "  ou usuario sem senha definida / e-mail nao confirmado)."
    )

# --- cabeçalho do token ----------------------------------------------------
cabecalho = jwt.get_unverified_header(token)
print()
print("-" * 72)
print("1. CABECALHO DO TOKEN")
print("-" * 72)
print(f"  alg : {cabecalho.get('alg')}")
print(f"  kid : {cabecalho.get('kid')}")

# --- claims (sem verificar, só para leitura) -------------------------------
claims = jwt.decode(token, options={"verify_signature": False})
iss_real = claims.get("iss", "")
aud_real = claims.get("aud", "")
expira = datetime.fromtimestamp(claims["exp"], tz=UTC) if "exp" in claims else None
emitido = datetime.fromtimestamp(claims["iat"], tz=UTC) if "iat" in claims else None

print()
print("-" * 72)
print("2. CLAIMS REAIS EMITIDOS")
print("-" * 72)
print(f"  iss  : {iss_real}")
print(f"  aud  : {aud_real}")
print(f"  role : {claims.get('role')}")
print(f"  sub  : {str(claims.get('sub'))[:8]}... (truncado)")
if emitido and expira:
    print(f"  iat  : {emitido:%Y-%m-%d %H:%M:%S} UTC")
    print(f"  exp  : {expira:%Y-%m-%d %H:%M:%S} UTC")
    print(f"  vida : {(expira - emitido).total_seconds() / 60:.0f} minutos")

# --- comparação com o configurado ------------------------------------------
print()
print("-" * 72)
print("3. CONFERENCIA COM backend/.env")
print("-" * 72)
divergencias: list[str] = []

if iss_real == iss_esperado:
    print("  [OK   ] iss confere")
else:
    print("  [AJUSTAR] iss divergente")
    print(f"           configurado: {iss_esperado}")
    print(f"           real       : {iss_real}")
    divergencias.append(f"SUPABASE_JWT_ISSUER={iss_real}")

if aud_real == aud_esperado:
    print("  [OK   ] aud confere")
else:
    print("  [AJUSTAR] aud divergente")
    print(f"           configurado: {aud_esperado}")
    print(f"           real       : {aud_real}")
    divergencias.append(f"SUPABASE_JWT_AUDIENCE={aud_real}")

# --- validação completa via JWKS (o caminho da tarefa 10) ------------------
print()
print("-" * 72)
print("4. VALIDACAO COMPLETA CONTRA O JWKS (caminho da tarefa 10)")
print("-" * 72)
try:
    cliente_jwks = PyJWKClient(jwks_url, cache_keys=True)
    chave = cliente_jwks.get_signing_key_from_jwt(token)
    jwt.decode(
        token,
        chave.key,
        algorithms=[cabecalho["alg"]],
        issuer=iss_real,
        audience=aud_real,
        options={"require": ["exp", "iss", "aud"]},
    )
    print("  [OK] assinatura, exp, iss e aud validados com a chave publica do JWKS")
    print("       -> a abordagem de validacao do design funciona nesta configuracao")
except Exception as erro:  # noqa: BLE001 — script de diagnóstico
    print(f"  [FALHA] {type(erro).__name__}: {erro}")
    divergencias.append("a validacao via JWKS falhou; revisar antes da tarefa 10")

# --- resultado -------------------------------------------------------------
print()
print("=" * 72)
if divergencias:
    print("ACAO NECESSARIA — ajuste backend/.env com:")
    for linha in divergencias:
        print(f"  {linha}")
else:
    print("RESULTADO: backend/.env esta correto. Nada a ajustar.")
print("=" * 72)

# limpa a variável de ambiente por precaução, caso algo tenha vazado para ela
os.environ.pop("SUPABASE_PASSWORD", None)
