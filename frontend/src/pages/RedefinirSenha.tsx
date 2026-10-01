/**
 * Tela "Redefinir senha" — nova senha + confirmar + botão "Salvar".
 * Acessada via link enviado por e-mail (o Supabase inclui o token na URL).
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { supabase } from "@/lib/supabase";
import { mensagemErroRedefinicao } from "@/features/auth/mensagens";
import { Lock } from "lucide-react";
import { MolduraAutenticacao } from "@/features/auth/MolduraAutenticacao";
import { Campo } from "@/components/Campo";
import { Botao } from "@/components/Botao";
import styles from "./Login.module.css";

export function PaginaRedefinirSenha() {
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [erroGeral, setErroGeral] = useState("");
  const [carregando, setCarregando] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErroGeral("");

    if (novaSenha !== confirmar) {
      setErroGeral("As senhas não coincidem.");
      return;
    }

    if (novaSenha.length < 8) {
      setErroGeral("A senha deve ter pelo menos 8 caracteres.");
      return;
    }

    setCarregando(true);
    const { error } = await supabase.auth.updateUser({ password: novaSenha });
    setCarregando(false);

    if (error) {
      // a regra de força da senha mora no Supabase; aqui só traduzimos o motivo
      setErroGeral(mensagemErroRedefinicao(error));
      return;
    }

    navigate("/login", { replace: true });
  }

  return (
    <MolduraAutenticacao titulo="Nova senha" descricao="Escolha uma senha forte e única.">
      {erroGeral && (
        <div className={styles.erro} role="alert">
          {erroGeral}
        </div>
      )}

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <Campo
          rotulo="Nova senha"
          type="password"
          autoComplete="new-password"
          icone={<Lock size={16} />}
          value={novaSenha}
          onChange={(e) => setNovaSenha(e.target.value)}
          dica="Mínimo de 8 caracteres."
          required
        />
        <Campo
          rotulo="Confirmar nova senha"
          type="password"
          autoComplete="new-password"
          icone={<Lock size={16} />}
          value={confirmar}
          onChange={(e) => setConfirmar(e.target.value)}
          required
        />
        <div className={styles.acoes}>
          <Botao type="submit" variante="primario" tamanho="lg" carregando={carregando}>
            Salvar
          </Botao>
        </div>
      </form>
    </MolduraAutenticacao>
  );
}
