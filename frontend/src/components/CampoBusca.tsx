/**
 * CampoBusca — busca com ícone de lupa, no mesmo acabamento dos demais campos.
 *
 * O rótulo existe para leitor de tela; visualmente, a lupa e o placeholder
 * deixam claro o propósito (padrão de busca em listas).
 */

import { Search, X } from "lucide-react";
import styles from "./CampoBusca.module.css";

interface PropsCampoBusca {
  valor: string;
  aoMudar: (texto: string) => void;
  rotulo: string;
  placeholder?: string;
  className?: string;
}

export function CampoBusca({ valor, aoMudar, rotulo, placeholder, className }: PropsCampoBusca) {
  return (
    <div className={[styles.campo, className ?? ""].filter(Boolean).join(" ")}>
      <Search size={16} className={styles.lupa} aria-hidden="true" />
      <input
        type="search"
        className={styles.input}
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        placeholder={placeholder}
        aria-label={rotulo}
        autoComplete="off"
      />
      {valor && (
        <button
          type="button"
          className={styles.limpar}
          onClick={() => aoMudar("")}
          aria-label="Limpar busca"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
