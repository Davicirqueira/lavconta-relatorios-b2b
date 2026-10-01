/**
 * TelaRelatorio — relação de valores do fechamento (tarefas 47 e 48).
 *
 * FONTE ÚNICA DOS TOTAIS (defeito B1)
 *   Os cartões leem `resumo`; o rodapé da tabela lê `totais`. Os dois vêm da
 *   mesma agregação no backend. Esta tela não soma nenhum número.
 *
 * ESCOPO (avaliação B2)
 *   Quatro cartões: Total R$, Total de peças, Nº de lançamentos e Média
 *   diária de peças. Sem ticket médio e sem variação percentual.
 */

import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router";
import {
  CalendarDays,
  ClipboardList,
  FileBarChart2,
  FileDown,
  FileSpreadsheet,
  Shirt,
  Wallet,
} from "lucide-react";
import { Botao } from "@/components/Botao";
import { Selecao } from "@/components/Selecao";
import { CampoData } from "@/components/CampoData";
import { SkeletonTabela } from "@/components/Skeleton";
import { EstadoVazio } from "@/components/EstadoVazio";
import { useToast } from "@/components/Toast";
import { ErroDeApi } from "@/lib/api";
import { useClientes } from "@/features/clientes/hooks";
import { rotuloCliente } from "@/features/clientes/rotulos";
import { paraExibicao, primeiroDiaDoMesAtual, ultimoDiaDoMesAtual } from "@/lib/datas";
import { formatarInteiro, formatarMoeda } from "@/lib/dinheiro";
import type { Relatorio } from "@/types/api";
import { barrasDoPeriodo, tomDaBarra } from "./grafico";
import {
  exportarRelatorio,
  useRelatorio,
  type FiltroRelatorio,
  type FormatoExportacao,
} from "./hooks";
import pagina from "@/components/Pagina.module.css";
import tabela from "@/components/TabelaDados.module.css";
import styles from "./TelaRelatorio.module.css";

// Chip de coluna: varia na escala azul para o olho seguir a coluna até o rodapé
const TONS_COLUNA = ["--azul-400", "--azul-600", "--azul-300", "--azul-700", "--azul-500"];

export function TelaRelatorio() {
  const [params, setParams] = useSearchParams();
  const { mostrar } = useToast();

  // Rascunho dos filtros (o que está nos campos)
  const [clienteId, setClienteId] = useState(params.get("cliente") ?? "");
  const [inicio, setInicio] = useState(params.get("inicio") ?? primeiroDiaDoMesAtual());
  const [fim, setFim] = useState(params.get("fim") ?? ultimoDiaDoMesAtual());
  const [erroFiltro, setErroFiltro] = useState("");

  // Filtro aplicado (o que o relatório exibe): vem da URL
  const aplicado: FiltroRelatorio | null =
    params.get("cliente") && params.get("inicio") && params.get("fim")
      ? { clienteId: params.get("cliente")!, inicio: params.get("inicio")!, fim: params.get("fim")! }
      : null;

  const { data: clientes } = useClientes(true);
  const relatorio = useRelatorio(aplicado);
  const [exportando, setExportando] = useState<FormatoExportacao | null>(null);

  function gerar(e: FormEvent) {
    e.preventDefault();
    if (!clienteId) return setErroFiltro("Selecione o cliente.");
    if (!inicio || !fim) return setErroFiltro("Informe as datas no formato dd/mm/aaaa.");
    if (inicio > fim) return setErroFiltro("A data inicial não pode ser posterior à data final.");
    setErroFiltro("");
    setParams({ cliente: clienteId, inicio, fim });
  }

  async function exportar(formato: FormatoExportacao) {
    if (!aplicado) return;
    setExportando(formato);
    try {
      await exportarRelatorio(aplicado, formato);
      mostrar(`Arquivo ${formato === "pdf" ? "PDF" : "Excel"} gerado.`, "sucesso");
    } catch (erro) {
      mostrar(
        erro instanceof ErroDeApi ? erro.message : "Não foi possível gerar o arquivo.",
        "erro",
      );
    } finally {
      setExportando(null);
    }
  }

  const dados = relatorio.data;
  const podeExportar = !!dados && !exportando;

  return (
    <div>
      <div className={pagina.cabecalho}>
        <h1 className={pagina.titulo}>Relatório de fechamento</h1>
        <div className={styles.exportar}>
          <Botao
            variante="secundario"
            onClick={() => exportar("pdf")}
            disabled={!podeExportar}
            carregando={exportando === "pdf"}
          >
            <FileDown size={16} aria-hidden="true" /> Exportar PDF
          </Botao>
          <Botao
            variante="secundario"
            onClick={() => exportar("excel")}
            disabled={!podeExportar}
            carregando={exportando === "excel"}
          >
            <FileSpreadsheet size={16} aria-hidden="true" /> Exportar Excel
          </Botao>
        </div>
      </div>

      <form className={pagina.filtros} onSubmit={gerar} noValidate>
        <Selecao
          rotulo="Cliente"
          className={pagina.filtroCliente}
          value={clienteId}
          onChange={(e) => setClienteId(e.target.value)}
          placeholder="Selecione um cliente…"
        >
          {(clientes ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {rotuloCliente(c)}
            </option>
          ))}
        </Selecao>
        <CampoData
          rotulo="Data inicial"
          id="relatorio-inicio"
          className={pagina.filtroData}
          valor={inicio}
          aoMudar={setInicio}
        />
        <CampoData
          rotulo="Data final"
          id="relatorio-fim"
          className={pagina.filtroData}
          valor={fim}
          aoMudar={setFim}
        />
        <Botao type="submit" className={pagina.filtroAcao}>
          Gerar relatório
        </Botao>
      </form>

      {erroFiltro && (
        <div className={pagina.bannerAlerta} role="alert">
          {erroFiltro}
        </div>
      )}

      {!aplicado && (
        <EstadoVazio
          icone={<FileBarChart2 size={28} />}
          titulo="Gere a relação de valores"
          descricao="Selecione o cliente e o período e clique em Gerar relatório. O período padrão é o mês atual."
        />
      )}

      {aplicado && relatorio.isLoading && <SkeletonTabela linhas={8} />}

      {aplicado && relatorio.isError && (
        <div className={pagina.bannerErro} role="alert">
          {relatorio.error.message || "Não foi possível gerar o relatório."}
          <Botao variante="fantasma" tamanho="sm" onClick={() => relatorio.refetch()}>
            Tentar novamente
          </Botao>
        </div>
      )}

      {dados && <ConteudoRelatorio relatorio={dados} />}
    </div>
  );
}

