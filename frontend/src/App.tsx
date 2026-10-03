import { Routes, Route, Navigate } from "react-router";

import { RotaProtegida } from "@/features/auth/RotaProtegida";
import { PaginaLogin } from "@/pages/Login";
import { PaginaEsqueciSenha } from "@/pages/EsqueciSenha";
import { PaginaRedefinirSenha } from "@/pages/RedefinirSenha";
import { Layout } from "@/components/Layout";
import { PaginaLancamentoForm, PaginaLancamentos } from "@/pages/Lancamentos";
import { PaginaRelatorio } from "@/pages/Relatorio";
import { PaginaClientes } from "@/pages/Clientes";
import { PaginaCatalogo } from "@/pages/Catalogo";
import { ToastProvider } from "@/components/Toast";

export function App() {
  return (
    <ToastProvider>
      <Routes>
        {/* Rotas públicas */}
        <Route path="/login" element={<PaginaLogin />} />
        <Route path="/esqueci-senha" element={<PaginaEsqueciSenha />} />
        <Route path="/redefinir-senha" element={<PaginaRedefinirSenha />} />

        {/* Rotas protegidas dentro do layout com sidebar */}
        <Route element={<RotaProtegida />}>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/lancamentos" replace />} />
            <Route path="/lancamentos" element={<PaginaLancamentos />} />
            <Route path="/lancamentos/novo" element={<PaginaLancamentoForm />} />
            <Route path="/lancamentos/:id/editar" element={<PaginaLancamentoForm />} />
            <Route path="/relatorio" element={<PaginaRelatorio />} />
            <Route path="/clientes" element={<PaginaClientes />} />
            <Route path="/catalogo" element={<PaginaCatalogo />} />
            {/* v1.1: o preço é definido no Catálogo; links antigos não dão 404 */}
            <Route path="/precos" element={<Navigate to="/catalogo" replace />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/lancamentos" replace />} />
      </Routes>
    </ToastProvider>
  );
}
