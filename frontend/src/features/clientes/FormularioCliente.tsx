/**
 * FormularioCliente — modal para criar ou renomear um cliente.
 * Campo único: nome (obrigatório, max 200 chars).
 */

import { useState, type FormEvent, useEffect } from "react";
import { Modal } from "@/components/Modal";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import { ErroDeApi } from "@/lib/api";
import type { Cliente } from "@/types/api";

interface PropsFormularioCliente {
  aberto: boolean;
  clienteEditando?: Cliente;
  onFechar: () => void;
  onSalvar: (nome: string) => Promise<void>;
}

export function FormularioCliente({
  aberto,
  clienteEditando,
  onFechar,
  onSalvar,
}: PropsFormularioCliente) {
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  // Pré-preenche ao editar
  useEffect(() => {
    if (aberto) {
      setNome(clienteEditando?.nome ?? "");
      setErro("");
    }
  }, [aberto, clienteEditando]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nomeLimpo = nome.trim();
    if (!nomeLimpo) {
      setErro("O nome do cliente é obrigatório.");
      return;
    }

    setCarregando(true);
    setErro("");
    try {
      await onSalvar(nomeLimpo);
      onFechar();
    } catch (err) {
      if (err instanceof ErroDeApi) {
        setErro(err.message);
      } else {
        setErro("Ocorreu um erro inesperado.");
      }
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Modal
      aberto={aberto}
      titulo={clienteEditando ? "Renomear cliente" : "Novo cliente"}
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar} disabled={carregando}>
            Cancelar
          </Botao>
          <Botao
            type="submit"
            form="form-cliente"
            variante="primario"
            carregando={carregando}
          >
            {clienteEditando ? "Salvar" : "Criar cliente"}
          </Botao>
        </>
      }
    >
      <form id="form-cliente" onSubmit={handleSubmit}>
        <Campo
          rotulo="Nome"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          erro={erro}
          maxLength={160}
          autoFocus
          required
        />
      </form>
    </Modal>
  );
}
