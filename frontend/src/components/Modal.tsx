/**
 * Modal — diálogo acessível com backdrop, painel com animação de entrada
 * e foco gerenciado.
 *
 * Animação: backdrop fade 160ms; painel escala 0,96→1 + fade 200ms.
 * Fechar com ESC ou clicando no backdrop.
 */

import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import styles from "./Modal.module.css";

export interface PropsModal {
  aberto: boolean;
  titulo: string;
  onFechar: () => void;
  children: ReactNode;
  rodape?: ReactNode;
}

export function Modal({ aberto, titulo, onFechar, children, rodape }: PropsModal) {
  const painelRef = useRef<HTMLDivElement>(null);

  // Fecha com ESC
  useEffect(() => {
    if (!aberto) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onFechar();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [aberto, onFechar]);

  // Foca o painel ao abrir (acessibilidade)
  useEffect(() => {
    if (aberto) {
      setTimeout(() => painelRef.current?.focus(), 10);
    }
  }, [aberto]);

  // Bloqueia o scroll da página com o modal aberto
  useEffect(() => {
    if (aberto) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [aberto]);

  if (!aberto) return null;

  return (
    <div
      className={styles.backdrop}
      onClick={(e) => { if (e.target === e.currentTarget) onFechar(); }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-titulo"
    >
      <div
        ref={painelRef}
        className={styles.painel}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.cabecalho}>
          <h2 id="modal-titulo" className={styles.titulo}>{titulo}</h2>
          <button
            className={styles.fechar}
            onClick={onFechar}
            aria-label="Fechar modal"
            type="button"
          >
            <X size={18} />
          </button>
        </div>
        <div className={styles.corpo}>{children}</div>
        {rodape && <div className={styles.rodape}>{rodape}</div>}
      </div>
    </div>
  );
}
