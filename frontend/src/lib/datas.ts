/**
 * Utilitários de data — sem `new Date()` para datas de negócio.
 *
 * POR QUE NUNCA `new Date(isoString)`
 *   `new Date("2026-08-31")` interpreta o valor como UTC e, dependendo do
 *   offset do navegador, pode resultar em 30/08 ao exibir no fuso local.
 *   Para datas de calendário (sem hora), a conversão certa é manipulação
 *   de texto: a string já contém o dia correto.
 *
 * `hojeSp` é a única exceção: precisa saber "hoje" em Sao_Paulo, então
 *   usa `Intl.DateTimeFormat` com o fuso explícito em vez de confiar no
 *   fuso do navegador — que pode ser diferente para equipes remotas.
 */

/** YYYY-MM-DD → dd/mm/yyyy (puro reformatamento de texto, sem conversão) */
export function paraExibicao(iso: string): string {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

/** dd/mm/yyyy → YYYY-MM-DD (puro reformatamento de texto, sem conversão) */
export function paraIso(br: string): string {
  const [dia, mes, ano] = br.split("/");
  return `${ano}-${mes}-${dia}`;
}

/**
 * "Hoje" no fuso de negócio (America/Sao_Paulo), como YYYY-MM-DD.
 *
 * `en-CA` retorna o formato ISO YYYY-MM-DD nativamente — evita
 * dividir uma string localizada cujo formato varia por navegador.
 */
export function hojeSp(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
  }).format(new Date());
}

/** Primeiro dia do mês vigente em SP, como YYYY-MM-DD */
export function primeiroDiaDoMesAtual(): string {
  const hoje = hojeSp();
  return hoje.slice(0, 7) + "-01";
}

/** Último dia do mês vigente em SP, como YYYY-MM-DD */
export function ultimoDiaDoMesAtual(): string {
  const [ano, mes] = hojeSp().split("-").map(Number);
  // Dia 0 do mês seguinte = último dia do mês atual
  const ultimo = new Date(Date.UTC(ano, mes, 0)).getUTCDate();
  return `${ano}-${String(mes).padStart(2, "0")}-${String(ultimo).padStart(2, "0")}`;
}

/** Mês e ano para exibição: "setembro/2026" */
export function mesExtenso(iso: string): string {
  const [ano, mes] = iso.split("-");
  const meses = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
  ];
  return `${meses[Number(mes) - 1]}/${ano}`;
}
