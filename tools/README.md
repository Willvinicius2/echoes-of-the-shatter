# Ferramentas do projeto

Scripts de apoio, um assunto por pasta. Rode sempre da raiz do repositório.

| Pasta | Para quê |
|---|---|
| `arte/` | Arte gerada por script: ícones, tokens, pranchas, UI com gpt-image (`ui_gpt_image/`), efeitos do Arqueiro (`fx_arqueiro/`). |
| `audio/` | Geração de áudio provisório. |
| `build/` | Export 2D do Godot e checagens do build. |
| `core/` | Build e testes do ShatterCore no Windows (`build_core.cmd`). |
| `dados/` | Validadores dos CSV de conteúdo e da história. |
| `git/` | Hook que confere se todo commit foi enviado ao GitHub. |
| `mapas/` | Geração das fases do mapa 2D (`gerar_fase_1.py`, que chama `marcos_fase1.py` no fim: estrada, marcos, bolsão e encontros; `aglomerados_fase1.py`) e `visao_geral_fase1.py` (visão geral anotada do mapa). |
| `painel/` | Gera o painel de progresso a partir de `docs/progresso/estado.json`. |
| `roteiro/` | Gera o roteiro do sócio. |
| `sprites2d/` | Montagem, recorte e limpeza das folhas de sprites 2D (heróis, inimigos, props, chão; `montar_marcos.py` faz as vergas do portão e da ruína e o baú do bolsão). |
| `votacao/` | Componente de votação embutido no painel. |
