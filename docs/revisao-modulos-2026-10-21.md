# Chamada utilizável e coerência entre módulos — 21/10/2026

## Problemas reproduzidos

A primeira abertura da chamada renderizava presença, ausência, marcação em lote
e salvar como controles desabilitados. Disciplina/horários ficavam em um GET
separado das presenças: completar os campos sem consultar mantinha a lista
bloqueada. O teste anterior enviava um POST completo e não exercitava essa
primeira interação. A validação foi ampliada para cobrir esse caminho real.

Na Secretaria, links e botões herdavam regras diferentes de tipografia e tamanho;
a edição de um documento pronto ainda selecionava Em processamento e esvaziava
a observação, apesar do estado salvo ser outro.

## Correções

- Consulta de turma/data continua GET. Disciplina, horários e presenças estão
  no mesmo POST. Marcação individual e em lote não dependem de consulta prévia;
  salvar aponta os campos faltantes. Carregar chamada salva não escreve dados.
- Vínculos, matrícula vigente, período aberto, horário passado, conflito e CSRF
  continuam validados no servidor. A revisão de uma aula não é reutilizada ao
  selecionar outra; correções continuam confirmadas e auditadas.
- Documento abre com situação e observação atuais. Abrir continua link de
  consulta; Atualizar abre o diálogo; Pronto permanece texto estático.
- Após aprovação explícita da revisão integral, `module-system.css` unifica
  cabeçalhos, cards e geometria de controles dos módulos dos quatro perfis.
  Login, painéis e portal FaeNet conservam a composição aprovada. Tokens e
  fotografia existentes são reutilizados, sem dependências novas.

## Evidência

- Suíte isolada: 207 testes, 206 aprovados e 1 opcional de backup PostgreSQL
  ignorado. Mais uma execução focal dos três testes de módulos após preservar
  a observação. `tools/run_tests.py` é o comando configurado para evitar acesso
  acidental a um banco real durante os testes.
- Auditoria estática estrita dos owners configurados: zero achados.
  Lint oficial de DESIGN.md: zero erros/avisos. Sintaxe JavaScript validada.
- Navegador local: presença/ausência, validação de horário vazio, marcação em
  lote com confirmação, salvar, recarregar, cancelar/confirmar correção e
  frequência consultada como aluno. Em celular, um novo salvamento preservou
  33 presentes/1 ausente após recarregar.
- Módulos do aluno e direção em computador/celular, professor em computador/
  celular e responsável em celular: nenhuma largura de documento ultrapassou
  a janela. As sete áreas da Estrutura foram abertas em 390 px. Secretaria
  adicionalmente conferida em 320 px; diálogo em 390 px preservou foco e seleção.
- Pronto/Abrir/Atualizar medidos em 44×92 px no computador; em 390 e 320 px,
  os três compartilham a largura disponível e mantêm 44 px de altura.

## Limites

Ensaio com banco descartável e identidades de teste. Nenhuma presença, documento
ou solicitação fictícia foi gravada em produção. Testes de renderização cobrem
42 rotas/perfis; isso não certifica manualmente todos os estados possíveis de
todas as funções. Não houve migração ou alteração de permissões. A publicação
deve ser confirmada no Render antes de anunciar disponibilidade.

## Reconciliação visual

| Contrato | Desvio encontrado | Resolução |
|---|---|---|
| Identidade Electric compartilhada | Módulos sem o mesmo acabamento do painel | Adaptador comum; painéis preservados |
| Controles coerentes | Tipografia/caixa variavam entre link e botão | Receita única e medidas verificadas |
| Estado de documento preservado ao editar | Seleção voltava a Em processamento | Seleção e observação carregadas do registro |

A revisão é de composição e componentes, não uma troca de identidade nem
implementação de funcionalidades ilustrativas da FaeNet/FaeMatch.
