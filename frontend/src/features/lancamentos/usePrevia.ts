/**
 * usePrevia — totais calculados pelo servidor enquanto o operador digita.
 *
 * Comportamento (design §11):
 *   - debounce de 400ms após a última alteração;
 *   - requisição anterior cancelada ao disparar uma nova;
 *   - durante a prévia em voo, o último resultado continua visível;
 *   - falha não apaga o último resultado: marca `indisponivel` e o
 *     formulário segue permitindo salvar (o salvamento recalcula).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { apiPost } from "@/lib/api";
import type { LinhaEntrada, PreviaEntrada, PreviaResposta } from "@/types/api";
import { criarAgendador } from "./logica";

const ATRASO_PREVIA_MS = 400;

export interface EstadoPrevia {
  resultado: PreviaResposta | null;
  calculando: boolean;
  indisponivel: boolean;
}

export function usePrevia(entrada: {
  clienteId: string;
  data: string;
  linhas: LinhaEntrada[];
  lancamentoId?: string;
}): EstadoPrevia {
  const [estado, setEstado] = useState<EstadoPrevia>({
    resultado: null,
    calculando: false,
    indisponivel: false,
  });

  const agendador = useRef(
    criarAgendador<PreviaEntrada, PreviaResposta>({
      atrasoMs: ATRASO_PREVIA_MS,
      executar: (corpo, sinal) =>
        apiPost<PreviaResposta>("/api/lancamentos/previa", corpo, { signal: sinal }),
      aoIniciar: () => setEstado((e) => ({ ...e, calculando: true })),
      aoResultado: (resultado) =>
        setEstado({ resultado, calculando: false, indisponivel: false }),
      // mantém o último resultado na tela; só sinaliza a falha
      aoErro: () => setEstado((e) => ({ ...e, calculando: false, indisponivel: true })),
    }),
  ).current;

  // Chave estável da entrada: só reagenda quando algo que afeta valor muda.
  const chave = useMemo(
    () => JSON.stringify([entrada.clienteId, entrada.data, entrada.linhas, entrada.lancamentoId]),
    [entrada.clienteId, entrada.data, entrada.linhas, entrada.lancamentoId],
  );

  useEffect(() => {
    const { clienteId, data, linhas, lancamentoId } = entrada;

    if (!clienteId || linhas.length === 0) {
      // Sem linhas completas não há o que calcular: nenhum resultado a exibir.
      agendador.cancelar();
      setEstado({ resultado: null, calculando: false, indisponivel: false });
      return;
    }
    if (!data) {
      // Data incompleta: mantém o último resultado até a data voltar a valer.
      agendador.cancelar();
      return;
    }

    agendador.agendar({
      cliente_id: clienteId,
      data,
      linhas,
      ...(lancamentoId ? { lancamento_id: lancamentoId } : {}),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave]);

  useEffect(() => () => agendador.cancelar(), [agendador]);

  return estado;
}
