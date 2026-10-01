/**
 * MolduraAutenticacao — estrutura comum de login, recuperação e redefinição.
 *
 * Do protótipo (aprovado na avaliação, Parte A item 2): marca acima do cartão,
 * cartão único e o aviso de acesso restrito. Sem "Lembrar-me" e sem links de
 * suporte/termos: fora do escopo da v1 (a sessão já persiste por padrão).
 * Nunca há link de cadastro.
 */

import type { ReactNode } from "react";
import { ShieldCheck, Waves } from "lucide-react";
import styles from "@/pages/Login.module.css";

interface PropsMoldura {
  titulo: string;
  descricao?: string;
  children: ReactNode;
}

export function MolduraAutenticacao({ titulo, descricao, children }: PropsMoldura) {
  return (
    <div className={styles.fundo}>
      <main className={styles.coluna}>
        <div className={styles.marca}>
          <span className={styles.selo} aria-hidden="true">
            <Waves size={26} />
          </span>
          <p className={styles.logotipo}>Lavconta</p>
          <p className={styles.subtitulo}>Relatórios B2B da Lavandix</p>
        </div>

        <section className={styles.cartao} aria-labelledby="titulo-autenticacao">
          <h1 id="titulo-autenticacao" className={styles.titulo}>
            {titulo}
          </h1>
          {descricao && <p className={styles.descricao}>{descricao}</p>}
          {children}
          <p className={styles.aviso}>
            <ShieldCheck size={14} aria-hidden="true" />
            Acesso exclusivo para a equipe autorizada.
          </p>
        </section>
      </main>
    </div>
  );
}
