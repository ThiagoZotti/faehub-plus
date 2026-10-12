# Otimização de navegação — 12/10/2026

Sem alterações de CSS, imagens, composição de tela ou animações. A aplicação
continua usando Supabase PostgreSQL; SQLite é exclusivo dos testes descartáveis.

## Alterações

- A direção não carrega mais dez tabelas de estrutura para um dropdown. Somente
  Turmas consulta os códigos ativos, na mesma ordenação anterior.
- O seletor de histórico consulta somente estudantes; responsável continua
  restrito às matrículas de seus vínculos. A rota revalida a seleção no servidor.
- Identificação, bloqueio, versão da sessão e autoridade do proprietário são
  verificados na mesma consulta, a cada requisição. Não há cache de autorização.
- Indicadores operacionais usam uma consulta com cinco agregações independentes.
- O cabeçalho consulta apenas a contagem, preservando a janela de 100 notificações,
  os destinatários, a expiração e a exclusão de mensagens no badge do aluno.
  Quando a página já carregou a caixa de notificações, o cabeçalho reutiliza-a.
- Notas, atividades e entregas dos painéis são filtradas antes da transferência.
  O resumo de mensagens traz no máximo duas prévias e totais calculados no banco,
  sem consultas de reações/recibos. O chat completo mantém seu comportamento.
- URLs estáticas usam hash dos bytes: arquivos iguais conservam cache entre
  deploys; alterações invalidam também versões manuais dos templates. Nenhum
  conteúdo autenticado passa a ser cacheado publicamente.

## Medição reproduzível

`python tools/profile_navigation.py` cria um banco temporário e aquece Jinja antes
de medir. Não abre o banco escolar. A contagem é de SELECTs do aplicativo, não
inclui o health check do pool PostgreSQL nem mede a latência do Render/Supabase.

Comparação local final, mantendo também a identificação da instituição no painel:

| Direção | Antes | Depois |
|---|---:|---:|
| Painel | 25 | 8 |
| Usuários | 19 | 8 |
| Configurações | 16 | 4 |
| Relatórios | 24 | 8 |

Validação final, incluindo bootstrap do responsável: 148 testes passaram em
158,653s; `git diff --check` sem erros.
Chrome headless isolado: 104 combinações de página/largura (1440/900/390/320px),
seis abas de estrutura e interações de foco, busca, vazio, confirmação e Escape,
sem erros de JavaScript ou overflow da página. O audit premium ficou sem achados
no escopo P0 declarado pelo manifesto; não é certificação global de acessibilidade.
Nenhum token visual ou arquivo CSS foi alterado.

Consultas de resumo e autenticação foram conferidas no PostgreSQL real sem
retornar corpos de mensagens, senhas ou e-mails. EXPLAIN ANALYZE da contagem do
badge utilizou os índices de destinatário/público, com execução de 2,572ms naquele
instante (sem notificações aplicáveis). Isso não é benchmark de navegação ou de
latência do Render, nem uma promessa de tempo constante.

## Reabertura das demos

O usuário escolheu explicitamente reabrir no app principal, ciente de que as demos
compartilham acesso aos dados escolares. Não se trata de ambiente isolado.

Comando privado (não exposto em rota web):

```text
python tools/reactivate_demos.py
python tools/reactivate_demos.py --apply --allow-shared-school-data
```

A primeira linha apenas informa o plano. A segunda requer o proprietário ativo
e com o e-mail reservado confirmado. Reabre contas demo existentes sem identidade
ou convite, preserva proprietário, contas pessoais, cadastros por convite e
senhas atuais; revoga sessões antigas das contas efetivamente reabertas. Não
imprime credenciais nem cria usuários. A operação é transacional e auditada.

O marcador `demos_seed_blocked=1` impede que a reabertura volte a semear contas ou
registros acadêmicos de exemplo no reinício. `demos_disabled=0` permite que a
direção volte a encerrar as demos pelo fluxo já existente. Nenhuma variável
pública ou alteração de RLS é necessária.

A reabertura é operação de dados separada do deploy: enviar código ao GitHub não
altera contas. Aplicar depois que a versão com `demos_seed_blocked` estiver no
servidor, verificar as contas no Supabase e testar o login. Na conferência prévia,
cinco contas estavam elegíveis; proprietário e Thiago Zotti tinham identidade/
convite e foram excluídos do plano. O fluxo de Gmail permanece pausado.

Conferência operacional em 12/10/2026: a versão otimizada foi enviada ao GitHub
e identificada no login público do Render pelo versionamento de conteúdo.
Cinco demos foram reabertas transacionalmente no projeto FaeHub+ via conexão
administrativa Supabase: `aline`, `jonathan.samuel`, `pablo.sousa`,
`marlon.eduardo` e `responsavel.thiago`. Login e painel de todas retornaram HTTP
200 com as credenciais legadas, sem registrar cookies, tokens ou corpos das
páginas. Proprietário e Thiago Zotti preservaram identidade, convite e versão
de sessão. Os marcadores foram conferidos: acesso habilitado e seed bloqueado.
`demo_seeding_enabled` é compartilhado também pelo bootstrap do responsável,
incluindo seus vínculos familiares; o teste de reinício cobre sua não recriação.
