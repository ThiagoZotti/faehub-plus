# Orientações do usuário para o FaeHub+

Após cada atualização solicitada pelo usuário, valide a alteração, crie um commit e envie ao repositório existente: https://github.com/ThiagoZotti/faehub-plus.git.

O usuário autorizou o envio como parte das futuras atualizações. Não peça confirmação novamente para cada push normal. Preserve alterações de terceiros e não faça force push. Se houver falha de autenticação, rede ou conflito, informe que a atualização ainda não foi enviada.

Não envie segredos, arquivos .env, bancos com dados escolares, logs, ambientes virtuais ou dependências locais (.run_dependencies, .test_dependencies, runtime_packages). Confira os arquivos preparados antes do commit.

O GitHub preserva o código e seu histórico; o banco de dados precisa de backup separado. Enviar o código não hospeda automaticamente a aplicação Flask.
