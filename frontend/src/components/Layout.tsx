/**
 * Layout principal — sidebar + área de conteúdo.
 *
 * O painel de "servidor acordando" fica aqui, uma única vez, alimentado pelo
 * sinal global do cliente de API: qualquer tela que esteja esperando mais de
 * 3s faz o painel aparecer, sem cada tela precisar tratar o caso.
 */

import { Outlet } from "react-router";
import { Sidebar } from "./Sidebar";
import { PainelServidorAcordando } from "./PainelServidorAcordando";
import { useServidorLento } from "@/lib/useServidorLento";
import styles from "./Layout.module.css";

export function Layout() {
  const servidorLento = useServidorLento();

  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={styles.conteudo}>
        <div className={styles.inner}>
          {servidorLento && (
            <div className={styles.avisoServidor}>
              <PainelServidorAcordando />
            </div>
          )}
          <Outlet />
        </div>
      </main>
    </div>
  );
}
