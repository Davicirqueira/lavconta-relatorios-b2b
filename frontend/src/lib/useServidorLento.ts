/**
 * Hook que expõe o sinal global de servidor lento (cold start do Render).
 *
 * Verdadeiro enquanto houver ao menos uma requisição esperando há mais de
 * 3s. Usado pelo Layout para exibir o PainelServidorAcordando.
 */

import { useSyncExternalStore } from "react";
import { assinarServidorLento, servidorEstaLento } from "./api";

export function useServidorLento(): boolean {
  return useSyncExternalStore(assinarServidorLento, servidorEstaLento, () => false);
}
