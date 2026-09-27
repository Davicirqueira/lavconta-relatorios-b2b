"""Autenticação: validação do JWT emitido pelo Supabase.

ABORDAGEM
    Validação completa, não apenas decodificação: assinatura verificada contra a
    chave pública do JWKS do Supabase, mais ``exp``, ``iss`` e ``aud``.

    Assinatura assimétrica (``ES256``) significa que este servidor guarda apenas
    a chave **pública**. Mesmo comprometido, não consegue *emitir* tokens —
    só validá-los. Com o segredo simétrico legado isso não seria verdade.

    Configuração confirmada no projeto real (ver design §18, item 1).

SAÍDA SEGURA
    O cliente recebe sempre ``401`` com mensagem genérica (Req 1.5): revelar
    *qual* verificação falhou ajudaria um atacante a ajustar o ataque.

    O log do servidor registra o motivo exato. Essa assimetria é deliberada: sem
    ela, uma configuração errada de ``iss``/``aud`` rejeitaria todo token válido
    sem deixar pista, e o diagnóstico viraria um mistério.
"""

import logging
import threading
import time
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import Configuracao, obter_configuracao
from app.core.erros import nao_autenticado

logger = logging.getLogger("lavconta.seguranca")

# O JWKS é buscado por HTTP. Sem cache seria uma chamada externa por requisição,
# o que é péssimo com o cold start do plano gratuito.
TTL_CACHE_JWKS_SEGUNDOS = 600

# auto_error=False: queremos devolver o nosso envelope de erro, não o do FastAPI
_extrator_bearer = HTTPBearer(auto_error=False, description="JWT emitido pelo Supabase")


class _CacheJWKS:
    """Cache do cliente de JWKS, com recarga sob ``kid`` desconhecido.

    Rotação de chave no Supabase produz um ``kid`` novo. Em vez de falhar até o
    TTL expirar, recarregamos uma vez ao encontrar ``kid`` desconhecido.
    """

    def __init__(self) -> None:
        self._cliente: PyJWKClient | None = None
        self._criado_em: float = 0.0
        self._trava = threading.Lock()

    def obter(self, url: str, *, forcar: bool = False) -> PyJWKClient:
        agora = time.monotonic()
        with self._trava:
            expirado = (agora - self._criado_em) > TTL_CACHE_JWKS_SEGUNDOS
            if self._cliente is None or expirado or forcar:
                self._cliente = PyJWKClient(url, cache_keys=True, max_cached_keys=8)
                self._criado_em = agora
            return self._cliente

    def limpar(self) -> None:
        """Usado pelos testes para isolar execuções."""
        with self._trava:
            self._cliente = None
            self._criado_em = 0.0


_cache_jwks = _CacheJWKS()


def limpar_cache_jwks() -> None:
    """Descarta o cache do JWKS (testes)."""
    _cache_jwks.limpar()


class UsuarioAutenticado:
    """Identidade extraída de um token já validado.

    Na v1 há usuário único e nenhuma autorização por papel: a regra é binária,
    token válido entra. Os campos existem para log e para evolução futura.
    """

    __slots__ = ("email", "id", "papel")

    def __init__(self, id: str, email: str | None, papel: str | None) -> None:  # noqa: A002
        self.id = id
        self.email = email
        self.papel = papel

    def __repr__(self) -> str:
        return f"<UsuarioAutenticado id={self.id[:8]}...>"


