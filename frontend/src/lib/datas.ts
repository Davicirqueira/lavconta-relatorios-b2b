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

/** Quantidade de dias do mês (1–12), considerando ano bissexto. */
export function diasNoMes(ano: number, mes: number): number {
  // Date.UTC com dia 0 = último dia do mês anterior; UTC evita qualquer fuso
  return new Date(Date.UTC(ano, mes, 0)).getUTCDate();
}

/**
 * Valida uma data digitada em dd/mm/yyyy e devolve o ISO, ou null.
 *
 * Valida calendário real: 31/02 e 29/02 em ano não bissexto são recusados.
 * É validação de formato de entrada, não regra de negócio — a data futura,
 * por exemplo, continua sendo decidida pelo servidor.
 */
export function interpretarDataBr(br: string): string | null {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(br);
  if (!match) return null;
  const [, diaTxt, mesTxt, anoTxt] = match;
  const dia = Number(diaTxt);
  const mes = Number(mesTxt);
  const ano = Number(anoTxt);
  if (ano < 2000 || ano > 2099) return null;
  if (mes < 1 || mes > 12) return null;
  if (dia < 1 || dia > diasNoMes(ano, mes)) return null;
  return `${anoTxt}-${mesTxt}-${diaTxt}`;
}

/**
 * Todos os dias de calendário entre `inicio` e `fim` (inclusive), em ISO.
 *
 * Aritmética em UTC sobre os componentes da data: como nada é interpretado
 * no fuso local, 31/08 nunca escorrega para 30/08.
 */
export function diasDoPeriodo(inicio: string, fim: string): string[] {
  const [ai, mi, di] = inicio.split("-").map(Number);
  const [af, mf, df] = fim.split("-").map(Number);
  const atual = Date.UTC(ai, mi - 1, di);
  const final = Date.UTC(af, mf - 1, df);
  const dias: string[] = [];
  const UM_DIA = 86_400_000;
  for (let t = atual; t <= final; t += UM_DIA) {
    const d = new Date(t);
    dias.push(
      `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(
        d.getUTCDate(),
      ).padStart(2, "0")}`,
    );
  }
  return dias;
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
  const ultimo = diasNoMes(ano, mes);
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
