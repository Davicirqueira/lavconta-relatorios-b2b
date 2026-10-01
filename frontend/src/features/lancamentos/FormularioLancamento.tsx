/**
 * FormularioLancamento — novo e edição de lançamento (tarefa 45).
 *
 * O QUE O FORMULÁRIO NÃO FAZ
 *   Não calcula preço nem total. Valor unitário, total da linha e os totais
 *   da barra vêm da prévia do servidor; no salvamento, o servidor congela o
 *   valor de novo e é a fonte final. O navegador nunca envia valor.
 *
 * ESCOPO (avaliação v1)
 *   Sem campo de notas/observações (B3). Comanda existe sempre, marcada como
 *   opcional. Quantidade aceita digitação direta e stepper (C1).
 */

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { AlertTriangle, ArrowLeft, Minus, Plus, Trash2 } from "lucide-react";
import { Botao } from "@/components/Botao";
import { Campo } from "@/components/Campo";
import { CampoData } from "@/components/CampoData";
import { Selecao } from "@/components/Selecao";
import { SkeletonTabela } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";
import { useClientes } from "@/features/clientes/hooks";
import { useItens } from "@/features/catalogo/hooks";
import { diasNoMes, hojeSp } from "@/lib/datas";
import { formatarMoeda } from "@/lib/dinheiro";
import type { LancamentoEntrada, LinhaPrevia } from "@/types/api";
import { useCriarLancamento, useEditarLancamento, useLancamento } from "./hooks";
import {
  interpretarErroDeSalvamento,
  MENSAGEM_PROBLEMA,
  normalizarQuantidade,
  novaLinha,
  passoQuantidade,
  prepararLinhas,
  type LinhaFormulario,
} from "./logica";
import { usePrevia } from "./usePrevia";
import { BarraTotais } from "./BarraTotais";
import styles from "./FormularioLancamento.module.css";

interface ErrosCampo {
  data?: string;
  comanda?: string;
  geral?: string;
}

/** Período do mês de uma data, para voltar à lista no lugar certo. */
function periodoDoMes(iso: string): { inicio: string; fim: string } {
  const [ano, mes] = iso.split("-").map(Number);
  const mm = String(mes).padStart(2, "0");
  return { inicio: `${ano}-${mm}-01`, fim: `${ano}-${mm}-${diasNoMes(ano, mes)}` };
}

