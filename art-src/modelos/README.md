# Pipeline de acabamento de personagens (art-src/modelos)

Malha alta gerada por IA + folha aprovada -> malha de jogo pintada, com esqueleto, FBX e prévias. Saídas ficam fora
do repositório (`final_dir` do json do personagem) até o dono aprovar; só os scripts ficam aqui.

Rodar: `python scripts/run_pipeline.py m01_guerreiro [--from s5] [--only s7] [--skip s9]` (Blender 5.1 em `-b`; `pymeshlab`
e a pintura usam o Python do venv do TripoSG; TEMP/TMP em D:). Parâmetros por personagem em `scripts/chars/<id>.json`
(`MDL_OVERRIDE='{"chave":valor}'` ajusta sem editar o json).

| Etapa | Script | O que faz |
|---|---|---|
| s1 | `s1_prepare.py` | remove pedaços soltos, escala (corpo = chão até a coroa do elmo = 1,50 m; a pluma fica acima), pés em z=0, frente -Y |
| s2 | `s2_decimate.py` | sólido externo (voxeliza, enche o exterior, marching cubes: some camada interna) e pymeshlab: decimação quádrica -> alvo (`tris_target`), Taubin leve, malha fechada |
| s3 | `s3_game_prep.py` | normais para fora, suavização, arestas vivas por ângulo |
| s4 | `s4_rig.py` | ajusta o `Rig_Humanoid_Chibi` por marcos (`markers`, esquerda = +X, frente = -Y) e pesos automáticos, máx. 4 influências |
| s5 | `s5_uv.py` | UV 1024: ilhas por região do corpo (osso dominante) e eixo da normal, desdobramento angular, rosto e mãos com mais texel, empacotamento côncavo |
| s6 | `s6_bake.py` | AO e cavidade da malha alta por raios (BVH), 1 processo do Blender (`bake_shards`); só começa com >= 2 GB (BVH da malha alta reduzida, high_ao.ply) de memória virtual livre; gera `bake_ao.png` e `bake_cavity.png` |
| s7a/s7 | `s7a_export_geo.py`, `s7_paint.py` | projeta a folha (frente, costas, direita, esquerda espelhada) com alinhamento de silhueta, visibilidade e peso pela normal; preenche buracos em 3D; soma AO, cavidade, luz quente do alto-esquerda e sombra violeta; gera `T_<Nome>_BC.png` (1024) e `T_<Nome>_M.png` (512) |
| s8 | `s8_export.py` | 1 material, teste de pose com métrica de esticamento, `.blend` e `SK_<Nome>.fbx` com o preset do graybox (`gb_rig.export_fbx_rigged`) |
| s9 | `s9_previews.py` | prévias Eevee 1024 (frente, 3/4, costas, pose) e captura da câmera do jogo |
| s10 | `s10_captures.py` | capturas a 512, 88 e 65 px de altura para o Art Director |
| v | `verify_modelo.py` | conferência do FBX reimportado (eixos, escala, triângulos, material, UV, malha fechada, ossos, pesos) |

## Modo por peça (corpo base + 5 peças)

O esqueleto é ajustado uma vez ao corpo base e reaproveitado:
- `norm_from`: json `norm.json` do corpo base (s1 usa a mesma escala e o mesmo deslocamento, para as peças encaixarem).
- `markers_from`: json do corpo base com `markers` (s4 cria o rig com as mesmas posições de osso; os pesos são calculados na malha da peça).
- `asset` e `mesh_name` por peça (`SK_<Heroi>_Body`, `SK_<Heroi>_<Slot>_<Conjunto>`); `sheet`/`sheet_cuts` da folha da própria peça; `work_dir`/`final_dir` próprios.
Cada peça sai como FBX próprio com o mesmo esqueleto.

## Tipos (`kind`)

- `humanoid` (padrão): `Rig_Humanoid_Chibi`, marcos em `markers`; `no_legs` tira os ossos das pernas (espectro).
- `quadruped`: esqueleto simples sem Humanoid (~22 ossos: Pelvis, Spine, Chest, Neck, Head, Tail1-3, 4 pernas de 3 ossos).
- `static` (arma): sem esqueleto; `body_height_m` = comprimento, `pivot_frac` = posição da empunhadura, `single_view` = imagem única (costas = espelho), `delete_boxes_frac` apaga faces por caixa (corda do arco).

Máscara `T_<Nome>_M.png` (docs/04 3.5): R emissão (só o que brilha), G rim, B tinta; AO só no albedo. Ferramenta `tool_grid.py` gera vistas com grade para ler marcos.

## Tipo `prop` (cenario da Cripta, estatico, sem esqueleto): `env_*.py`

Kit de cenario (26 pecas SM_Cripta_*) a partir das malhas altas da IA (GLB) e dos recortes das folhas aprovadas c01 a c06.
Especificacao de cada peca (dimensoes do kit, pivo, triangulos, colisor) em `scripts/env_common.py`; rodar com
`python scripts/env_run.py <peca|a,b|all> [--from a|b|c|d|e] [--only x]` (um processo por vez; espera 4 GB de memoria virtual
livre; `MDL_OVERRIDE='{"shell_close":6}'` ajusta sem editar a tabela). `env_f_prancha.py` (prancha), `env_g_scene.py` (cena de
teste 3 x 3 com a camera do jogo) e `env_h_verify.py` (reimporta os FBX e confere) rodam depois.

| Etapa | Script | O que faz |
|---|---|---|
| a | `env_a_import.py` | GLB -> `raw.ply` (pose da fonte: Z para cima, a imagem de entrada vista de -Y) |
| b | `env_b_geometry.py` | tira fios/folhas flutuantes e pedacos soltos; solido externo (fecha o fundo aberto da IA); decimacao ate `tris`; malha alta decimada (120 k) para a AO; escala NAO uniforme minima e pivo (`norm.json`); pecas `proc` (superelipsoide ou L por campo de distancia) quando a malha da IA e recusada |
| c | `env_c_uv_ao.py` | arestas vivas por angulo; UV 512 por ilhas planares na direcao da normal (a ilha da frente e a propria imagem da folha); AO da malha alta decimada por raios (BVH) |
| d | `env_d_paint.py` | projeta a imagem de entrada (alinhada por caixa + ECC) na frente, nas costas (espelho), nos lados (imagem girada 90 graus) e no topo (faixa alta); o que sobra recebe a mediana 3D; soma AO, luz do alto-esquerda e sombra violeta; mascara R emissao (fogo), G rim (ouro), B tinta (pano) |
| e | `env_e_export.py` | 1 material, FBX com o preset do graybox, `.blend`, json (`SM_Cripta_<Peca>.json`: colisor sugerido em coordenadas da Unity, triangulos, tamanho) e previas |

Pisos: topo em z = 0 (pivo no centro do topo); paredes: face de frente (-Y) em y = 0 e corpo para +Y; demais: centro da base.
A IA normaliza todo objeto num cubo de ~1,9 m; por isso a escala nao uniforme e grande em pisos (espessura x0,1) e paredes.
