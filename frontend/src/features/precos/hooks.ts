/**
 * Hooks TanStack Query para Preços.
 *
 * Os preços são consultados por (cliente, mês) e o backend resolve a
 * vigência — cada item retorna seu preço vigente e de qual mês ele vem.
 *
 * usePrecosDoMes: busca preço vigente de cada item num determinado mês.
 * useDefinirPreco: upsert de (cliente, item, mês, valor).
 * useVigenciaSugerida: mês que a interface deve propor ao definir preço.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiGet, apiPut, ErroDeApi } from "@/lib/api";
import type { PrecosDoMes, PrecoResposta, VigenciaSugerida } from "@/types/api";

const CHAVE = "precos";

// ------------------------------------------------------------------ //
// Queries                                                             //
// ------------------------------------------------------------------ //

export function usePrecosDoMes(
  clienteId: string,
  mes: string, // "YYYY-MM"
  incluirInativos = false,
): UseQueryResult<PrecosDoMes, ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE, clienteId, mes, { incluirInativos }],
    queryFn: () =>
      apiGet<PrecosDoMes>(`/api/clientes/${clienteId}/precos`, {
        mes,
        incluir_inativos: incluirInativos,
      }),
    enabled: !!clienteId && !!mes,
  });
}

export function useVigenciaSugerida(
  clienteId: string,
  itemId: string,
): UseQueryResult<VigenciaSugerida, ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE, "vigencia-sugerida", clienteId, itemId],
    queryFn: () =>
      apiGet<VigenciaSugerida>(
        `/api/clientes/${clienteId}/precos/vigencia-sugerida/${itemId}`,
      ),
    enabled: !!clienteId && !!itemId,
  });
}

// ------------------------------------------------------------------ //
// Mutações                                                            //
// ------------------------------------------------------------------ //

interface DefinirPrecoPayload {
  clienteId: string;
  item_id: string;
  vigencia_mes: string; // "YYYY-MM"
  valor_unitario: string; // string decimal "4.50"
}

export function useDefinirPreco() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ clienteId, ...corpo }: DefinirPrecoPayload) =>
      apiPut<PrecoResposta>(`/api/clientes/${clienteId}/precos`, corpo),
    onSuccess: (_data, { clienteId }) =>
      qc.invalidateQueries({ queryKey: [CHAVE, clienteId] }),
  });
}
