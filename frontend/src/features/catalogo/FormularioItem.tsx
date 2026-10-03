/**
 * FormularioItem — criar ou editar um item do catálogo, com o preço por peça
 * (v1.1, Req 3.1, 3.2 e 1.11–1.14).
 *
 * REGRAS REFLETIDAS AQUI (a autoridade é a API)
 *   - Criar: nome e preço obrigatórios. O preço vale a partir de hoje.
 *   - Editar o preço: o operador escolhe "mudar a partir de hoje" ou "corrigir
 *     o preço atual". A escolha só aparece quando faz diferença — se o preço
 *     atual começou hoje, as duas têm o mesmo efeito.
 *   - Antes de gravar uma alteração, a API diz quantos pedidos já registrados
 *     continuam com o valor anterior; havendo algum, o operador confirma.
 *   - O valor digitado vira texto decimal sem passar por Number.
 */

import { useEffect, useState, type FormEvent } from "react";
import { AlertTriangle } from "lucide-react";
import { Modal } from "@/components/Modal";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import { ErroDeApi } from "@/lib/api";
import { paraExibicao } from "@/lib/datas";
import { decimalParaCampo, formatarMoeda, textoParaDecimal } from "@/lib/dinheiro";
import type { Item, ModoDeAlteracao } from "@/types/api";
import { consultarImpacto } from "./hooks";
import styles from "./FormularioItem.module.css";

export interface DadosDoItem {
  nome: string;
  /** Texto decimal ("4.50"); ausente quando o preço não mudou. */
  valorUnitario?: string;
  modo: ModoDeAlteracao;
}

interface PropsFormularioItem {
  aberto: boolean;
  itemEditando?: Item;
  onFechar: () => void;
  onSalvar: (dados: DadosDoItem) => Promise<void>;
}

const AJUDA_PRECO = "O preço vale a partir de hoje e continua valendo até você mudar.";

function plural(n: number, singular: string, varios: string): string {
  return n === 1 ? singular : varios;
}

