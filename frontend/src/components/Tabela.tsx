/**
 * Tabela — container com cabeçalho sticky, hover em azul-50 e linha de totais.
 *
 * Design: brief-design.md §5 "Tabela de fechamento".
 * Células numéricas devem receber a classe `.num` para tabular-nums.
 */

import type { ReactNode } from "react";
import styles from "./Tabela.module.css";

export interface ColunaDef {
  chave: string;
  titulo: ReactNode;
  alinhamento?: "esquerda" | "direita" | "centro";
}

export interface PropsTabelaGenérica<T> {
  colunas: ColunaDef[];
  dados: T[];
  renderLinha: (item: T, colunas: ColunaDef[]) => ReactNode;
  rodape?: ReactNode;
  className?: string;
  "aria-label"?: string;
}

// Versão genérica usada para tabelas de dados normais
export function Tabela<T>({
  colunas,
  dados,
  renderLinha,
  rodape,
  className,
  "aria-label": ariaLabel,
}: PropsTabelaGenérica<T>) {
  return (
    <div className={[styles.container, className ?? ""].filter(Boolean).join(" ")}>
      <div className={styles.scroll}>
        <table className={styles.tabela} aria-label={ariaLabel}>
          <thead className={styles.cabecalho}>
            <tr>
              {colunas.map((col) => (
                <th
                  key={col.chave}
                  className={[
                    styles.th,
                    col.alinhamento === "direita" ? styles.direita : "",
                    col.alinhamento === "centro" ? styles.centro : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  scope="col"
                >
                  {col.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dados.map((item, i) => (
              <tr key={i} className={styles.tr}>
                {renderLinha(item, colunas) as React.ReactElement}
              </tr>
            ))}
          </tbody>
          {rodape && <tfoot>{rodape}</tfoot>}
        </table>
      </div>
    </div>
  );
}

// Exporta as classes para uso direto nas células
export { styles as tabelaStyles };

// Componentes primitivos para composição manual
export function TabelaTd({
  children,
  alinhamento,
  className,
}: {
  children: ReactNode;
  alinhamento?: "esquerda" | "direita" | "centro";
  className?: string;
}) {
  return (
    <td
      className={[
        styles.td,
        alinhamento === "direita" ? styles.direita : "",
        alinhamento === "centro" ? styles.centro : "",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </td>
  );
}

import React from "react";
