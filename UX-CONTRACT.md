# UX Contract — FaeHub+ P0/P1

## Contexto

- Público: alunos, responsáveis, professores, coordenação, secretaria e direção da ETESC/FAETEC.
- Locale: `pt-BR`; fuso: `America/Sao_Paulo`; calendário gregoriano.
- Meta de acessibilidade: WCAG 2.2 AA.
- Fontes de verdade: `ROADMAP.md`, autorização em `app.py`/`director.py`, dados em `database.py`/`p1_operations.py` e migrações em `supabase/migrations/`.
- Direção visual canônica: `DESIGN.md`; `campus-electric.css` cobre aluno, professor e direção. `staff-modules.css` adapta todos os módulos docentes/administrativos; `staff-reference.css` compõe seus painéis. `arrival-electric.css` adapta o login em tela cheia. Responsável mantém `campus-bright.css`; ativação/recuperação continuam intactas. A logo aprovada é `static/logo-faehub.webp`.

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

### Horários configuráveis — 15/10/2026

- Owner: `school_timetable.py`, Estrutura → Horários e o formulário P0 existente.
  Select e time permanecem nativos, com popup e interação pertencentes à plataforma.
- Direção cadastra/edita somente em turma/ano em planejamento ou ativo; anos
  encerrados são consultáveis. Arquivar preserva o registro; restaurar revalida
  conflitos. Confirmação de arquivamento usa `CampusActions`, sem diálogo nativo.
- Grade semanal recorrente: intervalos contíguos são aceitos; sobreposição de
  turma/sala/docentes vinculados é bloqueada, inclusive no vínculo docente criado
  depois da grade. Campos não sensíveis são preservados após erro.
- A sala explícita prevalece sobre a sala da turma. Docentes vêm de vínculos
  persistidos, não dos nomes da imagem de referência. Não se promete agendamento
  de substituições, exceções de feriados ou atribuição individual em cotutoria.
- Criação/edição retorna à lista da turma/página selecionadas. Edição tem URL
  própria na mesma área; Novo horário volta à criação. A listagem mostra até 50
  registros por página e mantém rolagem natural do documento/formulário.
- Revisão do registro impede sobrescrever uma edição concorrente. Escritas de
  grade/vínculos compartilham lock transacional no PostgreSQL. Auditoria conserva
  os valores anteriores/novos; não há exclusão física de horários.
- Painel/horário do aluno depende da matrícula ativa e da grade publicada; o
  professor vê somente horários de seus vínculos vigentes. Vazio não herda 3110.
- Cadastro escolar e nome de exibição são distintos: nome/matrícula/turma vêm
  do banco. Perfis sem notas ou presenças não recebem os números das demos.

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
| Scrollbar | Shell FaeHub | `static/campus-system.css`, adaptador aluno `static/campus-electric.css` | página, navegação e tabela responsiva | desktop e celular |
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
- O shell dos perfis ainda não migrados mostra no máximo sete destinos frequentes; secundários usam o disclosure canônico Mais. No aluno, a sidebar mostra todos os destinos no desktop e o Mais reúne os secundários no celular, com rótulos e links completos acessíveis por teclado.
- No espaço do aluno, `Agenda` reúne frequência e calendário escolar; `Comunicados` reúne avisos docentes e notificações persistentes; `Secretaria` reúne documentos e histórico acadêmico.
- A identificação da conta inclui nome/turma e foto circular opcional; sem foto, aparecem iniciais. Não existe sistema de personagens. Menu da conta abre envio de JPG/PNG, remoção confirmada e saída. No aluno, Secretaria está na sidebar do desktop e em Mais no celular.
- Rotas antigas continuam válidas para compatibilidade, mas não duplicam destinos na navegação principal.
- No aluno, abaixo de 760px a barra inferior expõe os três primeiros destinos e **Mais**, que contém os demais módulos autorizados; no computador, todos os destinos estão na sidebar persistente. Demais perfis preservam barra superior/carrossel e breakpoint de 600px. Menus fecham ao navegar, clicar fora ou pressionar Escape; Escape devolve foco ao acionador. Foto/conta permanece no cabeçalho.
- O boletim exibe Nota 1, Nota 2, Média e Situação diretamente em tabela. Os filtros preservam os valores e a impressão inclui todas as disciplinas; em telas estreitas a tabela possui rolagem horizontal com acesso por teclado. A simulação é um disclosure separado e não altera registros.
- Conteúdo P1 colapsa para uma coluna abaixo de 980 px.
- Listas densas viram blocos; rótulos não desaparecem. Conteúdo completo não depende de tooltip.
- Datas usam controles nativos quando a aparência do popup não é requisito de marca.
- Matrículas usam busca e paginação no servidor, com estado na URL e dez linhas por página.
- Filtros locais permanecem apenas em conjuntos pequenos; acima de 50 itens devem migrar para URL/paginação do servidor.