export function FormularioItem({ aberto, itemEditando, onFechar, onSalvar }: PropsFormularioItem) {
  const [nome, setNome] = useState("");
  const [preco, setPreco] = useState("");
  const [modo, setModo] = useState<ModoDeAlteracao>("a_partir_de_hoje");
  const [erroNome, setErroNome] = useState("");
  const [erroPreco, setErroPreco] = useState("");
  const [erroGeral, setErroGeral] = useState("");
  const [pedidosMantidos, setPedidosMantidos] = useState<number | null>(null);
  const [carregando, setCarregando] = useState(false);

  const atual = itemEditando?.preco_atual ?? null;

  useEffect(() => {
    if (!aberto) return;
    setNome(itemEditando?.nome ?? "");
    setPreco(atual ? decimalParaCampo(atual.valor_unitario) : "");
    setModo("a_partir_de_hoje");
    setErroNome("");
    setErroPreco("");
    setErroGeral("");
    setPedidosMantidos(null);
  }, [aberto, itemEditando, atual]);

  const valorDigitado = textoParaDecimal(preco);
  const precoMudou = !atual || (valorDigitado !== null && valorDigitado !== atual.valor_unitario);
  // a escolha só existe quando há preço atual, ele não começou hoje, e o valor mudou
  const mostrarModos = !!atual && !atual.e_hoje && precoMudou && valorDigitado !== null;
  const modoEfetivo: ModoDeAlteracao = mostrarModos ? modo : "a_partir_de_hoje";
  const aguardandoConfirmacao = pedidosMantidos !== null && pedidosMantidos > 0;

  // qualquer mudança no que será gravado invalida o aviso já mostrado
  function aoMudar<T>(definir: (valor: T) => void) {
    return (valor: T) => {
      definir(valor);
      setPedidosMantidos(null);
      setErroGeral("");
    };
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const nomeLimpo = nome.trim();
    setErroNome(nomeLimpo ? "" : "Informe o nome do item.");
    setErroPreco(
      valorDigitado
        ? ""
        : preco.trim()
          ? "Valor inválido. Use até duas casas decimais, por exemplo 4,50."
          : "Informe o preço por peça.",
    );
    if (!nomeLimpo || !valorDigitado) return;

    setCarregando(true);
    setErroGeral("");
    try {
      // Edição com preço já existente: avisar antes, se algum pedido ficar como está
      if (itemEditando && atual && precoMudou && pedidosMantidos === null) {
        const impacto = await consultarImpacto(itemEditando.id, valorDigitado, modoEfetivo);
        if (impacto.pedidos_com_valor_anterior > 0) {
          setPedidosMantidos(impacto.pedidos_com_valor_anterior);
          return;
        }
      }

      await onSalvar({
        nome: nomeLimpo,
        valorUnitario: precoMudou ? valorDigitado : undefined,
        modo: modoEfetivo,
      });
      onFechar();
    } catch (err) {
      setErroGeral(
        err instanceof ErroDeApi ? err.message : "Não foi possível salvar. Tente novamente.",
      );
    } finally {
      setCarregando(false);
    }
  }

  const titulo = !itemEditando ? "Novo item" : atual ? "Editar item" : "Definir preço";
  const rotuloBotao = !itemEditando
    ? "Criar item"
    : aguardandoConfirmacao
      ? "Confirmar e salvar"
      : "Salvar alterações";

  const dicaPreco = atual
    ? `Hoje: ${formatarMoeda(atual.valor_unitario)} por peça, desde ${paraExibicao(atual.desde)}.`
    : AJUDA_PRECO;

  return (
    <Modal
      aberto={aberto}
      titulo={titulo}
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar} disabled={carregando}>
            Cancelar
          </Botao>
          <Botao type="submit" form="form-item" variante="primario" carregando={carregando}>
            {rotuloBotao}
          </Botao>
        </>
      }
    >
      <form id="form-item" className={styles.formulario} onSubmit={handleSubmit} noValidate>
        <Campo
          rotulo="Nome do item"
          value={nome}
          onChange={(e) => aoMudar(setNome)(e.target.value)}
          erro={erroNome}
          placeholder="Ex.: Lençol, Fronha, Toalha"
          maxLength={120}
          autoComplete="off"
          required
        />

        <Campo
          rotulo="Preço por peça (R$)"
          value={preco}
          onChange={(e) => aoMudar(setPreco)(e.target.value)}
          erro={erroPreco}
          dica={dicaPreco}
          placeholder="Ex.: 4,50"
          inputMode="decimal"
          autoComplete="off"
          required
        />

        {mostrarModos && atual && (
          <fieldset className={styles.modos}>
            <legend className={styles.modosTitulo}>Como aplicar o novo preço</legend>
            <label className={styles.modo}>
              <input
                type="radio"
                name="modo"
                value="a_partir_de_hoje"
                checked={modo === "a_partir_de_hoje"}
                onChange={() => aoMudar(setModo)("a_partir_de_hoje")}
              />
              <span className={styles.modoTexto}>
                <span className={styles.modoNome}>Mudar a partir de hoje</span>
                <span className={styles.modoDescricao}>
                  Pedidos de hoje em diante usam o novo preço. Pedidos anteriores continuam com o
                  preço antigo.
                </span>
              </span>
            </label>
            <label className={styles.modo}>
              <input
                type="radio"
                name="modo"
                value="corrigir_atual"
                checked={modo === "corrigir_atual"}
                onChange={() => aoMudar(setModo)("corrigir_atual")}
              />
              <span className={styles.modoTexto}>
                <span className={styles.modoNome}>Corrigir o preço atual</span>
                <span className={styles.modoDescricao}>
                  Use se o preço foi digitado errado. Vale desde {paraExibicao(atual.desde)}.
                </span>
              </span>
            </label>
          </fieldset>
        )}

        {aguardandoConfirmacao && atual && pedidosMantidos !== null && (
          <div className={styles.aviso} role="alert">
            <AlertTriangle size={16} aria-hidden="true" />
            <span>
              {pedidosMantidos}{" "}
              {plural(pedidosMantidos, "pedido já registrado continua", "pedidos já registrados continuam")}{" "}
              com o valor anterior. Para mudar{" "}
              {plural(pedidosMantidos, "esse pedido, edite-o", "esses pedidos, edite cada um")}.
            </span>
          </div>
        )}

        {erroGeral && (
          <div className={styles.erroGeral} role="alert">
            {erroGeral}
          </div>
        )}
      </form>
    </Modal>
  );
}
