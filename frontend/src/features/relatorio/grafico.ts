/**
 * Dados do gráfico de volume diário — só apresentação.
 *
 * A altura de cada barra é proporcional ao total de peças do dia vindo da
 * API. Não há soma aqui: cada lançamento já é um dia (um por cliente/dia),
 * então o total de peças da linha É o volume daquele dia.
 */

import { diasDoPeriodo } from "@/lib/datas";
import type { LinhaRelatorio } from "@/types/api";

/** Acima disso, uma barra por dia fica fina demais: mostra só dias com lançamento. */
export const MAX_DIAS_NO_GRAFICO = 62;

export interface BarraDia {
  data: string;
  pecas: number;
  /** 0–1, relativo ao maior dia do período. */
  proporcao: number;
}

export function barrasDoPeriodo(
  inicio: string,
  fim: string,
  linhas: LinhaRelatorio[],
): BarraDia[] {
  const pecasPorDia = new Map(linhas.map((l) => [l.data, l.total_pecas]));
  const dias = diasDoPeriodo(inicio, fim);
  const usados = dias.length > MAX_DIAS_NO_GRAFICO ? dias.filter((d) => pecasPorDia.has(d)) : dias;

  const maior = Math.max(0, ...usados.map((d) => pecasPorDia.get(d) ?? 0));
  return usados.map((data) => {
    const pecas = pecasPorDia.get(data) ?? 0;
    return { data, pecas, proporcao: maior > 0 ? pecas / maior : 0 };
  });
}

/**
 * Rampa azul-300 → azul-700 conforme o volume (brief-design §5, volume diário).
 * Devolve o nome do token CSS, não uma cor calculada.
 */
export function tomDaBarra(proporcao: number): string {
  const escala = ["--azul-300", "--azul-400", "--azul-500", "--azul-600", "--azul-700"];
  const indice = Math.min(escala.length - 1, Math.floor(proporcao * escala.length));
  return `var(${escala[indice]})`;
}
