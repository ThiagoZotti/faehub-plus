# UX Contract

## Product context

- Audience: alunos, professores e direção da ETESC/FAETEC.
- Primary jobs: consultar vida acadêmica, operar turmas e administrar o campus.
- Target market(s): ensino técnico brasileiro.
- Active locales: `pt-BR`.
- Language/content register and native-review policy: português brasileiro direto e institucional; conteúdo escolar final é revisado pelo responsável do projeto.
- Timezone/calendar policy: `America/Sao_Paulo`, calendário gregoriano, datas visíveis em `dd/mm/aaaa`.
- Accessibility target: WCAG 2.2 AA

## Business-context sources

| Domain / scope | Authoritative source | Source type | Reviewed date |
|---|---|---|---|
| Permission model | `app.py`, `director.py`, `teacher_studio.py` | Código de autorização do servidor | 2026-09-25 |
| Data lifecycle | `database.py`, `supabase/migrations/` | Camada de persistência e migrações | 2026-09-25 |
| Deletion / retention | `ROADMAP.md` | Roadmap do produto | 2026-09-25 |
| Estágios P1 | `ROADMAP.md` | Escopo aprovado | 2026-09-25 |
| Dados acadêmicos | `school_roster.py`, `school_schedule.py` | Dados canônicos atuais | 2026-09-25 |
| Legal / regulatory copy | Não fornecido | Pendente de validação da escola | 2026-09-25 |

## Visual contract

- Project `DESIGN.md`: `DESIGN.md`.
- Token ownership model: runtime CSS canônico; `DESIGN.md` espelha as decisões estáveis.
- Runtime design-system/token source: `static/campus-system.css`, `static/academic.css`.
- Mapping/export/adapters: classes Jinja e variáveis CSS.
- Token drift gate: lint de `DESIGN.md`, auditoria premium e revisão visual em desktop/mobile.
- Supported themes: experiência autenticada escura e impressão clara para módulos acadêmicos.
- Design-context owner/review policy: alterações compartilhadas atualizam CSS, `DESIGN.md` e este contrato na mesma mudança.

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | Navegador | `<select>` em templates | native | teclado + formulário |
| Date | Navegador | `<input type="date">` | native | locale + teclado + teste de rota |
| Form | Flask/Jinja | rota correspondente e template | create / edit | validação do servidor + teste funcional |
| Scrollbar | CSS do campus | `campus-system.css` e módulo | geometry exceptions | inspeção visual |
| Toast | Shell do campus | flash + `#flashToast` em `base.html` | success / warning / info / error | live region + teste de resposta |
| CRUD | Rota Flask do módulo | `app.py` + `database.py` | return to same module | fluxo funcional completo |

## Component behavior

| Component | Default | Hover | Focus | Active | Disabled | Busy | Error |
|---|---|---|---|---|---|---|---|
| Button | rótulo e alvo 44px | realce tonal | anel visível | leve compressão | opacidade + cursor | largura preservada, `aria-busy` | mensagem adjacente |
| Icon button | nome acessível | realce tonal | anel visível | leve compressão | opacidade | geometria preservada | alerta no contexto |
| Input | rótulo persistente | borda mais clara | anel visível | n/a | fundo inativo | formulário bloqueia duplicata | campo + resumo |
| Secret input | masked | borda mais clara | anel visível | n/a | fundo inativo | submissão bloqueada | sem ecoar valor |
| Search | botão Limpar, sem debounce remoto | borda mais clara | anel visível | resultado filtrado | n/a | n/a em filtro local | estado sem resultados |
| Textarea | `resize: none` | borda mais clara | anel visível | n/a | fundo inativo | submissão bloqueada | campo + resumo |
| Table/list | linhas/cards estáveis | realce por borda/fundo | ações focáveis | seleção explícita | n/a | placeholders se remoto | vazio/erro nomeado |

## Dataset navigation

- Admin tables: preservam filtros e ação principal visível; paginação será definida quando o volume real exigir.
- Exploratory lists: busca e filtros locais para conjuntos pequenos; nenhum resultado mostra orientação e Limpar filtros.
- URL state: filtros locais da P1 de Estágios são transitórios por serem uma lista pequena carregada no servidor.
- Page size: sem paginação na P1; revisar acima de 50 vagas ativas.
- Empty/no-results/error/loading treatment: mensagem específica, ação de recuperação e nenhum vazio silencioso.
- Back/scroll restoration: navegação normal do navegador; mutações retornam à rota do módulo.
- Selection scope: não há seleção em massa na P1.

## Flow ledger

| Operation | Trigger | Pending | Success destination | Success feedback | Failure recovery | Focus outcome | Source ref |
|---|---|---|---|---|---|---|---|
| Create | botão Publicar vaga | botão bloqueado | `/estagios` | toast flash | formulário reabre preenchido | título do diálogo/erro | `ROADMAP.md` |
| Edit | ação Editar | botão bloqueado | `/estagios` | toast flash | formulário reabre preenchido | título do diálogo/erro | `ROADMAP.md` |
| Search | digitação/filtro | local imediato | mesma tela | contagem atualizada | Limpar filtros | busca permanece focada | `ROADMAP.md` |
| Cancel/back | fechar diálogo | n/a | mesma tela | nenhum | rascunho preservado na sessão | volta ao disparador | `UX-CONTRACT.md` |
| Soft-delete | Arquivar/Restaurar | confirmação do app | `/estagios` | toast flash | estado anterior preservado | cabeçalho da lista | `ROADMAP.md` |
| Hard-delete (irreversible) | não disponível | n/a | n/a | n/a | n/a | n/a | `ROADMAP.md` |

