/**
 * RelatorioGeral — todos os clientes com pedido no período (v1.1, Req 5).
 *
 * Uma seção por cliente (item · por peça · peças · subtotal) e o total geral.
 * Fase 6: inclui tabela de controle de demanda (todos os clientes somados
 * por data), exibida acima das seções de cliente.
 *
 * Tudo vem calculado da API; a tela não soma nada. Item a dois valores no
 * período aparece em duas linhas: é o que foi cobrado em cada pedido.
 */

import { Building2, FileBarChart2, Shirt, Wallet } from "lucide-react";
import { EstadoVazio } from "@/components/EstadoVazio";
import { paraExibicao } from "@/lib/datas";
import { formatarInteiro, formatarMoeda } from "@/lib/dinheiro";
import type { RelatorioGeral as TipoRelatorioGeral } from "@/types/api";
import { TabelaDemandaDiaria } from "./TabelaDemandaDiaria";
import tabela from "@/components/TabelaDados.module.css";
import styles from "./TelaRelatorio.module.css";

export function RelatorioGeral({ relatorio }: { relatorio: TipoRelatorioGeral }) {
  const { periodo, secoes, demanda_diaria, colunas_itens } = relatorio;
  const textoPeriodo = `${paraExibicao(periodo.inicio)} a ${paraExibicao(periodo.fim)}`;

  const cartoes = [
    { rotulo: "Total R$", valor: formatarMoeda(relatorio.total_valor), Icone: Wallet, acento: styles.acentoValor },
    { rotulo: "Total de peças", valor: formatarInteiro(relatorio.total_pecas), Icone: Shirt, acento: styles.acentoPecas },
    { rotulo: "Clientes no período", valor: formatarInteiro(secoes.length), Icone: Building2, acento: styles.acentoLancamentos },
  ];

  // Calcular totais por item para o rodapé da tabela de demanda (v1.1 fase 6)
  const totaisPorItem: Record<string, number> = {};
  const precosPorItem: Record<string, string> = {};
  
  // Coletar preços das colunas (vêm da API)
  for (const coluna of colunas_itens) {
    if (coluna.valor_unitario) {
      precosPorItem[coluna.item_id] = coluna.valor_unitario;
    }
  }
  
  // Calcular totais (com verificação defensiva)
  if (demanda_diaria && Array.isArray(demanda_diaria)) {
    for (const linha of demanda_diaria) {
      if (linha.quantidades) {
        for (const [item_id, qtd] of Object.entries(linha.quantidades)) {
          totaisPorItem[item_id] = (totaisPorItem[item_id] ?? 0) + qtd;
        }
      }
    }
  }

  return (
    <>
      <div className={styles.identificacao}>
        <p className={styles.clienteNome}>Todos os clientes</p>
        <p className={styles.periodo}>{textoPeriodo}</p>
      </div>

      <div className={`${styles.cartoes} ${styles.cartoesTres}`}>
        {cartoes.map(({ rotulo, valor, Icone, acento }, i) => (
          <div key={rotulo} className={styles.cartaoResumo} style={{ animationDelay: `${i * 40}ms` }}>
            <div>
              <p className={styles.cartaoRotulo}>{rotulo}</p>
              <p className={styles.cartaoNumero}>{valor}</p>
            </div>
            <span className={`${styles.cartaoIcone} ${acento}`} aria-hidden="true">
              <Icone size={20} />
            </span>
          </div>
        ))}
      </div>

      {secoes.length === 0 ? (
        <EstadoVazio
          icone={<FileBarChart2 size={28} />}
          titulo="Nenhum pedido no período escolhido"
          descricao="Nenhum cliente teve pedido registrado nestas datas. Os totais estão zerados."
        />
      ) : (
        <>
          {/* Tabela de controle de demanda — v1.1 fase 6 */}
          {demanda_diaria.length > 0 && (
            <section aria-labelledby="titulo-demanda" className={styles.tabelaDemanda}>
              <h2 id="titulo-demanda" className={styles.secaoTitulo}>
                Controle de demanda
              </h2>
              <TabelaDemandaDiaria
                linhas={demanda_diaria}
                colunas={colunas_itens}
                totaisPorItem={totaisPorItem}
                totalPecas={relatorio.total_pecas}
                totalValor={relatorio.total_valor}
                ariaLabel={`Demanda diária de todos os clientes, ${textoPeriodo}`}
                semComanda
                precosPorItem={precosPorItem}
              />
            </section>
          )}

          {secoes.map((secao) => (
            <section
              key={secao.cliente.id}
              className={styles.secaoCliente}
              aria-labelledby={`secao-${secao.cliente.id}`}
            >
              <div className={styles.secaoTopo}>
                <h2 id={`secao-${secao.cliente.id}`} className={styles.secaoTitulo}>
                  {secao.cliente.nome}
                </h2>
                <p className={styles.secaoTotais}>
                  {formatarInteiro(secao.total_pecas)} peças · {formatarMoeda(secao.total_valor)}
                </p>
              </div>
              <div className={tabela.container}>
                <div className={tabela.rolagem}>
                  <table
                    className={`${tabela.tabela} ${styles.tabelaSecao}`}
                    aria-label={`Itens de ${secao.cliente.nome}, ${textoPeriodo}`}
                  >
                    {/* mesmas larguras em todas as seções: as colunas se alinham entre clientes */}
                    <colgroup>
                      <col className={styles.colItem} />
                      <col className={styles.colNumero} />
                      <col className={styles.colNumero} />
                      <col className={styles.colSubtotal} />
                    </colgroup>
                    <thead>
                      <tr>
                        <th scope="col">Item</th>
                        <th scope="col" className={tabela.direita}>
                          Por peça
                        </th>
                        <th scope="col" className={tabela.direita}>
                          Peças
                        </th>
                        <th scope="col" className={tabela.direita}>
                          Subtotal
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {secao.linhas.map((linha) => (
                        <tr key={`${linha.item_id}-${linha.valor_unitario}`}>
                          <td>{linha.item_nome}</td>
                          <td className={tabela.direita}>{formatarMoeda(linha.valor_unitario)}</td>
                          <td className={tabela.direita}>{formatarInteiro(linha.quantidade)}</td>
                          <td className={`${tabela.direita} ${tabela.valor}`}>
                            {formatarMoeda(linha.subtotal)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td>Total</td>
                        <td />
                        <td className={tabela.direita}>{formatarInteiro(secao.total_pecas)}</td>
                        <td className={tabela.direita}>{formatarMoeda(secao.total_valor)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </section>
          ))}

          <div className={styles.totalGeral} role="group" aria-label="Total geral do período">
            <span className={styles.totalGeralRotulo}>Total geral</span>
            <span className={styles.totalGeralValores}>
              {formatarInteiro(relatorio.total_pecas)} peças ·{" "}
              <strong>{formatarMoeda(relatorio.total_valor)}</strong>
            </span>
          </div>
        </>
      )}
    </>
  );
}
