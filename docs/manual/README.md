# Documentação funcional e manual do FaeHub

Edição de 22 de outubro de 2026. O material foi produzido por leitura e navegação
da interface, com 55 capturas de uma cópia local descartável. Não foram alterados
registros de produção. Dados de demonstração não representam a situação da escola.

## Entregas

- [PDF ilustrado](../../output/pdf/FaeHub_documentacao_e_manual.pdf)
- [Manual em Markdown](manual.md)
- [Fonte editável de conteúdo](conteudo.json)
- [Inventário das telas navegadas](navegacao.json)
- [Diagramas UML em SVG](diagramas/)
- [Capturas originais do navegador](capturas/)

O PDF inclui manual dos quatro perfis, caminhos e regras das funcionalidades,
matriz de acesso, recuperação de senha e usuário, autenticador, integração com a
FaeNet, rotina técnica de backup, suporte, três diagramas de casos de uso, três
diagramas de classes e catálogo de 39 casos de uso.

Os diagramas são modelos conceituais conferidos com o código. Não afirmam que
existam classes Python de domínio ou herança de perfis. Relações por identificador
legado e o vínculo polimórfico de anexos não são apresentados como FKs diretas.

## Referência de versão

Base do projeto: `7c5b9a0`, acrescida da cópia de trabalho disponível na leitura.
A captura do Boletim inclui o piloto visual ainda não publicado nessa base.
Gmail, MFA, federação e Drive são descritos com requisitos, sem presumir que o
estado da cópia local corresponda à configuração de produção. As funções sociais
internas da FaeNet não fazem parte deste manual do FaeHub.

## Regenerar

Use o Python do runtime de documentos, com `reportlab` e `Pillow` disponíveis:

```text
python tools/build_user_documentation.py
python tools/check_user_documentation.py
```

O gerador não importa o app, não abre banco e não usa rede. Ele lê `conteudo.json`
e as capturas, gera o PDF, os SVGs, `manual.md` e o manifesto de hashes. Não execute
operações escolares ou um deploy para gerar a documentação.

O verificador requer também `pypdf` e confere hashes, capturas, casos de uso,
diagramas, texto do PDF, orientação e links locais. Ele não certifica o app em
produção nem substitui a revisão visual das páginas.

Após mudanças, renderize todas as páginas do PDF com Poppler, confira a composição
e verifique o texto e os links. Ao atualizar prints, preserve o contexto e substitua
dados de estudantes por dados de demonstração antes da captura, no ambiente
isolado. Não publique senhas, códigos, QR de MFA, tokens, logs ou bancos.
