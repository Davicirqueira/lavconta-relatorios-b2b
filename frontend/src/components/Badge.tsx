/**
 * Badge — indicador de estado: fundo "suave", borda "borda", texto "forte".
 * Verde = sucesso, vermelho = erro, amarelo = alerta, azul = info/neutro.
 *
 * ATENÇÃO (acessibilidade de cor): amarelo usa texto escuro, nunca branco —
 * branco sobre a base de alerta fica abaixo do contraste AA.
 */

import type { ReactNode } from "react";
import styles from "./Badge.module.css";

export type TipoBadge = "sucesso" | "erro" | "alerta" | "info" | "neutro";

interface PropsBadge {
  tipo?: TipoBadge;
  children: ReactNode;
  className?: string;
}

export function Badge({ tipo = "neutro", children, className }: PropsBadge) {
  return (
    <span
      className={[styles.badge, styles[tipo], className ?? ""]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}