### Variante visual do aluno

- Todos os módulos do aluno compartilham `campus-electric.css`; o login e os painéis iniciais de professor/direção reutilizam esse owner na etapa seguinte. Nenhuma conta é desbloqueada para demonstrar o visual.
- Lista de atividades preserva os formulários e anexos reais. `campus-modules.js` é o owner dos filtros e da validação de entrega; a busca local tem botão explícito de limpar, atualização imediata e foco devolvido ao campo. O estado transitório de busca continua local, como os filtros existentes; o filtro de pendências vindo do painel permanece na URL.
- Entrega vazia mostra erro associado à resposta e move foco para ela; envio válido bloqueia duplicação e apresenta `Enviando…` sem reduzir o botão. Voltar pelo histórico restaura o estado disponível do botão. O campo mantém oito linhas, no mínimo 200px e rolagem interna, sem redimensionamento manual.
- Médias continuam em texto; barras de nota são decorativas (`aria-hidden`) e derivadas dos valores reais. Impressão remove barras e navegação.
- Seletores de matrícula/documento e mês permanecem nativos: a geometria e interação dos popups pertencem à plataforma. A página e os formulários mantêm altura natural; somente listas, tabela, menu e diálogos limitam sua própria rolagem quando necessário.

### Variante das três telas (12/10/2026)

- O novo pedido autoriza somente login e `/painel` docente/direção. `electric_view` em `base.html` limita CSS e sidebar a esses painéis, além do aluno já migrado. Responsável e demais rotas não recebem a classe nem o asset Electric.
- Navegação dos painéis usa a lista de destinos já autorizados, sem ampliar acesso. Foto opcional, iniciais, ações de conta e seus diálogos reutilizam o owner existente. No celular, três destinos e Mais permanecem disponíveis; documentos e formulários externos mantêm o shell anterior.
- Login conserva IDs dos campos, máscara/revelação, seleção de perfil por teclado, CSRF, erro, bloqueio de duplicação e confirmação explícita antes de entrar. Seleção visual não concede perfil; a conta autenticada determina o acesso no servidor. Sem contas demo desbloqueadas, novos botões SSO ou alteração de senha.
- Números do painel vêm de `teacher_overview` e `director_section`/`p1_metrics`; ausência de aulas ou vínculos conserva o estado vazio verdadeiro. Atalhos conduzem às operações existentes; não apresentam ações fictícias.
- Impressões, e-mails, convites e recuperação não são redesenhados. A auditoria automatizada verifica a ausência do tema nas rotas fora do escopo; não substitui inspeção visual no navegador.

### Reparação visual orientada aos novos mockups

