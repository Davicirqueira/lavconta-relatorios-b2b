/**
 * Selecao — select nativo estilizado com as mesmas regras de foco do Campo.
 */

import { forwardRef, type SelectHTMLAttributes } from "react";
import styles from "./Campo.module.css"; // reutiliza os mesmos tokens
import selStyles from "./Selecao.module.css";

export interface PropsSelecao extends SelectHTMLAttributes<HTMLSelectElement> {
  rotulo: string;
  erro?: string;
  placeholder?: string;
}

export const Selecao = forwardRef<HTMLSelectElement, PropsSelecao>(
  function Selecao({ rotulo, erro, placeholder, id, children, className, ...rest }, ref) {
    const selectId = id ?? `selecao-${rotulo.toLowerCase().replace(/\s+/g, "-")}`;

    return (
      <div className={[styles.grupo, className ?? ""].filter(Boolean).join(" ")}>
        <label htmlFor={selectId} className={styles.rotulo}>
          {rotulo}
        </label>
        <select
          ref={ref}
          id={selectId}
          className={[selStyles.select, erro ? styles.comErro : ""]
            .filter(Boolean)
            .join(" ")}
          aria-invalid={erro ? "true" : undefined}
          aria-describedby={erro ? `${selectId}-erro` : undefined}
          {...rest}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {children}
        </select>
        {erro && (
          <span id={`${selectId}-erro`} className={styles.erroTexto} role="alert">
            {erro}
          </span>
        )}
      </div>
    );
  },
);
