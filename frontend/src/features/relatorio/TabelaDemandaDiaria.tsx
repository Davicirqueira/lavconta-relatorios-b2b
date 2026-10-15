/**
 * TabelaDemandaDiaria — tabela de lançamentos agrupados por dia (v1.1 fase 6).
 *
 * Reutilizável entre relatório individual e geral. Estrutura idêntica: data, colunas
 * de itens dinâmicas, totais. A diferença é que no geral não há comanda e os dados
 * consolidam múltiplos clientes.
 */

import { formatarInteiro, formatarMoeda } from "@/lib/dinheiro";
import { paraExibicao } from "@/lib/datas";
import type { ColunaItem, LinhaDemandaDiaria } from "@/types/api";
import tabela from "@/components/TabelaDados.module.css";
import styles from "./TelaRelatorio.module.css";

interface TabelaDemandaDiariaProps {
  linhas: LinhaDemandaDiaria[];
  colunas: ColunaItem[];
  /** Totais por item (para o rodapé) */
  totaisPorItem: Record<string, number>;
  totalPecas: number;
  totalValor: string;
  /** Texto para acessibilidade */
  ariaLabel: string;
  /** Se true, não mostra coluna de comanda (relatório geral) */
  semComanda?: boolean;
  /** Preços por item_id (opcional) - usado para exibir no cabeçalho */
  precosPorItem?: Record<string, string>;
}

const TONS_COLUNA = [
  "--cor-chip-1",
  "--cor-chip-2",
  "--cor-chip-3",
  "--cor-chip-4",
  "--cor-chip-5",
] as const;

export function TabelaDemandaDiaria({
  linhas,
  colunas,
  totaisPorItem,
  totalPecas,
  totalValor,
  ariaLabel,
  semComanda = false,
  precosPorItem,
}: TabelaDemandaDiariaProps) {
  return (
    <div className={tabela.container}>
      <div className={tabela.rolagem}>
        <table className={tabela.tabela} aria-label={ariaLabel}>
          <thead>
            <tr>
              <th scope="col">Data</th>
              {!semComanda && <th scope="col">Comanda</th>}
              {colunas.map((coluna, i) => {
                const preco = precosPorItem?.[coluna.item_id];
                const textoColuna = preco ? `${coluna.nome} (R$ ${preco})` : coluna.nome;
                
                return (
                  <th key={coluna.item_id} scope="col" className={tabela.direita}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                      <span
                        className={styles.chipColuna}
                        style={{ background: `var(${TONS_COLUNA[i % TONS_COLUNA.length]})` }}
                        aria-hidden="true"
                      />
                      <span>{textoColuna}</span>
                    </div>
                  </th>
                );
              })}
              <th scope="col" className={tabela.direita}>
                Total de peças
              </th>
              <th scope="col" className={tabela.direita}>
                Total R$
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.data}>
                <td>{paraExibicao(linha.data)}</td>
                {/* Comanda não existe no consolidado */}
                {!semComanda && <td />}
                {colunas.map((coluna) => {
                  const qtd = linha.quantidades[coluna.item_id];
                  return (
                    // item ausente no dia: célula vazia, não zero
                    <td key={coluna.item_id} className={tabela.direita}>
                      {qtd !== undefined ? formatarInteiro(qtd) : ""}
                    </td>
                  );
                })}
                <td className={tabela.direita}>{formatarInteiro(linha.total_pecas)}</td>
                <td className={`${tabela.direita} ${tabela.valor}`}>
                  {formatarMoeda(linha.total_valor)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Totais</td>
              {!semComanda && <td />}
              {colunas.map((coluna) => (
                <td key={coluna.item_id} className={tabela.direita}>
                  {formatarInteiro(totaisPorItem[coluna.item_id] ?? 0)}
                </td>
              ))}
              <td className={tabela.direita}>{formatarInteiro(totalPecas)}</td>
              <td className={tabela.direita}>{formatarMoeda(totalValor)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
