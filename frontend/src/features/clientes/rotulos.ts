import type { Cliente } from "@/types/api";

/**
 * Rótulo do cliente em seleções de consulta (lista e relatório).
 *
 * Cliente inativo continua consultável (Req 2.8): o histórico e o fechamento
 * de períodos passados precisam seguir acessíveis. A marcação em texto evita
 * depender só de cor para indicar o estado.
 */
export function rotuloCliente(cliente: Cliente): string {
  return cliente.ativo ? cliente.nome : `${cliente.nome} (inativo)`;
}
