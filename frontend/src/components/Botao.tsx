/**
 * Botao — componente de botão com quatro variantes.
 *
 * Variantes:
 *   primario   — azul-600, hover azul-500, sombra sobe de nível no hover
 *   secundario — fundo branco, borda gelo-300, texto azul-700
 *   destrutivo — base de erro (vermelho), para ações como "Excluir"
 *   fantasma   — só texto azul-700, sem borda nem fundo
 *
 * Animação: escala 0,98 ao pressionar em 100ms (brief-design.md §4).
 */

import { forwardRef, type ButtonHTMLAttributes } from "react";
import styles from "./Botao.module.css";

export type VarianteBotao = "primario" | "secundario" | "destrutivo" | "fantasma";
export type TamanhoBotao = "sm" | "md" | "lg";

export interface PropsBotao extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: VarianteBotao;
  tamanho?: TamanhoBotao;
  carregando?: boolean;
}

export const Botao = forwardRef<HTMLButtonElement, PropsBotao>(
  function Botao(
    {
      variante = "primario",
      tamanho = "md",
      carregando = false,
      disabled,
      children,
      className,
      ...rest
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        disabled={disabled || carregando}
        aria-busy={carregando}
        className={[
          styles.botao,
          styles[variante],
          styles[tamanho],
          carregando ? styles.carregando : "",
          className ?? "",
        ]
          .filter(Boolean)
          .join(" ")}
        {...rest}
      >
        {carregando ? (
          <>
            <span className={styles.spinner} aria-hidden="true" />
            <span className="sr-only">Carregando…</span>
          </>
        ) : (
          children
        )}
      </button>
    );
  },
);
