"""Configuração da aplicação.

Ponto único de leitura de variáveis de ambiente. Nenhum outro módulo deve chamar
``os.getenv`` — todos consomem ``obter_configuracao()``.

A validação acontece na inicialização: se faltar variável obrigatória, a aplicação
falha imediatamente com erro que nomeia a chave, em vez de subir com default inseguro
e quebrar depois em produção.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ErroDeConfiguracao(RuntimeError):
    """Configuração ausente ou inválida na inicialização."""


class Configuracao(BaseSettings):
    """Variáveis de ambiente do backend.

    Todos os campos são obrigatórios e sem default: a ausência de qualquer um
    impede a aplicação de subir. Isso é deliberado — um default silencioso em
    configuração de segurança é pior que uma falha ruidosa.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Banco de dados ---------------------------------------------------
    # SENSÍVEL: credencial de acesso total ao Postgres.
    # Nunca logar o valor; referenciar sempre pelo nome da chave.
    DATABASE_URL: str = Field(min_length=1)

    # --- Autenticação (Supabase) ------------------------------------------
    # URL do JWKS: chaves públicas para validar a assinatura do JWT.
    SUPABASE_JWKS_URL: str = Field(min_length=1)
    # Emissor esperado (claim "iss").
    SUPABASE_JWT_ISSUER: str = Field(min_length=1)
    # Audiência esperada (claim "aud").
    SUPABASE_JWT_AUDIENCE: str = Field(min_length=1)

    # --- Borda ------------------------------------------------------------
    # Origens permitidas para CORS, separadas por vírgula. Coringa é proibido.
    CORS_ORIGENS: str = Field(min_length=1)

    @field_validator("CORS_ORIGENS")
    @classmethod
    def _recusar_coringa_em_cors(cls, valor: str) -> str:
        """Impede ``*`` em CORS.

        A API é consumida com credencial (JWT). Coringa em CORS permitiria que
        qualquer origem chamasse a API pelo navegador do usuário autenticado.
        """
        if "*" in valor:
            raise ValueError(
                "CORS_ORIGENS não pode conter '*'. Liste as origens "
                "explicitamente, separadas por vírgula."
            )
        return valor

    @property
    def origens_cors(self) -> list[str]:
        """``CORS_ORIGENS`` como lista, sem entradas vazias."""
        return [origem.strip() for origem in self.CORS_ORIGENS.split(",") if origem.strip()]


@lru_cache
def obter_configuracao() -> Configuracao:
    """Devolve a configuração validada (memorizada).

    Raises:
        ErroDeConfiguracao: quando falta variável obrigatória ou um valor é
            inválido. A mensagem nomeia as chaves problemáticas e **não** expõe
            valores, para não vazar segredo em log.
    """
    try:
        return Configuracao()  # type: ignore[call-arg]
    except Exception as erro:  # noqa: BLE001 — traduzido para erro de domínio
        chaves = _extrair_chaves_com_problema(erro)
        detalhe = ", ".join(chaves) if chaves else "verifique o arquivo .env"
        raise ErroDeConfiguracao(
            f"Configuração inválida ou incompleta. Chaves com problema: {detalhe}. "
            f"Use backend/.env.example como referência."
        ) from erro


def _extrair_chaves_com_problema(erro: Exception) -> list[str]:
    """Extrai os nomes das chaves com erro de validação, sem expor valores."""
    erros = getattr(erro, "errors", None)
    if not callable(erros):
        return []
    return [str(item["loc"][0]) for item in erros() if isinstance(item, dict) and item.get("loc")]
