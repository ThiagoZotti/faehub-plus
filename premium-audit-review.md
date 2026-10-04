# Revisão do relatório estático P1

O relatório `premium-audit.json` registra 14 ocorrências de `affordance.actionless-button` em `templates/p1/estagios.html`.

Elas são falsos positivos do analisador estático: os botões usam eventos registrados em `static/p1/internships.js`, enquanto a regra atual detecta somente ações inline (`onclick`, `@click` ou `v-on:click`). Os controles foram verificados no navegador — abertura e fechamento dos diálogos, filtros, limpeza, edição, arquivamento, restauração e validação do formulário — e também pelos testes de fluxo em `test_internships.py`.

Não foram adicionados manipuladores inline apenas para satisfazer o analisador, porque a política CSP do aplicativo os bloqueia e a separação entre HTML e JavaScript é a opção mais segura.
