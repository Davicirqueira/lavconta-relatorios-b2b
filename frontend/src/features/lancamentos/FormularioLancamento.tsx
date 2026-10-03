/**
 * FormularioLancamento — novo e edição de lançamento (tarefa 45, revisada).
 *
 * TODOS OS ITENS DO CATÁLOGO À VISTA
 *   Em vez de escolher item linha a linha, o formulário lista o catálogo do
 *   cliente e o operador só informa as quantidades — digitando ou pelo
 *   stepper (avaliação C1). Item sem quantidade não entra no pedido. Como cada
 *   item aparece uma única vez, item repetido é impossível por construção.
 *
 * O QUE O FORMULÁRIO NÃO FAZ
 *   Não calcula preço nem total. O preço por peça exibido vem da API:
 *     - item no pedido → valor da prévia (respeita o congelado na edição);
 *     - item fora do pedido → preço do item na data do pedido (definido no Catálogo).
 *   Totais vêm da prévia; no salvamento o servidor congela de novo e é a
 *   fonte final. O navegador nunca envia valor.
 *
 * ESCOPO: sem notas/observações (avaliação B3); comanda sempre presente e
 * opcional.
 */

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { AlertTriangle, ArrowLeft, Minus, Plus, Shirt } from "lucide-react";
import { Botao } from "@/components/Botao";
import { Campo } from "@/components/Campo";
import { CampoBusca } from "@/components/CampoBusca";
import { CampoData } from "@/components/CampoData";
import { Selecao } from "@/components/Selecao";
import { SkeletonTabela } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";
import { useClientes } from "@/features/clientes/hooks";
import { useItens, usePrecosNaData } from "@/features/catalogo/hooks";
import { diasNoMes, hojeSp } from "@/lib/datas";
import { formatarMoeda } from "@/lib/dinheiro";
import type { LancamentoEntrada, LinhaPrevia } from "@/types/api";
import { useCriarLancamento, useEditarLancamento, useLancamento } from "./hooks";
import {
  interpretarErroDeSalvamento,
  linhasDoPedido,
  normalizarQuantidade,
  passoQuantidade,
  type Quantidades,
} from "./logica";
import { usePrevia } from "./usePrevia";
import { BarraTotais } from "./BarraTotais";
import pagina from "@/components/Pagina.module.css";
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

/** A partir de quantos itens vale oferecer o filtro por nome. */
const MINIMO_PARA_FILTRO = 7;

