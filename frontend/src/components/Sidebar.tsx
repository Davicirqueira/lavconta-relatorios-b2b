/**
 * Sidebar — navegação colapsável com gradiente azul-900→azul-800.
 *
 * COMPORTAMENTO DE COLAPSO (brief-design.md §5)
 *   1. Rótulos somem em 80ms (opacity 0) — via CSS [data-colapsada="true"]
 *   2. Largura contrai de 240px para 68px em 320ms --ease-suave
 *   3. Expandir: ordem inversa — largura primeiro, rótulos aparecem por último
 *
 *   Isso evita que o texto amasse no meio da transição, que é o sinal
 *   de implementação descuidada.
 *
 * PERSISTÊNCIA: estado salvo em localStorage.
 *
 * BARRA INDICADORA: 3px em azul-300 na borda esquerda do item ativo,
 *   implementada via CSS ::before no .itemAtivo.
 *
 * ACESSIBILIDADE: aria-expanded no botão de colapso; tooltips com
 *   role="tooltip" para leitores de tela no estado colapsado.
 */

import { useState, useEffect, useId } from "react";
import { NavLink, useNavigate } from "react-router";
import {
  ClipboardList,
  FileBarChart2,
  Building2,
  Shirt,
  Tag,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import styles from "./Sidebar.module.css";
import { supabase } from "@/lib/supabase";
import { marcarSaidaVoluntaria } from "@/features/auth/saida";

const CHAVE_STORAGE = "lavconta:sidebar-colapsada";

const ITENS_NAV = [
  { para: "/lancamentos", rotulo: "Lançamentos",  Icone: ClipboardList },
  { para: "/relatorio",   rotulo: "Relatório",    Icone: FileBarChart2 },
  { para: "/clientes",    rotulo: "Clientes",     Icone: Building2 },
  { para: "/catalogo",    rotulo: "Catálogo",     Icone: Shirt },
  { para: "/precos",      rotulo: "Preços",       Icone: Tag },
] as const;

export function Sidebar() {
  const [colapsada, setColapsada] = useState<boolean>(() => {
    // Inicia colapsada em telas < 1024px
    if (typeof window !== "undefined" && window.innerWidth < 1024) return true;
    return localStorage.getItem(CHAVE_STORAGE) === "true";
  });
  const [email, setEmail] = useState<string>("");
  const navigate = useNavigate();
  const idTooltipBase = useId();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setEmail(session?.user?.email ?? "");
    });
  }, []);

  function alternarColapso() {
    setColapsada((prev) => {
      const novoEstado = !prev;
      localStorage.setItem(CHAVE_STORAGE, String(novoEstado));
      return novoEstado;
    });
  }

  async function sair() {
    marcarSaidaVoluntaria();
    await supabase.auth.signOut();
    navigate("/login");
  }

  const inicial = email?.[0]?.toUpperCase() ?? "U";

  return (
    <nav
      className={styles.sidebar}
      data-colapsada={colapsada}
      aria-label="Navegação principal"
    >
      {/* Topo: marca */}
      <div className={styles.topo}>
        <div className={styles.marca}>
          <span className={styles.monograma} aria-hidden="true">
            {colapsada ? "L" : "Lc"}
          </span>
          {!colapsada && (
            <span className={styles.marcaNome}>Lavconta</span>
          )}
        </div>
      </div>

      {/* Navegação */}
      <ul className={styles.nav} role="list">
        {ITENS_NAV.map(({ para, rotulo, Icone }) => {
          const tooltipId = `${idTooltipBase}-${para.slice(1)}`;
          return (
            <li key={para} className={styles.itemWrapper}>
              <NavLink
                to={para}
                className={({ isActive }) =>
                  [styles.item, isActive ? styles.itemAtivo : ""]
                    .filter(Boolean)
                    .join(" ")
                }
                aria-describedby={colapsada ? tooltipId : undefined}
              >
                <span className={styles.iconeItem} aria-hidden="true">
                  <Icone size={20} strokeWidth={1.75} />
                </span>
                <span className={styles.rotuloItem}>{rotulo}</span>
              </NavLink>
              {/* Tooltip só no estado colapsado */}
              {colapsada && (
                <span id={tooltipId} role="tooltip" className={styles.tooltip}>
                  {rotulo}
                </span>
              )}
            </li>
          );
        })}
      </ul>

      {/* Rodapé: usuário + colapso */}
      <div className={styles.rodape}>
        <div className={styles.usuario}>
          <div className={styles.avatar} aria-hidden="true">{inicial}</div>
          <span className={styles.email} title={email}>{email}</span>
        </div>

        {/* Sair */}
        <div className={styles.itemWrapper}>
          <button
            className={styles.item}
            onClick={sair}
            type="button"
            aria-describedby={colapsada ? `${idTooltipBase}-sair` : undefined}
          >
            <span className={styles.iconeItem} aria-hidden="true">
              <LogOut size={20} strokeWidth={1.75} />
            </span>
            <span className={styles.rotuloItem}>Sair</span>
          </button>
          {colapsada && (
            <span id={`${idTooltipBase}-sair`} role="tooltip" className={styles.tooltip}>
              Sair
            </span>
          )}
        </div>

        {/* Controle de colapso */}
        <button
          className={styles.botaoColapso}
          onClick={alternarColapso}
          type="button"
          aria-expanded={!colapsada}
          aria-label={colapsada ? "Expandir menu" : "Recolher menu"}
        >
          <span className={styles.iconeItem} aria-hidden="true">
            {colapsada
              ? <PanelLeftOpen size={18} strokeWidth={1.75} />
              : <PanelLeftClose size={18} strokeWidth={1.75} />
            }
          </span>
          <span className={styles.rotuloColapso}>
            {colapsada ? "" : "Recolher"}
          </span>
        </button>
      </div>
    </nav>
  );
}
