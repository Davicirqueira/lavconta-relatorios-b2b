/**
 * TabelaDemandaDiaria — tabela de lançamentos agrupados por dia (v1.1 fase 6).
 *
 * Reutilizável entre relatório individual e geral. Estrutura idêntica: data, colunas
 * de itens dinâmicas, totais. A diferença é que no geral não há comanda e os dados
 * consolidam múltiplos clientes.
 *
 * Modo controleDemanda: exibe apenas quantidades de peças (volume de produção),
 * sem valores monetários. Usado no relatório geral para controle operacional.
 * Inclui heatmap visual para facilitar identificação de padrões de volume.
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
  totalValor?: string;
  /** Texto para acessibilidade */
  ariaLabel: string;
  /** Se true, não mostra coluna de comanda (relatório geral) */
  semComanda?: boolean;
  /** Se true, remove valores monetários (controle de demanda operacional) */
  controleDemanda?: boolean;
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

/**
 * Calcula a intensidade do heatmap (0-1) baseada no valor em relação ao máximo.
 * Usa escala logarítmica suave para melhor distribuição visual.
 */
function calcularIntensidade(valor: number, maximo: number): number {
  if (maximo === 0 || valor === 0) return 0;
  // Escala logarítmica suave: log(1 + valor) / log(1 + max)
  return Math.log(1 + valor) / Math.log(1 + maximo);
}

/**
 * Gera cor de fundo para heatmap baseada na intensidade.
 * Usa tons de azul com opacidade crescente para não interferir na legibilidade.
 */
function corHeatmap(intensidade: number): string {
  if (intensidade === 0) return "transparent";
  // Mapeia 0-1 para opacidade 0.05-0.25 (sutil mas visível)
  const opacidade = 0.05 + intensidade * 0.20;
  return `rgba(59, 130, 246, ${opacidade})`; // blue-500
}

export function TabelaDemandaDiaria({
  linhas,
  colunas,
  totaisPorItem,
  totalPecas,
  totalValor,
  ariaLabel,
  semComanda = false,
  controleDemanda = false,
  precosPorItem,
}: TabelaDemandaDiariaProps) {
  // Calcular máximos por coluna para o heatmap (apenas no modo controle de demanda)
  const maximosPorItem: Record<string, number> = {};
  if (controleDemanda) {
    for (const coluna of colunas) {
      let max = 0;
      for (const linha of linhas) {
        const qtd = linha.quantidades[coluna.item_id] ?? 0;
        if (qtd > max) max = qtd;
      }
      maximosPorItem[coluna.item_id] = max;
    }
  }

  // Encontrar maior e menor total de peças do dia para badges
  let maiorDia = 0;
  let menorDia = Infinity;
  if (controleDemanda && linhas.length > 0) {
    for (const linha of linhas) {
      if (linha.total_pecas > maiorDia) maiorDia = linha.total_pecas;
      if (linha.total_pecas < menorDia) menorDia = linha.total_pecas;
    }
  }

  return (
    <div className={tabela.container}>
      <div className={tabela.rolagem}>
        <table className={tabela.tabela} aria-label={ariaLabel}>
          <thead>
            <tr>
              <th scope="col">Data</th>
              {!semComanda && <th scope="col">Comanda</th>}
              {colunas.map((coluna, i) => {
                // No controle de demanda, não mostra preços nos cabeçalhos
                const preco = !controleDemanda ? precosPorItem?.[coluna.item_id] : undefined;
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
                Total de peças{controleDemanda ? " (dia)" : ""}
              </th>
              {!controleDemanda && (
                <th scope="col" className={tabela.direita}>
                  Total R$
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => {
              const ehPico = controleDemanda && linha.total_pecas === maiorDia && linhas.length > 1;
              const ehVale = controleDemanda && linha.total_pecas === menorDia && linhas.length > 1 && menorDia !== maiorDia;
              
              return (
                <tr key={linha.data}>
                  <td>{paraExibicao(linha.data)}</td>
                  {/* Comanda não existe no consolidado */}
                  {!semComanda && <td />}
                  {colunas.map((coluna) => {
                    const qtd = linha.quantidades[coluna.item_id];
                    
                    // Heatmap apenas no modo controle de demanda
                    let estilo: React.CSSProperties = {};
                    if (controleDemanda && qtd !== undefined) {
                      const intensidade = calcularIntensidade(qtd, maximosPorItem[coluna.item_id]);
                      estilo = {
                        background: corHeatmap(intensidade),
                        fontWeight: intensidade > 0.7 ? 600 : 400,
                      };
                    }
                    
                    return (
                      // item ausente no dia: célula vazia, não zero
                      <td key={coluna.item_id} className={tabela.direita} style={estilo}>
                        {qtd !== undefined ? formatarInteiro(qtd) : ""}
                      </td>
                    );
                  })}
                  <td className={tabela.direita} style={{ position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                      <span>{formatarInteiro(linha.total_pecas)}</span>
                      {ehPico && (
                        <span 
                          className={styles.badgePico}
                          title="Maior volume do período"
                          aria-label="Pico de demanda"
                        >
                          ↑
                        </span>
                      )}
                      {ehVale && (
                        <span 
                          className={styles.badgeVale}
                          title="Menor volume do período"
                          aria-label="Vale de demanda"
                        >
                          ↓
                        </span>
                      )}
                    </div>
                  </td>
                  {!controleDemanda && (
                    <td className={`${tabela.direita} ${tabela.valor}`}>
                      {formatarMoeda(linha.total_valor)}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <td>
                <strong>Totais{controleDemanda ? " (período)" : ""}</strong>
              </td>
              {!semComanda && <td />}
              {colunas.map((coluna) => {
                const total = totaisPorItem[coluna.item_id] ?? 0;
                return (
                  <td key={coluna.item_id} className={tabela.direita}>
                    {controleDemanda ? (
                      <div className={styles.totalComBarra}>
                        <strong>{formatarInteiro(total)}</strong>
                        <div 
                          className={styles.barraTotal}
                          style={{ 
                            width: `${(total / totalPecas) * 100}%`,
                            background: `var(${TONS_COLUNA[colunas.indexOf(coluna) % TONS_COLUNA.length]})`
                          }}
                          title={`${((total / totalPecas) * 100).toFixed(1)}% do total`}
                        />
                      </div>
                    ) : (
                      formatarInteiro(total)
                    )}
                  </td>
                );
              })}
              <td className={tabela.direita}>
                <strong>{formatarInteiro(totalPecas)}</strong>
              </td>
              {!controleDemanda && totalValor && (
                <td className={tabela.direita}>
                  <strong>{formatarMoeda(totalValor)}</strong>
                </td>
              )}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
