# Frequência por aula, autenticador e backup — 16/10/2026

## Frequência

Professor → Chamada: consulte turma, data, disciplina, início e término. Marque
todos os estudantes e salve. A mesma disciplina/início identifica a mesma aula;
outra aula do mesmo dia possui registros independentes. Horários são da escola
(America/Sao_Paulo); o PostgreSQL guarda os instantes com fuso.

`lessons` + `attendance_records` são a base dos novos registros. A situação
persistida é `present`/`absent`; a interface usa Presente/Ausente. O professor
precisa de vínculo vigente na data da aula e a matrícula deve abranger essa
data. Turma e ano ativos, exatamente um período aberto para a data, nenhuma
sobreposição na turma e início não futuro são obrigatórios. Os horários podem
representar aulas de reposição, não apenas a recorrência semanal da grade.

Correções usam revisão: uma janela antiga não sobrescreve outra silenciosamente.
A auditoria conserva seleção anterior/nova e professor; não há exclusão física.
Uma aula registrada por outro docente não pode ser sobrescrita. Alterar o
término de um início já usado é rejeitado; substituições/cancelamentos e abonos
especiais não foram criados nesta etapa.

Novas aulas não são inferidas das chamadas diárias antigas. O calendário mostra
± quando há presenças e faltas em aulas diferentes do mesmo dia. A agenda lista
disciplina/horário; o histórico diário anterior continua acessível separadamente
em `/frequencia?base=diaria`. Quando há chamadas por aula, o percentual usa
somente aulas; sem elas, preserva a frequência diária anterior. Não misturar
unidades ou tratar ausência de registro como falta.

## Autenticador

Minha conta → Segurança da conta (`/conta/seguranca`), disponível aos quatro
perfis e proprietário. Somente uma conta já ativada por e-mail pode configurar:

1. Confirmar senha atual.
2. Adicionar QR/chave ao Google Authenticator ou outro TOTP (SHA1, 6 dígitos,
   30 segundos). A configuração pendente expira em dez minutos.
3. Confirmar um código antes de ativar.
4. Guardar os dez códigos de recuperação, exibidos uma vez e baixados somente
   por ação explícita do titular. São de uso único e continuam exigindo senha.

TOTP é validado com janela ±1 e contador atômico contra repetição. Segredos ficam
criptografados com Fernet; códigos de recuperação ficam somente como SHA256 de
valores aleatórios de 64 bits. QR é gerado localmente, sem rastreador externo.
Nada secreto entra na sessão assinada, URLs HTTP, flashes ou logs.

Login com MFA guarda apenas um desafio pré-autenticação por cinco minutos;
nenhuma função protegida é liberada antes do segundo fator. Bloqueio, alteração
de perfil ou versão de acesso invalidam o desafio. Ativação, desativação e nova
lista revogam outras sessões. Tentativas têm limites persistentes compartilhados.

Desativar/gerar códigos exige senha e um código novo (TOTP ou outro código de
recuperação), com confirmação do app. A recuperação de senha pela secretaria
**não remove** MFA. Não existe formulário escolar que desative o autenticador
de outra pessoa, nem da conta proprietária. Sem celular e sem códigos, será
necessária verificação privada de identidade pelo operador; não há atalho demo.

### Configuração privada obrigatória

`FAEHUB_MFA_ENCRYPTION_KEY`: chave Fernet estável, separada da chave de sessão.
`tools/provision_security_keys.py --output-dir <pasta privada nova>` gera
`security.env` fora do repositório, sem imprimir valores. Importar no Render
privadamente e guardar cópia segura fora do banco. **Não regenerar/trocar a chave
depois de ativar contas**: isso impediria abrir os segredos existentes. Sem a
chave configurada, a tela informa a pendência e não permite começar a ativação.

## Gmail e Drive

O transporte Gmail mantém HTML/texto dos convites e envio único via HTTPS.
`tools/check_gmail.py --env-file <arquivo privado>` verifica renovação sem envio;
adicionar `--send-self` envia um único teste à própria caixa remetente, nunca
convites em massa. Aceitação pela API não comprova recebimento na caixa.

`scripts/authorize_gmail.py --client <JSON OAuth desktop privado> --output-dir
<pasta privada nova> --service both` solicita somente `gmail.send` e
`drive.file`. O titular conclui o consentimento pessoalmente. Gmail API e Google
Drive API precisam estar habilitadas no mesmo projeto. A ferramenta cria uma
pasta de backup na conta autorizada, sem alterar compartilhamento, e grava
`render.env` privado. `--service gmail` continua compatível; `--service drive`
autoriza somente Drive. Tokens não aparecem no terminal.

Configurar no operador/servidor as variáveis `FAEHUB_GMAIL_*`, provider `gmail`,
origem pública HTTPS e `FAEHUB_DRIVE_CLIENT_ID`, `FAEHUB_DRIVE_CLIENT_SECRET`,
`FAEHUB_DRIVE_REFRESH_TOKEN`, `FAEHUB_DRIVE_FOLDER_ID`. Não publicar nem anexar
arquivos privados ao Git/chat. Em OAuth externo Testing, revisar a validade
limitada do refresh token e publicação/verificação antes de uso durável.

