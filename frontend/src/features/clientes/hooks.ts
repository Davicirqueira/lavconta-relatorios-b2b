/**
 * Hooks TanStack Query para Clientes.
 *
 * Cache automático reduz chamadas ao backend que hiberna (design.md §11).
 * Mutações invalidam a query de listagem para manter a UI sincronizada.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiDelete, apiGet, apiPatch, apiPost, ErroDeApi } from "@/lib/api";
import type { Cliente } from "@/types/api";

const CHAVE = "clientes";

// ------------------------------------------------------------------ //
// Queries                                                             //
// ------------------------------------------------------------------ //

export function useClientes(
  incluirInativos = false,
): UseQueryResult<Cliente[], ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE, { incluirInativos }],
    queryFn: () =>
      apiGet<Cliente[]>("/api/clientes", {
        incluir_inativos: incluirInativos,
      }),
  });
}

export function useCliente(id: string): UseQueryResult<Cliente, ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE, id],
    queryFn: () => apiGet<Cliente>(`/api/clientes/${id}`),
    enabled: !!id,
  });
}

// ------------------------------------------------------------------ //
// Mutações                                                            //
// ------------------------------------------------------------------ //

export function useCriarCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nome: string) =>
      apiPost<Cliente>("/api/clientes", { nome }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

export function useRenomearCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nome }: { id: string; nome: string }) =>
      apiPatch<Cliente>(`/api/clientes/${id}`, { nome }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

export function useInativarCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiPost<Cliente>(`/api/clientes/${id}/inativar`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

export function useReativarCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiPost<Cliente>(`/api/clientes/${id}/reativar`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

export function useExcluirCliente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/api/clientes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}
