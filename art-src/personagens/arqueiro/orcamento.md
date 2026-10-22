# Orçamento de triângulos do Arqueiro modular (LOD0)

Medido com `verificar_glb.py` sobre os GLBs de `godot/art/models/personagens/arqueiro/` (JSON glTF: 27 ossos Rig_Humanoid_Chibi, 1 material, UV presente, 0 animações, 1 textura embutida). Orçamento: `docs/tecnico/04_arquitetura.md`, seção 17.4 (peça: alvo / teto).

| Módulo | Triângulos | Alvo | Teto | Situação |
|---|---|---|---|---|
| Capuz (Head) | 1.862 (capuz 1.046 incl. moldura de osso, máscara 372, rosto/olhos/lenço 444) | 500 a 900 | 1.400 (2.000 autorizado pelo dono/orquestrador para o capuz v3: é o foco do close) | acima do teto 17.4 (1.400), dentro do limite de 2.000 do brief; texturas 1024 (capuz) e 512x1024 (máscara) em vez de 256: aprovar ou reduzir |
| Peitoral (Chest) | 2.837 | 900 a 1.500 | 2.200 (17.4) | ACIMA do teto da 17.4 por decisao de arte: a capa de penas (~1.000 tris de capa + 250 mantel + 460 asas) e o destaque da folha; teto do brief 3.000. Capa de penas reconstruida (arte3), textura propria `T_Arqueiro_Peitoral_BC.png` 512 |
| Calça (Legs) | 1.162 | 500 a 800 | 1.200 | refeita por script (pernas_geo.py): dobras, joelheiras, ataduras, barra de penas irregular; no teto |
| Luvas (Hands) | 1.396 (par) | 900 a 1.400 (brief da revisão) | 1.400 | refeitas do zero (luvas_geo.py): ~700 por mão; fora do alvo 17.4 (300 a 500), dentro do pedido da revisora |
| Botas (Feet) | 920 | 300 a 500 | 750 (pedido do dono: até ~900) | refeitas por script: botas grandes, cano alto, placas de osso, solado grosso; ~20 acima do combinado |
| Soma das 5 peças | ~5.240 | 2.500 a 4.200 | < 7.500 | acima do alvo; com a cabeça do corpo (~1.020) ~6.260 (sem contar o Peitoral novo de 2.837: recalcular) |
| Arco | 900 | sem linha própria | n/d | estático |
| Aljava | 800 | sem linha própria | n/d | estático |

Corpo base (outro agente): 2.500 triângulos medidos no FBX (cabeça 1.020). Pior caso com a cabeça do corpo visível: 4.693 + 1.020 = ~5.700 (alvo do herói 4.000 a 6.500, teto 10.000). Com arco e aljava (900 + 800): ~7.400.

## Texturas (traje: Peitoral, Calça, Luvas, Botas)

Um único arquivo `T_Archer_Starter_BC.png` 512x512 (514 KB) e `T_Archer_Starter_M.png` 256x256, em `godot/art/models/personagens/arqueiro/`, gerados por `grade_traje.py` a partir da fonte 1024 (gradação de cor + redução com nitidez). Os 4 GLBs referenciam esse arquivo por uri externo (não vai mais embutido: GLBs de 26 KB a 166 KB, antes ~1,4 a 1,6 MB cada). O Capuz ainda embute a textura 1024 original (outro agente); para unificar basta usar `textura=c.TEX_TRAJE` em `build_capuz.py`. Os arquivos `Arqueiro_<Peca>_T_Archer_Starter_BC.png(.import)` antigos (extraídos pelo Godot) ficaram obsoletos e podem ser apagados.

Outros desvios: 17.4 prevê Chest 512², Legs 256², Hands/Feet 128²; o traje compartilha 512² (atlas único, as 4 peças juntas), aceitável como um material só. Altura do modelo: 1,50 m (pé em y=0), não 1,82 m.

