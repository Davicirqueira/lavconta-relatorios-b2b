/**
 * Testes das mensagens de falha ao redefinir senha.
 *
 * Usa as classes de erro reais do supabase-js, não objetos imitando o formato:
 * se a biblioteca mudar a forma do erro, o teste acusa.
 */

import { describe, expect, it } from "vitest";
import { AuthApiError, AuthSessionMissingError, AuthWeakPasswordError } from "@supabase/supabase-js";
import { mensagemErroRedefinicao } from "./mensagens";

const LINK_INVALIDO = "O link de redefinição expirou ou já foi usado. Solicite um novo link.";

describe("mensagemErroRedefinicao", () => {
  it("senha fraca não manda pedir novo link", () => {
    const erro = new AuthWeakPasswordError("weak", 422, ["length"]);
    const mensagem = mensagemErroRedefinicao(erro);

    expect(mensagem).toBe("A senha é mais curta do que a política de segurança permite.");
    expect(mensagem).not.toBe(LINK_INVALIDO);
  });

  it("combina os motivos quando há mais de um", () => {
    const erro = new AuthWeakPasswordError("weak", 422, ["length", "characters"]);
    expect(mensagemErroRedefinicao(erro)).toBe(
      "A senha é mais curta do que a política de segurança permite. " +
        "A senha não tem todos os tipos de caractere exigidos pela política de segurança.",
    );
  });

  it("senha vazada tem mensagem própria", () => {
    const erro = new AuthWeakPasswordError("weak", 422, ["pwned"]);
    expect(mensagemErroRedefinicao(erro)).toBe(
      "Esta senha já apareceu em vazamentos conhecidos. Escolha outra.",
    );
  });

  it("senha fraca sem motivo informado tem texto genérico, não o de link", () => {
    const erro = new AuthWeakPasswordError("weak", 422, []);
    expect(mensagemErroRedefinicao(erro)).toMatch(/política de segurança/);
  });

  it("sessão ausente é o único caso em que o link é o problema", () => {
    expect(mensagemErroRedefinicao(new AuthSessionMissingError())).toBe(LINK_INVALIDO);
    expect(mensagemErroRedefinicao(new AuthApiError("x", 403, "session_not_found"))).toBe(
      LINK_INVALIDO,
    );
  });

  it("senha igual à atual", () => {
    expect(mensagemErroRedefinicao(new AuthApiError("x", 422, "same_password"))).toBe(
      "A nova senha precisa ser diferente da senha atual.",
    );
  });

  it("limite de tentativas", () => {
    expect(
      mensagemErroRedefinicao(new AuthApiError("x", 429, "over_request_rate_limit")),
    ).toMatch(/Aguarde/);
  });

  it("erro desconhecido cai no texto genérico em português", () => {
    expect(mensagemErroRedefinicao(new Error("boom"))).toBe(
      "Não foi possível redefinir a senha. Tente novamente ou solicite um novo link.",
    );
  });
});
