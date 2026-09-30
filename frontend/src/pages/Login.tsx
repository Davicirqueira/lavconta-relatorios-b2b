/**
 * Tela de Login — cartão único sobre fundo gelo-50.
 *
 * Campos: e-mail e senha. Botão primário "Entrar".
 * Link discreto "Esqueceu sua senha?".
 * SEM link de cadastro (disable_signup=true no Supabase).
 * Erro: banner único acima do formulário (não por campo — não revela
 * se o e-mail existe ou não).
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { supabase } from "@/lib/supabase";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
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
    <div className={styles.fundo}>
      <div className={styles.cartao}>
        <div className={styles.marca}>
          <h1 className={styles.logotipo}>Lavconta</h1>
          <p className={styles.subtitulo}>Relatórios B2B</p>
        </div>

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
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Campo
            rotulo="Senha"
            type="password"
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
          />

          <div className={styles.acoes}>
            <Botao
              type="submit"
              variante="primario"
              tamanho="lg"
              carregando={carregando}
            >
              Entrar
            </Botao>
            <Link to="/esqueci-senha" className={styles.linkEsqueci}>
              Esqueceu sua senha?
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
