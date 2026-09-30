/**
 * FormularioPreco — modal para definir ou corrigir o preço de um item.
 *
 * REGRAS DE NEGÓCIO REFLETIDAS AQUI
 *   - Mês padrão vem da API (vigencia_sugerida): primeiro preço → mês corrente;
 *     alteração → mês seguinte (Req 4.15 e 4.16).
 *   - Aviso ao salvar mês passado: "Lançamentos já registrados não mudam."
 *   - Valor com no máximo duas casas decimais; maior que zero.
 *   - O campo mês aceita YYYY-MM (formato do contrato da API).
 */

import { useState, type FormEvent, useEffect } from "react";
import { Modal } from "@/components/Modal";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import { ErroDeApi } from "@/lib/api";
import { hojeSp } from "@/lib/datas";
import type { ItemComPreco } from "@/types/api";
import { useVigenciaSugerida, useDefinirPreco } from "./hooks";

interface PropsFormularioPreco {
  aberto: boolean;
  clienteId: string;
  item: ItemComPreco | undefined;
  onFechar: () => void;
  onSalvo: () => void;
}

export function FormularioPreco({
  aberto,
  clienteId,
  item,
  onFechar,
  onSalvo,
}: PropsFormularioPreco) {
  const [valor, setValor] = useState("");
  const [mes, setMes] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  const { data: vigencia } = useVigenciaSugerida(
    clienteId,
    aberto && item ? item.item_id : "",
  );
  const definirPreco = useDefinirPreco();

  // Ao abrir: pré-preenche com valor vigente e mês sugerido
  useEffect(() => {
    if (!aberto) return;
    setErro("");
    setValor(item?.valor_unitario ?? "");
    setMes(vigencia?.vigencia_mes ?? hojeSp().slice(0, 7));
  }, [aberto, item, vigencia]);

  // Mês passado? → aviso (não bloqueia)
  const mesSelecionado = mes; // "YYYY-MM"
  const mesAtual = hojeSp().slice(0, 7);
  const eMesPassado = mesSelecionado < mesAtual;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const valorLimpo = valor.replace(",", ".").trim();
    if (!valorLimpo || isNaN(Number(valorLimpo)) || Number(valorLimpo) <= 0) {
      setErro("Informe um valor maior que zero.");
      return;
    }
    if (!/^\d{4}-\d{2}$/.test(mes)) {
      setErro("Mês inválido. Use o formato AAAA-MM.");
      return;
    }
    if (!item) return;

    setCarregando(true);
    setErro("");
    try {
      await definirPreco.mutateAsync({
        clienteId,
        item_id: item.item_id,
        vigencia_mes: mes,
        valor_unitario: Number(valorLimpo).toFixed(2),
      });
      onSalvo();
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
      titulo={`Definir preço — ${item?.nome ?? ""}`}
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar} disabled={carregando}>
            Cancelar
          </Botao>
          <Botao
            type="submit"
            form="form-preco"
            variante="primario"
            carregando={carregando}
          >
            Salvar preço
          </Botao>
        </>
      }
    >
      <form
        id="form-preco"
        onSubmit={handleSubmit}
        style={{ display: "flex", flexDirection: "column", gap: 16 }}
      >
        {/* Aviso de mês passado */}
        {eMesPassado && (
          <div
            role="note"
            style={{
              padding: "10px 14px",
              background: "var(--alerta-suave)",
              border: "1px solid var(--alerta-borda)",
              borderRadius: "var(--raio-md)",
              color: "var(--alerta-forte)",
              fontSize: 13,
              lineHeight: 1.5,
            }}
          >
            Você está corrigindo um mês passado. Lançamentos já registrados
            permanecem com o valor congelado e não serão alterados.
          </div>
        )}

        <Campo
          rotulo="Mês de vigência (AAAA-MM)"
          value={mes}
          onChange={(e) => setMes(e.target.value)}
          placeholder="2026-09"
          maxLength={7}
          dica={
            vigencia?.e_primeiro_preco
              ? "Primeiro preço: sugerimos o mês corrente para lançar hoje."
              : "Alteração: vigência sugerida no mês seguinte."
          }
          required
        />

        <Campo
          rotulo="Valor unitário (R$)"
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          placeholder="4.50"
          inputMode="decimal"
          erro={erro}
          required
          autoFocus
        />
      </form>
    </Modal>
  );
}
