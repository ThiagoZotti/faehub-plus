# Identidade FaeHub → FaeNet

Decisão do proprietário, 19/10/2026: todos os perfis ativos e ativados do FaeHub
podem acessar a FaeNet; não haverá cadastro independente após o corte.
Contas demo públicas não comprovam identidade. A aplicação FaeHub continua
permitindo suas demos conforme a configuração anterior.

## Contrato

- Cliente único `faenet`, callback exato `https://faenet.onrender.com/auth/faehub/callback`.
- Código opaco de 60 segundos, uso único, estado da sessão e PKCE S256.
  Ponte privada, não um provedor OAuth/OIDC genérico.
- Senha e autenticador são conferidos somente no FaeHub. UUID estável aleatório,
  nome, perfil e flag de proprietário são compartilhados, nunca matrícula/notas/e-mail.
- Token opaco de 12h, somente hash no FaeHub e cifra no servidor FaeNet. Cookies
  contêm identificadores opacos, não bearer/verifier. Segredo privado de cliente
  autentica a troca e a introspecção; não compartilhar com navegadores.
- Toda API/upload protegido revalida a conta: bloqueio/troca de senha ou versão
  de autenticação invalida o acesso anterior. Falha remota nega acesso com 503,
  sem fallback de senha local. Isso acrescenta uma chamada de rede por requisição,
  com timeout de 8s; disponibilidade FaeNet depende do FaeHub.
- Somente o proprietário pode receber administração social. Diretor não é admin
  social automaticamente. As permissões escolares não são ampliadas.
- Vínculo exige senha antiga privada e confirmação explícita. Não se vincula por
  username coincidente nem senha pública demo. Limites: cinco tentativas por
  confirmação e dez por conta antiga/15min, persistentes. Criar perfil novo não
  apaga os antigos; não há mesclagem posterior automática.
- Sair da FaeNet encerra sua sessão local, não a sessão do FaeHub. Uma nova entrada
  pode reutilizar a sessão FaeHub válida. Rotacionar o segredo exige reautenticação;
  vínculos e publicações permanecem.

## Ativação coordenada

1. Aplicar as migrations versionadas nos dois bancos; RLS ativo e Data API fechada.
2. Publicar ambos os repositórios e aguardar os dois deploys Live.
3. Gerar arquivos privados com `tools/provision_faenet_sso.py --output-dir <pasta-privada-nova>`.
   Nunca versionar/colar seu conteúdo no chat. Não gerar novas chaves se já importadas.
4. Importar `faehub.env` no Environment do FaeHub, preservando as variáveis existentes;
   salvar/reimplantar e aguardar Live.
5. Importar `faenet.env` no Environment da FaeNet, preservando SECRET_KEY/DATABASE_URL;
   salvar/reimplantar e aguardar Live. Requer SECRET_KEY privada estável de 32+ caracteres.
6. Verificar `/api/auth/options` com `faehub_only=true`, entrada, MFA, vínculo ou
   criação e revogação. Contas/sessões independentes antigas deixam de liberar dados.

O código mantém `FAEHUB_LOGIN_REQUIRED=0` por padrão para não bloquear o app durante
o deploy coordenado. **Publicar código sozinho não ativa a integração.** Importar
as configurações privadas é etapa separada e deve ser confirmado em produção.
Rollback seguro: bloquear a entrada para manutenção, reverter o código se necessário;
não reabrir login independente sem decisão do proprietário e não apagar vínculos/dados.
Tabelas transitórias têm validade lógica; uma limpeza periódica física ainda não
está agendada. Não tratá-las como dados escolares nem apagar tabelas de usuários.

## Recuperação de acesso

Decisão adicional de 19/10/2026: recuperação autônoma por e-mail confirmado, sem
direção/secretaria. `/recuperar-senha` recebe apenas e-mail, envia código aleatório
de uso único/30min para senha ou identificação do usuário para o próprio endereço.
Resposta pública neutra não confirma cadastro. Apenas conta ativa e e-mail
verificado são elegíveis; proprietário incluído. O código é armazenado em hash e
só liberado após aceitação do envio. Limites por e-mail/IP; reenvio invalida o anterior.
Reset exige e-mail+código+nova senha de 8–128 caracteres; não entra automaticamente,
revoga sessões existentes e mantém autenticador, permissões e vínculos escolares.
Código de secretaria não pode redefinir uma conta verificada; a interface antiga
de aprovação foi retirada. Sem acesso ao e-mail, este fluxo não contorna MFA nem
oferece alteração de endereço sem outra prova de identidade.

## Evidência

`tools/run_tests.py`: suíte completa; `test_faenet_sso.py` cobre PKCE, uso único,
MFA, quatro perfis e revogação. `test_account_recovery.py` cobre e-mail, reset,
falha de envio e limites. FaeNet: `tests/test_federation.py` e suíte de performance.
Fluxo real local em dois servidores e bancos descartáveis: entrada → FaeHub →
confirmação → senha antiga → feed com publicação preservada → logout → reentrada.
Desktop e 390px, campos inválidos, erro de senha e consentimento foram conferidos.

## Personalização da FaeNet — 20/10/2026

A FaeNet passa a solicitar @, nome de exibição com sobrenome e, opcionalmente,
foto, capa, bio, curso e turma após confirmar a identidade no FaeHub. A chave de
vínculo permanece imutável: personalizar o perfil social não muda conta, senha,
autenticador, permissões ou registros escolares. Contas geradas automaticamente
concluem esse fluxo na próxima entrada, preservando posts, mensagens e relações.
Implementação, migration e testes estão no repositório FaeNet, contrato
`docs/faehub-sso.md`. Nenhum segredo novo é necessário no FaeHub.

Correção de envio em 20/10/2026: o cadastro FaeNet resolve o destino pelo atributo
HTML/URL atual, sem usar a propriedade form.action que o campo oculto mascarava.
Regressão cliente: `node --test tests/test_identity_client.js` na FaeNet.

Ensaio da prévia: correções adicionais de atualização do feed e roteamento de
Mensagens com destinatário, preservando aparência e permissões. Regressões em
`tests/test_feed_client.js` e `tests/test_router_client.js` no repositório FaeNet.
Escopo e limitações da checagem em `docs/previa-checklist.md`.
