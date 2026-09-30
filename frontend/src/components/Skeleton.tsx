/**
 * Skeleton — placeholder animado para conteúdo em carregamento.
 * Shimmer horizontal em loop de 1,6s (brief-design.md §4).
 */

import styles from "./Skeleton.module.css";

type VarianteSkeleton = "linha" | "titulo" | "bloco";

interface PropsSkeleton {
  variante?: VarianteSkeleton;
  largura?: string;
  className?: string;
}

export function Skeleton({
  variante = "linha",
  largura = "100%",
  className,
}: PropsSkeleton) {
  return (
    <div
      className={[styles.skeleton, styles[variante], className ?? ""]
        .filter(Boolean)
        .join(" ")}
      style={{ width: largura }}
      aria-hidden="true"
    />
  );
}

/** Layout de tabela em carregamento */
export function SkeletonTabela({ linhas = 5 }: { linhas?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Skeleton variante="titulo" largura="60%" />
      {Array.from({ length: linhas }, (_, i) => (
        <Skeleton key={i} variante="linha" />
      ))}
    </div>
  );
}
