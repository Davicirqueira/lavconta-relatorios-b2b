/**
 * Hooks TanStack Query para Itens do catálogo.
 * O catálogo é sempre por cliente — itens não têm existência sem cliente.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiDelete, apiGet, apiPatch, apiPost, ErroDeApi } from "@/lib/api";
import type { Item } from "@/types/api";

const CHAVE = "itens";

// ------------------------------------------------------------------ //
// Queries                                                             //
// ------------------------------------------------------------------ //

export function useItens(
  clienteId: string,
  incluirInativos = false,
): UseQueryResult<Item[], ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE, clienteId, { incluirInativos }],
    queryFn: () =>
      apiGet<Item[]>(`/api/clientes/${clienteId}/itens`, {
        incluir_inativos: incluirInativos,
      }),
    enabled: !!clienteId,
  });
}

// ------------------------------------------------------------------ //
// Mutações                                                            //
// ------------------------------------------------------------------ //

export function useCriarItem(clienteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nome: string) =>
      apiPost<Item>(`/api/clientes/${clienteId}/itens`, { nome }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE, clienteId] }),
  });
}

export function useRenomearItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nome }: { id: string; nome: string }) =>
      apiPatch<Item>(`/api/itens/${id}`, { nome }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

export function useInativarItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiPost<Item>(`/api/itens/${id}/inativar`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

export function useReativarItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiPost<Item>(`/api/itens/${id}/reativar`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}

export function useExcluirItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/api/itens/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: [CHAVE] }),
  });
}
