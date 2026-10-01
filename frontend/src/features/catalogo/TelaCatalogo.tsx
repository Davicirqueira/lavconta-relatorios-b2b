/**
 * TelaCatalogo — gestão do catálogo de itens de um cliente.
 *
 * O catálogo é sempre contextualizado por cliente: o operador seleciona
 * o cliente no topo e a lista atualiza. Sem categoria de item (avaliação B5).
 *
 * Exclusão só se o item nunca foi usado em lançamento; com histórico a API
 * devolve EXCLUSAO_COM_HISTORICO e sugerimos inativação.
 */

import { useState } from "react";
import { Plus, Pencil, PowerOff, Power, Trash2, Shirt } from "lucide-react";
import { Botao } from "@/components/Botao";
import { Selecao } from "@/components/Selecao";
import { Badge } from "@/components/Badge";
import { SkeletonTabela } from "@/components/Skeleton";
import { EstadoVazio } from "@/components/EstadoVazio";
import { DialogoConfirmacao } from "@/components/DialogoConfirmacao";
import { useToast } from "@/components/Toast";
import { ErroDeApi } from "@/lib/api";
import { useClientes } from "@/features/clientes/hooks";
import type { Item } from "@/types/api";
import {
  useItens,
  useCriarItem,
  useRenomearItem,
  useInativarItem,
  useReativarItem,
  useExcluirItem,
} from "./hooks";
import { FormularioItem } from "./FormularioItem";
import styles from "./TelaCatalogo.module.css";

export function TelaCatalogo() {
  const [clienteId, setClienteId] = useState("");
  const [incluirInativos, setIncluirInativos] = useState(false);
  const [formularioAberto, setFormularioAberto] = useState(false);
  const [itemEditando, setItemEditando] = useState<Item | undefined>();
  const [confirmarExclusao, setConfirmarExclusao] = useState<Item | undefined>();

  const { data: clientes } = useClientes(false);

  const {
    data: itens,
    isLoading,
    isError,
    refetch,
  } = useItens(clienteId, incluirInativos);

  const criarItem = useCriarItem(clienteId);
  const renomearItem = useRenomearItem();
  const inativarItem = useInativarItem();
  const reativarItem = useReativarItem();
  const excluirItem = useExcluirItem();
  const { mostrar } = useToast();

  const clienteSelecionado = (clientes ?? []).find((c) => c.id === clienteId);

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
        mostrar(
          "Este item tem histórico de lançamentos. Use a opção Inativar.",
          "alerta",
        );
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
      {/* Cabeçalho */}
      <div className={styles.cabecalho}>
        <h1 className={styles.titulo}>Catálogo de itens</h1>
        <div className={styles.controles}>
          <Selecao
            rotulo="Cliente"
            value={clienteId}
            onChange={(e) => setClienteId(e.target.value)}
            placeholder="Selecione um cliente…"
            style={{ minWidth: 260 }}
          >
            {(clientes ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </Selecao>

          {clienteId && (
            <>
              <label className={styles.switchInativos}>
                <input
                  type="checkbox"
                  checked={incluirInativos}
                  onChange={(e) => setIncluirInativos(e.target.checked)}
                />
                Mostrar inativos
              </label>
              <Botao variante="primario" onClick={abrirNovoItem}>
                <Plus size={16} aria-hidden="true" />
                Novo item
              </Botao>
            </>
          )}
        </div>
      </div>

      {/* Sem cliente selecionado */}
      {!clienteId && (
        <EstadoVazio
          icone={<Shirt size={28} />}
          titulo="Selecione um cliente"
          descricao="O catálogo de itens é específico por cliente. Selecione um cliente para ver ou gerenciar os itens."
        />
      )}

      {/* Carregando */}
      {clienteId && isLoading && <SkeletonTabela linhas={5} />}

      {/* Erro */}
      {clienteId && isError && (
        <div className={styles.erroCarregamento}>
          Não foi possível carregar os itens.{" "}
          <Botao variante="fantasma" tamanho="sm" onClick={() => refetch()}>
            Tentar novamente
          </Botao>
        </div>
      )}

      {/* Sem itens */}
      {clienteId && !isLoading && !isError && (itens ?? []).length === 0 && (
        <EstadoVazio
          icone={<Shirt size={28} />}
          titulo="Nenhum item cadastrado"
          descricao={`Cadastre os itens que ${clienteSelecionado?.nome ?? "este cliente"} envia, como lençol, fronha e toalha. Cada item é cobrado por peça.`}
          rotuloBotao="Novo item"
          onAcao={abrirNovoItem}
        />
      )}

      {/* Tabela */}
      {clienteId && !isLoading && !isError && (itens ?? []).length > 0 && (
        <div className={styles.tabela}>
          <table aria-label={`Itens do catálogo de ${clienteSelecionado?.nome ?? ""}`}>
            <thead>
              <tr>
                <Th>Nome</Th>
                <Th>Situação</Th>
                <Th align="right">Ações</Th>
              </tr>
            </thead>
            <tbody>
              {(itens ?? []).map((item) => (
                <tr key={item.id} className={styles.linha}>
                  <Td>
                    <span
                      style={{
                        fontWeight: 500,
                        color: "var(--gelo-800)",
                        opacity: item.ativo ? 1 : 0.55,
                      }}
                    >
                      {item.nome}
                    </span>
                  </Td>
                  <Td>
                    <Badge tipo={item.ativo ? "sucesso" : "neutro"}>
                      {item.ativo ? "Ativo" : "Inativo"}
                    </Badge>
                  </Td>
                  <Td align="right">
                    <div className={styles.acoes}>
                      <button
                        className={styles.botaoAcao}
                        onClick={() => { setItemEditando(item); setFormularioAberto(true); }}
                        title="Renomear"
                        aria-label={`Renomear ${item.nome}`}
                        type="button"
                      >
                        <Pencil size={15} />
                      </button>
                      {item.ativo ? (
                        <button
                          className={styles.botaoAcao}
                          onClick={() => handleInativar(item)}
                          title="Inativar"
                          aria-label={`Inativar ${item.nome}`}
                          type="button"
                        >
                          <PowerOff size={15} />
                        </button>
                      ) : (
                        <button
                          className={styles.botaoAcao}
                          onClick={() => handleReativar(item)}
                          title="Reativar"
                          aria-label={`Reativar ${item.nome}`}
                          type="button"
                        >
                          <Power size={15} />
                        </button>
                      )}
                      <button
                        className={`${styles.botaoAcao} ${styles.botaoDestrutivo}`}
                        onClick={() => setConfirmarExclusao(item)}
                        title="Excluir"
                        aria-label={`Excluir ${item.nome}`}
                        type="button"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
        descricao={`Tem certeza que deseja excluir "${confirmarExclusao?.nome}"?`}
        rotuloBotaoConfirmar="Excluir"
        carregando={excluirItem.isPending}
        onConfirmar={handleExcluir}
        onCancelar={() => setConfirmarExclusao(undefined)}
      />
    </div>
  );
}

// Auxiliares de célula
function Th({
  children,
  align,
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <th
      scope="col"
      style={{
        padding: "12px 16px",
        textAlign: align ?? "left",
        fontSize: 12,
        fontWeight: 500,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        color: "var(--gelo-600)",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  align,
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <td
      style={{
        padding: "12px 16px",
        textAlign: align ?? "left",
        color: "var(--gelo-700)",
        verticalAlign: "middle",
      }}
    >
      {children}
    </td>
  );
}

import React from "react";
