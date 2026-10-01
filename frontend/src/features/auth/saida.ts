/**
 * Distingue saída voluntária de sessão expirada.
 *
 * O Supabase emite o mesmo evento SIGNED_OUT nos dois casos. Sem esta
 * marca, clicar em "Sair" mostraria "Sua sessão expirou" — mensagem falsa.
 */

let saidaVoluntaria = false;

export function marcarSaidaVoluntaria(): void {
  saidaVoluntaria = true;
}

/** Lê e consome a marca: vale para um único evento de saída. */
export function consumirSaidaVoluntaria(): boolean {
  const foi = saidaVoluntaria;
  saidaVoluntaria = false;
  return foi;
}
