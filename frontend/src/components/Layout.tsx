/**
 * Layout principal — sidebar + área de conteúdo.
 * O conteúdo acompanha a sidebar na mesma curva e duração de transição.
 */

import { Outlet } from "react-router";
import { Sidebar } from "./Sidebar";
import styles from "./Layout.module.css";

export function Layout() {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={styles.conteudo}>
        <div className={styles.inner}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
