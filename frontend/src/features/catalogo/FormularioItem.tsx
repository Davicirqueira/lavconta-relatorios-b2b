/**
 * FormularioItem — modal para criar ou renomear um item do catálogo.
 * Campo único: nome (obrigatório).
 */

import { useState, type FormEvent, useEffect } from "react";
import { Modal } from "@/components/Modal";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import { ErroDeApi } from "@/lib/api";
import type { Item } from "@/types/api";

interface PropsFormularioItem {
  aberto: boolean;
  itemEditando?: Item;
  onFechar: () => void;
  onSalvar: (nome: string) => Promise<void>;
}

export function FormularioItem({
  aberto,
  itemEditando,
  onFechar,
  onSalvar,
}: PropsFormularioItem) {
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (aberto) {
      setNome(itemEditando?.nome ?? "");
      setErro("");
    }
  }, [aberto, itemEditando]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nomeLimpo = nome.trim();
    if (!nomeLimpo) {
      setErro("O nome do item é obrigatório.");
      return;
    }
    setCarregando(true);
    setErro("");
    try {
      await onSalvar(nomeLimpo);
      onFechar();
    } catch (err) {
      setErro(err instanceof ErroDeApi ? err.message : "Ocorreu um erro inesperado.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Modal
      aberto={aberto}
      titulo={itemEditando ? "Renomear item" : "Novo item"}
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar} disabled={carregando}>
            Cancelar
          </Botao>
          <Botao
            type="submit"
            form="form-item"
            variante="primario"
            carregando={carregando}
          >
            {itemEditando ? "Salvar" : "Criar item"}
          </Botao>
        </>
      }
    >
      <form id="form-item" onSubmit={handleSubmit}>
        <Campo
          rotulo="Nome do item"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          erro={erro}
          placeholder="Ex.: Lençol, Fronha, Toalha…"
          maxLength={120}
          autoFocus
          required
        />
      </form>
    </Modal>
  );
}
