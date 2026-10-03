/**
 * Hooks TanStack Query para o catálogo (itens com preço, v1.1).
 * O catálogo é sempre por cliente — itens não têm existência sem cliente.
 *
 * Toda escrita invalida também os preços por data, usados pelo formulário de
 * pedido: mudar um preço no catálogo precisa refletir lá.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, ErroDeApi } from "@/lib/api";
import type {
  AlteracaoDePreco,
  ImpactoDaAlteracao,
  Item,
  ItemNovo,
  ModoDeAlteracao,
  PrecoAtual,
  PrecosNaData,
} from "@/types/api";

const CHAVE = "itens";
const CHAVE_PRECOS = "precos";

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

/** Preço de cada item na data do pedido (YYYY-MM-DD). */
export function usePrecosNaData(
  clienteId: string,
  data: string,
  incluirInativos = false,
): UseQueryResult<PrecosNaData, ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE_PRECOS, clienteId, data, { incluirInativos }],
    queryFn: () =>
      apiGet<PrecosNaData>(`/api/clientes/${clienteId}/precos`, {
        data,
        incluir_inativos: incluirInativos,
      }),
    enabled: !!clienteId && /^\d{4}-\d{2}-\d{2}$/.test(data),
  });
}

/** Quantos pedidos já registrados continuam com o valor anterior. */
export function consultarImpacto(
  itemId: string,
  valorUnitario: string,
  modo: ModoDeAlteracao,
): Promise<ImpactoDaAlteracao> {
  return apiGet<ImpactoDaAlteracao>(`/api/itens/${itemId}/preco/impacto`, {
    valor_unitario: valorUnitario,
    modo,
  });
}

// ------------------------------------------------------------------ //
// Mutações                                                            //
// ------------------------------------------------------------------ //

function useInvalidarCatalogo() {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: [CHAVE] }),
      qc.invalidateQueries({ queryKey: [CHAVE_PRECOS] }),
    ]);
}

export function useCriarItem(clienteId: string) {
  const invalidar = useInvalidarCatalogo();
  return useMutation({
    mutationFn: (corpo: ItemNovo) => apiPost<Item>(`/api/clientes/${clienteId}/itens`, corpo),
    onSuccess: invalidar,
  });
}

export function useRenomearItem() {
  const invalidar = useInvalidarCatalogo();
  return useMutation({
    mutationFn: ({ id, nome }: { id: string; nome: string }) =>
      apiPatch<Item>(`/api/itens/${id}`, { nome }),
    onSuccess: invalidar,
  });
}

export function useAlterarPreco() {
  const invalidar = useInvalidarCatalogo();
  return useMutation({
    mutationFn: ({ id, ...corpo }: AlteracaoDePreco & { id: string }) =>
      apiPut<PrecoAtual>(`/api/itens/${id}/preco`, corpo),
    onSuccess: invalidar,
  });
}

export function useInativarItem() {
  const invalidar = useInvalidarCatalogo();
  return useMutation({
    mutationFn: (id: string) => apiPost<Item>(`/api/itens/${id}/inativar`, {}),
    onSuccess: invalidar,
  });
}

export function useReativarItem() {
  const invalidar = useInvalidarCatalogo();
  return useMutation({
    mutationFn: (id: string) => apiPost<Item>(`/api/itens/${id}/reativar`, {}),
    onSuccess: invalidar,
  });
}

export function useExcluirItem() {
  const invalidar = useInvalidarCatalogo();
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/api/itens/${id}`),
    onSuccess: invalidar,
  });
}
