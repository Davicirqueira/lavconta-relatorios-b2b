import { describe, expect, it } from "vitest";
import { barrasDoPeriodo, MAX_DIAS_NO_GRAFICO, tomDaBarra } from "./grafico";
import type { LinhaRelatorio } from "@/types/api";

const linha = (data: string, total_pecas: number): LinhaRelatorio => ({
  lancamento_id: data,
  data,
  comanda: null,
  quantidades: {},
  total_pecas,
  total_valor: "0.00",
});

describe("barrasDoPeriodo", () => {
  it("uma barra por dia do período, inclusive dias sem lançamento", () => {
    const barras = barrasDoPeriodo("2026-09-01", "2026-09-05", [
      linha("2026-09-01", 90),
      linha("2026-09-03", 45),
    ]);
    expect(barras.map((b) => [b.data, b.pecas])).toEqual([
      ["2026-09-01", 90],
      ["2026-09-02", 0],
      ["2026-09-03", 45],
      ["2026-09-04", 0],
      ["2026-09-05", 0],
    ]);
  });

  it("proporção relativa ao maior dia", () => {
    const barras = barrasDoPeriodo("2026-09-01", "2026-09-02", [
      linha("2026-09-01", 100),
      linha("2026-09-02", 25),
    ]);
    expect(barras.map((b) => b.proporcao)).toEqual([1, 0.25]);
  });

  it("período sem lançamentos: todas as barras com proporção zero, sem divisão por zero", () => {
    const barras = barrasDoPeriodo("2026-09-01", "2026-09-03", []);
    expect(barras.every((b) => b.proporcao === 0)).toBe(true);
  });

  it("cruza meses sem perder o dia 31", () => {
    const barras = barrasDoPeriodo("2026-08-31", "2026-09-01", [linha("2026-08-31", 10)]);
    expect(barras.map((b) => b.data)).toEqual(["2026-08-31", "2026-09-01"]);
  });

  it("período longo mostra só os dias com lançamento", () => {
    const barras = barrasDoPeriodo("2026-01-01", "2026-12-31", [
      linha("2026-03-10", 5),
      linha("2026-09-01", 9),
    ]);
    expect(barras.map((b) => b.data)).toEqual(["2026-03-10", "2026-09-01"]);
    expect(MAX_DIAS_NO_GRAFICO).toBeLessThan(365);
  });
});

describe("tomDaBarra", () => {
  it("vai do tom mais claro ao mais forte conforme o volume", () => {
    expect(tomDaBarra(0)).toBe("var(--azul-300)");
    expect(tomDaBarra(1)).toBe("var(--azul-700)");
  });
});
