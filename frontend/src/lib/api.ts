/**
 * Cliente HTTP da API Lavconta.
 *
 * RESPONSABILIDADES
 *   1. Injeta o JWT do Supabase no cabeçalho Authorization.
 *   2. Traduz o envelope de erro { "erro": { codigo, mensagem, detalhes } }
 *      em ErroDeApi, com mensagem em português pronta para exibição.
 *   3. Expõe `requisicaoLenta`: sinal que dispara após 3s sem resposta,
 *      usado pela UI para exibir o PainelServidorAcordando.
 *   4. Suporta AbortSignal para cancelamento (prévia de lançamento).
 *
 * NENHUM cálculo de negócio aqui — só transporte.
 */

import { obterToken } from "./supabase";

const API_URL = import.meta.env.VITE_API_URL as string;

if (!API_URL) {
  throw new Error(
    "Variável VITE_API_URL é obrigatória. " +
      "Defina a URL da API FastAPI no arquivo frontend/.env.",
  );
}

// Duração em ms antes de sinalizar servidor lento (cold start do Render)
const LIMITE_LENTA_MS = 3_000;

/** Erros estruturados retornados pela API. */
export class ErroDeApi extends Error {
  constructor(
    public readonly codigo: string,
    mensagem: string,
    public readonly detalhes?: Record<string, unknown>,
    public readonly status?: number,
  ) {
    super(mensagem);
    this.name = "ErroDeApi";
  }
}

export interface OpcoesFetch extends RequestInit {
  /** Signal de cancelamento (AbortController). */
  signal?: AbortSignal;
  /** Callback chamado quando a requisição passa de 3s sem resposta. */
  aoFicarLenta?: () => void;
}

async function fetchComAuth(
  caminho: string,
  opcoes: OpcoesFetch = {},
): Promise<Response> {
  const { aoFicarLenta, ...initFetch } = opcoes;

  const token = await obterToken();
  const cabecalhos: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(initFetch.headers ?? {}),
  };

  // Timer de cold start: após LIMITE_LENTA_MS chama o callback
  let timerLenta: ReturnType<typeof setTimeout> | undefined;
  if (aoFicarLenta) {
    timerLenta = setTimeout(aoFicarLenta, LIMITE_LENTA_MS);
  }

  try {
    const resposta = await fetch(`${API_URL}${caminho}`, {
      ...initFetch,
      headers: cabecalhos,
    });

    clearTimeout(timerLenta);

    if (!resposta.ok) {
      await tratarErroHttp(resposta);
    }

    return resposta;
  } catch (erro) {
    clearTimeout(timerLenta);
    // Repassa AbortError sem envolver
    if (erro instanceof DOMException && erro.name === "AbortError") {
      throw erro;
    }
    if (erro instanceof ErroDeApi) throw erro;
    throw new ErroDeApi(
      "ERRO_REDE",
      "Não foi possível conectar ao servidor. Verifique sua conexão.",
    );
  }
}

async function tratarErroHttp(resposta: Response): Promise<never> {
  let corpo: unknown;
  try {
    corpo = await resposta.json();
  } catch {
    throw new ErroDeApi(
      "ERRO_INTERNO",
      "O servidor retornou uma resposta inesperada.",
      undefined,
      resposta.status,
    );
  }

  // Envelope padrão: { "erro": { codigo, mensagem, detalhes } }
  if (
    corpo &&
    typeof corpo === "object" &&
    "erro" in corpo &&
    corpo.erro &&
    typeof corpo.erro === "object"
  ) {
    const { codigo, mensagem, detalhes } = corpo.erro as {
      codigo: string;
      mensagem: string;
      detalhes?: Record<string, unknown>;
    };
    throw new ErroDeApi(codigo, mensagem, detalhes, resposta.status);
  }

  throw new ErroDeApi(
    "ERRO_INTERNO",
    "Ocorreu um erro inesperado.",
    undefined,
    resposta.status,
  );
}

// ------------------------------------------------------------------ //
// Métodos convenientes                                                //
// ------------------------------------------------------------------ //

export async function apiGet<T>(
  caminho: string,
  params?: Record<string, string | number | boolean | undefined>,
  opcoes?: OpcoesFetch,
): Promise<T> {
  let url = caminho;
  if (params) {
    const qs = new URLSearchParams();
    for (const [chave, valor] of Object.entries(params)) {
      if (valor !== undefined) qs.set(chave, String(valor));
    }
    const queryString = qs.toString();
    if (queryString) url += `?${queryString}`;
  }
  const resposta = await fetchComAuth(url, { method: "GET", ...opcoes });
  return resposta.json() as Promise<T>;
}

export async function apiPost<T>(
  caminho: string,
  corpo: unknown,
  opcoes?: OpcoesFetch,
): Promise<T> {
  const resposta = await fetchComAuth(caminho, {
    method: "POST",
    body: JSON.stringify(corpo),
    ...opcoes,
  });
  if (resposta.status === 204) return undefined as T;
  return resposta.json() as Promise<T>;
}

export async function apiPut<T>(
  caminho: string,
  corpo: unknown,
  opcoes?: OpcoesFetch,
): Promise<T> {
  const resposta = await fetchComAuth(caminho, {
    method: "PUT",
    body: JSON.stringify(corpo),
    ...opcoes,
  });
  return resposta.json() as Promise<T>;
}

export async function apiPatch<T>(
  caminho: string,
  corpo: unknown,
  opcoes?: OpcoesFetch,
): Promise<T> {
  const resposta = await fetchComAuth(caminho, {
    method: "PATCH",
    body: JSON.stringify(corpo),
    ...opcoes,
  });
  return resposta.json() as Promise<T>;
}

export async function apiDelete(
  caminho: string,
  opcoes?: OpcoesFetch,
): Promise<void> {
  await fetchComAuth(caminho, { method: "DELETE", ...opcoes });
}

/**
 * Download de arquivo binário (PDF ou Excel).
 * Retorna um Blob pronto para salvar no navegador.
 */
export async function apiDownload(
  caminho: string,
  params?: Record<string, string | number | boolean | undefined>,
  opcoes?: OpcoesFetch,
): Promise<{ blob: Blob; nomeArquivo: string }> {
  let url = caminho;
  if (params) {
    const qs = new URLSearchParams();
    for (const [chave, valor] of Object.entries(params)) {
      if (valor !== undefined) qs.set(chave, String(valor));
    }
    const queryString = qs.toString();
    if (queryString) url += `?${queryString}`;
  }

  const resposta = await fetchComAuth(url, { method: "GET", ...opcoes });
  const blob = await resposta.blob();

  // Extrai o nome do arquivo do header Content-Disposition
  const disposition = resposta.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";\n]+)"?/i);
  const nomeArquivo = match?.[1] ?? "arquivo";

  return { blob, nomeArquivo };
}
