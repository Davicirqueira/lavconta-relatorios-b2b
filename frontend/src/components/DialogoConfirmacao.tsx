/**
 * DialogoConfirmacao — modal para ações destrutivas.
 *
 * Identifica o registro ("Excluir o lançamento de Hotel Aurora em 03/09/2026?")
 * para que o operador saiba exatamente o que será removido.
 */

import { Modal } from "./Modal";
import { Botao } from "./Botao";

export interface PropsDialogoConfirmacao {
  aberto: boolean;
  titulo: string;
  descricao: string;
  rotuloBotaoConfirmar?: string;
  carregando?: boolean;
  onConfirmar: () => void;
  onCancelar: () => void;
}

export function DialogoConfirmacao({
  aberto,
  titulo,
  descricao,
  rotuloBotaoConfirmar = "Excluir",
  carregando = false,
  onConfirmar,
  onCancelar,
}: PropsDialogoConfirmacao) {
  return (
    <Modal
      aberto={aberto}
      titulo={titulo}
      onFechar={onCancelar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onCancelar} disabled={carregando}>
            Cancelar
          </Botao>
          <Botao
            variante="destrutivo"
            onClick={onConfirmar}
            carregando={carregando}
          >
            {rotuloBotaoConfirmar}
          </Botao>
        </>
      }
    >
      <p style={{ color: "var(--gelo-700)", lineHeight: 1.6 }}>{descricao}</p>
    </Modal>
  );
}
