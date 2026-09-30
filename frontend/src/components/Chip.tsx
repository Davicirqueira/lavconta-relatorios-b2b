/**
 * Chip — etiqueta compacta, animada ao aparecer (escala 0,9→1, 180ms).
 * Estado ativo: azul-50 fundo, azul-700 texto, azul-200 borda.
 * Estado inativo: gelo-100 fundo, gelo-600 texto.
 */

import type { ReactNode } from "react";
import styles from "./Chip.module.css";

interface PropsChip {
  ativo?: boolean;
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}

export function Chip({ ativo = true, children, onClick, className }: PropsChip) {
  const Tag = onClick ? "button" : "span";

  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={[
        styles.chip,
        ativo ? styles.ativo : styles.inativo,
        onClick ? styles.clicavel : "",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </Tag>
  );
}
