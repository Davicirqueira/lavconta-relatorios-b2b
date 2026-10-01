/**
 * Relatório de fechamento e exportação.
 *
 * O relatório chega pronto: `resumo` (cartões) e `totais` (rodapé) saem da
 * mesma agregação no backend. A tela só exibe — nunca soma (defeito B1).
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { apiDownload, apiGet, ErroDeApi } from "@/lib/api";
import type { Relatorio } from "@/types/api";

export interface FiltroRelatorio {
  clienteId: string;
  inicio: string;
  fim: string;
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
    enabled: !!filtro,
    // fechamento precisa refletir o estado atual dos lançamentos
    staleTime: 0,
  });
}

export type FormatoExportacao = "pdf" | "excel";

const EXTENSAO: Record<FormatoExportacao, string> = { pdf: "pdf", excel: "xlsx" };

/** Nome usado só se o servidor não informar o nome do arquivo. */
function nomeReserva(filtro: FiltroRelatorio, formato: FormatoExportacao): string {
  return `fechamento-${filtro.inicio}-a-${filtro.fim}.${EXTENSAO[formato]}`;
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
  const { blob, nomeArquivo } = await apiDownload(`/api/relatorio/${formato}`, {
    cliente_id: filtro.clienteId,
    inicio: filtro.inicio,
    fim: filtro.fim,
  });

  const url = URL.createObjectURL(blob);
  try {
    const ancora = document.createElement("a");
    ancora.href = url;
    ancora.download = nomeArquivo && nomeArquivo !== "arquivo" ? nomeArquivo : nomeReserva(filtro, formato);
    document.body.appendChild(ancora);
    ancora.click();
    ancora.remove();
  } finally {
    // libera a memória depois que o navegador iniciou o download
    setTimeout(() => URL.revokeObjectURL(url), 1_000);
  }
}
