# Graybox (malhas provisórias)

Malhas provisórias geradas por script no Blender para o gameplay começar antes da arte final. Formas simples, cores planas, pivô nos pés e triângulos bem abaixo dos orçamentos do `docs/04_arquitetura.md` (seção 17.2). Nada daqui é arte aprovada: as prévias em `previews/` vão para a aprovação do dono antes de qualquer coisa entrar no jogo.

## Arquivos

| Caminho | Conteúdo |
|---|---|
| `scripts/gb_lib.py` | Construtor de malhas por primitivas, paleta, preset de exportação FBX, câmera e render das prévias |
| `scripts/gb_rig.py` | Definição do `Rig_Humanoid_Chibi` e exportação de esqueleto + malhas |
| `scripts/make_rig.py` | `fbx/Rig_Humanoid_Chibi.fbx` (só o esqueleto) e prévias dos ossos |
| `scripts/make_heroes.py` | `SK_Warrior`, `SK_Archer`, `SK_Mage` no esqueleto compartilhado → `heroes_graybox.blend` |
| `scripts/make_enemies.py` | 4 inimigos do Ato I e o Guardião da Cripta (`SM_`, sem esqueleto) → `enemies_graybox.blend`, teste de silhueta |
| `scripts/make_crypt_kit.py` | Kit modular da Cripta Partida (`SM_Cripta_*`) → `crypt_kit_graybox.blend` |
| `scripts/make_crypt_testroom.py` | Sala de teste de 16 × 16 m com o kit, o Guerreiro e 3 inimigos → `crypt_testroom_graybox.blend` |
| `scripts/verify_fbx.py` | Reimporta todos os FBX e grava `previews/_fbx_verify_report.json` |
| `scripts/build_all.py` | Roda tudo em ordem, cada etapa num processo novo |
| `fbx/` | FBX exportados + `T_Graybox_Palette_BC.png` (cor) e `T_Graybox_Palette_E.png` (emissivo) |
| `previews/` | Prévias PNG e relatórios JSON (`_rig_report`, `_heroes_report`, `_enemies_report`, `_crypt_kit_report`, `_crypt_testroom_report`, `_fbx_verify_report`) |

`.blend` e `.fbx` vão pelo Git LFS (`.gitattributes` da raiz).

## Como regerar

Versão usada nesta rodada: **Blender 5.2.2 LTS** como módulo Python (`bpy` 5.2.2, Python 3.13.16) no Ubuntu 24.04 da nuvem, com render Workbench por Mesa llvmpipe (EGL, sem GPU).

Nuvem ou Linux sem Blender instalado:
```
apt-get install -y libegl1 libegl-mesa0 libgl1-mesa-dri   # Workbench headless
python3 -m venv venv && venv/bin/pip install bpy==5.2.2    # exige Python 3.13
venv/bin/python art-src/graybox/scripts/build_all.py
```
Windows com o Blender instalado:
```
blender.exe -b --factory-startup --python-exit-code 1 -P art-src\graybox\scripts\build_all.py
```
Os caminhos saem da pasta do script (ou da variável `GB_ROOT`), então funciona em `D:\openclaude\EchoesOfTheShatter` e na nuvem sem editar nada. `verify_fbx.py` sai com erro se alguma conferência falhar.

## Convenções

- **Escala:** 1 unidade = 1 m, cena em metros (escala 1,0). Herói com 1,50 m.
- **Frente:** todo asset fica de frente para **−Y no Blender**, que vira **+Z no Unity**. Os scripts descrevem personagens em "espaço do personagem" (frente +Y, esquerda −X) e o `Builder.build(turn=True)` e o esqueleto giram 180° em Z.
- **Mapeamento Blender → Unity:** Unity (x, y, z) = (−x, z, −y). Os relatórios trazem as medidas nos dois sistemas.
- **Pivô:** personagens nos pés (centro, y = 0). Piso: centro do ladrilho com a face de cima em y = 0 (o ladrilho tem 0,18 m de espessura para baixo). Parede e arco: centro da base, sobre a linha da grade. Canto: na intersecção das linhas da grade. Pilar, escada e props: centro da base.
- **Grade:** 1 m; módulos de 2 m; paredes de 3 m. Ladrilhos em coordenadas ímpares, paredes de 2 m centradas em coordenadas ímpares ao longo da linha, arco de 4 m e cantos em coordenadas pares.
- **Nomes** (04 seção 4.4): `SM_` malha estática, `SK_` malha com esqueleto, `Rig_` esqueleto, `M_` material, `T_..._BC` cor. As malhas dentro de cada `SK_` levam o dono no nome (`SK_Warrior_Body`, `SK_Warrior_Hammer`, `SK_Warrior_Shield`).
- **Material:** um só, `M_Graybox_Palette`, compartilhado por todos os assets (04 seção 17.2 pede 1 material por herói, inimigo e kit). Cada primitiva tem UV no centro de uma amostra de 16 × 16 px da paleta de 256 × 256 e a mesma cor gravada como cor de vértice (sRGB). Cores emissivas (olhos, cristal, fogo) também aparecem em `T_Graybox_Palette_E.png`. A lista de cores está em `gb_lib.PALETTE` (só acrescentar no fim, porque a ordem fixa a posição na textura).
- **Skinning:** rígido por peça. Cada primitiva pesa 1,0 em um único osso (1 influência por vértice).

