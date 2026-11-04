# Teste v7 de pixel art: proporção humana (04/11/2026)

Motivo: o arqueiro v6 (PR 202) tinha cabeça de ~14 de 40 unidades (cerca de 3 cabeças de altura), lia como bloco. "Pixel FX" do Will = `patch-gg/pixelfx` (MIT), já no catálogo: gera efeitos e golpes com um boneco 3D de esqueleto de 24x38, não personagens; serve para VFX, não para o corpo do arqueiro. Geradores de IA (PixelLab: 4/8 direções e animação por esqueleto, tela até 128x128 e 400x400 no plano Artisan, planos pagos) ficam como opção futura; não usados aqui (custo e licença a confirmar).

Mudanças (`tools/sprites2d/gerar_arqueiro_pixel_v7.py`, mesmo método do v6):
- quadro 72x72, figura de ~54 px (escala 1,32), cerca de 5 cabeças;
- remapeamento vertical: pernas x1,75, tronco x1,12, cabeça x0,66;
- membros mais finos, saia da túnica menor, capuz e aljava reduzidos, botas menores.

Cenário (`tools/sprites2d/gerar_cenario_pixel_teste.py`): piso de lajes irregulares 32x32 sem emenda e braseiro de pedra 32x48, pixel a pixel, mesma paleta fria/quente. Arquivos em `godot/art2d/teste_v7/` (não ligados ao jogo ainda).

Pendente: cabelo direcional (E/NE/N ainda uma massa), rosto de 9 px mais legível, animação de corrida com balanço de braços, calibrar `sprites_escala.csv` e âncoras para 72 px.

## r4 (04/11/2026): ligado ao jogo
Aprovado como nível alvo pela direção visual (r3). Ajustes finais: joelho marcado na corrida, boca clara de 2 px, arco menor e afastado do torso em S, aljava fria. As folhas v7 (quadro 72, pivô 36,64) substituem as do v6 em `godot/art2d/sprites/arqueiro/`; `sprites_manifest.csv` e as âncoras de ataque foram recalculados (`gerar_arqueiro_pixel_v7.py --ancoras` x 2,5). A escala de mundo (2,5) não mudou, então a figura (54 px) fica maior na tela que a v6 (42 px), de propósito, para a silhueta humana ler em 2K.

Piso de lajes e braseiro de `godot/art2d/teste_v7/`: o braseiro foi aprovado; o piso é **provisório** (não ligado ao jogo) até o próximo PR curto.
