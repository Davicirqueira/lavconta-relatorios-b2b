/**
 * TelaClientes — gestão de clientes-empresa.
 *
 * Estados obrigatórios (regras-interface.md):
 *   1. Carregando  — Skeleton
 *   2. Vazio       — EstadoVazio orientando a criar o primeiro cliente
 *   3. Com dados   — tabela com busca e alternância de inativos
 *   4. Erro        — banner com opção de tentar novamente
 *
 * Exclusão só é permitida sem lançamentos; com histórico, a API devolve
 * EXCLUSAO_COM_HISTORICO e a tela sugere inativação.
 */

import { useState } from "react";
import { Plus, Pencil, PowerOff, Power, Trash2, Building2 } from "lucide-react";
import { Botao } from "@/components/Botao";
import { Badge } from "@/components/Badge";
import { SkeletonTabela } from "@/components/Skeleton";
import { EstadoVazio } from "@/components/EstadoVazio";
import { DialogoConfirmacao } from "@/components/DialogoConfirmacao";
import { useToast } from "@/components/Toast";
import { ErroDeApi } from "@/lib/api";
import type { Cliente } from "@/types/api";
import {
  useClientes,
  useCriarCliente,
  useRenomearCliente,
  useInativarCliente,
  useReativarCliente,
  useExcluirCliente,
} from "./hooks";
import { FormularioCliente } from "./FormularioCliente";
import styles from "./TelaClientes.module.css";

