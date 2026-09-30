/**
 * PainelServidorAcordando — exibido após 3s de espera (cold start do Render).
 *
 * Aparece quando o cliente de API dispara o sinal `aoFicarLenta`.
 * Não é erro — é uma espera esperada no free tier.
 */

import styles from "./PainelServidorAcordando.module.css";

export function PainelServidorAcordando() {
  return (
    <div className={styles.painel} role="status" aria-live="polite">
      <div className={styles.icone} aria-hidden="true">
        <span className={styles.onda} />
        <span className={styles.onda} />
        <span className={styles.onda} />
      </div>
      <div className={styles.texto}>
        <p className={styles.titulo}>Reativando o servidor…</p>
        <p className={styles.descricao}>
          Isso leva alguns segundos na primeira requisição. Aguarde, por favor.
        </p>
      </div>
    </div>
  );
}