## Navigation and responsive behavior

- Route document title policy: `{{ view_title }} · FaeHub+` em `base.html`.
- Route error / 403 page behavior: erro amigável para navegação; autorização rejeitada no servidor.
- Breadcrumb/tab/route-state policy: módulo ativo marcado com `aria-current="page"`; carrossel segue a ordem de `NAV`.
- Sidebar/drawer/bottom-sheet transformation: barra superior possui rolagem horizontal; módulos mantêm conteúdo em uma coluna no celular.
- Responsive table strategy: listas se tornam blocos; rótulos permanecem visíveis.
- Truncation/full-value access: conteúdo de negócio não depende de tooltip; detalhes exibem valor completo.
- Focus restoration and sticky-obstruction policy: diálogos nativos devolvem foco ao disparador; cabeçalho não cobre foco dentro do conteúdo.

## Overlays and feedback

- Dialog primitive: `<dialog>` nativo, com botão fechar e clique no backdrop opcional.
- Destructive confirmation levels: arquivamento reversível usa diálogo de confirmação do app; exclusão irreversível não existe na P1.
- Toast placement/duration/deduplication: stack compartilhada no shell, `role=status`, mensagens do mesmo redirect são consolidadas pelo fluxo Flask.
- Alert/banner scope and persistence: validação pertence ao formulário; falha global aparece no topo do módulo.
- Tooltip delay/dismissal: não usar tooltip para informação obrigatória.
- Unsaved-changes behavior: rascunhos de formulários docentes usam `sessionStorage`; fechamento não apaga até submissão bem-sucedida.
- Layer/z-index contract: dialog > toast > navegação > conteúdo.

## Async and resilience

- Mutation default: pessimista, com confirmação do servidor antes do feedback.
- Idempotency and duplicate-submit policy: botão é desabilitado após submissão; operações de arquivo atualizam um estado único.
- Auto-save/draft recovery: rascunho local por usuário e diálogo para criação/edição de estágio.
- Offline/read-stale/write behavior: sem escrita offline; falha de rede preserva rascunho local.
- Retry/backoff/timeout behavior: submissão tradicional do navegador; usuário pode reenviar após falha.
- Version conflict and multi-tab behavior: último salvamento válido vence na P1; propriedade é verificada a cada mutação.
- Session expiry/re-authentication: autorização central redireciona para login e tokens de formulário expiram com a sessão.
- Long-running progress and return path: não aplicável à P1.
- Stale-request cancellation/invalidation and pending-state ownership: filtros são locais; cada formulário controla seu próprio estado ocupado.
- Dialog/form preservation and retry after mutation failure: servidor devolve 422 e o cliente reabre o diálogo com os dados enviados.

## Validation

- Schema/validation layer: validação de domínio na rota Flask e restrições no banco.
- Trigger timing: normalização ao receber POST; campos obrigatórios, comprimentos, enumeração, data e URL são verificados no servidor.
- Error summary/inline policy: resumo `role=alert` no módulo e valores preservados no formulário.
- Server error mapping: 400 para sessão/token, 403 para perfil proibido, 422 para dado/posse inválidos.
- Sensitive-value handling: credenciais e tokens nunca aparecem em mensagens ou rascunhos.
- `noValidate`, first-invalid focus, duplicate-submit prevention, unsaved changes, and submit recovery: formulários usam validação nativa mais servidor; JS impede duplicata e reabre falha no primeiro campo relevante.

## Permission and clipboard

- Permission UI strategy: navegação de Estágios só aparece para aluno e professor; POST docente é rejeitado para outros perfis no servidor.
- Clipboard copy policy: não aplicável à P1.
- Disabled-state explanation: controles indisponíveis recebem texto visível quando houver condição de negócio.

## Migration status (only for an inconsistent established product)

- Migration ledger location: `supabase/migrations/`.
- Canonical primitives and owners: shell em `base.html`; academic surface em `academic.css`; módulo em CSS/JS dedicado.
- Current risk-prioritized slices: Estágios P1, depois Cardápio semanal.
- Legacy import/token enforcement: novos módulos devem consumir variáveis `--campus-*` e padrões de foco do sistema.
- Rollout/rollback and removal gates: migrações são aditivas; arquivo reversível; SQLite continua fallback até Supabase ser configurado.

## Verification

- Required static commands: `python -m unittest discover -v`; lint `DESIGN.md`; auditoria premium estrita.
- Browser/device/locale/theme matrix: desktop 1440px, tablet 900px, celular 390px; pt-BR; modo escuro; movimento reduzido.
- Accessibility checks: teclado, foco, nomes acessíveis, contraste, live regions e diálogo.
- Native-language/domain review and target-user evidence: revisão pelo aluno responsável e professora orientadora.
- Component-state/visual regression coverage: default, hover, foco, vazio, sem resultados, erro e arquivado.
- Canonical sibling flow used for comparison: `professor_studio.html` e `aluno_exercicios.html`.
- Project audit command/result: registrar junto da entrega da P1.
- CRUD full-flow evidence: testes de criação, edição, arquivo, restauração e leitura do aluno.
- Failure-path evidence: token inválido, URL insegura, dado obrigatório ausente e tentativa de editar item alheio.
