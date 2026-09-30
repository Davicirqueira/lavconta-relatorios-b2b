/**
 * TelaPrecos — definição de preços por cliente e mês.
 *
 * COMPORTAMENTOS ESPECIAIS
 *   - Itens sem preço ficam destacados com fundo amarelo e badge de alerta.
 *     Item sem preço bloqueia lançamento, então o operador precisa saber
 *     antes de tentar (Req 4.10).
 *   - `vigencia_origem` mostra de qual mês o preço foi herdado, dando
 *     transparência à propagação da vigência (design §8.2).
 *   - Ao corrigir mês passado, o FormularioPreco exibe aviso inline.
 *
 * O componente não recalcula nenhum preço — só exibe o que a API retorna.
 */

import { useState } from "react";
import { Pencil, Tag, AlertTriangle } from "lucide-react";
import { Botao } from "@/components/Botao";
import { Selecao } from "@/components/Selecao";
import { SkeletonTabela } from "@/components/Skeleton";
import { EstadoVazio } from "@/components/EstadoVazio";
import { useToast } from "@/components/Toast";
import { formatarMoeda } from "@/lib/dinheiro";
import { hojeSp } from "@/lib/datas";
import { useClientes } from "@/features/clientes/hooks";
import type { ItemComPreco } from "@/types/api";
import { usePrecosDoMes } from "./hooks";
import { FormularioPreco } from "./FormularioPreco";
import styles from "./TelaPrecos.module.css";

/** Gera lista de meses para o seletor: 6 meses passados + corrente + 3 futuros. */
function gerarOpcoesMes(): { valor: string; rotulo: string }[] {
  const hoje = hojeSp();
  const [ano, mes] = hoje.split("-").map(Number);
  const opcoes: { valor: string; rotulo: string }[] = [];

  const MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
  ];

  for (let delta = -6; delta <= 3; delta++) {
    let m = mes - 1 + delta; // 0-based
    let a = ano;
    if (m < 0) { m += 12; a -= 1; }
    if (m > 11) { m -= 12; a += 1; }
    const valor = `${a}-${String(m + 1).padStart(2, "0")}`;
    const rotulo = `${MESES[m]}/${a}`;
    opcoes.push({ valor, rotulo });
  }

  return opcoes;
}

