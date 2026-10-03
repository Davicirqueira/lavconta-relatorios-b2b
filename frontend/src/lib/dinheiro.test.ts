/**
 * Testes dos utilitários de dinheiro (tarefa 36).
 */

import { describe, it, expect } from "vitest";
import { decimalParaCampo, formatarMoeda, formatarInteiro, textoParaDecimal } from "./dinheiro";

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

describe("textoParaDecimal (v1.1, tarefa 10)", () => {
  it.each([
    ["4,5", "4.50"],
    ["4,50", "4.50"],
    ["4.50", "4.50"],
    ["4.5", "4.50"],
    ["4", "4.00"],
    ["1.234,56", "1234.56"],
    ["1234,56", "1234.56"],
    ["1.234", "1234.00"],
    ["4.555,1", "4555.10"],
    ["R$ 4,80", "4.80"],
    [" 0,48 ", "0.48"],
    ["007,10", "7.10"],
  ])('"%s" vira "%s"', (entrada, esperado) => {
    expect(textoParaDecimal(entrada)).toBe(esperado);
  });

  it.each(["", "   ", "0", "0,00", "-1", "-4,50", "4,555", "4.55,10", "abc", "4,5,0", "1.23,45", "4,"])(
    '"%s" é recusado',
    (entrada) => {
      expect(textoParaDecimal(entrada)).toBeNull();
    },
  );

  it("não passa por ponto flutuante: valores que o double não representa saem exatos", () => {
    // 0.1 + 0.2 em double é 0.30000000000000004; aqui é só texto
    expect(textoParaDecimal("0,30")).toBe("0.30");
    expect(textoParaDecimal("99999999,99")).toBe("99999999.99");
  });
});

describe("decimalParaCampo", () => {
  it('"4.50" vira "4,50"', () => {
    expect(decimalParaCampo("4.50")).toBe("4,50");
  });
});