export function FormularioLancamento() {
  const { id: lancamentoId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { mostrar } = useToast();
  const editando = !!lancamentoId;
  const hoje = hojeSp();

  const [clienteId, setClienteId] = useState(params.get("cliente") ?? "");
  const [data, setData] = useState(hoje);
  const [comanda, setComanda] = useState("");
  const [quantidades, setQuantidades] = useState<Quantidades>({});
  const [incluirInativos, setIncluirInativos] = useState(false);
  const [filtro, setFiltro] = useState("");
  const [erros, setErros] = useState<ErrosCampo>({});
  const [itensMarcados, setItensMarcados] = useState<string[]>([]);
  // itens que o lançamento já tinha: aparecem mesmo se inativos (Req 3.9)
  const [itensDoLancamento, setItensDoLancamento] = useState<Set<string>>(new Set());

  const existente = useLancamento(lancamentoId);
  const { data: clientes } = useClientes(true);
  // Catálogo completo (com inativos): a alternância só filtra o que é exibido
  const catalogo = useItens(clienteId, true);
  // Preço de cada item na data do pedido; com data incompleta, usa hoje
  const dataDosPrecos = /^\d{4}-\d{2}-\d{2}$/.test(data) ? data : hoje;
  const precosNaData = usePrecosNaData(clienteId, dataDosPrecos, true);
  const criar = useCriarLancamento();
  const editar = useEditarLancamento();

  // Carrega o lançamento existente uma única vez, ao chegar do servidor
  const carregado = useRef(false);
  useEffect(() => {
    if (!existente.data || carregado.current) return;
    carregado.current = true;
    const l = existente.data;
    setClienteId(l.cliente_id);
    setData(l.data);
    setComanda(l.comanda ?? "");
    setQuantidades(Object.fromEntries(l.linhas.map((li) => [li.item_id, String(li.quantidade)])));
    setItensDoLancamento(new Set(l.linhas.map((li) => li.item_id)));
  }, [existente.data]);

  const itens = useMemo(() => catalogo.data ?? [], [catalogo.data]);
  const ordemCatalogo = useMemo(() => itens.map((i) => i.id), [itens]);
  const linhas = useMemo(() => linhasDoPedido(quantidades, ordemCatalogo), [quantidades, ordemCatalogo]);
  const previa = usePrevia({ clienteId, data, linhas, lancamentoId });

  const linhaPreviaPorItem = useMemo(() => {
    const mapa = new Map<string, LinhaPrevia>();
    for (const l of previa.resultado?.linhas ?? []) mapa.set(l.item_id, l);
    return mapa;
  }, [previa.resultado]);

  const precoNaDataPorItem = useMemo(
    () => new Map((precosNaData.data?.itens ?? []).map((p) => [p.item_id, p])),
    [precosNaData.data],
  );

  // Sem preço: avisado pela prévia (antes de salvar) ou pela recusa do salvamento
  const semPrecoNoPedido = useMemo(
    () => new Set([...(previa.resultado?.itens_sem_preco ?? []), ...itensMarcados]),
    [previa.resultado, itensMarcados],
  );

  const termo = filtro.trim().toLowerCase();
  const itensExibidos = itens.filter((item) => {
    const relevante =
      item.ativo || incluirInativos || itensDoLancamento.has(item.id) || !!quantidades[item.id];
    return relevante && (!termo || item.nome.toLowerCase().includes(termo));
  });

  const clientesSelecionaveis = (clientes ?? []).filter((c) => c.ativo || c.id === clienteId);

  // --- edição --------------------------------------------------------------

  function mudarQuantidade(itemId: string, valor: string) {
    setQuantidades((atual) => ({ ...atual, [itemId]: valor }));
    setItensMarcados([]);
    setErros((e) => ({ ...e, geral: undefined }));
  }

  function mudarCliente(novo: string) {
    // itens pertencem ao cliente: trocar de cliente zera o pedido
    setClienteId(novo);
    setQuantidades({});
    setItensDoLancamento(new Set());
    setItensMarcados([]);
    setFiltro("");
    setErros({});
  }

  // --- salvamento ----------------------------------------------------------

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErros({});

    const novosErros: ErrosCampo = {};
    if (!clienteId) novosErros.geral = "Selecione o cliente.";
    else if (linhas.length === 0) novosErros.geral = "Informe a quantidade de ao menos um item.";
    if (!data) novosErros.data = "Informe uma data válida.";
    if (Object.keys(novosErros).length > 0) {
      setErros(novosErros);
      return;
    }

    const corpo: LancamentoEntrada = {
      cliente_id: clienteId,
      data,
      comanda: comanda.trim() || null,
      linhas,
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
      setErros({ data: interpretado.data, comanda: interpretado.comanda, geral: interpretado.geral });
      setItensMarcados(interpretado.itensMarcados);
    }
  }

  const salvando = criar.isPending || editar.isPending;
  const urlVoltar = clienteId ? `/lancamentos?cliente=${clienteId}` : "/lancamentos";

  // --- carregamento da edição ----------------------------------------------

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
      <div className={`${pagina.cabecalho} ${styles.cabecalho}`}>
        <div>
          <Link to={urlVoltar} className={styles.voltar}>
            <ArrowLeft size={14} aria-hidden="true" /> Voltar para lançamentos
          </Link>
          <h1 className={pagina.titulo} style={{ marginTop: 12 }}>
            {editando ? "Editar lançamento" : "Novo lançamento"}
          </h1>
          <p className={pagina.subtitulo}>Registre as peças do pedido do dia.</p>
        </div>
      </div>

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
            rotulo="Data do pedido"
            id="lancamento-data"
            valor={data}
            // data futura é recusada pelo servidor; aqui só não é oferecida
            max={hoje}
            aoMudar={(iso) => {
              setData(iso);
              setErros((er) => ({ ...er, data: undefined }));
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
            placeholder="Ex.: 1206"
            maxLength={50}
            erro={erros.comanda}
            autoComplete="off"
          />
        </div>
      </section>

      {/* Itens */}
      <section className={styles.cartao} aria-labelledby="titulo-itens">
        <div className={styles.itensTopo}>
          <h2 id="titulo-itens" className={styles.cartaoTitulo}>
            Peças do pedido
          </h2>
          {clienteId && itens.length > 0 && (
            <div className={styles.itensControles}>
              {itens.length >= MINIMO_PARA_FILTRO && (
                <CampoBusca
                  valor={filtro}
                  aoMudar={setFiltro}
                  rotulo="Filtrar itens"
                  placeholder="Filtrar itens…"
                />
              )}
              <label className={styles.alternanciaInativos}>
                <input
                  type="checkbox"
                  checked={incluirInativos}
                  onChange={(e) => setIncluirInativos(e.target.checked)}
                />
                Incluir itens inativos
              </label>
            </div>
          )}
        </div>

        {!clienteId ? (
          <p className={styles.dicaItens}>Selecione o cliente para listar os itens do catálogo.</p>
        ) : catalogo.isLoading ? (
          <SkeletonTabela linhas={3} />
        ) : itens.length === 0 ? (
          <p className={styles.dicaItens}>
            Este cliente ainda não tem itens no catálogo. Cadastre os itens em{" "}
            <Link to="/catalogo">Catálogo</Link>.
          </p>
        ) : itensExibidos.length === 0 ? (
          <p className={styles.dicaItens}>Nenhum item corresponde ao filtro.</p>
        ) : (
          <ul className={styles.listaItens}>
            {itensExibidos.map((item) => {
              const quantidade = quantidades[item.id] ?? "";
              const noPedido = Number(quantidade) > 0;
              const linhaPrevia = noPedido ? linhaPreviaPorItem.get(item.id) : undefined;
              const precoNaData = precoNaDataPorItem.get(item.id);
              const semPreco = noPedido
                ? semPrecoNoPedido.has(item.id)
                : !!precoNaData?.sem_preco;
              const valorUnitario =
                linhaPrevia?.valor_unitario ?? precoNaData?.valor_unitario ?? null;

              return (
                <li
                  key={item.id}
                  className={[
                    styles.item,
                    noPedido ? styles.itemNoPedido : "",
                    noPedido && semPreco ? styles.itemAlerta : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <span className={styles.itemMarca} aria-hidden="true">
                    <Shirt size={18} />
                  </span>

                  <div className={styles.itemInfo}>
                    <span className={styles.itemNome}>
                      {item.nome}
                      {!item.ativo && " (inativo)"}
                    </span>
                    {semPreco ? (
                      <span className={styles.semPreco}>
                        <AlertTriangle size={12} aria-hidden="true" /> Sem preço
                      </span>
                    ) : (
                      <span className={styles.itemPreco}>
                        {valorUnitario ? `${formatarMoeda(valorUnitario)} / peça` : "—"}
                      </span>
                    )}
                  </div>

                  <span
                    className={[styles.itemTotal, linhaPrevia ? "" : styles.itemTotalVazio]
                      .filter(Boolean)
                      .join(" ")}
                    aria-label={`Total de ${item.nome}`}
                  >
                    {linhaPrevia ? formatarMoeda(linhaPrevia.total) : "—"}
                  </span>

                  <div className={styles.stepper}>
                    <button
                      type="button"
                      className={styles.passo}
                      aria-label={`Diminuir ${item.nome}`}
                      onClick={() => mudarQuantidade(item.id, passoQuantidade(quantidade, -1))}
                      disabled={!noPedido}
                      tabIndex={-1}
                    >
                      <Minus size={14} />
                    </button>
                    <input
                      className={styles.quantidade}
                      aria-label={`Quantidade de ${item.nome}`}
                      inputMode="numeric"
                      autoComplete="off"
                      placeholder="0"
                      value={quantidade}
                      onChange={(e) => mudarQuantidade(item.id, normalizarQuantidade(e.target.value))}
                      onKeyDown={(e) => {
                        if (e.key === "ArrowUp" || e.key === "ArrowDown") {
                          e.preventDefault();
                          mudarQuantidade(
                            item.id,
                            passoQuantidade(quantidade, e.key === "ArrowUp" ? 1 : -1),
                          );
                        }
                      }}
                    />
                    <button
                      type="button"
                      className={styles.passo}
                      aria-label={`Aumentar ${item.nome}`}
                      onClick={() => mudarQuantidade(item.id, passoQuantidade(quantidade, 1))}
                      tabIndex={-1}
                    >
                      <Plus size={14} />
                    </button>
                  </div>

                  {noPedido && semPreco && (
                    <span className={styles.mensagemItem}>
                      Este item ainda não tem preço. Defina o preço no{" "}
                      <Link to="/catalogo">Catálogo</Link> para salvar o pedido.
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
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
              Salvar lançamento
            </Botao>
          </>
        }
      />
    </form>
  );
}
