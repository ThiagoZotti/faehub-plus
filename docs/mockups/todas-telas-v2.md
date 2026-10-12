# FaeHub+ — pranchas completas por perfil

Geradas em 12/10/2026 com imagegen integrado, usando como referência visual a prancha original do aluno `output/branding/student-screens-mockup.png`, enviada no chat Desenvolvimento Faehub.

## Professor — 12 telas

Arquivo: `professor-todas-telas-v2.png`. Grade de quatro colunas por três linhas, com desktop e celular em cada módulo.

1. Painel
2. Minhas turmas
3. Lançar notas
4. Chamada
5. Diário
6. Exercícios
7. Mensagens
8. Avisos
9. Estágios
10. Calendário
11. Notificações
12. Perfil

## Direção — 15 telas

Arquivo: `diretor-todas-telas-v2.png`. Grade de cinco colunas por três linhas, com desktop e celular em cada módulo.

1. Painel
2. Usuários
3. Estrutura
4. Turmas
5. Secretaria
6. Coordenação
7. Diário
8. Histórico
9. Relatórios
10. Períodos
11. Calendário
12. Mensagens
13. Notificações
14. Configurações
15. Perfil

A cobertura corresponde aos módulos de navegação e às telas complementares identificadas em `NAV` e `VIEW_TITLES` de app.py, acrescida da proposta visual de conta/perfil. Perfil é uma proposta de tela dedicada para os controles de conta atualmente disponíveis no menu.

## Prompts e direção visual

Professor: gerar uma prancha panorâmica completa do FaeHub+ no formato da referência do aluno, com cabeçalho de marca e fotografia de campus ao anoitecer, fundo azul profundo, contornos elétricos e doze pares desktop/celular. Cada módulo deve ter conteúdo próprio: próxima aula, turmas, tabela editável de notas, chamada, diário, estúdio de atividades, conversa, avisos, estágios, calendário, notificações e conta. Títulos numerados legíveis, sem marca d'água, sem perspectiva e com indicação de dados ilustrativos.

Direção: gerar uma prancha panorâmica da mesma família visual, com quinze pares desktop/celular. Cada módulo deve exibir sua operação: panorama escolar, acessos, estrutura acadêmica, gestão de turmas, documentos, intervenções, validação de diário, histórico, relatórios, períodos letivos, calendário, mensagens, notificações, configurações institucionais e conta. Títulos numerados legíveis, sem marca d'água, sem perspectiva e com indicação de dados ilustrativos.

## Validação e limites

Inspeção visual confirmou os 12 módulos do professor e os 15 da direção, com versões desktop e celular, conteúdos distintos, grade completa e identidade consistente com a referência. Os mockups são imagens conceituais; textos internos pequenos podem apresentar imprecisões de geração. Nomes, fotos, números, datas e gráficos são ilustrativos. Funcionalidades e permissões devem ser conferidas no código antes de qualquer implementação. As pranchas não modificam as telas Flask.
