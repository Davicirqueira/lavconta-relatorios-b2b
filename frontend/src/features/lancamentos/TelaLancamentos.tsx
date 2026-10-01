/**
 * TelaLancamentos — lista de lançamentos de um cliente num período (tarefa 44).
 *
 * A API exige cliente e período para listar, então a tela começa pedindo o
 * cliente. Os filtros ficam na URL: ao voltar do formulário, o operador
 * reencontra a mesma lista em vez de refazer a seleção.
 *
 * Os totais de cada linha vêm prontos da API — a tela não soma nada.
 */

import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { ClipboardList, Pencil, Plus, Trash2 } from "lucide-react";
import { Botao } from "@/components/Botao";
import { Selecao } from "@/components/Selecao";
import { CampoData } from "@/components/CampoData";
import { SkeletonTabela } from "@/components/Skeleton";
import { EstadoVazio } from "@/components/EstadoVazio";
import { DialogoConfirmacao } from "@/components/DialogoConfirmacao";
import { useToast } from "@/components/Toast";
import { useClientes } from "@/features/clientes/hooks";
import { rotuloCliente } from "@/features/clientes/rotulos";
import { paraExibicao, primeiroDiaDoMesAtual, ultimoDiaDoMesAtual } from "@/lib/datas";
import { formatarInteiro, formatarMoeda } from "@/lib/dinheiro";
import type { LancamentoResumo } from "@/types/api";
import { useExcluirLancamento, useLancamentos } from "./hooks";
import pagina from "@/components/Pagina.module.css";
import tabela from "@/components/TabelaDados.module.css";