export function FormularioLancamento() {
  const { id: lancamentoId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { mostrar } = useToast();
  const editando = !!lancamentoId;

  const [clienteId, setClienteId] = useState(params.get("cliente") ?? "");
  const [data, setData] = useState(hojeSp());
  const [comanda, setComanda] = useState("");
  const [linhas, setLinhas] = useState<LinhaFormulario[]>(() => [novaLinha()]);
  const [incluirInativos, setIncluirInativos] = useState(false);
  const [erros, setErros] = useState<ErrosCampo>({});
  const [itensMarcados, setItensMarcados] = useState<string[]>([]);
  const [tentouSalvar, setTentouSalvar] = useState(false);

  const existente = useLancamento(lancamentoId);
  const { data: clientes } = useClientes(true);
  // Catálogo completo (com inativos): a alternância só filtra a seleção.
  // Assim uma linha antiga com item inativo continua editável (Req 3.9).
  const catalogo = useItens(clienteId, true);
  const criar = useCriarLancamento();
  const editar = useEditarLancamento();

  // Carrega o lançamento existente uma única vez, ao chegar do servidor.
  const carregado = useRef(false);
  useEffect(() => {
    if (!existente.data || carregado.current) return;
    carregado.current = true;
    const l = existente.data;
    setClienteId(l.cliente_id);
    setData(l.data);
    setComanda(l.comanda ?? "");
    setLinhas([
      ...l.linhas.map((linha) => novaLinha(linha.item_id, String(linha.quantidade))),
      novaLinha(),
    ]);
  }, [existente.data]);

  const preparadas = useMemo(() => prepararLinhas(linhas), [linhas]);
  const previa = usePrevia({
    clienteId,
    data,
    linhas: preparadas.linhas,
    lancamentoId,
  });

  const linhaPreviaPorItem = useMemo(() => {
    const mapa = new Map<string, LinhaPrevia>();
    for (const l of previa.resultado?.linhas ?? []) mapa.set(l.item_id, l);
    return mapa;
  }, [previa.resultado]);

  // Itens sem preço: avisados pela prévia (antes de salvar) ou pelo salvamento
  const semPreco = useMemo(
    () => new Set([...(previa.resultado?.itens_sem_preco ?? []), ...itensMarcados]),
    [previa.resultado, itensMarcados],
  );

  const itens = catalogo.data ?? [];
  const clientesSelecionaveis = (clientes ?? []).filter(
    (c) => c.ativo || c.id === clienteId,
  );

  // --- edição das linhas -------------------------------------------------

  function atualizarLinha(chave: string, mudanca: Partial<LinhaFormulario>) {
    setLinhas((atual) => {
      const novas = atual.map((l) => (l.chave === chave ? { ...l, ...mudanca } : l));
      // sempre uma linha em branco no fim: o próximo item já tem onde entrar
      const ultima = novas[novas.length - 1];
      if (ultima && (ultima.item_id || ultima.quantidade)) novas.push(novaLinha());
      return novas;
    });
    setItensMarcados([]);
  }

  function removerLinha(chave: string) {
    setLinhas((atual) => {
      const restantes = atual.filter((l) => l.chave !== chave);
      return restantes.length > 0 ? restantes : [novaLinha()];
    });
  }

  function mudarCliente(novo: string) {
    // itens pertencem ao cliente: trocar de cliente invalida as linhas
    setClienteId(novo);
    setLinhas([novaLinha()]);
    setItensMarcados([]);
    setErros({});
  }

  // --- salvamento --------------------------------------------------------

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setTentouSalvar(true);
    setErros({});

    const novosErros: ErrosCampo = {};
    if (!clienteId) novosErros.geral = "Selecione o cliente.";
    if (!data) novosErros.data = "Informe uma data válida no formato dd/mm/aaaa.";
    if (preparadas.problemas.size > 0) {
      novosErros.geral = "Revise as linhas destacadas antes de salvar.";
    } else if (preparadas.linhas.length === 0) {
      novosErros.geral = "Informe ao menos um item com quantidade.";
    }
    if (Object.keys(novosErros).length > 0) {
      setErros(novosErros);
      return;
    }

    const corpo: LancamentoEntrada = {
      cliente_id: clienteId,
      data,
      comanda: comanda.trim() || null,
      linhas: preparadas.linhas,
    };

    try {
      if (editando && lancamentoId) {
        await editar.mutateAsync({ id: lancamentoId, corpo });
        mostrar("Lançamento atualizado.", "sucesso");
      } else {
        await criar.mutateAsync(corpo);
        mostrar("Lançamento registrado.", "sucesso");
      }
      const { inicio, fim } = periodoDoMes(data);
      navigate(`/lancamentos?cliente=${clienteId}&inicio=${inicio}&fim=${fim}`);
    } catch (erro) {
      const interpretado = interpretarErroDeSalvamento(erro, itens);
      setErros({
        data: interpretado.data,
        comanda: interpretado.comanda,
        geral: interpretado.geral,
      });
      setItensMarcados(interpretado.itensMarcados);
    }
  }

  const salvando = criar.isPending || editar.isPending;
  const urlVoltar = clienteId ? `/lancamentos?cliente=${clienteId}` : "/lancamentos";

  // --- estados de carregamento da edição ---------------------------------

  if (editando && existente.isLoading) {
    return <SkeletonTabela linhas={6} />;
  }

  if (editando && existente.isError) {
    return (
      <div className={styles.pagina}>
        <Link to="/lancamentos" className={styles.voltar}>
          <ArrowLeft size={14} aria-hidden="true" /> Voltar para lançamentos
        </Link>
        <div className={styles.bannerErro} role="alert">
          {existente.error.codigo === "NAO_ENCONTRADO"
            ? "Este lançamento não existe mais. Ele pode ter sido excluído."
            : "Não foi possível carregar o lançamento."}
        </div>
      </div>
    );
  }

  return (
    <form className={styles.pagina} onSubmit={salvar} noValidate>
      <Link to={urlVoltar} className={styles.voltar}>
        <ArrowLeft size={14} aria-hidden="true" /> Voltar para lançamentos
      </Link>
      <h1 style={{ fontSize: 28 }}>{editando ? "Editar lançamento" : "Novo lançamento"}</h1>

      {erros.geral && (
        <div className={styles.bannerErro} role="alert">
          <AlertTriangle size={16} aria-hidden="true" style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{erros.geral}</span>
        </div>
      )}

      {/* Cabeçalho do pedido */}
      <section className={styles.cartao} aria-labelledby="titulo-pedido">
        <h2 id="titulo-pedido" className={styles.cartaoTitulo}>
          Pedido
        </h2>
        <div className={styles.cabecalhoPedido}>
          <Selecao
            rotulo="Cliente"
            id="lancamento-cliente"
            value={clienteId}
            onChange={(e) => mudarCliente(e.target.value)}
            placeholder="Selecione um cliente…"
          >
            {clientesSelecionaveis.map((c) => (
              <option key={c.id} value={c.id}>
                {c.ativo ? c.nome : `${c.nome} (inativo)`}
              </option>
            ))}
          </Selecao>
          <CampoData
            rotulo="Data"
            id="lancamento-data"
            valor={data}
            aoMudar={(iso) => {
              setData(iso);
              setErros((e) => ({ ...e, data: undefined }));
            }}
            erro={erros.data}
          />
          <Campo
            rotulo="Comanda (opcional)"
            id="lancamento-comanda"
            value={comanda}
            onChange={(e) => {
              setComanda(e.target.value);
              setErros((er) => ({ ...er, comanda: undefined }));
            }}
            maxLength={50}
            erro={erros.comanda}
            autoComplete="off"
          />
        </div>
      </section>

      {/* Itens */}
      <section className={styles.cartao} aria-labelledby="titulo-itens">
        <div className={styles.itensTopo}>
          <h2 id="titulo-itens" className={styles.cartaoTitulo} style={{ marginBottom: 0 }}>
            Itens
          </h2>
          <label className={styles.alternanciaInativos}>
            <input
              type="checkbox"
              checked={incluirInativos}
              onChange={(e) => setIncluirInativos(e.target.checked)}
            />
            Incluir itens inativos
          </label>
        </div>

        {!clienteId ? (
          <p className={styles.dicaItens}>Selecione o cliente para escolher os itens do catálogo.</p>
        ) : catalogo.isLoading ? (
          <SkeletonTabela linhas={3} />
        ) : itens.length === 0 ? (
          <p className={styles.dicaItens}>
            Este cliente ainda não tem itens no catálogo. Cadastre os itens em{" "}
            <Link to="/catalogo">Catálogo</Link>.
          </p>
        ) : (
          <>
            <div className={`${styles.grade} ${styles.cabecalhoGrade}`} aria-hidden="true">
              <span>Item</span>
              <span className={styles.direita}>Quantidade</span>
              <span className={styles.direita}>Valor unitário</span>
              <span className={styles.direita}>Total</span>
              <span />
            </div>

            {linhas.map((linha, indice) => {
              const numero = indice + 1;
              const problema = preparadas.problemas.get(linha.chave);
              // incompletude só aparece depois da tentativa de salvar;
              // item repetido aparece na hora
              const mostrarProblema =
                problema && (problema === "duplicado" || tentouSalvar);
              const itemSemPreco = !!linha.item_id && semPreco.has(linha.item_id);
              const linhaPrevia = !problema ? linhaPreviaPorItem.get(linha.item_id) : undefined;
              const opcoes = itens.filter(
                (i) => i.ativo || incluirInativos || i.id === linha.item_id,
              );
              const vazia = !linha.item_id && !linha.quantidade;

              return (
                <div
                  key={linha.chave}
                  className={`${styles.grade} ${styles.linha} ${itemSemPreco ? styles.linhaAlerta : ""}`}
                >
                  <select
                    className={`${styles.campo} ${mostrarProblema && problema === "sem_item" ? styles.campoErro : ""}`}
                    aria-label={`Item da linha ${numero}`}
                    value={linha.item_id}
                    onChange={(e) => atualizarLinha(linha.chave, { item_id: e.target.value })}
                  >
                    <option value="">Selecione o item…</option>
                    {opcoes.map((i) => (
                      <option key={i.id} value={i.id}>
                        {i.ativo ? i.nome : `${i.nome} (inativo)`}
                      </option>
                    ))}
                  </select>

                  <div className={styles.stepper}>
                    <button
                      type="button"
                      className={styles.passo}
                      aria-label={`Diminuir quantidade da linha ${numero}`}
                      onClick={() =>
                        atualizarLinha(linha.chave, {
                          quantidade: passoQuantidade(linha.quantidade, -1),
                        })
                      }
                      tabIndex={-1}
                    >
                      <Minus size={14} />
                    </button>
                    <input
                      className={`${styles.campo} ${mostrarProblema && problema === "sem_quantidade" ? styles.campoErro : ""}`}
                      aria-label={`Quantidade da linha ${numero}`}
                      inputMode="numeric"
                      autoComplete="off"
                      value={linha.quantidade}
                      onChange={(e) =>
                        atualizarLinha(linha.chave, {
                          quantidade: normalizarQuantidade(e.target.value),
                        })
                      }
                      onKeyDown={(e) => {
                        if (e.key === "ArrowUp" || e.key === "ArrowDown") {
                          e.preventDefault();
                          atualizarLinha(linha.chave, {
                            quantidade: passoQuantidade(
                              linha.quantidade,
                              e.key === "ArrowUp" ? 1 : -1,
                            ),
                          });
                        }
                      }}
                    />
                    <button
                      type="button"
                      className={styles.passo}
                      aria-label={`Aumentar quantidade da linha ${numero}`}
                      onClick={() =>
                        atualizarLinha(linha.chave, {
                          quantidade: passoQuantidade(linha.quantidade, 1),
                        })
                      }
                      tabIndex={-1}
                    >
                      <Plus size={14} />
                    </button>
                  </div>

                  <span className={styles.somenteLeitura} aria-label={`Valor unitário da linha ${numero}`}>
                    {itemSemPreco ? (
                      <span className={styles.semPreco}>
                        <AlertTriangle size={12} aria-hidden="true" /> Sem preço
                      </span>
                    ) : linhaPrevia ? (
                      formatarMoeda(linhaPrevia.valor_unitario)
                    ) : (
                      "—"
                    )}
                  </span>

                  <span className={styles.totalLinha} aria-label={`Total da linha ${numero}`}>
                    {linhaPrevia && !itemSemPreco ? formatarMoeda(linhaPrevia.total) : "—"}
                  </span>

                  {vazia ? (
                    <span />
                  ) : (
                    <button
                      type="button"
                      className={styles.remover}
                      onClick={() => removerLinha(linha.chave)}
                      aria-label={`Remover a linha ${numero}`}
                      title="Remover"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}

                  {mostrarProblema && (
                    <span className={styles.mensagemLinha} role="alert">
                      {MENSAGEM_PROBLEMA[problema]}
                    </span>
                  )}
                  {itemSemPreco && !mostrarProblema && (
                    <span
                      className={`${styles.mensagemLinha} ${styles.mensagemLinhaAlerta}`}
                    >
                      Sem preço cadastrado para o mês desta data. Defina o preço em Preços antes
                      de salvar.
                    </span>
                  )}
                </div>
              );
            })}

            <Botao
              type="button"
              variante="fantasma"
              tamanho="sm"
              className={styles.adicionar}
              onClick={() => setLinhas((atual) => [...atual, novaLinha()])}
            >
              <Plus size={14} aria-hidden="true" /> Adicionar item
            </Botao>
          </>
        )}
      </section>

      <BarraTotais
        previa={previa}
        acoes={
          <>
            <Botao
              type="button"
              variante="secundario"
              onClick={() => navigate(urlVoltar)}
              disabled={salvando}
            >
              Cancelar
            </Botao>
            <Botao type="submit" carregando={salvando}>
              Salvar
            </Botao>
          </>
        }
      />
    </form>
  );
}
