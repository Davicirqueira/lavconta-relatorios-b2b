/**
 * Testes dos utilitários de dinheiro (tarefa 36).
 */

import { describe, it, expect } from "vitest";
import { formatarMoeda, formatarInteiro } from "./dinheiro";

describe("formatarMoeda", () => {
  it('formata "315.00" como R$ 315,00', () => {
    expect(formatarMoeda("315.00")).toBe("R$\u00a0315,00");
  });

  it('formata "1380.50" como R$ 1.380,50', () => {
    expect(formatarMoeda("1380.50")).toBe("R$\u00a01.380,50");
  });

  it('formata "0.00" como R$ 0,00', () => {
    expect(formatarMoeda("0.00")).toBe("R$\u00a00,00");
  });

  it("aceita número diretamente", () => {
    expect(formatarMoeda(45.1)).toBe("R$\u00a045,10");
  });

  it("sempre exibe duas casas decimais", () => {
    const resultado = formatarMoeda("100");
    expect(resultado).toContain(",00");
  });
});

describe("formatarInteiro", () => {
  it("formata 1234 com separador de milhar", () => {
    expect(formatarInteiro(1234)).toBe("1.234");
  });

  it("formata 90 sem separador", () => {
    expect(formatarInteiro(90)).toBe("90");
  });
});
