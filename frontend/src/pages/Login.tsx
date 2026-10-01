/**
 * Tela de Login.
 *
 * E-mail e senha, botão "Entrar", link "Esqueceu a senha?" junto ao rótulo da
 * senha (protótipo). SEM link de cadastro (disable_signup=true no Supabase).
 * Erro: banner único acima do formulário — não indica se o e-mail existe.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight, Lock, Mail } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import { MolduraAutenticacao } from "@/features/auth/MolduraAutenticacao";
import styles from "./Login.module.css";

export function PaginaLogin() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erroGeral, setErroGeral] = useState("");
  const [carregando, setCarregando] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErroGeral("");
    setCarregando(true);

    const { error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password: senha,
    });

    setCarregando(false);

    if (error) {
      // Mensagem genérica: não vaza se o e-mail existe ou não
      setErroGeral("E-mail ou senha inválidos. Verifique e tente novamente.");
      return;
    }

    navigate("/lancamentos");
  }

  return (
    <MolduraAutenticacao titulo="Entrar">
      {erroGeral && (
        <div className={styles.erro} role="alert">
          {erroGeral}
        </div>
      )}

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <Campo
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          icone={<Mail size={16} />}
          placeholder="nome@lavandix.com.br"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Campo
          rotulo="Senha"
          type="password"
          autoComplete="current-password"
          icone={<Lock size={16} />}
          extraRotulo={
            <Link to="/esqueci-senha" className={styles.linkEsqueci}>
              Esqueceu a senha?
            </Link>
          }
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
        />

        <div className={styles.acoes}>
          <Botao type="submit" variante="primario" tamanho="lg" carregando={carregando}>
            Entrar
            <ArrowRight size={16} aria-hidden="true" />
          </Botao>
        </div>
      </form>
    </MolduraAutenticacao>
  );
}
