/**
 * TelaClientes — gestão de clientes-empresa, em cartões.
 *
 * Estados obrigatórios (regras-interface.md): carregando, vazio, com dados e
 * erro. Cartão com iniciais, situação e ações (avaliação, Parte A item 6);
 * sem endereço, volume ou último pedido (avaliação B7 e escopo).
 *
 * Exclusão só sem lançamentos; com histórico, a API devolve
 * EXCLUSAO_COM_HISTORICO e a tela sugere inativação.
 */

import { useState } from "react";
import { Building2, Pencil, Plus, Power, PowerOff, Trash2 } from "lucide-react";
import { Botao } from "@/components/Botao";
import { CampoBusca } from "@/components/CampoBusca";
import { CartaoGestao, GradeCartoes, iniciais } from "@/components/CartaoGestao";
import { Skeleton } from "@/components/Skeleton";
import { EstadoVazio } from "@/components/EstadoVazio";
import { DialogoConfirmacao } from "@/components/DialogoConfirmacao";
import { useToast } from "@/components/Toast";
import { ErroDeApi } from "@/lib/api";
import type { Cliente } from "@/types/api";
import {
  useClientes,
  useCriarCliente,
  useExcluirCliente,
  useInativarCliente,
  useReativarCliente,
  useRenomearCliente,
} from "./hooks";
import { FormularioCliente } from "./FormularioCliente";
import pagina from "@/components/Pagina.module.css";

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

  const termo = busca.trim().toLowerCase();
  const filtrados = (clientes ?? []).filter((c) => c.nome.toLowerCase().includes(termo));

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
      if (err instanceof ErroDeApi && err.codigo === "EXCLUSAO_COM_HISTORICO") {
        mostrar("Este cliente tem lançamentos. Use a opção Inativar para desativá-lo.", "alerta");
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

  return (
    <div>
      <div className={pagina.cabecalho}>
        <div>
          <h1 className={pagina.titulo}>Clientes</h1>
          <p className={pagina.subtitulo}>Empresas atendidas pela lavanderia.</p>
        </div>
        <div className={pagina.controles}>
          <CampoBusca
            valor={busca}
            aoMudar={setBusca}
            rotulo="Buscar cliente"
            placeholder="Buscar cliente…"
          />
          <label className={pagina.alternancia}>
            <input
              type="checkbox"
              checked={incluirInativos}
              onChange={(e) => setIncluirInativos(e.target.checked)}
            />
            Mostrar inativos
          </label>
          <Botao onClick={abrirNovoCliente}>
            <Plus size={16} aria-hidden="true" />
            Novo cliente
          </Botao>
        </div>
      </div>

      {isLoading && (
        <GradeCartoes rotulo="Carregando clientes">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} role="listitem">
              <Skeleton variante="bloco" />
            </div>
          ))}
        </GradeCartoes>
      )}

      {isError && (
        <div className={pagina.bannerErro} role="alert">
          Não foi possível carregar os clientes.
          <Botao variante="fantasma" tamanho="sm" onClick={() => refetch()}>
            Tentar novamente
          </Botao>
        </div>
      )}

      {!isLoading && !isError && filtrados.length === 0 && (
        <EstadoVazio
          icone={<Building2 size={28} />}
          titulo={termo ? "Nenhum cliente encontrado" : "Nenhum cliente cadastrado"}
          descricao={
            termo
              ? "Tente outro termo de busca."
              : "Comece cadastrando a primeira empresa atendida."
          }
          rotuloBotao={termo ? undefined : "Novo cliente"}
          onAcao={termo ? undefined : abrirNovoCliente}
        />
      )}

      {!isLoading && !isError && filtrados.length > 0 && (
        <GradeCartoes rotulo="Clientes">
          {filtrados.map((cliente, indice) => (
            <CartaoGestao
              key={cliente.id}
              indice={indice}
              titulo={cliente.nome}
              ativo={cliente.ativo}
              marca={iniciais(cliente.nome)}
              acoes={[
                {
                  rotulo: "Renomear",
                  icone: <Pencil size={14} aria-hidden="true" />,
                  aoClicar: () => abrirEdicao(cliente),
                },
                cliente.ativo
                  ? {
                      rotulo: "Inativar",
                      icone: <PowerOff size={14} aria-hidden="true" />,
                      aoClicar: () => handleInativar(cliente),
                    }
                  : {
                      rotulo: "Reativar",
                      icone: <Power size={14} aria-hidden="true" />,
                      aoClicar: () => handleReativar(cliente),
                    },
                {
                  rotulo: "Excluir",
                  icone: <Trash2 size={14} aria-hidden="true" />,
                  aoClicar: () => setConfirmarExclusao(cliente),
                  destrutiva: true,
                },
              ]}
            />
          ))}
        </GradeCartoes>
      )}

      <FormularioCliente
        aberto={formularioAberto}
        clienteEditando={clienteEditando}
        onFechar={() => setFormularioAberto(false)}
        onSalvar={handleSalvar}
      />

      <DialogoConfirmacao
        aberto={!!confirmarExclusao}
        titulo="Excluir cliente"
        descricao={`Tem certeza? Excluir "${confirmarExclusao?.nome}"? Clientes com lançamentos não podem ser excluídos; nesse caso, use Inativar.`}
        carregando={excluirCliente.isPending}
        onConfirmar={handleExcluir}
        onCancelar={() => setConfirmarExclusao(undefined)}
      />
    </div>
  );
}
