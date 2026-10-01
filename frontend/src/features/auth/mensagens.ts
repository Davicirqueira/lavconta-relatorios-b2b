/**
 * Mensagens em português para falhas ao redefinir a senha.
 *
 * POR QUE EXISTE
 *   A tela dizia "Solicite um novo link" para qualquer falha. Quando o
 *   servidor recusa a senha por ser fraca, o link continua válido e a
 *   mensagem mandava o operador refazer um passo desnecessário.
 *
 * O texto não cita números da política (ex.: "12 caracteres"): a regra mora
 * no painel do Supabase e pode mudar sem mudar o código. Inventar o número
 * aqui criaria uma segunda fonte que divergiria.
 *
 * Formatos conferidos em @supabase/auth-js instalado: AuthWeakPasswordError
 * com `reasons` ("length" | "characters" | "pwned") e `code` em AuthError.
 */

import { isAuthError, isAuthSessionMissingError, isAuthWeakPasswordError } from "@supabase/supabase-js";

const MOTIVO_SENHA_FRACA: Record<string, string> = {
  length: "A senha é mais curta do que a política de segurança permite.",
  characters: "A senha não tem todos os tipos de caractere exigidos pela política de segurança.",
  pwned: "Esta senha já apareceu em vazamentos conhecidos. Escolha outra.",
};

const LINK_INVALIDO = "O link de redefinição expirou ou já foi usado. Solicite um novo link.";

export function mensagemErroRedefinicao(erro: unknown): string {
  if (isAuthWeakPasswordError(erro)) {
    const motivos = erro.reasons.map((m) => MOTIVO_SENHA_FRACA[m]).filter(Boolean);
    return motivos.length > 0
      ? motivos.join(" ")
      : "A senha não atende à política de segurança. Escolha uma senha mais forte.";
  }

  // sem sessão de recuperação: o link não foi aberto, expirou ou já foi usado
  if (isAuthSessionMissingError(erro)) return LINK_INVALIDO;

  if (isAuthError(erro)) {
    switch (erro.code) {
      case "same_password":
        return "A nova senha precisa ser diferente da senha atual.";
      case "session_not_found":
      case "session_expired":
      case "otp_expired":
        return LINK_INVALIDO;
      case "over_request_rate_limit":
        return "Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente de novo.";
    }
  }

  return "Não foi possível redefinir a senha. Tente novamente ou solicite um novo link.";
}
