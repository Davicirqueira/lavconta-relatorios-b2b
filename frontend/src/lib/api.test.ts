/**
 * Testes do cliente de API: sinal de servidor lento e tradução de erro.
 *
 * Só a fronteira externa é substituída: `fetch` (rede) e o token do Supabase.
 * O contador de lentidão e a tradução do envelope rodam de verdade.
 *
 * O caso que mais importa: o contador precisa voltar a zero em TODOS os
 * desfechos (sucesso, erro HTTP, falha de rede, cancelamento). Se vazar, o
 * painel "Reativando o servidor" fica preso na tela para sempre.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./supabase", () => ({ obterToken: async () => "token-de-teste" }));

type Api = typeof import("./api");
let api: Api;

beforeEach(async () => {
  vi.stubEnv("VITE_API_URL", "http://api.teste");
  vi.useFakeTimers();
  vi.resetModules();
  api = await import("./api");
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

/** fetch controlável: devolve a promessa e as funções para resolvê-la. */
function fetchPendente() {
  let resolver!: (r: Response) => void;
  let rejeitar!: (e: unknown) => void;
  const promessa = new Promise<Response>((res, rej) => {
    resolver = res;
    rejeitar = rej;
  });
  const fetchFalso = vi.fn(() => promessa);
  vi.stubGlobal("fetch", fetchFalso);
  return { resolver, rejeitar, fetchFalso };
}

function respostaJson(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("sinal de servidor lento", () => {
  it("só acende depois de 3s e apaga quando a resposta chega", async () => {
    const { resolver } = fetchPendente();
    const chamada = api.apiGet("/api/clientes");

    await vi.advanceTimersByTimeAsync(2_900);
    expect(api.servidorEstaLento()).toBe(false);

    await vi.advanceTimersByTimeAsync(200);
    expect(api.servidorEstaLento()).toBe(true);

    resolver(respostaJson([]));
    await chamada;
    expect(api.servidorEstaLento()).toBe(false);
  });

  it("não acende para resposta rápida", async () => {
    const { resolver } = fetchPendente();
    const chamada = api.apiGet("/api/clientes");
    resolver(respostaJson([]));
    await chamada;

    await vi.advanceTimersByTimeAsync(5_000);
    expect(api.servidorEstaLento()).toBe(false);
  });

  it("apaga quando a requisição lenta termina em erro HTTP", async () => {
    const { resolver } = fetchPendente();
    const chamada = api.apiGet("/api/clientes");
    const verificacao = expect(chamada).rejects.toBeInstanceOf(api.ErroDeApi);

    await vi.advanceTimersByTimeAsync(3_100);
    expect(api.servidorEstaLento()).toBe(true);

    resolver(respostaJson({ erro: { codigo: "NAO_ENCONTRADO", mensagem: "x" } }, 404));
    await verificacao;
    expect(api.servidorEstaLento()).toBe(false);
  });

  it("apaga quando a requisição lenta falha na rede", async () => {
    const { rejeitar } = fetchPendente();
    const chamada = api.apiGet("/api/clientes");
    const verificacao = expect(chamada).rejects.toMatchObject({ codigo: "ERRO_REDE" });

    await vi.advanceTimersByTimeAsync(3_100);
    rejeitar(new TypeError("Failed to fetch"));
    await verificacao;

    expect(api.servidorEstaLento()).toBe(false);
  });

  it("apaga quando a requisição lenta é cancelada", async () => {
    const { rejeitar } = fetchPendente();
    const chamada = api.apiGet("/api/clientes");
    const verificacao = expect(chamada).rejects.toMatchObject({ name: "AbortError" });

    await vi.advanceTimersByTimeAsync(3_100);
    rejeitar(new DOMException("cancelada", "AbortError"));
    await verificacao;

    expect(api.servidorEstaLento()).toBe(false);
  });

  it("notifica os ouvintes ao acender e ao apagar", async () => {
    const ouvinte = vi.fn();
    const cancelar = api.assinarServidorLento(ouvinte);
    const { resolver } = fetchPendente();
    const chamada = api.apiGet("/api/clientes");

    await vi.advanceTimersByTimeAsync(3_100);
    resolver(respostaJson([]));
    await chamada;

    expect(ouvinte).toHaveBeenCalledTimes(2);
    cancelar();
  });
});

describe("tradução do envelope de erro", () => {
  it("expõe código, mensagem e detalhes da API", async () => {
    const { resolver } = fetchPendente();
    const chamada = api.apiPost("/api/lancamentos", {});
    resolver(
      respostaJson(
        {
          erro: {
            codigo: "ITENS_SEM_PRECO",
            mensagem: "Os itens Roupão não têm preço.",
            detalhes: { itens: ["Roupão"] },
          },
        },
        422,
      ),
    );

    await expect(chamada).rejects.toMatchObject({
      codigo: "ITENS_SEM_PRECO",
      message: "Os itens Roupão não têm preço.",
      detalhes: { itens: ["Roupão"] },
      status: 422,
    });
  });

  it("injeta o token no cabeçalho Authorization", async () => {
    const { resolver, fetchFalso } = fetchPendente();
    const chamada = api.apiGet("/api/clientes");
    resolver(respostaJson([]));
    await chamada;

    const [, init] = fetchFalso.mock.calls[0] as unknown as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe(
      "Bearer token-de-teste",
    );
  });
});
