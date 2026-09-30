/**
 * Testes dos utilitários de data (tarefa 36).
 *
 * A propriedade crítica: a data nunca muda de dia ao converter entre
 * formatos, especialmente nas fronteiras de virada de mês (31/08 e 01/09).
 */

import { describe, it, expect } from "vitest";
import { paraExibicao, paraIso, hojeSp } from "./datas";

describe("paraExibicao", () => {
  it("converte YYYY-MM-DD para dd/mm/yyyy sem mudar o dia", () => {
    expect(paraExibicao("2026-09-01")).toBe("01/09/2026");
    expect(paraExibicao("2026-08-31")).toBe("31/08/2026");
  });

  it("31 de agosto não vira 30 nem 01 de setembro", () => {
    expect(paraExibicao("2026-08-31")).toBe("31/08/2026");
  });

  it("01 de setembro não vira 31 de agosto", () => {
    expect(paraExibicao("2026-09-01")).toBe("01/09/2026");
  });

  it("converte datas de dezembro corretamente", () => {
    expect(paraExibicao("2026-12-31")).toBe("31/12/2026");
  });
});

describe("paraIso", () => {
  it("converte dd/mm/yyyy para YYYY-MM-DD sem mudar o dia", () => {
    expect(paraIso("01/09/2026")).toBe("2026-09-01");
    expect(paraIso("31/08/2026")).toBe("2026-08-31");
  });

  it("31 de agosto não vira outra data", () => {
    expect(paraIso("31/08/2026")).toBe("2026-08-31");
  });

  it("01 de setembro não vira outra data", () => {
    expect(paraIso("01/09/2026")).toBe("2026-09-01");
  });
});

describe("round-trip: paraIso(paraExibicao(iso)) === iso", () => {
  const datas = [
    "2026-08-31",
    "2026-09-01",
    "2026-01-01",
    "2026-12-31",
    "2026-02-28",
  ];

  for (const iso of datas) {
    it(`${iso} → exibição → ISO = ${iso}`, () => {
      expect(paraIso(paraExibicao(iso))).toBe(iso);
    });
  }
});

describe("hojeSp", () => {
  it("retorna string no formato YYYY-MM-DD", () => {
    const hoje = hojeSp();
    expect(hoje).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("retorna data plausível (entre 2026 e 2030)", () => {
    const ano = Number(hojeSp().split("-")[0]);
    expect(ano).toBeGreaterThanOrEqual(2026);
    expect(ano).toBeLessThanOrEqual(2030);
  });
});
