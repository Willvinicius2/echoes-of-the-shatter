# Método de modelagem 3D por partes (régua: estandarte da Cripta, PR 48)

Aprovado pelo Will. Exemplo completo em `art-src/cenario/modulos/estandarte/`. Copie a estrutura para cada objeto novo.

## Estrutura
- `lib.py`: contrato de medidas do objeto (eixos, alturas, larguras, pivô) e utilitários (`mat`, `add`, `box`, `cyl`, `bevel_obj`, `chip_corners`). Todas as partes usam os mesmos números, para encaixar sem conversa.
- Uma parte por arquivo (`pano.py`, `ferragem.py`, `base_corrente.py`) com `def build(L)`. Um agente por parte (Sonnet, subagente em paralelo), cada um só edita o seu arquivo.
- `build_estandarte.py`: importa as partes, junta, exporta `.glb` para `godot/art/models/` e renderiza prévias (`PARTES=`, `VISTAS=`, `AMOSTRAS=` filtram para iterar numa parte só).

## Ferramentas
- Blender em Python puro via `pip install bpy` (5.1) num venv; roda na nuvem, sem GUI. EEVEE não roda sem GPU: use Cycles CPU, `samples` 16–32 com denoise nas iterações.
- Um render por vez na máquina: `flock /tmp/render.lock <comando>`.

## Ciclo (o que fez o resultado sair bom)
1. Ver a referência (`referencias-cripta/*.png`) antes de modelar; mirar silhueta, proporção e materiais dela.
2. Mínimo de 6 ciclos curtos: render baixa amostragem → `Read` no PNG → corrigir → repetir. Vistas: frente, três quartos e closes de cada parte.
3. Comparar com a referência no fim; só entregar quando parecer arte de jogo, não plástico liso.

## Geometria (anti "massinha")
- Bevel real só nas arestas vivas (`L.bevel_obj`, ângulo 28–30°, 2 segmentos), perfis em camadas (molduras, cintas, bases escalonadas), rebites, espigões, curvas viradas em malha (`bevel_depth`).
- Pedra: blocos separados, cantos deslocados, lascas com boolean EXACT (`L.chip_corners`) e checagem de manifold; musgo em calotas baixas.
- Tecido: grade densa (84×200) com pregas em 3 frequências crescendo para baixo, solidify fino, barra feita de faces removidas (tiras, buracos), franjas em fitas. Nada de ruído suave.
- Ferro: malha subdividida com jitter controlado nos vértices (martelado) + textura.

## Texturas pintadas em Python (numpy + PIL), embutidas no .glb
- Albedo (pano 1024×2048, ferro 512², corrente 256²): cor base + manchas, desgaste, bordas escurecidas, bordado/riscos/ferrugem; sem luz assada.
- Normal map OpenGL (+Y) derivado de um mapa de altura (trama, relevo do bordado, costura, rugas), espaço Non-Color.
- UVs 0..1 com texel density uniforme; `L.mat(..., image=..., normal=...)` cria o material e empacota o PNG; exportar com `export_image_format='JPEG', export_jpeg_quality=88`.
- Pedra: manter o nome `M_PedraEscura` com cor sólida; o Godot troca pela pedra triplanar.
- Checar PNGs com `.claude/skills/create-game-assets/scripts/asset_report.py` e seguir `references/three-d-pipeline.md` (gates de geometria e material).

## Peso
- Antes de exportar, `DECIMATE` tipo DISSOLVE a 6° com delimit MATERIAL+UV (tira faces coplanares sem mudar o visual): 92 mil → 54 mil faces; `.glb` 13 → 10,7 MB (o resto é geometria com flat shading).

## Armadilhas
- `bmesh normal_flip()` inverte a ordem dos loops: atribuir UV pela posição do vértice, não por canto.
- Boolean pode deixar bloco aberto: verificar volume/manifold e refazer com outra variação.
- Pivô no centro da base, frente do módulo = +Y do Blender (-Z no Godot), metros.
