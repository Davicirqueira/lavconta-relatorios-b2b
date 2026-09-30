/**
 * EstadoVazio — tela sem dados, com orientação ao próximo passo.
 */

import type { ReactNode } from "react";
import { Botao } from "./Botao";
import styles from "./EstadoVazio.module.css";

interface PropsEstadoVazio {
  titulo: string;
  descricao: string;
  rotuloBotao?: string;
  onAcao?: () => void;
  icone?: ReactNode;
}

export function EstadoVazio({
  titulo,
  descricao,
  rotuloBotao,
  onAcao,
  icone,
}: PropsEstadoVazio) {
  return (
    <div className={styles.container}>
      {icone && <div className={styles.icone}>{icone}</div>}
      <h3 className={styles.titulo}>{titulo}</h3>
      <p className={styles.descricao}>{descricao}</p>
      {rotuloBotao && onAcao && (
        <Botao variante="primario" onClick={onAcao}>
          {rotuloBotao}
        </Botao>
      )}
    </div>
  );
}
