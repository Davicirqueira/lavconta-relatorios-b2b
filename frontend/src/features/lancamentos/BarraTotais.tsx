/**
 * BarraTotais — rodapé fixo do formulário com total de peças e total em R$
 * (tarefa 46). Os números vêm da prévia do servidor.
 *
 * O flash de fundo (azul-50 decaindo em 600ms) responde a um resultado novo
 * da API, não à digitação: movimento com causa real.
 */

import type { ReactNode } from "react";
import { NumeroAnimado } from "@/components/NumeroAnimado";
import { formatarInteiro, formatarMoeda } from "@/lib/dinheiro";
import type { EstadoPrevia } from "./usePrevia";
import styles from "./FormularioLancamento.module.css";

interface PropsBarraTotais {
  previa: EstadoPrevia;
  acoes: ReactNode;
}

export function BarraTotais({ previa, acoes }: PropsBarraTotais) {
  const { resultado, calculando, indisponivel } = previa;
  const pecas = resultado?.total_pecas ?? 0;
  const valorTexto = resultado?.total_valor ?? "0.00";

  return (
    <div className={styles.barraTotais}>
      {/* key muda a cada resultado novo → reinicia a animação de flash */}
      <div key={valorTexto + pecas} className={resultado ? styles.flash : undefined} />

      <div className={styles.totais} aria-label="Totais do lançamento">
        <div className={styles.total}>
          <span className={styles.totalRotulo}>Total de peças</span>
          <NumeroAnimado
            className={styles.totalValor}
            valor={pecas}
            textoFinal={formatarInteiro(pecas)}
            formatar={(n) => formatarInteiro(Math.round(n))}
          />
        </div>
        <div className={styles.total}>
          <span className={styles.totalRotulo}>Total R$</span>
          <NumeroAnimado
            className={styles.totalValor}
            valor={Number(valorTexto)}
            textoFinal={formatarMoeda(valorTexto)}
            formatar={formatarMoeda}
          />
        </div>
        <span className={styles.statusPrevia} role="status">
          {indisponivel
            ? "Totais indisponíveis no momento. Ao salvar, o valor é recalculado."
            : calculando
              ? "Atualizando…"
              : ""}
        </span>
      </div>

      <div className={styles.acoesBarra}>{acoes}</div>
    </div>
  );
}
