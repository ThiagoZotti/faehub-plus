# Referência visual — login, professor e direção

Imagem original enviada pelo usuário em 09/10/2026:
`login-professor-direcao-mockup.png`.

Status: **implementação autorizada em 12/10/2026 somente nas três telas**.
O usuário pediu login e painéis iniciais do professor e da direção.
Demais telas desses perfis e área do responsável permanecem inalteradas.

O arquivo foi copiado integralmente, sem gerar outra imagem, recortar ou editar.
O mockup apresenta login à esquerda, painel docente ao centro e painel da direção
à direita, com fundo azul profundo, destaques elétricos e navegação lateral.

Contrato aplicado na implementação:

- A imagem orienta o visual, não as permissões ou funcionalidades.
- Nomes, métricas, gráficos e situações são ilustrativos; usar dados reais.
- Botões Google/Microsoft e indicadores de disponibilidade não comprovam
  integrações ou monitoramento existentes.
- Preservar a logo já aprovada, salvo nova decisão explícita do usuário.
- Não usar a marca d'água OpenArt nem o cartaz inteiro como interface funcional.
- Autenticação e acessos permanecem iguais. O tema é limitado por rota em `base.html`.

O rollout usa `campus-electric.css` como owner de tokens/shell e
`arrival-electric.css` como adaptador do login. A foto do login é o asset
original existente, escurecido por CSS; nenhuma imagem foi gerada.
Professor usa contagens reais dos seus vínculos e entregas. Direção usa
cadastros e filas persistidos; gráfico de tendência e SSO do cartaz não foram
inventados. A validação visual em navegador foi bloqueada pelo controle de
Computer Use por não conseguir identificar com segurança a URL do Chrome.
Não houve contorno desse bloqueio. Testes e validação estática são registrados
na entrega; fidelidade pixel a pixel e publicação no Render não foram confirmadas.

## Validação de 12/10/2026

- `python -m unittest discover -q`: 137 testes passaram em 152,725s,
  com banco temporário descartável e transporte de e-mail simulado.
- Novos contratos de navegação verificam o tema somente nos dois painéis,
  ausência do tema nas outras rotas docentes/administrativas e no responsável,
  preservação das doze rotas do aluno e identificação da nova logo no login.
- `node --check static/arrival.js` e `git diff --check`: passaram.
- Auditoria estática `audit_project.py --mode strict`: zero achados no escopo
  P0 configurado em `premium-ui.json`; não certifica acessibilidade global.
- O lint externo oficial de DESIGN.md continua bloqueado pela autorização de
  execução do pacote remoto, como registrado em `electric-rollout.md`.
- CSS inclui desktop, tablet, celular, foco, contraste semântico e movimento
  reduzido; os layouts novos não foram medidos em navegador/aparelho físico.
- A prévia local foi encerrada; helper, dados de teste e logs não são enviados.

Para reverter, reverter o commit visual; não há migração de banco necessária.
