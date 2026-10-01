/**
 * Campo — input de texto com rótulo visível.
 *
 * Rótulo é sempre visível (não usar placeholder como substituto — acessibilidade).
 * Borda gelo-300 em repouso; ao focar: borda azul-600 + anel sombra-foco em 160ms.
 *
 * Opcionais:
 *   - `icone`: ícone decorativo à esquerda, dentro do campo;
 *   - `extraRotulo`: elemento alinhado à direita do rótulo (ex.: link
 *     "Esqueceu a senha?").
 */

import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import styles from "./Campo.module.css";

export interface PropsCampo extends InputHTMLAttributes<HTMLInputElement> {
  rotulo: string;
  erro?: string;
  dica?: string;
  icone?: ReactNode;
  extraRotulo?: ReactNode;
}

export const Campo = forwardRef<HTMLInputElement, PropsCampo>(function Campo(
  { rotulo, erro, dica, id, className, icone, extraRotulo, ...rest },
  ref,
) {
  const inputId = id ?? `campo-${rotulo.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <div className={[styles.grupo, className ?? ""].filter(Boolean).join(" ")}>
      <div className={styles.linhaRotulo}>
        <label htmlFor={inputId} className={styles.rotulo}>
          {rotulo}
        </label>
        {extraRotulo}
      </div>
      <div className={styles.envoltorio}>
        {icone && (
          <span className={styles.icone} aria-hidden="true">
            {icone}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          className={[styles.input, icone ? styles.comIcone : "", erro ? styles.comErro : ""]
            .filter(Boolean)
            .join(" ")}
          aria-describedby={
            [erro ? `${inputId}-erro` : "", dica ? `${inputId}-dica` : ""]
              .filter(Boolean)
              .join(" ") || undefined
          }
          aria-invalid={erro ? "true" : undefined}
          {...rest}
        />
      </div>
      {dica && !erro && (
        <span id={`${inputId}-dica`} className={styles.dica}>
          {dica}
        </span>
      )}
      {erro && (
        <span id={`${inputId}-erro`} className={styles.erroTexto} role="alert">
          {erro}
        </span>
      )}
    </div>
  );
});
