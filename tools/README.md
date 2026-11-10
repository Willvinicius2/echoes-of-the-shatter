# Ferramentas do projeto

Scripts de apoio, um assunto por pasta. Rode sempre da raiz do repositório.

| Pasta | Para quê |
|---|---|
| `arte/` | Arte gerada por script: ícones, tokens, pranchas, UI com gpt-image (`ui_gpt_image/`), efeitos do Arqueiro (`fx_arqueiro/`) e os ícones definitivos do Arqueiro desenhados por código, sem serviço pago (`icones_por_codigo/`, doc 29). |
| `audio/` | Geração de áudio provisório. |
| `build/` | Export 2D do Godot e checagens do build. |
| `core/` | Build e testes do ShatterCore no Windows (`build_core.cmd`). |
| `dados/` | Validadores dos CSV de conteúdo e da história. |
| `git/` | Hook que confere se todo commit foi enviado ao GitHub. |
| `mapas/` | Geração das fases do mapa 2D (`gerar_fase_1.py`, que chama `marcos_fase1.py` no fim: estrada, marcos, bolsão e encontros; `aglomerados_fase1.py`) e `visao_geral_fase1.py` (visão geral anotada do mapa). `gerar_fase_2.py` gera a Pedreira dos Ecos (`fase_2.txt`, os PNG dos fossos e da ponte por `fosso_pixel.py`, `--visao` para a visão geral e as linhas de captura; ver `docs/arte/35_pedreira_dos_ecos.md`). |
| `painel/` | Gera o painel de progresso a partir de `docs/progresso/estado.json`. |
| `roteiro/` | Gera o roteiro do sócio. |
| `sprites2d/` | Montagem, recorte e limpeza das folhas de sprites 2D (heróis, inimigos, props, chão; `montar_marcos.py` faz as vergas do portão e da ruína e o baú do bolsão; `dessaturar_folhas_arvore.py` tira um tom do ciano da árvore `tree_teal_leaves`; `montar_pedreira.py` desenha por código os props da Pedreira: blocos, andaime, carrinho, pórtico, poste de lanterna, o portão de pedra e as lascas; `recolorir_piso_pedreira.py` e `manchas_piso_pedreira.py` fazem o chão dela; `cao_de_cinza/` anima o Cão de Cinza recortando a base aprovada e `arauto_de_pedra/` desenha o Arauto de Pedra a partir de um modelo 3D de pedra feito por código, os dois sem serviço pago: `docs/arte/36_animacao_por_codigo.md`). |
| `votacao/` | Componente de votação embutido no painel. |
