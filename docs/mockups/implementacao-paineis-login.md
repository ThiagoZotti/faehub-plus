# Implementação das referências — 12/10/2026

Pedido: usar os mockups do chat **Criar mockups para diretor e docente** e corrigir o login. Mantido o escopo das três telas: login e painéis iniciais docente/direção. Os commits de imagens `85737bd` e `40546e2` foram preservados.

## Referências e resultado

- Professor: `professor-v1.png`, com faixa do campus, três indicadores, próxima aula azul, correções, turmas em tabela e próximas aulas.
- Direção: `diretor-v1.png`, com quatro indicadores, fila de atendimento, calendário real e panorama das turmas.
- Login: quadro central com borda azul, imagem noturna já existente, credenciais em superfície opaca, ícones SVG e texto inferior sem sobreposição.
- Pranchas v2: complemento de identidade; os demais módulos não são alterados.

Não foram usados cartazes como interface, novos assets gerados, dados escolares fictícios, percentuais de crescimento ou busca global simulada. A logo aprovada permanece a mesma. As contas bloqueadas e a política de convites não foram alteradas.

## Verificação

O controle da janela do usuário permaneceu indisponível, mas a validação desta correção foi feita com **Playwright local em processo headless isolado**, com perfil temporário, somente em `127.0.0.1:5018` e banco descartável. Nenhuma sessão real do Chrome ou endpoint de produção foi controlado.

- Doze combinações de página/largura: login, professor e direção em 1440, 900, 390 e 320px; respostas HTTP 200, imagens carregadas, zero overflow horizontal do documento.
- Sem erros de JavaScript. Troca de perfil, revelar/ocultar senha, erro de usuário vazio, diálogo de foto e Escape, menu Mais e Escape passaram.
- Seis capturas reais, desktop e celular, inspecionadas visualmente. A captura inicial revelou conflito de estilo nas células da tabela e dependência indevida de ícones da sessão no login; ambos foram corrigidos e a revisão foi repetida.
- Suíte completa: 137 testes passaram em 157,988s antes da inclusão dos dois testes adicionais de agrupamento de turma e eventos do calendário. A execução final de `python -m unittest test_teacher_dashboard test_director -q` passou os 13 testes desses módulos, incluindo os dois novos, em 6,662s.
- Auditoria estrita da skill frontend-design-premium: zero achados no escopo P0 do manifesto. Não é certificação de acessibilidade global.
- `git diff --check` passou. Scripts/helpers, dados de teste, logs e dependências locais não entram no commit.

Limites: não foram testados aparelhos físicos, teclado virtual ou toda a matriz de impressão/alto contraste. O lint externo de DESIGN.md continua pendente pelo bloqueio de execução do pacote remoto; não foi contornado. Publicação no Render não foi confirmada por este teste local. Reversão requer somente revert do commit, sem alteração no banco.