function ConteudoRelatorio({ relatorio }: { relatorio: Relatorio }) {
  const { cliente, periodo, colunas_itens, linhas, totais, resumo } = relatorio;
  const vazio = linhas.length === 0;

  const cartoes = [
    {
      rotulo: "Total R$",
      valor: formatarMoeda(resumo.total_valor),
      Icone: Wallet,
      acento: styles.acentoValor,
    },
    {
      rotulo: "Total de peças",
      valor: formatarInteiro(resumo.total_pecas),
      Icone: Shirt,
      acento: styles.acentoPecas,
    },
    {
      rotulo: "Nº de lançamentos",
      valor: formatarInteiro(resumo.quantidade_lancamentos),
      Icone: ClipboardList,
      acento: styles.acentoLancamentos,
    },
    {
      rotulo: "Média diária de peças",
      valor: formatarInteiro(resumo.media_diaria_pecas),
      Icone: CalendarDays,
      acento: styles.acentoMedia,
    },
  ];

  return (
    <>
      <div className={styles.identificacao}>
        <p className={styles.clienteNome}>{cliente.nome}</p>
        <p className={styles.periodo}>
          {paraExibicao(periodo.inicio)} a {paraExibicao(periodo.fim)}
        </p>
      </div>

      <div className={styles.cartoes}>
        {cartoes.map(({ rotulo, valor, Icone, acento }, i) => (
          <div
            key={rotulo}
            className={styles.cartaoResumo}
            style={{ animationDelay: `${i * 40}ms` }}
          >
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

      {vazio ? (
        <EstadoVazio
          icone={<FileBarChart2 size={28} />}
          titulo="Nenhum lançamento no período"
          descricao="Não há registros para este cliente no período selecionado. Os totais estão zerados."
        />
      ) : (
        <>
          <VolumeDiario relatorio={relatorio} />

          <div className={tabela.container}>
            <div className={tabela.rolagem}>
              <table
                className={tabela.tabela}
                aria-label={`Relação de valores de ${cliente.nome}, ${paraExibicao(periodo.inicio)} a ${paraExibicao(periodo.fim)}`}
              >
                <thead>
                  <tr>
                    <th scope="col">Data</th>
                    <th scope="col">Comanda</th>
                    {colunas_itens.map((coluna, i) => (
                      <th key={coluna.item_id} scope="col" className={tabela.direita}>
                        <span
                          className={styles.chipColuna}
                          style={{ background: `var(${TONS_COLUNA[i % TONS_COLUNA.length]})` }}
                          aria-hidden="true"
                        />
                        {coluna.nome}
                      </th>
                    ))}
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
                    <tr key={linha.lancamento_id}>
                      <td className="num">{paraExibicao(linha.data)}</td>
                      {/* sem comanda: a célula existe, só fica vazia (Req 7.10) */}
                      <td>{linha.comanda ?? ""}</td>
                      {colunas_itens.map((coluna) => {
                        const qtd = linha.quantidades[coluna.item_id];
                        return (
                          // item ausente no dia: célula vazia, não zero (Req 7.8)
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
                    <td />
                    {colunas_itens.map((coluna) => (
                      <td key={coluna.item_id} className={tabela.direita}>
                        {formatarInteiro(totais.por_item[coluna.item_id] ?? 0)}
                      </td>
                    ))}
                    <td className={tabela.direita}>{formatarInteiro(totais.total_pecas)}</td>
                    <td className={tabela.direita}>{formatarMoeda(totais.total_valor)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function VolumeDiario({ relatorio }: { relatorio: Relatorio }) {
  const barras = barrasDoPeriodo(relatorio.periodo.inicio, relatorio.periodo.fim, relatorio.linhas);

  return (
    <section className={styles.volume} aria-labelledby="titulo-volume">
      <h2 id="titulo-volume" className={styles.volumeTitulo}>
        Volume diário de peças
      </h2>
      {/* Cada barra tem rótulo próprio: a informação não depende só da cor */}
      <div className={styles.barras} role="list">
        {barras.map((barra) => {
          const rotulo = `${paraExibicao(barra.data)}: ${formatarInteiro(barra.pecas)} peças`;
          return (
            <div
              key={barra.data}
              className={styles.barra}
              role="listitem"
              tabIndex={0}
              aria-label={rotulo}
            >
              {barra.pecas > 0 ? (
                <div
                  className={styles.barraPreenchida}
                  style={{
                    height: `${Math.max(4, barra.proporcao * 100)}%`,
                    background: tomDaBarra(barra.proporcao),
                  }}
                />
              ) : (
                <div className={styles.barraVazia} />
              )}
              <span className={styles.dica} aria-hidden="true">
                {rotulo}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