export function TelaClientes() {
  const [incluirInativos, setIncluirInativos] = useState(false);
  const [busca, setBusca] = useState("");
  const [formularioAberto, setFormularioAberto] = useState(false);
  const [clienteEditando, setClienteEditando] = useState<Cliente | undefined>();
  const [confirmarExclusao, setConfirmarExclusao] = useState<Cliente | undefined>();

  const { data: clientes, isLoading, isError, refetch } = useClientes(incluirInativos);
  const criarCliente = useCriarCliente();
  const renomearCliente = useRenomearCliente();
  const inativarCliente = useInativarCliente();
  const reativarCliente = useReativarCliente();
  const excluirCliente = useExcluirCliente();
  const { mostrar } = useToast();

  // Filtro de busca por nome (client-side, sobre dados já carregados)
  const clientesFiltrados = (clientes ?? []).filter((c) =>
    c.nome.toLowerCase().includes(busca.toLowerCase()),
  );

  async function handleSalvar(nome: string) {
    if (clienteEditando) {
      await renomearCliente.mutateAsync({ id: clienteEditando.id, nome });
      mostrar("Cliente renomeado.", "sucesso");
    } else {
      await criarCliente.mutateAsync(nome);
      mostrar("Cliente criado.", "sucesso");
    }
  }

  async function handleInativar(cliente: Cliente) {
    try {
      await inativarCliente.mutateAsync(cliente.id);
      mostrar(`${cliente.nome} foi inativado.`, "info");
    } catch {
      mostrar("Não foi possível inativar o cliente.", "erro");
    }
  }

  async function handleReativar(cliente: Cliente) {
    try {
      await reativarCliente.mutateAsync(cliente.id);
      mostrar(`${cliente.nome} foi reativado.`, "sucesso");
    } catch {
      mostrar("Não foi possível reativar o cliente.", "erro");
    }
  }

  async function handleExcluir() {
    if (!confirmarExclusao) return;
    try {
      await excluirCliente.mutateAsync(confirmarExclusao.id);
      mostrar(`${confirmarExclusao.nome} foi excluído.`, "sucesso");
    } catch (err) {
      if (
        err instanceof ErroDeApi &&
        err.codigo === "EXCLUSAO_COM_HISTORICO"
      ) {
        mostrar(
          "Este cliente tem lançamentos. Use a opção Inativar para desativá-lo.",
          "alerta",
        );
      } else {
        mostrar("Não foi possível excluir o cliente.", "erro");
      }
    } finally {
      setConfirmarExclusao(undefined);
    }
  }

  function abrirNovoCliente() {
    setClienteEditando(undefined);
    setFormularioAberto(true);
  }

  function abrirEdicao(cliente: Cliente) {
    setClienteEditando(cliente);
    setFormularioAberto(true);
  }

  // --- Estados de carregamento e erro ---

  if (isLoading) {
    return (
      <div>
        <div className={styles.cabecalho}>
          <h1 className={styles.titulo}>Clientes</h1>
        </div>
        <SkeletonTabela linhas={6} />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <div className={styles.cabecalho}>
          <h1 className={styles.titulo}>Clientes</h1>
        </div>
        <div className={styles.erroCarregamento}>
          Não foi possível carregar os clientes.{" "}
          <Botao variante="fantasma" tamanho="sm" onClick={() => refetch()}>
            Tentar novamente
          </Botao>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Cabeçalho */}
      <div className={styles.cabecalho}>
        <h1 className={styles.titulo}>Clientes</h1>
        <div className={styles.controles}>
          <input
            type="search"
            placeholder="Buscar cliente…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className={styles.busca}
            aria-label="Buscar cliente"
          />
          <label className={styles.switchInativos}>
            <input
              type="checkbox"
              checked={incluirInativos}
              onChange={(e) => setIncluirInativos(e.target.checked)}
            />
            Mostrar inativos
          </label>
          <Botao variante="primario" onClick={abrirNovoCliente}>
            <Plus size={16} aria-hidden="true" />
            Novo cliente
          </Botao>
        </div>
      </div>

      {/* Estado vazio */}
      {clientesFiltrados.length === 0 ? (
        <EstadoVazio
          icone={<Building2 size={28} />}
          titulo={busca ? "Nenhum cliente encontrado" : "Nenhum cliente cadastrado"}
          descricao={
            busca
              ? "Tente outro termo de busca."
              : "Comece cadastrando o primeiro cliente-empresa."
          }
          rotuloBotao={busca ? undefined : "Novo cliente"}
          onAcao={busca ? undefined : abrirNovoCliente}
        />
      ) : (
        /* Tabela */
        <div
          style={{
            background: "var(--branco)",
            border: "1px solid var(--gelo-200)",
            borderRadius: "var(--raio-lg)",
            boxShadow: "var(--sombra-1)",
            overflow: "hidden",
          }}
        >
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}
            aria-label="Lista de clientes"
          >
            <thead>
              <tr
                style={{
                  background: "var(--gelo-100)",
                  borderBottom: "1px solid var(--gelo-200)",
                }}
              >
                <Th>Nome</Th>
                <Th>Situação</Th>
                <Th align="right">Ações</Th>
              </tr>
            </thead>
            <tbody>
              {clientesFiltrados.map((cliente) => (
                <tr
                  key={cliente.id}
                  style={{
                    borderBottom: "1px solid var(--gelo-200)",
                    transition: "background-color 120ms",
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.backgroundColor = "var(--azul-50)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.backgroundColor = "")
                  }
                >
                  <Td>
                    <span
                      style={{
                        fontWeight: 500,
                        color: "var(--gelo-800)",
                        opacity: cliente.ativo ? 1 : 0.55,
                      }}
                    >
                      {cliente.nome}
                    </span>
                  </Td>
                  <Td>
                    <Badge tipo={cliente.ativo ? "sucesso" : "neutro"}>
                      {cliente.ativo ? "Ativo" : "Inativo"}
                    </Badge>
                  </Td>
                  <Td align="right">
                    <div className={styles.acoes}>
                      <button
                        className={styles.botaoAcao}
                        onClick={() => abrirEdicao(cliente)}
                        title="Renomear"
                        aria-label={`Renomear ${cliente.nome}`}
                        type="button"
                      >
                        <Pencil size={15} />
                      </button>
                      {cliente.ativo ? (
                        <button
                          className={styles.botaoAcao}
                          onClick={() => handleInativar(cliente)}
                          title="Inativar"
                          aria-label={`Inativar ${cliente.nome}`}
                          type="button"
                        >
                          <PowerOff size={15} />
                        </button>
                      ) : (
                        <button
                          className={styles.botaoAcao}
                          onClick={() => handleReativar(cliente)}
                          title="Reativar"
                          aria-label={`Reativar ${cliente.nome}`}
                          type="button"
                        >
                          <Power size={15} />
                        </button>
                      )}
                      <button
                        className={`${styles.botaoAcao} ${styles.botaoAcaoDestrutivo}`}
                        onClick={() => setConfirmarExclusao(cliente)}
                        title="Excluir"
                        aria-label={`Excluir ${cliente.nome}`}
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

      {/* Modal de formulário */}
      <FormularioCliente
        aberto={formularioAberto}
        clienteEditando={clienteEditando}
        onFechar={() => setFormularioAberto(false)}
        onSalvar={handleSalvar}
      />

      {/* Diálogo de confirmação de exclusão */}
      <DialogoConfirmacao
        aberto={!!confirmarExclusao}
        titulo="Excluir cliente"
        descricao={`Tem certeza que deseja excluir "${confirmarExclusao?.nome}"? Esta ação não pode ser desfeita.`}
        rotuloBotaoConfirmar="Excluir"
        carregando={excluirCliente.isPending}
        onConfirmar={handleExcluir}
        onCancelar={() => setConfirmarExclusao(undefined)}
      />
    </div>
  );
}

// Auxiliares de célula de tabela para evitar repetição de estilo
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

// Importação necessária para o auxiliar Th/Td inline
import React from "react";