## Backup criptografado no Drive

`tools/school_backup.py` é ferramenta privada, sem rota web/exportação pelo app.
Precisa de clientes PostgreSQL 17+ (`pg_dump`, `pg_restore`), conexão direta ou
Session pooler e variáveis privadas. Não usar Transaction pooler para snapshot.

- `FAEHUB_BACKUP_DATABASE_URL` (ou a conexão normal do app).
- `FAEHUB_BACKUP_KEY`: 32 bytes aleatórios em base64, gerados pelo provisionador.
  Guardar em local seguro **fora da pasta de backup e do próprio banco**.
- Variáveis Drive acima; nenhum acesso completo ao Drive é solicitado.

Comandos (ajustar o interpretador à instalação):

```text
python tools/school_backup.py --env-file <privado> create --output-dir <pasta privada externa> --drive
python tools/school_backup.py --env-file <privado> verify <arquivo.fhbackup>
python tools/school_backup.py --env-file <privado> test-restore <arquivo.fhbackup>
```

`create` usa snapshot PostgreSQL consistente com contagem de cada tabela, dump
custom de `public`, manifesto e checksum SHA256. Anexos e fotos estão em bytea
nesse esquema e entram na cópia. O envelope usa AES-256-GCM com nonce aleatório,
autenticação do cabeçalho e processamento em blocos. Temporários são privados do
operador e removidos ao terminar. Só o arquivo criptografado vai para o Drive.
Upload resumable é confirmado por tamanho/MD5 do ciphertext. Sem repetição cega:
se o envio ficar incerto, conferir a pasta antes de tentar novamente.

O uploader inicial limita arquivos a 128 MB; cópias maiores exigem upload
segmentado antes de ativar a rotina. Falha de envio preserva a cópia local.
Não apaga backups antigos nem muda permissões; retenção/agenda devem ser
definidas pelo proprietário, não inferidas.

`verify` autentica/decripta, confere checksum e legibilidade do dump;
**não comprova restauração**. `test-restore` exige `FAEHUB_RESTORE_DATABASE_URL`
distinta da origem e um destino vazio. Não usa `--clean`/DROP: restaura em uma
transação e compara todas as contagens do manifesto. Nunca testar restauração
sobre produção. Conferir login, histórico e downloads no destino isolado antes
de tratá-lo como recuperação operacional. Permissões públicas devem continuar
revogadas; secrets de sessão/MFA/Google não são substituídos pelo Git.

Esta versão não ativa agendamento, retenção ou armazenamento pago. A primeira
cópia real, autorização do Drive e exercício completo de
recuperação dependem da configuração privada. Sem essas evidências, não chamar
o backup de automático/operacional.

## Migração e evidências

`20261016200538_lesson_attendance_and_mfa.sql` aplicada no FaeHub+
(`qlungxnsjmrkozsrtwon`). Corrige a restrição de weekday da grade vazia para
segunda=0…domingo=6 (causa confirmada do deploy anterior falhar), adiciona
revisão/índices e tabelas privadas de MFA. O guard recusa adoção automática se
houver grade preenchida; não desloca horários administrados silenciosamente.
O modelo SQLite de testes agora tem os mesmos enums/restrições fundamentais.

Teste PostgreSQL transacional de aula/presença/MFA concluído com ROLLBACK,
sem registros de teste persistidos. RLS ativo e SELECT revogado de
anon/authenticated; advisors de segurança reportaram apenas INFO de tabelas
privadas sem políticas públicas, comportamento esperado desta arquitetura.

Suíte completa: 188 testes, 187 aprovados e o teste PostgreSQL opcional pulado
nessa execução. O teste opcional foi executado separadamente com PostgreSQL
17.11 real, em cluster local descartável com dados fictícios: dump consistente,
criptografia, restauração, anexos bytea, segredo MFA cifrado, RLS, sequência de
identidade e recusa de destino não vazio aprovados. Nenhum dado escolar foi
usado nesse teste. Isso valida a ferramenta, não comprova uma cópia de produção
nem envio real ao Drive. A restauração preserva o schema public já existente e
omite apenas sua criação no índice do dump, sem DROP.

Testes cobrem também erros de senha sem rollback do limitador.
Chrome isolado: chamada real, erro/CSRF,
larguras 1440/900/390/320, QR, ativação, recuperação, confirmação e cancelamento.
Criptografia/tamper/truncamento, preservação de destino, manifesto, bloqueio de
produção e Drive simulado são testados; a primeira recuperação operacional
de produção continua pendente de configuração privada e destino isolado.

Fontes: [TOTP/PyOTP](https://pyauth.github.io/pyotp/),
[Fernet](https://cryptography.io/en/latest/fernet/),
[escopo mínimo Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth),
[backup Supabase](https://supabase.com/docs/guides/platform/backups).
