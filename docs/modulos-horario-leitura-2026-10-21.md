# Revisão de módulos, horário e leitura — 21/10/2026

## Correções e decisões

- Agenda: fluxo em grid com 24px entre cabeçalho/calendário/histórico (18px no
  celular). Eventos formam trilha lateral; histórico antigo permanece separado.
- Horário: apresentação independente do contrato de sete dias do dashboard.
  Colunas com eixo comum, horários publicados intactos, lacunas explícitas e
  fim de semana somente quando há aula publicada. Terça da referência: Física
  07:00–08:40, sem aula cadastrada 08:40–10:40, Biologia 10:40–12:20.
  Não se declara um intervalo oficial nem se muda o cadastro da escola.
- Comunicados: composição de caixa de leitura, canais separados e ação global
  explícita. POST com CSRF; escopo resolvido no servidor; leitura em ambos os
  registros na mesma transação. Sem mensagens privadas, descartados ou leitura
  de outra conta. A central mantém o limite existente de 100 notificações.
- Notificações dos demais perfis: mesma ação de leitura, sobre a central
  autorizada da conta. Leitura de notificação não abre conversas privadas.
- Boletim usa resumo contínuo/tabela; Exercícios conserva estúdio/entregas;
  Secretaria destaca protocolos/situações; Mensagens prioriza conversa com
  cabeçalho compacto. Sem fotografia repetida nos módulos, sem novos assets,
  dependências, permissões ou indicadores ilustrativos.
- Notificações novas de documentos mostram a situação em português.
- Cabeçalhos em coluna não herdam o flex-basis de 440px do desktop como altura.

## Evidência de verificação

- Suíte completa: `tools/run_tests.py`: 212 testes, 211 aprovados e um teste
  opcional de backup PostgreSQL pulado por ausência do runtime portátil.
- Depois, teste adicional de rollback e verificação focada:
  `tools/run_tests.py test_module_refinements test_interface_copy`: 8 aprovados.
- Auditoria Premium strict: zero findings; lint oficial de DESIGN.md: zero
  erros/warnings. `node --check static/inbox-actions.js` e `git diff --check` OK.
- Navegador local, SQLite descartável e envio de e-mail desativado: leitura de
  três comunicados, recarga e persistência; ação desativada quando zerada;
  filtros de dia; eixo das seis aulas de 10:40 alinhado na mesma coordenada.
- Aluno em 390px: Agenda, Horário, Comunicados, Boletim, Exercícios, Secretaria
  e Mensagens sem overflow horizontal. Agenda com 18px de separação; desktop
  com 24px. Desktop conferido em 1280px e 1440px.
- Direção: Pronto/Abrir/Atualizar preservam 44×92px e sem overflow.
- Bases e credenciais de teste, capturas e logs ficam fora do commit.

## Reconciliação visual

| Regra anterior | Evidência/decisão | Ação |
|---|---|---|
| Foto diagonal em todo módulo | Usuário rejeitou repetição | Composições por tarefa; foto restrita às telas aprovadas |
| Ritmo 24/18px | Histórico da Agenda tocava a grade | Fluxo de página com gap verificável |
| Cabeçalhos responsivos | Base desktop virava altura de 440px | Flex-basis natural no celular |
| Tokens Electric | Mantidos no owner existente | Adaptador de composição sem nova paleta |