export function TelaPrecos() {
  const mesAtual = hojeSp().slice(0, 7);
  const [clienteId, setClienteId] = useState("");
  const [mes, setMes] = useState(mesAtual);
  const [itemSelecionado, setItemSelecionado] = useState<ItemComPreco | undefined>();
  const [formularioAberto, setFormularioAberto] = useState(false);

  const { data: clientes } = useClientes(false);
  const {
    data: precosDoMes,
    isLoading,
    isError,
    refetch,
  } = usePrecosDoMes(clienteId, mes);

  const { mostrar } = useToast();
  const opcoesMes = gerarOpcoesMes();
  const clienteSelecionado = (clientes ?? []).find((c) => c.id === clienteId);

  const itensSemPreco = (precosDoMes?.itens ?? []).filter((i) => i.sem_preco);
  const temItensSemPreco = itensSemPreco.length > 0;

  function abrirFormulario(item: ItemComPreco) {
    setItemSelecionado(item);
    setFormularioAberto(true);
  }

  function handleSalvo() {
    mostrar("Preço salvo.", "sucesso");
  }

  return (
    <div>
      {/* Cabeçalho */}
      <div className={styles.cabecalho}>
        <h1 className={styles.titulo}>Preços</h1>
        <div className={styles.filtros}>
          <Selecao
            rotulo="Cliente"
            value={clienteId}
            onChange={(e) => setClienteId(e.target.value)}
            placeholder="Selecione um cliente…"
            style={{ minWidth: 240 }}
          >
            {(clientes ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </Selecao>
          <Selecao
            rotulo="Mês"
            value={mes}
            onChange={(e) => setMes(e.target.value)}
            style={{ minWidth: 180 }}
          >
            {opcoesMes.map(({ valor, rotulo }) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </Selecao>
        </div>
      </div>

      {/* Sem cliente selecionado */}
      {!clienteId && (
        <EstadoVazio
          icone={<Tag size={28} />}
          titulo="Selecione um cliente"
          descricao="Selecione o cliente e o mês para ver e editar os preços vigentes."
        />
      )}

      {/* Carregando */}
      {clienteId && isLoading && <SkeletonTabela linhas={5} />}

      {/* Erro */}
      {clienteId && isError && (
        <div className={styles.erroCarregamento}>
          Não foi possível carregar os preços.{" "}
          <Botao variante="fantasma" tamanho="sm" onClick={() => refetch()}>
            Tentar novamente
          </Botao>
        </div>
      )}

      {/* Dados */}
      {clienteId && !isLoading && !isError && precosDoMes && (
        <>
          {/* Aviso: itens sem preço bloqueiam lançamento */}
          {temItensSemPreco && (
            <div className={styles.avisoSemPrecos} role="alert">
              <AlertTriangle size={16} aria-hidden="true" style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                {itensSemPreco.length === 1
                  ? `O item "${itensSemPreco[0].nome}" não tem preço`
                  : `${itensSemPreco.length} itens não têm preço`}{" "}
                para este mês. Itens sem preço bloqueiam o registro de
                lançamentos.
              </span>
            </div>
          )}

          {/* Estado vazio: cliente sem itens */}
          {precosDoMes.itens.length === 0 ? (
            <EstadoVazio
              icone={<Tag size={28} />}
              titulo="Nenhum item no catálogo"
              descricao={`${clienteSelecionado?.nome ?? "Este cliente"} ainda não tem itens cadastrados. Cadastre os itens no Catálogo primeiro.`}
            />
          ) : (
            <div className={styles.tabela}>
              <table
                aria-label={`Preços de ${clienteSelecionado?.nome ?? ""} em ${mes}`}
              >
                <thead>
                  <tr>
                    <Th>Item</Th>
                    <Th>Preço vigente</Th>
                    <Th>Vigência de origem</Th>
                    <Th align="right">Ações</Th>
                  </tr>
                </thead>
                <tbody>
                  {precosDoMes.itens.map((item) => (
                    <tr
                      key={item.item_id}
                      className={
                        item.sem_preco
                          ? `${styles.linha} ${styles.linhaSemPreco}`
                          : styles.linha
                      }
                    >
                      {/* Nome */}
                      <Td>
                        <span
                          style={{ fontWeight: 500, color: "var(--gelo-800)" }}
                        >
                          {item.nome}
                        </span>
                      </Td>

                      {/* Preço */}
                      <Td>
                        {item.sem_preco ? (
                          <span className={styles.semPrecoLabel}>
                            <AlertTriangle size={12} aria-hidden="true" />
                            Sem preço
                          </span>
                        ) : (
                          <span
                            className="num"
                            style={{
                              fontWeight: 500,
                              color: "var(--gelo-800)",
                            }}
                          >
                            {formatarMoeda(item.valor_unitario!)}
                          </span>
                        )}
                      </Td>

                      {/* Vigência de origem */}
                      <Td>
                        {item.vigencia_origem ? (
                          <span className={styles.vigenciaOrigem}>
                            {item.vigencia_origem === mes
                              ? "Definido neste mês"
                              : `Herdado de ${item.vigencia_origem}`}
                          </span>
                        ) : (
                          <span className={styles.vigenciaOrigem}>—</span>
                        )}
                      </Td>

                      {/* Ações */}
                      <Td align="right">
                        <button
                          className={styles.botaoAcao}
                          onClick={() => abrirFormulario(item)}
                          title={
                            item.sem_preco
                              ? "Definir preço"
                              : "Editar preço"
                          }
                          aria-label={
                            item.sem_preco
                              ? `Definir preço para ${item.nome}`
                              : `Editar preço de ${item.nome}`
                          }
                          type="button"
                        >
                          <Pencil size={15} />
                        </button>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <FormularioPreco
        aberto={formularioAberto}
        clienteId={clienteId}
        item={itemSelecionado}
        onFechar={() => setFormularioAberto(false)}
        onSalvo={handleSalvo}
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
