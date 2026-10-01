/**
 * Testes da lógica do formulário de lançamento (tarefas 45 e 46).
 *
 * O grupo mais importante é o do agendador: ele garante que a barra de
 * totais nunca exiba um valor antigo por cima de um mais novo.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase", () => ({ obterToken: async () => null }));
vi.stubEnv("VITE_API_URL", "http://api.teste");

const { ErroDeApi } = await import("@/lib/api");
const {
  criarAgendador,
  interpretarErroDeSalvamento,
  normalizarQuantidade,
  passoQuantidade,
  linhasDoPedido,
} = await import("./logica");
const { valorNoInstante } = await import("@/lib/animacao");

describe("linhasDoPedido", () => {
  const ordem = ["lencol", "fronha", "toalha"];

  it("envia só itens com quantidade positiva, como número", () => {
    expect(linhasDoPedido({ lencol: "40", fronha: "", toalha: "20" }, ordem)).toEqual([
      { item_id: "lencol", quantidade: 40 },
      { item_id: "toalha", quantidade: 20 },
    ]);
  });

  it("zero e vazio ficam fora do pedido", () => {
    expect(linhasDoPedido({ lencol: "0", fronha: "" }, ordem)).toEqual([]);
  });

  it("segue a ordem do catálogo, não a ordem de preenchimento", () => {
    const quantidades = { toalha: "5", lencol: "3" };
    expect(linhasDoPedido(quantidades, ordem).map((l) => l.item_id)).toEqual(["lencol", "toalha"]);
  });

  it("ignora quantidade de item que não está no catálogo exibido", () => {
    expect(linhasDoPedido({ fantasma: "9" }, ordem)).toEqual([]);
  });
});

describe("quantidade", () => {
  it("aceita só dígitos e remove zeros à esquerda", () => {
    expect(normalizarQuantidade("4a0")).toBe("40");
    expect(normalizarQuantidade("007")).toBe("7");
    expect(normalizarQuantidade("-5")).toBe("5");
    expect(normalizarQuantidade("1,5")).toBe("15");
    expect(normalizarQuantidade("")).toBe("");
  });

  it("stepper sobe a partir de vazio", () => {
    expect(passoQuantidade("", 1)).toBe("1");
    expect(passoQuantidade("9", 1)).toBe("10");
  });

  it("descer de 1 tira o item do pedido em vez de ficar em zero", () => {
    expect(passoQuantidade("1", -1)).toBe("");
    expect(passoQuantidade("", -1)).toBe("");
    expect(passoQuantidade("5", -1)).toBe("4");
  });
});

describe("agendador da prévia", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("debounce: alterações seguidas disparam uma única requisição, com a última entrada", async () => {
    const executar = vi.fn(async (n: number) => n);
    const aoResultado = vi.fn();
    const agendador = criarAgendador({ executar, atrasoMs: 400, aoResultado, aoErro: vi.fn() });

    agendador.agendar(1);
    await vi.advanceTimersByTimeAsync(200);
    agendador.agendar(2);
    await vi.advanceTimersByTimeAsync(200);
    agendador.agendar(3);
    await vi.advanceTimersByTimeAsync(399);
    expect(executar).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    expect(executar).toHaveBeenCalledTimes(1);
    expect(executar.mock.calls[0][0]).toBe(3);
    expect(aoResultado).toHaveBeenCalledWith(3);
  });

  it("resposta atrasada não sobrescreve a mais nova", async () => {
    // A primeira requisição demora mais que a segunda. O servidor falso
    // ignora o sinal de cancelamento de propósito: o descarte precisa
    // acontecer do nosso lado, não depender do fetch.
    const respostas: Array<(valor: string) => void> = [];
    const executar = vi.fn(
      () => new Promise<string>((resolver) => respostas.push(resolver)),
    );
    const aoResultado = vi.fn();
    const agendador = criarAgendador({ executar, atrasoMs: 400, aoResultado, aoErro: vi.fn() });

    agendador.agendar(1);
    await vi.advanceTimersByTimeAsync(400); // requisição 1 em voo
    agendador.agendar(2);
    await vi.advanceTimersByTimeAsync(400); // requisição 2 em voo

    respostas[1]("nova");
    await vi.advanceTimersByTimeAsync(0);
    respostas[0]("antiga");
    await vi.advanceTimersByTimeAsync(0);

    expect(aoResultado).toHaveBeenCalledTimes(1);
    expect(aoResultado).toHaveBeenCalledWith("nova");
  });

  it("aborta o sinal da requisição em voo ao reagendar", async () => {
    const sinais: AbortSignal[] = [];
    const executar = vi.fn((_: number, sinal: AbortSignal) => {
      sinais.push(sinal);
      return new Promise<number>(() => {});
    });
    const agendador = criarAgendador({
      executar,
      atrasoMs: 400,
      aoResultado: vi.fn(),
      aoErro: vi.fn(),
    });

    agendador.agendar(1);
    await vi.advanceTimersByTimeAsync(400);
    agendador.agendar(2);

    expect(sinais[0].aborted).toBe(true);
  });

  it("erro de requisição cancelada não é reportado", async () => {
    const aoErro = vi.fn();
    const executar = vi.fn(
      (_: number, sinal: AbortSignal) =>
        new Promise<number>((_res, rejeitar) =>
          sinal.addEventListener("abort", () => rejeitar(new DOMException("x", "AbortError"))),
        ),
    );
    const agendador = criarAgendador({ executar, atrasoMs: 400, aoResultado: vi.fn(), aoErro });

    agendador.agendar(1);
    await vi.advanceTimersByTimeAsync(400);
    agendador.cancelar();
    await vi.advanceTimersByTimeAsync(0);

    expect(aoErro).not.toHaveBeenCalled();
  });

  it("falha real é reportada", async () => {
    const aoErro = vi.fn();
    const agendador = criarAgendador({
      executar: async () => {
        throw new Error("rede");
      },
      atrasoMs: 400,
      aoResultado: vi.fn(),
      aoErro,
    });

    agendador.agendar(1);
    await vi.advanceTimersByTimeAsync(400);

    expect(aoErro).toHaveBeenCalledTimes(1);
  });
});

describe("interpretarErroDeSalvamento", () => {
  const catalogo = [
    { id: "id-roupao", cliente_id: "c", nome: "Roupão", ativo: true },
    { id: "id-tapete", cliente_id: "c", nome: "Tapete", ativo: true },
    { id: "id-lencol", cliente_id: "c", nome: "Lençol", ativo: true },
  ];

  it("data duplicada vai para o campo de data, com a mensagem da API", () => {
    const erro = new ErroDeApi("LANCAMENTO_DUPLICADO", "Já existe um lançamento em 01/09/2026.");
    expect(interpretarErroDeSalvamento(erro, catalogo)).toEqual({
      data: "Já existe um lançamento em 01/09/2026.",
      itensMarcados: [],
    });
  });

  it("data futura vai para o campo de data", () => {
    const erro = new ErroDeApi("DATA_FUTURA", "Data futura.");
    expect(interpretarErroDeSalvamento(erro, catalogo).data).toBe("Data futura.");
  });

  it("comanda duplicada vai para o campo de comanda", () => {
    const erro = new ErroDeApi("COMANDA_DUPLICADA", "A comanda “1201” já foi usada.");
    expect(interpretarErroDeSalvamento(erro, catalogo).comanda).toBe(
      "A comanda “1201” já foi usada.",
    );
  });

  it("itens sem preço: banner com a mensagem e as linhas certas marcadas", () => {
    const erro = new ErroDeApi("ITENS_SEM_PRECO", "Os itens Roupão e Tapete não têm preço.", {
      itens: ["Roupão", "Tapete"],
      mes_referencia: "setembro/2026",
    });
    const interpretado = interpretarErroDeSalvamento(erro, catalogo);
    expect(interpretado.geral).toBe("Os itens Roupão e Tapete não têm preço.");
    expect(interpretado.itensMarcados.sort()).toEqual(["id-roupao", "id-tapete"]);
  });

  it("item duplicado marca a linha pelo nome", () => {
    const erro = new ErroDeApi("ITEM_DUPLICADO_NO_LANCAMENTO", "Repetido.", { item: "Lençol" });
    expect(interpretarErroDeSalvamento(erro, catalogo).itensMarcados).toEqual(["id-lencol"]);
  });

  it("erro desconhecido vira banner genérico", () => {
    expect(interpretarErroDeSalvamento(new Error("x"), catalogo).geral).toMatch(/inesperado/);
  });
});

describe("valorNoInstante", () => {
  it("começa no valor anterior e termina exatamente no novo", () => {
    expect(valorNoInstante(100, 250, 0)).toBe(100);
    expect(valorNoInstante(100, 250, 1)).toBe(250);
  });

  it("não ultrapassa o destino fora do intervalo", () => {
    expect(valorNoInstante(100, 250, 1.5)).toBe(250);
    expect(valorNoInstante(100, 250, -1)).toBe(100);
  });

  it("é monotônico (não oscila)", () => {
    let anterior = valorNoInstante(0, 100, 0);
    for (let p = 0.1; p <= 1; p += 0.1) {
      const atual = valorNoInstante(0, 100, p);
      expect(atual).toBeGreaterThanOrEqual(anterior);
      anterior = atual;
    }
  });
});
