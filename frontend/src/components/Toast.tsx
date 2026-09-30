/**
 * Toast — notificações não-bloqueantes.
 *
 * Entra deslizando 12px do topo com fade em 200ms.
 * Barra de 3px à esquerda indica o tipo (sucesso=verde, erro=vermelho, etc).
 * Auto-remove após `duracao` ms (padrão 4s).
 */

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { X } from "lucide-react";
import styles from "./Toast.module.css";

export type TipoToast = "sucesso" | "erro" | "alerta" | "info";

interface ToastItem {
  id: number;
  mensagem: string;
  tipo: TipoToast;
}

interface ContextoToast {
  mostrar: (mensagem: string, tipo?: TipoToast) => void;
}

const ContextoToast = createContext<ContextoToast | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const contadorRef = useRef(0);

  const mostrar = useCallback((mensagem: string, tipo: TipoToast = "info") => {
    const id = ++contadorRef.current;
    setToasts((prev) => [...prev, { id, mensagem, tipo }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4_000);
  }, []);

  function remover(id: number) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  return (
    <ContextoToast.Provider value={{ mostrar }}>
      {children}
      <div className={styles.regiao} aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={[styles.toast, styles[toast.tipo]].join(" ")}
            role="status"
          >
            <div className={styles.barra} aria-hidden="true" />
            <div className={styles.conteudo}>
              <p className={styles.mensagem}>{toast.mensagem}</p>
            </div>
            <button
              className={styles.fechar}
              onClick={() => remover(toast.id)}
              aria-label="Fechar notificação"
              type="button"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ContextoToast.Provider>
  );
}

export function useToast(): ContextoToast {
  const ctx = useContext(ContextoToast);
  if (!ctx) {
    throw new Error("useToast deve ser usado dentro de <ToastProvider>");
  }
  return ctx;
}
