/**
 * TelaCatalogo — catálogo de itens de um cliente, em cartões.
 *
 * O catálogo é sempre por cliente: o operador escolhe o cliente e vê os itens.
 * Sem categoria de item (avaliação B5). Exclusão só de item nunca usado; com
 * histórico, a API devolve EXCLUSAO_COM_HISTORICO e sugerimos inativação.
 */

import { useState } from "react";
import { Pencil, Plus, Power, PowerOff, Shirt, Trash2 } from "lucide-react";
import { Botao } from "@/components/Botao";
import { Selecao } from "@/components/Selecao";
import {
  CartaoAdicionar,
  CartaoGestao,
  GradeCartoes,
} from "@/components/CartaoGestao";
import { Skeleton } from "@/components/Skeleton";
import { EstadoVazio } from "@/components/EstadoVazio";
import { DialogoConfirmacao } from "@/components/DialogoConfirmacao";
import { useToast } from "@/components/Toast";
import { ErroDeApi } from "@/lib/api";
import { useClientes } from "@/features/clientes/hooks";
import type { Item } from "@/types/api";
import {
  useCriarItem,
  useExcluirItem,
  useInativarItem,
  useItens,
  useReativarItem,
  useRenomearItem,
} from "./hooks";
import { FormularioItem } from "./FormularioItem";
import pagina from "@/components/Pagina.module.css";

