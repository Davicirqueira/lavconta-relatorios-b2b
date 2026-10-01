/**
 * CartaoGestao — cartão de cliente ou de item nas telas de gestão.
 *
 * Estrutura do protótipo (aprovada na avaliação, Parte A item 6): marca visual
 * (iniciais ou ícone), situação como badge e ações. Só o que está no escopo:
 * sem endereço, volume, último pedido ou categoria (avaliação B5 e B7).
 *
 * Inativo usa tom neutro, não de erro: inativar não é problema, é estado.
 */

import type { CSSProperties, ReactNode } from "react";
import { Plus } from "lucide-react";
import { Badge } from "./Badge";
import styles from "./CartaoGestao.module.css";

interface AcaoCartao {
  rotulo: string;
  icone: ReactNode;
  aoClicar: () => void;
  destrutiva?: boolean;
}

interface PropsCartaoGestao {
  titulo: string;
  ativo: boolean;
  /** Iniciais ou ícone exibido no selo do cartão. */
  marca: ReactNode;
  acoes: AcaoCartao[];
  /** Ordem do cartão na lista, para a entrada escalonada (40ms entre cartões). */
  indice?: number;
}

export function CartaoGestao({ titulo, ativo, marca, acoes, indice = 0 }: PropsCartaoGestao) {
  // limita o escalonamento: listas longas não devem demorar para aparecer
  const estilo = { "--atraso": `${Math.min(indice, 12) * 40}ms` } as CSSProperties;

  return (
    <article
      role="listitem"
      className={[styles.cartao, ativo ? "" : styles.inativo].filter(Boolean).join(" ")}
      style={estilo}
      aria-label={`${titulo}, ${ativo ? "ativo" : "inativo"}`}
    >
      <div className={styles.topo}>
        <span className={styles.marca} aria-hidden="true">
          {marca}
        </span>
        <Badge tipo={ativo ? "sucesso" : "neutro"}>{ativo ? "Ativo" : "Inativo"}</Badge>
      </div>

      <h3 className={styles.titulo} title={titulo}>
        {titulo}
      </h3>

      <div className={styles.rodape}>
        {acoes.map((acao) => (
          <button
            key={acao.rotulo}
            type="button"
            className={[styles.acao, acao.destrutiva ? styles.acaoDestrutiva : ""]
              .filter(Boolean)
              .join(" ")}
            onClick={acao.aoClicar}
            aria-label={`${acao.rotulo} ${titulo}`}
            title={acao.rotulo}
          >
            {acao.icone}
            {/* destrutiva mostra só o ícone; o rótulo fica no aria-label/title */}
            {!acao.destrutiva && <span>{acao.rotulo}</span>}
          </button>
        ))}
      </div>
    </article>
  );
}

/** Iniciais das duas primeiras palavras: "Hotel Aurora" → "HA". */
export function iniciais(nome: string): string {
  const palavras = nome.trim().split(/\s+/).filter(Boolean);
  const letras = palavras.slice(0, 2).map((p) => p[0]);
  return letras.join("").toUpperCase() || "?";
}

/** Cartão tracejado de "adicionar", último da grade. */
export function CartaoAdicionar({ rotulo, aoClicar }: { rotulo: string; aoClicar: () => void }) {
  return (
    <div role="listitem" className={styles.itemAdicionar}>
      <button type="button" className={styles.adicionar} onClick={aoClicar}>
        <span className={styles.adicionarIcone} aria-hidden="true">
          <Plus size={18} />
        </span>
        {rotulo}
      </button>
    </div>
  );
}

/** Grade responsiva dos cartões. */
export function GradeCartoes({ children, rotulo }: { children: ReactNode; rotulo: string }) {
  return (
    <div className={styles.grade} role="list" aria-label={rotulo}>
      {children}
    </div>
  );
}
