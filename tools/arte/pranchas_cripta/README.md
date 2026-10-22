# Pranchas de ângulos da Cripta

Gera, para cada `.glb` da Cripta (`SM_Cripta_*.glb`), uma prancha única de 4×4 com: 4 vistas ortogonais (+Z, -Z, +X, -X), 4 três-quartos, de cima, rasante, 3/4 alto (câmera do jogo), 2 vistas ortográficas de escala com boneco de 1,8 m, um 3/4 com boneco, a planta e um painel de medidas em metros (largura, profundidade, altura, triângulos). Serve para posicionar os objetos no Godot; **não** substitui a prancha de aprovação do objeto.

## Como rodar
```
cd tools/arte/pranchas_cripta
npm install
node gerar_pranchas.mjs <pasta dos .glb> <pasta de saída> [objeto ...]
# ex.: node gerar_pranchas.mjs ../../../godot/art/models /mnt/project-files/pranchas-cripta
```
Sem lista de objetos, gera todos. O nome do objeto é o do arquivo sem `SM_Cripta_` e `.glb`, em minúsculas e sem acentos (`colunacorrente`, `tapete_grande`).

Usa three.js e o Chromium headless do Playwright (renderização por software, ~5 a 15 s por objeto). Luz e fundo são fixos e neutros, por isso a cor pode diferir do render de aprovação.

Premissas: glTF com Y para cima e 1 unidade = 1 m (padrão do exportador do Blender). A "frente" do objeto não é padronizada: veja qual vista mostra a face principal.