export function TelaCatalogo() {
  const [clienteId, setClienteId] = useState("");
  const [incluirInativos, setIncluirInativos] = useState(false);
  const [formularioAberto, setFormularioAberto] = useState(false);
  const [itemEditando, setItemEditando] = useState<Item | undefined>();
  const [confirmarExclusao, setConfirmarExclusao] = useState<Item | undefined>();

  const { data: clientes } = useClientes(false);
  const { data: itens, isLoading, isError, refetch } = useItens(clienteId, incluirInativos);
  const criarItem = useCriarItem(clienteId);
  const renomearItem = useRenomearItem();
  const inativarItem = useInativarItem();
  const reativarItem = useReativarItem();
  const excluirItem = useExcluirItem();
  const { mostrar } = useToast();

  const clienteSelecionado = (clientes ?? []).find((c) => c.id === clienteId);
  const lista = itens ?? [];

  async function handleSalvar(nome: string) {
    if (itemEditando) {
      await renomearItem.mutateAsync({ id: itemEditando.id, nome });
      mostrar("Item renomeado.", "sucesso");
    } else {
      await criarItem.mutateAsync(nome);
      mostrar("Item criado.", "sucesso");
    }
  }

  async function handleInativar(item: Item) {
    try {
      await inativarItem.mutateAsync(item.id);
      mostrar(`"${item.nome}" foi inativado.`, "info");
    } catch {
      mostrar("Não foi possível inativar o item.", "erro");
    }
  }

  async function handleReativar(item: Item) {
    try {
      await reativarItem.mutateAsync(item.id);
      mostrar(`"${item.nome}" foi reativado.`, "sucesso");
    } catch {
      mostrar("Não foi possível reativar o item.", "erro");
    }
  }

  async function handleExcluir() {
    if (!confirmarExclusao) return;
    try {
      await excluirItem.mutateAsync(confirmarExclusao.id);
      mostrar(`"${confirmarExclusao.nome}" foi excluído.`, "sucesso");
    } catch (err) {
      if (err instanceof ErroDeApi && err.codigo === "EXCLUSAO_COM_HISTORICO") {
        mostrar("Este item tem histórico de lançamentos. Use a opção Inativar.", "alerta");
      } else {
        mostrar("Não foi possível excluir o item.", "erro");
      }
    } finally {
      setConfirmarExclusao(undefined);
    }
  }

  function abrirNovoItem() {
    setItemEditando(undefined);
    setFormularioAberto(true);
  }

  return (
    <div>
      <div className={pagina.cabecalho}>
        <div>
          <h1 className={pagina.titulo}>Catálogo de itens</h1>
          <p className={pagina.subtitulo}>Tipos de peça que cada cliente envia, cobrados por peça.</p>
        </div>
        {clienteId && (
          <div className={pagina.controles}>
            <label className={pagina.alternancia}>
              <input
                type="checkbox"
                checked={incluirInativos}
                onChange={(e) => setIncluirInativos(e.target.checked)}
              />
              Mostrar inativos
            </label>
            <Botao onClick={abrirNovoItem}>
              <Plus size={16} aria-hidden="true" />
              Novo item
            </Botao>
          </div>
        )}
      </div>

      <div className={pagina.filtros}>
        <Selecao
          rotulo="Cliente"
          className={pagina.filtroCliente}
          value={clienteId}
          onChange={(e) => setClienteId(e.target.value)}
          placeholder="Selecione um cliente…"
        >
          {(clientes ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome}
            </option>
          ))}
        </Selecao>
      </div>

      {!clienteId && (
        <EstadoVazio
          icone={<Shirt size={28} />}
          titulo="Selecione um cliente"
          descricao="O catálogo é específico de cada cliente. Escolha um cliente para ver e gerenciar os itens."
        />
      )}

      {clienteId && isLoading && (
        <GradeCartoes rotulo="Carregando itens">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} role="listitem">
              <Skeleton variante="bloco" />
            </div>
          ))}
        </GradeCartoes>
      )}

      {clienteId && isError && (
        <div className={pagina.bannerErro} role="alert">
          Não foi possível carregar os itens.
          <Botao variante="fantasma" tamanho="sm" onClick={() => refetch()}>
            Tentar novamente
          </Botao>
        </div>
      )}

      {clienteId && !isLoading && !isError && lista.length === 0 && (
        <EstadoVazio
          icone={<Shirt size={28} />}
          titulo="Nenhum item cadastrado"
          descricao={`Cadastre os itens que ${clienteSelecionado?.nome ?? "este cliente"} envia, como lençol, fronha e toalha.`}
          rotuloBotao="Novo item"
          onAcao={abrirNovoItem}
        />
      )}

      {clienteId && !isLoading && !isError && lista.length > 0 && (
        <GradeCartoes rotulo={`Itens de ${clienteSelecionado?.nome ?? "cliente"}`}>
          {lista.map((item, indice) => (
            <CartaoGestao
              key={item.id}
              indice={indice}
              titulo={item.nome}
              ativo={item.ativo}
              marca={<Shirt size={20} />}
              acoes={[
                {
                  rotulo: "Renomear",
                  icone: <Pencil size={14} aria-hidden="true" />,
                  aoClicar: () => {
                    setItemEditando(item);
                    setFormularioAberto(true);
                  },
                },
                item.ativo
                  ? {
                      rotulo: "Inativar",
                      icone: <PowerOff size={14} aria-hidden="true" />,
                      aoClicar: () => handleInativar(item),
                    }
                  : {
                      rotulo: "Reativar",
                      icone: <Power size={14} aria-hidden="true" />,
                      aoClicar: () => handleReativar(item),
                    },
                {
                  rotulo: "Excluir",
                  icone: <Trash2 size={14} aria-hidden="true" />,
                  aoClicar: () => setConfirmarExclusao(item),
                  destrutiva: true,
                },
              ]}
            />
          ))}
          <CartaoAdicionar rotulo="Novo item" aoClicar={abrirNovoItem} />
        </GradeCartoes>
      )}

      <FormularioItem
        aberto={formularioAberto}
        itemEditando={itemEditando}
        onFechar={() => setFormularioAberto(false)}
        onSalvar={handleSalvar}
      />

      <DialogoConfirmacao
        aberto={!!confirmarExclusao}
        titulo="Excluir item"
        descricao={`Tem certeza? Excluir "${confirmarExclusao?.nome}"? Itens já usados em lançamentos não podem ser excluídos; nesse caso, use Inativar.`}
        carregando={excluirItem.isPending}
        onConfirmar={handleExcluir}
        onCancelar={() => setConfirmarExclusao(undefined)}
      />
    </div>
  );
}
