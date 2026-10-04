# UX Contract — FaeHub+ P0/P1

## Contexto

- Público: alunos, responsáveis, professores, coordenação, secretaria e direção da ETESC/FAETEC.
- Locale: `pt-BR`; fuso: `America/Sao_Paulo`; calendário gregoriano.
- Meta de acessibilidade: WCAG 2.2 AA.
- Fontes de verdade: `ROADMAP.md`, autorização em `app.py`/`director.py`, dados em `database.py`/`p1_operations.py` e migrações em `supabase/migrations/`.
- Direção visual canônica: `DESIGN.md`; tokens do shell e superfícies acadêmicas em `static/campus-system.css`, `static/academic.css` e `static/p1/operations.css`.

## Modelo de permissão

| Perfil | Capacidades P1 |
|---|---|
| Aluno | calendário, notificações, documentos próprios, mensagens e entregas com anexo |
| Responsável | painel das matrículas vinculadas, documentos, calendário, notificações e mensagens |
| Professor | diário próprio, calendário, notificações, atividades e mensagens com anexo |
| Direção/coordenação | secretaria, validação de diário, acompanhamento, períodos, calendário, notificações e relatórios |

### Capacidades P0

- Direção: criar e alterar situação de anos, períodos, cursos, disciplinas e turmas; vincular grade e professor; cadastrar estudante; criar e encerrar matrícula.
- Aluno e responsável: consultar somente a trajetória das matrículas autorizadas.
- Direção: consultar qualquer trajetória; professor não acessa o histórico individual pela rota P0.
- Encerramento preserva registro e datas; nenhuma ação P0 faz exclusão física.

A interface oculta rotas não autorizadas, mas o servidor sempre revalida sessão, perfil, propriedade e vínculo. Downloads de anexos verificam remetente/destinatário, turma, estudante, professor ou direção.

### Mensagens e privacidade familiar

- Responsáveis veem como destinatários somente seus alunos vinculados e a equipe escolar; outros alunos e outros responsáveis não entram na lista nem são aceitos em requisições diretas.
- Direção e Coordenação mantêm visão ampla da comunidade escolar para atendimento e mediação.
- Imagens aparecem dentro da conversa; os demais anexos permanecem como arquivos identificados, sempre sujeitos à autorização do servidor.
- Somente o autor pode apagar uma mensagem. A exclusão é lógica, substitui o conteúdo por um marcador e permite restauração pelo próprio autor; o arquivo deixa de ser entregue enquanto a mensagem está apagada.

## Componentes e estados

### Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | Navegador nativo | `templates/p0/estrutura.html` | curso, turma, disciplina, situação | teste de mutação P0 + teclado |
| Date | Navegador nativo | `templates/p0/estrutura.html` | início, término e encerramento | teste de cadeia acadêmica |
| Form | FaeHub `academic-core.js` | `static/p0/academic-core.js` | criação, vínculo, alteração de situação | erro inline + retry + testes P0 |
| Scrollbar | Shell FaeHub | `static/p0/academic-core.css` | página e tabela responsiva | desktop e celular |
| Toast | Shell FaeHub | `templates/base.html` | sucesso após redirect | teste de mutação P0 |
| CRUD | Núcleo acadêmico | `academic_core.py` | criação e mudança de estado sem exclusão física | `test_p0_academic_core.py` |

| Componente | Estados obrigatórios |
|---|---|
| Botão | padrão, hover, foco visível, desabilitado e ocupado sem mudar largura |
| Campo | rótulo persistente, foco, obrigatório, ajuda, erro preservando conteúdo |
| Lista | carregada, vazia, sem resultados, erro e item com ações contextualizadas |
| Situação | texto + cor; nunca depender apenas da cor |
| Diálogo | nome acessível, fechar explícito, Escape/backdrop e foco devolvido ao gatilho |
| Notificação | lida/não lida, ação opcional e data persistente |
| Anexo | nome, tamanho, tipo aceito, falha acionável e download autorizado |

Uploads aceitam PDF, PNG, JPG, TXT e ZIP, um arquivo por ação, até 5 MB. O seletor nativo permanece acessível. Extensão/MIME e tamanho são validados pelo servidor; caminhos locais nunca são expostos.

## Fluxos críticos