export function TelaLancamentos() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { mostrar } = useToast();

  const clienteId = params.get("cliente") ?? "";
  const [inicio, setInicio] = useState(params.get("inicio") ?? primeiroDiaDoMesAtual());
  const [fim, setFim] = useState(params.get("fim") ?? ultimoDiaDoMesAtual());
  const [paraExcluir, setParaExcluir] = useState<LancamentoResumo | undefined>();

  // Lista e relatório consultam também clientes inativos (Req 2.8)
  const { data: clientes } = useClientes(true);
  const cliente = clientes?.find((c) => c.id === clienteId);

  const periodoInvertido = !!inicio && !!fim && inicio > fim;
  const consulta = useLancamentos(clienteId, inicio, fim);
  const excluir = useExcluirLancamento();

  function atualizarFiltro(chave: string, valor: string) {
    const novos = new URLSearchParams(params);
    if (valor) novos.set(chave, valor);
    else novos.delete(chave);
    setParams(novos, { replace: true });
  }

  function mudarInicio(iso: string) {
    setInicio(iso);
    atualizarFiltro("inicio", iso);
  }

  function mudarFim(iso: string) {
    setFim(iso);
    atualizarFiltro("fim", iso);
  }

  async function confirmarExclusao() {
    if (!paraExcluir) return;
    try {
      await excluir.mutateAsync(paraExcluir.id);
      mostrar("Lançamento excluído.", "sucesso");
    } catch {
      mostrar("Não foi possível excluir o lançamento. Tente novamente.", "erro");
    } finally {
      setParaExcluir(undefined);
    }
  }

  function novoLancamento() {
    navigate(clienteId ? `/lancamentos/novo?cliente=${clienteId}` : "/lancamentos/novo");
  }

  const lancamentos = consulta.data ?? [];

  return (
    <div>
      <div className={pagina.cabecalho}>
        <h1 className={pagina.titulo}>Lançamentos</h1>
        <Botao onClick={novoLancamento}>
          <Plus size={16} aria-hidden="true" />
          Novo lançamento
        </Botao>
      </div>

      <div className={pagina.filtros}>
        <Selecao
          rotulo="Cliente"
          className={pagina.filtroCliente}
          value={clienteId}
          onChange={(e) => atualizarFiltro("cliente", e.target.value)}
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
          id="filtro-inicio"
          className={pagina.filtroData}
          valor={inicio}
          aoMudar={mudarInicio}
        />
        <CampoData
          rotulo="Data final"
          id="filtro-fim"
          className={pagina.filtroData}
          valor={fim}
          aoMudar={mudarFim}
          erro={periodoInvertido ? "A data inicial não pode ser posterior à data final." : undefined}
        />
      </div>

      {!clienteId && (
        <EstadoVazio
          icone={<ClipboardList size={28} />}
          titulo="Selecione um cliente"
          descricao="Escolha o cliente e o período para ver os lançamentos registrados."
        />
      )}

      {clienteId && (!inicio || !fim) && !periodoInvertido && (
        <div className={pagina.bannerAlerta} role="status">
          Informe as datas inicial e final no formato dd/mm/aaaa.
        </div>
      )}

      {clienteId && consulta.isLoading && <SkeletonTabela linhas={6} />}

      {clienteId && consulta.isError && (
        <div className={pagina.bannerErro} role="alert">
          {consulta.error.message || "Não foi possível carregar os lançamentos."}
          <Botao variante="fantasma" tamanho="sm" onClick={() => consulta.refetch()}>
            Tentar novamente
          </Botao>
        </div>
      )}

      {clienteId && consulta.isSuccess && lancamentos.length === 0 && (
        <EstadoVazio
          icone={<ClipboardList size={28} />}
          titulo="Nenhum lançamento no período"
          descricao={`Não há lançamentos de ${cliente?.nome ?? "este cliente"} entre ${paraExibicao(inicio)} e ${paraExibicao(fim)}.`}
          rotuloBotao="Novo lançamento"
          onAcao={novoLancamento}
        />
      )}

      {clienteId && consulta.isSuccess && lancamentos.length > 0 && (
        <div className={tabela.container}>
          <div className={tabela.rolagem}>
            <table className={tabela.tabela} aria-label={`Lançamentos de ${cliente?.nome ?? ""}`}>
              <thead>
                <tr>
                  <th scope="col">Data</th>
                  <th scope="col">Cliente</th>
                  <th scope="col">Comanda</th>
                  <th scope="col" className={tabela.direita}>
                    Total de peças
                  </th>
                  <th scope="col" className={tabela.direita}>
                    Total R$
                  </th>
                  <th scope="col" className={tabela.direita}>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lancamentos.map((l) => (
                  <tr key={l.id}>
                    <td className="num">{paraExibicao(l.data)}</td>
                    <td>{cliente?.nome}</td>
                    <td>{l.comanda ?? <span className={tabela.vazio}>—</span>}</td>
                    <td className={tabela.direita}>{formatarInteiro(l.total_pecas)}</td>
                    <td className={`${tabela.direita} ${tabela.valor}`}>
                      {formatarMoeda(l.total_valor)}
                    </td>
                    <td>
                      <div className={tabela.acoes}>
                        <button
                          type="button"
                          className={tabela.botaoAcao}
                          onClick={() => navigate(`/lancamentos/${l.id}/editar`)}
                          aria-label={`Editar o lançamento de ${paraExibicao(l.data)}`}
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          type="button"
                          className={`${tabela.botaoAcao} ${tabela.botaoAcaoDestrutivo}`}
                          onClick={() => setParaExcluir(l)}
                          aria-label={`Excluir o lançamento de ${paraExibicao(l.data)}`}
                          title="Excluir"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <DialogoConfirmacao
        aberto={!!paraExcluir}
        titulo="Excluir lançamento"
        descricao={
          paraExcluir
            ? `Tem certeza? Excluir o lançamento de ${cliente?.nome ?? "este cliente"} em ${paraExibicao(paraExcluir.data)}? O registro deixa de compor os relatórios do período.`
            : ""
        }
        carregando={excluir.isPending}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setParaExcluir(undefined)}
      />
    </div>
  );
}