- Referências: `docs/mockups/professor-v1.png` e `diretor-v1.png`, localizadas no chat solicitado. Composição dos dois painéis em `staff-reference.css`, sem estender o tema às outras rotas.
- Login conserva o mesmo POST, CSRF, nomes/IDs e confirmação de entrada. O quadro tem largura máxima e altura natural, e o texto inferior não reutiliza posicionamento de grade antigo. Os SVGs dos perfis não dependem de sessão autenticada.
- `teacher_overview.class_summaries` agrupa somente as turmas já autorizadas e conta a lista correspondente, sem exibir matrículas de outra turma. A direção usa `list_calendar_events('admin')`, limita a prévia a dois eventos de hoje em diante (America/Sao_Paulo) e mantém link para o calendário completo.
- Valores, nomes, horários e lugares fictícios dos mockups não são gravados nem exibidos como reais. Dias sem evento preservam estado vazio. A tabela informa quantidade de vínculos, não uma certificação de completude.
- Revisão real em navegador isolado: três telas em 1440, 900, 390 e 320px; nenhuma largura de documento excedeu a janela. Também foram conferidos seleção de perfil, máscara/revelação, erro de login vazio e Escape em menu/foto. Banco e perfis usados são descartáveis, sem acesso ao Supabase de produção.

## Feedback e resiliência

### FaeNet e anexos de atividades

- `/faenet` requer sessão ativa e conserva a revalidação por requisição. Todos
  os quatro perfis existentes recebem um destino no menu, sem ampliar suas
  permissões acadêmicas. O proprietário utiliza o mesmo destino do admin.
- As ações abrem `https://faenet.onrender.com/feed`, `/messages`, `/explore` e
  `/faemap` em nova aba, com `noopener noreferrer`. Não são enviados cookies,
  tokens, nome, turma ou matrícula do FaeHub. Login e sessões são independentes.
- Os rótulos anunciam nova aba também para leitores de tela; não se substituem
  links por botões para esconder a prévia de endereço do navegador.
- O anexo da atividade usa o mesmo macro visual das mensagens e um input nativo
  associado ao rótulo. Seleção por teclado, nome/tamanho, remoção com foco
  restaurado e erro inline são obrigatórios. Aceita um PDF/PNG/JPG/TXT/ZIP não
  vazio de até 5 MB; o backend continua validando tipo, conteúdo e autorização.
- O arquivo não é enviado ao selecionar: continua no multipart do formulário
  de entrega, com CSRF e bloqueio de duplicação existentes. Arquivos inválidos
  impedem o submit; resposta e seleção são preservadas para correção. Não se
  anunciam porcentagens de upload que o fluxo nativo não mede.

### Escopo integral confirmado em 12/10/2026

- A limitação anterior de três telas foi revogada por confirmação explícita do usuário: todas as páginas existentes de professor/direção recebem o tema e a navegação Electric. Os testes percorrem as rotas principais e complementares dos dois perfis. Perfil mantém o menu e diálogos reais; imagens conceituais não autorizam inventar recursos.
- Owners mantidos: `academic-core.js` na P0, `director.js` na gestão, `operations.js` em P1. `campus-actions.js` é o owner de confirmação/validação para as variantes docentes de linha, chamada e publicação; `teacher-workspace.js`/`teacher-studio.js` continuam donos das regras desses fluxos. Confirmações mantêm consequências e verbos explícitos, foco inicial em Cancelar, Escape e foco restaurado.
- Validação docente usa `novalidate`, erro associado ao campo e preservação dos valores. Campos e tokens enviados ao servidor são os mesmos. Antes de substituir notas/chamada ou arquivar, a confirmação do app é obrigatória. Submit duplicado é bloqueado, rótulos reservam largura e BFCache restaura botões; timers de reenvio são cancelados ao sair.
- Buscas de alunos e publicações têm limpar explícito com foco restaurado; filtro local continua restrito à lista já autorizada e não faz requisições remotas. Salvamento de uma linha continua avisando sobre outras alterações não salvas.
- Login não possui limite de largura ou margem externa; permanece responsivo e naturalmente rolável. O foco no campo de senha é visível na caixa externa, não no input interno. Não se altera máscara, senha, CSRF, autenticação ou confirmação de entrada.

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
- SQLite existe somente para testes isolados; o aplicativo usa Supabase, sem fallback de produção.
- Fotografias são normalizadas para JPEG de 320×320px, até 192 KB, sem metadados da imagem original. Originais são aceitos em JPG/PNG até 5 MB; imagens inválidas ou excessivas são rejeitadas antes de alterar a foto salva.
- A tabela `profile_photos` tem RLS ativo e não é acessível pela Data API pública. Leitura, alteração e remoção usam exclusivamente a conta da sessão Flask; o cliente não pode escolher outro usuário. O cache HTTP é privado e varia pelo cookie. A revisão da foto é consultada no máximo a cada cinco minutos durante a navegação, sem baixar os bytes nos templates.

