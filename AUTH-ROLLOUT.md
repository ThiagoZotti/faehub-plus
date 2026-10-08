# Acesso real — implantação por etapas

## Etapa entregue: convites e primeiro acesso

- Direção → Usuários → Preparar convite. A direção confirma sua senha, define identificação interna, nome, e-mail, perfil e vínculo acadêmico.
- Conta nova nasce inativa e com senha aleatória inutilizável; a direção não define a senha do titular.
- Sem serviço de e-mail, o cadastro é salvo como **Aguardando envio**. Nenhum link utilizável é emitido nem exibido pela central.
- Com envio configurado, o convite é encaminhado ao e-mail autorizado. A API confirma aceitação, não entrega na caixa de entrada; confira spam e o painel do provedor.
- Link de uso único, validade de 48 horas, cancelamento e reenvio (intervalo mínimo de um minuto). Reenviar invalida o link anterior.
- O usuário abre o link, confirma o endereço recebido e define senha de 15–128 caracteres. Perfil, matrícula e vínculos não vêm do formulário de ativação.
- Após ativar, entra com e-mail ou identificação interna; o botão explícito **Entrar no campus** é mantido.
- Senhas usam o hash scrypt do Werkzeug; tokens são armazenados apenas como SHA-256. Segredos não aparecem no diretório, logs ou URL HTTP: o link usa fragmento, removido pelo script ao abrir.
- Limites de tentativas persistem no Supabase e são compartilhados pelos processos da aplicação. Identificadores dos limites usam HMAC, não e-mail/IP em texto.
- Requisição concorrente/repetida consome o convite por atualização condicional atômica. Ativação e revogação de sessões pertencem à mesma transação.
- Fotografias, notas, mensagens, matrículas e demais registros continuam ligados à identificação escolar, não ao e-mail.

## Conectar o envio

O Render Free bloqueia as portas SMTP 25, 465 e 587. Por isso esta etapa usa a API HTTPS do Resend, sem SDK adicional.

Configure **apenas no ambiente privado do servidor**:

| Variável | Conteúdo |
| --- | --- |
| `FAEHUB_PUBLIC_URL` | Origem HTTPS pública, por exemplo `https://faehub-plus.onrender.com` |
| `FAEHUB_MAIL_FROM` | Remetente autorizado no Resend |
| `FAEHUB_RESEND_API_KEY` | Chave privada com permissão de envio |
| `FAEHUB_BOOTSTRAP_ADMIN_EMAIL` | E-mail legítimo autorizado para ativar o primeiro diretor |

Uma caixa Gmail/Outlook pode servir como contato institucional, mas não substitui a autorização do remetente no serviço de envio. Para mandar convites a toda a comunidade via Resend, configure um domínio remetente verificado. O remetente de teste do provedor tem restrições e não deve ser apresentado como pronto para todos os usuários.

Não cole chaves neste documento, no GitHub ou em mensagens públicas. Não habilite rastreamento de cliques nos links de ativação. Não envie convites para endereços que não foram confirmados no cadastro escolar. Nenhum domínio, conta ou assinatura paga é adquirido pelo código.

## Migrar a direção sem bloqueio

**Proteção de bootstrap:** o dono do servidor define `FAEHUB_BOOTSTRAP_ADMIN_EMAIL` em ambiente privado. Uma direção não ativada só pode convidar a própria conta para esse endereço, nunca criar outras identidades. A senha pública da demonstração não é autoridade suficiente para distribuir acessos reais. Não configure um e-mail escolhido por um visitante do app. Após ativar, a direção verificada pode emitir os demais convites.

Alternativamente, o proprietário pode provisionar `bootstrap_admin_email` na tabela privada `enrollment_settings`, por conexão administrativa. Não existe formulário público ou administrativo do app que possa editar essa chave; a variável de ambiente, quando preenchida, tem precedência. O endereço administrativo autorizado pelo proprietário é vinculado ao perfil de direção existente, preservando sua identificação escolar, e fica apenas na configuração privada/banco, nunca fixado no código público. O vínculo fica pendente até a confirmação por convite e definição da senha. O FaeNet não é alterado nesta etapa.

1. Entrar com o acesso atual da direção.
2. Em Usuários, gerenciar a própria conta e abrir **Migrar para acesso por e-mail**. Perfil e registros permanecem iguais.
3. Informar o e-mail legítimo do diretor e confirmar a senha atual.
4. Receber o convite, abrir e definir uma nova senha pessoal.
5. Entrar novamente pelo e-mail e validar a central de Usuários. As sessões anteriores são revogadas.
6. Só então usar **Encerrar contas de demonstração**, confirmar a senha nova e a confirmação do app.

O encerramento desativa somente as sete contas demo conhecidas que ainda não foram convertidas em contas verificadas. Não exclui registros escolares, não desativa contas reais e não pode ser feito por um diretor não ativado. O marcador persistente bloqueia a recriação automática das contas demo nas próximas inicializações.

## Limites desta etapa

- Ainda não é uma migração para Supabase Auth: o backend Flask mantém o controle de sessões/perfis e usa PostgreSQL Supabase para persistência. Nenhuma chave `service_role` é exposta.
- Recuperação atual continua mediada pela secretaria, agora aceitando e-mail confirmado ou identificação interna. Não afirmar que existe recuperação automática por e-mail.
- Autenticador TOTP, códigos de recuperação, telefone/SMS e painel de sessões são **próximas etapas**, não funcionalidades já habilitadas. Não guardar telefone como se fosse verificado.
- Envio síncrono tem timeout de dez segundos. Se o processo cair durante o envio, a direção pode reenviar após o cooldown; o novo link invalida o anterior. Não há retentativa automática de efeito externo.
- A integração foi testada com transporte simulado, sem enviar convites a pessoas reais. Exige um teste real de entrega/ativação após configurar o remetente.

## Fontes técnicas

- [Limitações do Render Free](https://render.com/docs/free)
- [API de envio Resend](https://resend.com/docs/api-reference/emails/send-email)
- [Tokens de uso único e recuperação — OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)

## Verificação

`test_account_enrollment.py` cobre rascunho bloqueado, ativação, e-mail como alias, perfil imutável, tokens sem exposição, expiração, cancelamento, falha do provedor, reenvio/cooldown, CSRF/permissões, vínculo familiar, transição segura das demos e limites persistentes. Os testes usam exclusivamente bancos temporários isolados; o envio é simulado.