## Proporcao chibi (proporcao.py)
Todo FBX do rig passa por `proporcao.aplicar(arm, malhas)` (cabeca x1,4, pernas x0,8, tronco x0,88, maos/pes x1,15-1,18, ombros caidos 10 graus, cotovelos e joelhos levemente flexionados; novo repouso). Altura final 1,494 m (corpo) / 1,527 m (capuz), sola em y=0. No Godot a escala do no e 1,0 (Arqueiro.tscn nao escala): a altura em jogo e a do GLB, igual a de antes (1,5 m).

## Peitoral arte3 (capa de penas)
Decisao: o Peitoral sobe para 2.837 tris (teto do brief ~3.000; a 17.4 previa 2.200) porque a silhueta da folha e a capa longa de penas. Partes: capa de costas 970 + forro 96, mantel de penas 250, asas 460, ombreiras de osso 312, braceletes 248, gibao e saia 167, cinto e bolsas 188, correias 63, fecho 83. Soma com as outras pecas (Capuz 962, Calca 1.099, Luvas 196, Botas 438 medidos antes) = ~5.530 < 7.500; com a cabeca do corpo (1.020) ~6.550; com arco e aljava ~8.250 (as armas nao entram na soma das 5 pecas).
Textura propria 512x512 (`peitoral_textura.py`): 8 celulas de pena + amostras de tecido, couro, osso e metal; sem normal map. Malha modelada direto no espaco chibi (ossos recebem `proporcao.aplicar(arm, [])`).

## Calça e Botas v3 (texturas próprias)
`T_Arqueiro_Calca_BC.png` e `T_Arqueiro_Botas_BC.png` (1024, uso próprio; deixaram de usar `T_Archer_Starter_BC`). Geradas por `pernas_textura.py` (numpy/PIL, semente fixa) sobre o layout de UV de `pernas_atlas.py`; geometria por `pernas_geo.py` (build_calca.py / build_botas.py). Ordem: `python pernas_textura.py`, depois os dois build no Blender. Pesos por regra de altura/posição nos 27 ossos (sem transferência). Medido: Calça 1.162 tris, Botas 920 tris (soma 2.082).

## Luvas v2 (build_luvas.py + luvas_geo.py + luvas_tex.py)
- Modeladas do zero (procedural, bmesh); o FBX da mão só dá o rig e o repouso chibi (`proporcao.aplicar`). 1.396 triângulos o par, 27 ossos Rig_Humanoid_Chibi, 1 material `M_Arqueiro_Luvas`, 0 animações.
- Textura PRÓPRIA `T_Arqueiro_Luvas_BC.png` 512x512 (atlas por zonas: couro, palma, cinta, osso, pele, metal, pano), pintada por `python luvas_tex.py`, referenciada por uri externo no GLB. Não usa mais `T_Archer_Starter_BC.png`.
- Por mão (~700 tris): couro/dedos ~330, braçadeira de osso (2 placas chanfradas + nervura) ~220, punho e cintas ~150, fivelas 24. Garras de osso nos nós dos dedos, espinhos na braçadeira.
- Pesos: braçadeira e cintas = LowerArm 100%; punho = mistura LowerArm/Hand pelo eixo do antebraço; dedos, palma, garras = Hand 100% (o rig não tem ossos de dedo, então a mão deforma rígida).
- Mão esquerda: punho fechado no cabo, eixo vertical em G = pulso + (0, -0,085, 0) (Blender, Z cima, frente -Y; no Godot/glTF: z + 0,085). **O arco precisa entrar com esse deslocamento em relação a `socket_weapon_l`** (ex.: offset do `BoneAttachment3D`/nó filho). Sem o deslocamento o cabo atravessa o antebraço. Distância medida: braçadeira a 4,7 mm do arco (sem penetração); dedos penetram 1 a 6 mm na corda do cabo (aperto intencional).
- Mão direita: relaxada, indicador/médio/anelar em gancho para a corda, polegar recolhido, escala 1,16 sobre a base.
- Sobreposição com o Peitoral (versão atual): franjas de manga a 0,03 a 0,07 m do eixo do antebraço até ~60% do comprimento; a braçadeira (raio externo 0,047 a 0,050) fica por baixo/entre as penas. Revisar quando o módulo Peitoral for fechado.
- Os arquivos `Arqueiro_Luvas_T_Archer_Starter_BC.png(.import)` ficaram obsoletos (podem ser apagados).