## Esqueleto `Rig_Humanoid_Chibi`

27 ossos (21 deformam): `root` → `Hips` → `Spine` → `Chest` → `Neck` → `Head`; `Left/RightShoulder`, `UpperArm`, `LowerArm`, `Hand`; `Left/RightUpperLeg`, `LowerLeg`, `Foot`, `Toes`; sockets `socket_weapon_r`, `socket_weapon_l`, `socket_cast`, `socket_head`, `socket_fx_ground` (não deformam). Os nomes são os de `HumanBodyBones`, então o mesmo FBX serve como **Generic** (decisão do 04 seção 3.3) ou **Humanoid** sem renomear: os 15 ossos obrigatórios do Humanoid estão presentes. Pose A (braços a ~60° para baixo): ao configurar Humanoid, usar "Enforce T-Pose".

## Preset de exportação FBX

`gb_lib.FBX_PRESET`: Forward **−Z**, Up **Y**, Apply Transform ligado, Apply Scalings **FBX Units Scale**, escala 1,0, sem leaf bones, todos os ossos (inclusive os sockets), suavização por face, cor de vértice sRGB, textura por caminho relativo.

Por que mudou em relação à primeira versão (Forward Z): com Forward Z o Blender grava no FBX um sistema de eixos girado 180° (FrontAxisSign −1, CoordAxisSign −1). O Unity converte qualquer sistema diferente do dele, então a raiz entraria girada 180° em Y. Com Forward −Z o arquivo declara o sistema Y-up padrão e o Unity não precisa girar nada.

O Apply Transform do Blender só é aplicado em malhas; no esqueleto a conversão de eixos viraria `Lcl Rotation (−90, 0, 0)` no nó `Rig_Humanoid_Chibi`. O `export_fbx_rigged` contorna isso na exportação: gira o objeto do esqueleto +90° em X, gira os ossos ao contrário (posições iguais) e restaura tudo depois. Resultado conferido no arquivo: todos os nós de topo com rotação 0 e escala 1, `UnitScaleFactor` 100 (1 unidade = 1 m).

## Importação no Unity (sugestão para o Frontend)

- Model: Scale Factor 1, Convert Units ligado, **Bake Axis Conversion desligado** (não deve ser necessário), Import Normals.
- Rig: Generic (ou Humanoid com Enforce T-Pose); Optimize Game Objects expondo os 5 sockets.
- Materials: Import via MaterialDescription (o URP cria o material com a textura de cor e a de emissão), ou um `M_Graybox` URP Lit com `T_Graybox_Palette_BC` em Base Map e `T_Graybox_Palette_E` em Emission.
- Textura da paleta: Filter Mode **Point**, sem mipmaps, sem compressão (cada cor ocupa só 16 × 16 px).
- **Confirmar no editor** (04 seção 17.1): rotação importada (0, 0, 0), escala 1, herói com 1,50 m olhando para +Z.

## Conferência (`verify_fbx.py`)

Reimporta cada FBX e confere dimensões, triângulos, pivô, materiais, UV e cor de vértice, skinning, ossos e nomes do Humanoid, além de ler do arquivo o que o Unity vai usar (eixos, `UnitScaleFactor`, rotação e escala dos nós de topo). Nos `SK_`, gira o osso `Head` 30° e confere que só as peças da cabeça se movem (prova o bind pose). Compara tudo com os relatórios de geração e com os orçamentos do 04 seção 17.2. O resumo fica em `previews/_fbx_verify_report.json` → `summary`.

## O que ficou simplificado

- Sem LODs: todas as peças estão abaixo de 1.000 triângulos (o 04 pede LOD só acima de 1.500 no cenário) e os personagens têm ~10% do orçamento; LOD1/LOD2 ficam para a arte final.
- Sem UV de pintura (só UV de paleta), sem colisores e sem animação.
- Inimigos e chefe continuam sem esqueleto (`SM_`), como na primeira versão; o 04 prevê rig próprio por família.
- Kit sem borda de abismo, ruína solta e os outros props da folha 07 (estandarte solto, vasos, velas, cristais).
- Mago com capuz pontudo e cajado com cristal num anel dourado, como manda o `CLAUDE.md` e a folha 04 (o `docs/03` seção 3.4 item 9 ainda fala em "chapéu pontudo").
