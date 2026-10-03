/**
 * Relatório de fechamento e exportação.
 *
 * O relatório chega pronto: `resumo` (cartões) e `totais` (rodapé) saem da
 * mesma agregação no backend. A tela só exibe — nunca soma (defeito B1).
 *
 * v1.1: "Todos os clientes" é o valor `TODOS_OS_CLIENTES` no filtro; ele usa as
 * rotas `/api/relatorio/geral*`, com contrato próprio.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { apiDownload, apiGet, ErroDeApi } from "@/lib/api";
import type { Relatorio, RelatorioGeral } from "@/types/api";

/** Valor do seletor de cliente (e da URL) para o relatório geral. */
export const TODOS_OS_CLIENTES = "todos";

export interface FiltroRelatorio {
  clienteId: string;
  inicio: string;
  fim: string;
}

export function eGeral(filtro: FiltroRelatorio | null): boolean {
  return filtro?.clienteId === TODOS_OS_CLIENTES;
}

export function useRelatorio(
  filtro: FiltroRelatorio | null,
): UseQueryResult<Relatorio, ErroDeApi> {
  return useQuery({
    queryKey: ["relatorio", filtro],
    queryFn: () =>
      apiGet<Relatorio>("/api/relatorio", {
        cliente_id: filtro!.clienteId,
        inicio: filtro!.inicio,
        fim: filtro!.fim,
      }),
    enabled: !!filtro && !eGeral(filtro),
    // fechamento precisa refletir o estado atual dos lançamentos
    staleTime: 0,
  });
}

export function useRelatorioGeral(
  filtro: FiltroRelatorio | null,
): UseQueryResult<RelatorioGeral, ErroDeApi> {
  return useQuery({
    queryKey: ["relatorio-geral", filtro?.inicio, filtro?.fim],
    queryFn: () =>
      apiGet<RelatorioGeral>("/api/relatorio/geral", { inicio: filtro!.inicio, fim: filtro!.fim }),
    enabled: eGeral(filtro),
    staleTime: 0,
  });
}

export type FormatoExportacao = "pdf" | "excel";

const EXTENSAO: Record<FormatoExportacao, string> = { pdf: "pdf", excel: "xlsx" };

/** Nome usado só se o servidor não informar o nome do arquivo. */
function nomeReserva(filtro: FiltroRelatorio, formato: FormatoExportacao): string {
  const prefixo = eGeral(filtro) ? "fechamento-todos-os-clientes" : "fechamento";
  return `${prefixo}-${filtro.inicio}-a-${filtro.fim}.${EXTENSAO[formato]}`;
}

/**
 * Baixa o arquivo gerado pelo backend e entrega ao navegador como download.
 *
 * O arquivo é gerado no servidor a partir do mesmo relatório da tela
 * (Req 8.5); o frontend só transporta os bytes.
 */
export async function exportarRelatorio(
  filtro: FiltroRelatorio,
  formato: FormatoExportacao,
): Promise<void> {
  const { blob, nomeArquivo } = eGeral(filtro)
    ? await apiDownload(`/api/relatorio/geral/${formato}`, {
        inicio: filtro.inicio,
        fim: filtro.fim,
      })
    : await apiDownload(`/api/relatorio/${formato}`, {
        cliente_id: filtro.clienteId,
        inicio: filtro.inicio,
        fim: filtro.fim,
      });

  const url = URL.createObjectURL(blob);
  try {
    const ancora = document.createElement("a");
    ancora.href = url;
    ancora.download =
      nomeArquivo && nomeArquivo !== "arquivo" ? nomeArquivo : nomeReserva(filtro, formato);
    document.body.appendChild(ancora);
    ancora.click();
    ancora.remove();
  } finally {
    // libera a memória depois que o navegador iniciou o download
    setTimeout(() => URL.revokeObjectURL(url), 1_000);
  }
}
