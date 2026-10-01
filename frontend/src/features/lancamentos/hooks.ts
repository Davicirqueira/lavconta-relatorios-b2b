/**
 * Hooks TanStack Query para Lançamentos.
 *
 * A prévia de totais NÃO usa TanStack Query: ela precisa de debounce e de
 * cancelamento da requisição anterior, então vive em `usePrevia`.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut, ErroDeApi } from "@/lib/api";
import type { Lancamento, LancamentoEntrada, LancamentoResumo } from "@/types/api";

const CHAVE = "lancamentos";

export function useLancamentos(
  clienteId: string,
  inicio: string,
  fim: string,
): UseQueryResult<LancamentoResumo[], ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE, clienteId, inicio, fim],
    queryFn: () =>
      apiGet<LancamentoResumo[]>("/api/lancamentos", { cliente_id: clienteId, inicio, fim }),
    // a API exige os três; período invertido é recusado na própria tela
    enabled: !!clienteId && !!inicio && !!fim && inicio <= fim,
  });
}

export function useLancamento(id: string | undefined): UseQueryResult<Lancamento, ErroDeApi> {
  return useQuery({
    queryKey: [CHAVE, "detalhe", id],
    queryFn: () => apiGet<Lancamento>(`/api/lancamentos/${id}`),
    enabled: !!id,
    // edição precisa do estado atual do banco, não de cache antigo
    staleTime: 0,
  });
}

/** Salvar invalida listas e relatórios: o fechamento depende dos lançamentos. */
function invalidarDependentes(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [CHAVE] });
  qc.invalidateQueries({ queryKey: ["relatorio"] });
}

export function useCriarLancamento() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (corpo: LancamentoEntrada) => apiPost<Lancamento>("/api/lancamentos", corpo),
    onSuccess: () => invalidarDependentes(qc),
  });
}

export function useEditarLancamento() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, corpo }: { id: string; corpo: LancamentoEntrada }) =>
      apiPut<Lancamento>(`/api/lancamentos/${id}`, corpo),
    onSuccess: () => invalidarDependentes(qc),
  });
}

export function useExcluirLancamento() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/api/lancamentos/${id}`),
    onSuccess: () => invalidarDependentes(qc),
  });
}
