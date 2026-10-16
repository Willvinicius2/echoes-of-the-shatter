# Pipeline de acabamento de personagens (art-src/modelos)

Malha alta gerada por IA + folha aprovada -> malha de jogo pintada, com esqueleto, FBX e prévias. Saídas ficam fora
do repositório (`final_dir` do json do personagem) até o dono aprovar; só os scripts ficam aqui.

Rodar: `python scripts/run_pipeline.py m01_guerreiro [--from s5] [--only s7] [--skip s9]` (Blender 5.1 em `-b`; `pymeshlab`
e a pintura usam o Python do venv do TripoSG; TEMP/TMP em D:). Parâmetros por personagem em `scripts/chars/<id>.json`
(`MDL_OVERRIDE='{"chave":valor}'` ajusta sem editar o json).

| Etapa | Script | O que faz |
|---|---|---|
| s1 | `s1_prepare.py` | remove pedaços soltos, escala (corpo = chão até a coroa do elmo = 1,50 m; a pluma fica acima), pés em z=0, frente -Y |
| s2 | `s2_decimate.py` | pymeshlab: decimação quádrica 1 M -> 80 k -> alvo (5.500 a 6.500), Taubin leve, malha fechada |
| s3 | `s3_game_prep.py` | normais para fora, suavização, arestas vivas por ângulo |
| s4 | `s4_rig.py` | ajusta o `Rig_Humanoid_Chibi` por marcos (`markers`, esquerda = +X, frente = -Y) e pesos automáticos, máx. 4 influências |
| s5 | `s5_uv.py` | UV 1024: ilhas por região do corpo (osso dominante) e eixo da normal, desdobramento angular, rosto e mãos com mais texel, empacotamento côncavo |
| s6 | `s6_bake.py` | AO e cavidade da malha alta por raios (BVH), em processos paralelos; gera `bake_ao.png` e `bake_cavity.png` |
| s7a/s7 | `s7a_export_geo.py`, `s7_paint.py` | projeta a folha (frente, costas, direita, esquerda espelhada) com alinhamento de silhueta, visibilidade e peso pela normal; preenche buracos em 3D; soma AO, cavidade, luz quente do alto-esquerda e sombra violeta; gera `T_<Nome>_BC.png` (1024) e `T_<Nome>_M.png` (512) |
| s8 | `s8_export.py` | 1 material, teste de pose com métrica de esticamento, `.blend` e `SK_<Nome>.fbx` com o preset do graybox (`gb_rig.export_fbx_rigged`) |
| s9 | `s9_previews.py` | prévias Eevee 1024 (frente, 3/4, costas, pose) |
| v | `verify_modelo.py` | conferência do FBX reimportado (eixos, escala, triângulos, material, UV, malha fechada, ossos, pesos) |

## Modo por peça (corpo base + 5 peças)

O esqueleto é ajustado uma vez ao corpo base e reaproveitado:
- `norm_from`: json `norm.json` do corpo base (s1 usa a mesma escala e o mesmo deslocamento, para as peças encaixarem).
- `markers_from`: json do corpo base com `markers` (s4 cria o rig com as mesmas posições de osso; os pesos são calculados na malha da peça).
- `asset` e `mesh_name` por peça (`SK_<Heroi>_Body`, `SK_<Heroi>_<Slot>_<Conjunto>`); `sheet`/`sheet_cuts` da folha da própria peça; `work_dir`/`final_dir` próprios.
Cada peça sai como FBX próprio com o mesmo esqueleto.