## Verificação obrigatória

### Primeiro acesso por convite

- Conforme `AUTH-ROLLOUT.md`, a central identifica o **Proprietário do sistema**, distinguindo-o do **Responsável pelo aluno**. A conta protegida aparece somente para consulta pelos diretores, sem ações de alteração. O titular vê a reserva pendente e o convite com endereço fixo; após confirmar, o cabeçalho exibe sua autoridade. A seleção de novos cadastros não permite criar proprietários.

- Política de autorização e rollout: `AUTH-ROLLOUT.md`; operação canônica em `account_enrollment.py`.
- Direção prepara cadastro e confirma sua senha; sem configuração de e-mail, a interface anuncia cadastro pendente, nunca envio fictício.
- A direção demo não pode criar contas reais arbitrárias. O primeiro diretor só migra a própria conta para o e-mail autorizado em `FAEHUB_BOOTSTRAP_ADMIN_EMAIL`; a configuração pertence ao dono do servidor. Os demais convites requerem direção verificada.
- Convites só são ativáveis após aceitação pelo serviço de envio, valem 48h e são consumidos uma vez. Reenvio/cancelamento invalida o link anterior.
- O titular confirma o endereço autorizado recebendo o convite e define sua senha; perfil e vínculos permanecem sob controle da escola.
- No primeiro acesso, o titular escolhe nome de exibição com nome e sobrenome; erros preservam esse campo, nunca a senha. O formulário e o servidor aceitam senhas de 8 a 128 caracteres; recuperação usa a mesma regra. A propriedade institucional usa o nome inicial `admin` como exceção. Matrícula e identificação interna permanecem inalteradas.
- Convites usam o template canônico `templates/emails/invitation.html`, com tabela fluida até 560px, cores da identidade clara, fontes do sistema, CTA cobalto e alternativa textual; nenhum recurso remoto ou tracker.
- Ativação conclui no login, sem entrada automática. O e-mail confirmado funciona como alias da identificação escolar.
- Atalhos públicos com senhas demo não são exibidos. Encerramento das contas demo requer diretor ativado e confirmação da senha; dados escolares não são apagados.
- Recuperação segue mediada pela secretaria até a próxima etapa. Autenticador/SMS não são anunciados como funcionalidades prontas.
- Formulários públicos usam CSRF, erros textuais, botão de revelar senha, bloqueio de submit duplicado e tokens fora da URL HTTP. Confirmações da direção usam diálogo do app, não confirmação nativa.
- Owner visual das novas superfícies: adaptador compartilhado `static/campus-bright.css`; controles administrativos permanecem em `director.js`/`account_directory.html`.

- `python -m unittest discover -v`.
- Testes P1: perfis autorizados, diário, documento, notificação, anexo e código de recuperação.
- Verificar desktop 1440 px, tablet 900 px, celular 390 px, teclado, foco, alto contraste e movimento reduzido.
- Auditoria visual deve cobrir vazio, erro, hover, foco, diálogo e conteúdo longo.
- Conferir advisors do Supabase após DDL; `RLS enabled no policy` é esperado enquanto a Data API pública permanecer fechada.
