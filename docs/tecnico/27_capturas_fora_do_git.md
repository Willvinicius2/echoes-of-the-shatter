# Capturas de revisão ficam fora do Git

O histórico do repositório chegou a 822 MB porque capturas, prévias de render e PNGs de revisão entravam no Git a cada PR. Cada PNG de revisão fica no histórico para sempre, mesmo depois de apagado.

## Regra
- Capturas e prévias de revisão **não são commitadas**. Isso vale para `previas/`, `previews/`, `capturas/`, `capturas_*/` e saídas de `AutoTeste` (`godot/capturas_arqueiro/`). O `.gitignore` já cobre esses nomes.
- Onde guardar: na pasta compartilhada do projeto, `/mnt/project-files/capturas/<assunto>/` (anexe à resposta da thread para o revisor), ou no artefato do CI. Os workflows `capturas_*.yml` já publicam artefato e a branch temporária `capturas/pr-<N>`; apague essa branch depois do merge.
- No PR, cite o caminho ou o artefato em vez de adicionar o PNG.
- O que o jogo carrega (`godot/art*/`, texturas e sprites aprovados) continua no Git. PNGs de documentação que os `.md` realmente referenciam (por exemplo `docs/arte/sprites2d/capturas_cripta/*.png` da raiz) podem ficar, se pequenos; binários grandes vão para o LFS.
- Dúvida entre guardar ou não: não commite.

## Limpeza feita (esta mudança)
Removidos do `master` ~326 arquivos de revisão sem nenhuma referência no jogo, nos scripts ou nos documentos: prévias do Arqueiro e dos módulos do cenário, capturas da arquitetura, `godot/capturas_arqueiro/` (com os `.import`) e as capturas de ancoragem e lapidação da Cripta. Isso reduz o checkout em cerca de 300 MB. Os `.md` dessas pastas ficaram.

## O que não foi feito
O `.git` continua com cerca de 822 MB, porque os arquivos removidos seguem no histórico. Reduzir isso exigiria reescrever o histórico (`git filter-repo` e force-push), que muda todos os hashes e invalida branches, PRs e clones. Decisão do Will, caso queira.
