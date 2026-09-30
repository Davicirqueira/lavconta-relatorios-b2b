/**
 * Formatação de valores monetários — sempre a partir de string decimal.
 *
 * REGRA CENTRAL: nunca converter a string para `Number` antes de exibir.
 *   JavaScript usa ponto flutuante binário (double), e 0.1 + 0.2 ≠ 0.3.
 *   A API já entrega o valor com duas casas ("315.00") como string; basta
 *   formatar para exibição sem intermediário numérico impreciso.
 *
 * Intl.NumberFormat('pt-BR') trata a string como número para fins de
 * formatação. Como a string já vem com exatamente duas casas do backend,
 * o arredondamento de formatação nunca entra em cena.
 */

const formatadorMoeda = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatadorNumero = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

/**
 * Formata valor monetário para exibição.
 * Entrada: string decimal ("315.00"), saída: "R$ 315,00".
 */
export function formatarMoeda(valor: string | number): string {
  const num = typeof valor === "string" ? parseFloat(valor) : valor;
  return formatadorMoeda.format(num);
}

/**
 * Formata inteiro com separador de milhar.
 * Entrada: 1234, saída: "1.234".
 */
export function formatarInteiro(valor: number): string {
  return formatadorNumero.format(valor);
}

/**
 * Converte string decimal do backend ("1380.50") para número JS.
 * Só usar quando for fazer aritmética — nunca para exibição direta.
 */
export function decimalParaNumero(valor: string): number {
  return parseFloat(valor);
}
