/**
 * Tela "Esqueceu a senha" — campo de e-mail + botão "Enviar link".
 *
 * Após envio, mensagem NEUTRA: não revela se o e-mail existe no sistema
 * (evita enumeração de usuários, mesmo que seja uso interno).
 */

import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { Mail } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import { MolduraAutenticacao } from "@/features/auth/MolduraAutenticacao";
import styles from "./Login.module.css";

export function PaginaEsqueciSenha() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setCarregando(true);
    // Ignora erros deliberadamente — mensagem neutra independente do resultado
    await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/redefinir-senha`,
    });
    setCarregando(false);
    setEnviado(true);
  }

  return (
    <MolduraAutenticacao
      titulo="Recuperar acesso"
      descricao="Informe seu e-mail e enviaremos um link para redefinir a senha."
    >
      {enviado ? (
        <div className={styles.sucesso} role="status">
          Se esse e-mail estiver cadastrado, você receberá um link em instantes. Verifique também a
          caixa de spam.
        </div>
      ) : (
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
          <div className={styles.acoes}>
            <Botao type="submit" variante="primario" tamanho="lg" carregando={carregando}>
              Enviar link
            </Botao>
          </div>
        </form>
      )}

      <Link to="/login" className={`${styles.linkEsqueci} ${styles.voltar}`}>
        Voltar para o login
      </Link>
    </MolduraAutenticacao>
  );
}
