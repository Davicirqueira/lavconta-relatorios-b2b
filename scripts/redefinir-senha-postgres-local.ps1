<#
.SYNOPSIS
    Redefine a senha do usuario 'postgres' da instancia LOCAL do PostgreSQL 16
    e cria o banco de testes do Lavconta.

.DESCRIPTION
    Necessario porque a senha original nao e recuperavel (o Postgres guarda
    apenas o hash scram-sha-256).

    O QUE O SCRIPT FAZ:
      1. Faz backup do pg_hba.conf (com data/hora no nome).
      2. Troca temporariamente a autenticacao local de scram-sha-256 para trust.
      3. Reinicia o servico do Postgres.
      4. Chama o comando \password do psql, que pede a nova senha de forma
         interativa e segura.
      5. Cria o banco 'lavconta_teste' (se ainda nao existir).
      6. RESTAURA o pg_hba.conf original e reinicia o servico novamente.

    O passo 6 esta em bloco 'finally': a restauracao acontece mesmo se algo
    falhar no meio.

    SEGURANCA DA SENHA: usamos o \password do psql em vez de montar um comando
    ALTER USER. Assim a senha nunca e escrita em arquivo, nunca aparece na lista
    de processos e nunca pode ser ecoada em mensagem de erro.

    JANELA DE RISCO: entre os passos 3 e 6 (poucos segundos), conexoes locais ao
    Postgres sao aceitas SEM senha. Afeta apenas esta maquina.

    ESCOPO: mexe somente na instancia local de desenvolvimento. Nenhuma relacao
    com o banco do Supabase (producao).

    NOTA DE CODIFICACAO: este arquivo e intencionalmente ASCII puro. O Windows
    PowerShell 5.1 interpreta .ps1 sem BOM como ANSI, o que embaralharia
    acentos na saida.

.NOTES
    Executar em PowerShell ABERTO COMO ADMINISTRADOR.
#>

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$raizPg = 'C:\Program Files\PostgreSQL\16'
$dirDados = Join-Path $raizPg 'data'
$hba = Join-Path $dirDados 'pg_hba.conf'
$psql = Join-Path $raizPg 'bin\psql.exe'
$servico = 'postgresql-x64-16'
$bancoTeste = 'lavconta_teste'

foreach ($caminho in @($dirDados, $hba, $psql)) {
    if (-not (Test-Path $caminho)) { throw "Caminho nao encontrado: $caminho" }
}

Write-Host '=== Senha do Postgres local: redefinicao ===' -ForegroundColor Cyan
Write-Host "Instancia : $raizPg"
Write-Host "Servico   : $servico"
Write-Host "Banco     : $bancoTeste"
Write-Host ''
Write-Host 'O psql vai pedir a nova senha duas vezes, mais adiante.' -ForegroundColor Yellow
Write-Host ''

$backup = "$hba.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $hba $backup
Write-Host "[1/6] Backup criado: $(Split-Path $backup -Leaf)" -ForegroundColor Green

try {
    # --- trust temporario --------------------------------------------------
    (Get-Content $hba) -replace '(^\s*(local|host)\s+\S+\s+\S+.*?)scram-sha-256\s*$', '$1trust' |
        Set-Content $hba -Encoding ASCII
    Write-Host '[2/6] Autenticacao temporaria: trust' -ForegroundColor Yellow

    Restart-Service $servico
    Start-Sleep -Seconds 4
    Write-Host '[3/6] Servico reiniciado' -ForegroundColor Green

    # --- nova senha via \password (interativo, nunca gravado em arquivo) ---
    # Ate 3 tentativas: um erro de digitacao nao deve obrigar a repetir todo o
    # ciclo de troca de autenticacao e reinicio do servico.
    Write-Host ''
    Write-Host '[4/6] Defina a nova senha nos prompts abaixo:' -ForegroundColor Cyan

    $definida = $false
    for ($tentativa = 1; $tentativa -le 3; $tentativa++) {
        if ($tentativa -gt 1) {
            Write-Host ''
            Write-Host "      Tentativa $tentativa de 3 (digite a MESMA senha nas duas vezes):" -ForegroundColor Yellow
        }
        & $psql -U postgres -d postgres -c '\password postgres'
        if ($LASTEXITCODE -eq 0) { $definida = $true; break }
    }
    if (-not $definida) { throw 'Nao foi possivel definir a senha em 3 tentativas.' }
    Write-Host '      Senha definida.' -ForegroundColor Green

    # --- banco de teste ----------------------------------------------------
    $existe = & $psql -U postgres -d postgres -tAc "select 1 from pg_database where datname = '$bancoTeste'"
    if ($existe -eq '1') {
        Write-Host "[5/6] Banco '$bancoTeste' ja existia" -ForegroundColor Green
    }
    else {
        & $psql -U postgres -d postgres -v ON_ERROR_STOP=1 -q -c "CREATE DATABASE $bancoTeste"
        if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o banco $bancoTeste." }
        Write-Host "[5/6] Banco '$bancoTeste' criado" -ForegroundColor Green
    }
}
finally {
    Copy-Item $backup $hba -Force
    Restart-Service $servico
    Start-Sleep -Seconds 4
    Write-Host '[6/6] pg_hba.conf restaurado (scram-sha-256) e servico reiniciado' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Concluido.' -ForegroundColor Cyan
Write-Host 'Proximo passo: informe a senha no arquivo backend\.env.teste' -ForegroundColor Cyan
Write-Host 'URL de teste:' -ForegroundColor Cyan
Write-Host "  postgresql+psycopg://postgres:SUA_SENHA@localhost:5432/$bancoTeste"