def _validar_token(token: str, configuracao: Configuracao) -> dict[str, Any]:
    """Valida assinatura e claims, devolvendo o payload.

    Levanta ``ErroDeDominio`` (401) em qualquer falha, registrando no log o
    motivo real.
    """
    try:
        cabecalho = jwt.get_unverified_header(token)
    except jwt.PyJWTError as erro:
        logger.warning("Token malformado: %s", erro)
        raise nao_autenticado() from erro

    algoritmo = cabecalho.get("alg")
    if algoritmo not in ("ES256", "RS256"):
        # 'none' ou algoritmo simétrico inesperado: recusa explícita para não
        # abrir caminho a confusão de algoritmo
        logger.warning("Algoritmo de assinatura não aceito: %r", algoritmo)
        raise nao_autenticado()

    chave = _obter_chave_de_assinatura(token, configuracao)

    try:
        return jwt.decode(
            token,
            chave,
            algorithms=[algoritmo],
            issuer=configuracao.SUPABASE_JWT_ISSUER,
            audience=configuracao.SUPABASE_JWT_AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError as erro:
        logger.info("Token expirado")
        raise nao_autenticado() from erro
    except jwt.InvalidAudienceError as erro:
        # Diagnóstico explícito: 'aud' errado na configuração rejeitaria TODO
        # token válido, e sem esta linha a causa não apareceria em lugar algum.
        logger.error(
            "Audiência divergente: esperava %r. Verifique SUPABASE_JWT_AUDIENCE.",
            configuracao.SUPABASE_JWT_AUDIENCE,
        )
        raise nao_autenticado() from erro
    except jwt.InvalidIssuerError as erro:
        logger.error(
            "Emissor divergente: esperava %r. Verifique SUPABASE_JWT_ISSUER.",
            configuracao.SUPABASE_JWT_ISSUER,
        )
        raise nao_autenticado() from erro
    except jwt.InvalidSignatureError as erro:
        logger.warning("Assinatura inválida")
        raise nao_autenticado() from erro
    except jwt.MissingRequiredClaimError as erro:
        logger.warning("Claim obrigatório ausente: %s", erro.claim)
        raise nao_autenticado() from erro
    except jwt.PyJWTError as erro:
        logger.warning("Token inválido (%s): %s", type(erro).__name__, erro)
        raise nao_autenticado() from erro


def _obter_chave_de_assinatura(token: str, configuracao: Configuracao) -> Any:  # noqa: ANN401
    """Busca no JWKS a chave pública correspondente ao ``kid`` do token."""
    try:
        cliente = _cache_jwks.obter(configuracao.SUPABASE_JWKS_URL)
        return cliente.get_signing_key_from_jwt(token).key
    except jwt.PyJWKClientError as erro:
        # 'kid' desconhecido pode ser rotação de chave: recarrega uma vez antes
        # de desistir.
        logger.info("Chave não encontrada no cache do JWKS, recarregando: %s", erro)
        try:
            cliente = _cache_jwks.obter(configuracao.SUPABASE_JWKS_URL, forcar=True)
            return cliente.get_signing_key_from_jwt(token).key
        except Exception as erro_recarga:  # noqa: BLE001
            logger.warning("Chave de assinatura não encontrada após recarga: %s", erro_recarga)
            raise nao_autenticado() from erro_recarga
    except Exception as erro:  # noqa: BLE001 — falha de rede ao buscar o JWKS
        logger.error("Falha ao obter o JWKS em %s: %s", configuracao.SUPABASE_JWKS_URL, erro)
        raise nao_autenticado() from erro


async def usuario_atual(
    credencial: Annotated[HTTPAuthorizationCredentials | None, Depends(_extrator_bearer)],
) -> UsuarioAutenticado:
    """Dependência de autenticação de toda rota de dados.

    Aplicada no nível do ``APIRouter``, não rota a rota: esquecer um ``Depends``
    deixaria uma rota de dados pública, e essa é uma falha que não pode depender
    de disciplina individual. Um teste estrutural reforça a regra.
    """
    if credencial is None or not credencial.credentials:
        logger.info("Requisição sem cabeçalho Authorization")
        raise nao_autenticado()

    if credencial.scheme.lower() != "bearer":
        logger.info("Esquema de autorização inesperado: %r", credencial.scheme)
        raise nao_autenticado()

    payload = _validar_token(credencial.credentials, obter_configuracao())

    return UsuarioAutenticado(
        id=str(payload["sub"]),
        email=payload.get("email"),
        papel=payload.get("role"),
    )


# Alias para uso nas assinaturas dos routers
Autenticado = Annotated[UsuarioAutenticado, Depends(usuario_atual)]