| Operação | Pendente | Sucesso | Falha/recuperação |
|---|---|---|---|
| Diário | bloquear envio duplicado | redirect + flash, registro no histórico | 422, conteúdo preservado |
| Validar/devolver diário | ação pessimista | situação e parecer persistidos | item continua na fila |
| Documento | gerar protocolo único | acompanhamento na mesma tela | erro contextual sem protocolo falso |
| Notificação | bloquear publicação duplicada | central atualizada e badge recalculado | mensagem no módulo |
| Calendário | validar datas e público | evento publicado e notificação criada | 422 com formulário recuperável |
| Recuperação | resposta neutra evita enumeração de conta | código único, 30 minutos, revogação de sessões | código permanece inválido/expirado |
| Fechar/reabrir período | justificativa obrigatória | trilha de auditoria | estado anterior preservado |
| Upload | validação antes da entidade quando possível | arquivo vinculado ao registro | tamanho/tipo explicado |

## Integridade acadêmica

- Período fechado bloqueia lançamento de notas, chamada e diário dentro das datas correspondentes.
- Reabertura só existe para a Direção e exige motivo entre 5 e 500 caracteres.
- Documentos não são apagados; avançam por solicitado, processando, pronto, entregue ou indeferido.
- Acompanhamentos pedagógicos não somem: passam por aberto, monitorando e encerrado.
- Relatórios CSV vêm de linhas realmente persistidas; não exibir métricas fictícias.
- Valores iniciados por `=`, `+`, `-` ou `@` recebem proteção contra fórmula em CSV.

## Navegação e responsividade

- Título: `{{ view_title }} · FaeHub+`; módulo ativo usa `aria-current="page"`.
- O shell superior mostra no máximo sete destinos frequentes. Itens secundários usam o disclosure canônico “Mais”, com rótulos e links completos acessíveis por teclado.
- No espaço do aluno, `Agenda` reúne frequência e calendário escolar; `Comunicados` reúne avisos docentes e notificações persistentes; `Secretaria` reúne documentos e histórico acadêmico.
- A identificação da conta é textual. Não existe rota, personalização ou persistência de avatar.
- Rotas antigas continuam válidas para compatibilidade, mas não duplicam destinos na navegação principal.
- Conteúdo P1 colapsa para uma coluna abaixo de 980 px.
- Listas densas viram blocos; rótulos não desaparecem. Conteúdo completo não depende de tooltip.
- Datas usam controles nativos quando a aparência do popup não é requisito de marca.
- Matrículas usam busca e paginação no servidor, com estado na URL e dez linhas por página.
- Filtros locais permanecem apenas em conjuntos pequenos; acima de 50 itens devem migrar para URL/paginação do servidor.

## Feedback e resiliência

- Mutações são pessimistas e retornam ao módulo somente após commit.
- Tokens CSRF são específicos da sessão em todos os formulários, inclusive recuperação pública.
- Botões são desabilitados após submit; falha não apaga entradas não sensíveis.
- Senhas, códigos e tokens não entram em logs, flashes, URL ou armazenamento do navegador.
- O status de leitura fica no banco e acompanha a conta em outros dispositivos.
- Comunicados lidos podem ser descartados sem apagar a publicação original. O descarte é individual, persistente e reversível pela área `Descartados`; itens não lidos não podem ser descartados.
- Abrir uma conversa marca como lidas somente as mensagens recebidas daquele participante. A tela mantém lista de conversas, histórico cronológico em balões e envio no próprio contexto; o assunto legado não é exigido em novas mensagens.
- `prefers-reduced-motion` remove transformações e reduz transições.

## Dados e segurança Supabase

- Migração P0 complementar: `20260926133712_complete_p0_academic_core.sql`.
- Migração P1: `20260925191206_p1_school_operations.sql`.
- Preferências individuais de comunicados: `20260928201235_communication_preferences.sql`.
- A aplicação usa conexão PostgreSQL direta no servidor Flask.
- RLS está ativo e os papéis públicos `anon` e `authenticated` não recebem acesso às tabelas; portanto, não há políticas públicas nesta fase.
- O acesso deve migrar para políticas por usuário somente quando Supabase Auth for adotado conscientemente.
- SQLite permanece fallback de demonstração e executa o mesmo contrato funcional.

## Verificação obrigatória

- `python -m unittest discover -v`.
- Testes P1: perfis autorizados, diário, documento, notificação, anexo e código de recuperação.
- Verificar desktop 1440 px, tablet 900 px, celular 390 px, teclado, foco, alto contraste e movimento reduzido.
- Auditoria visual deve cobrir vazio, erro, hover, foco, diálogo e conteúdo longo.
- Conferir advisors do Supabase após DDL; `RLS enabled no policy` é esperado enquanto a Data API pública permanecer fechada.
