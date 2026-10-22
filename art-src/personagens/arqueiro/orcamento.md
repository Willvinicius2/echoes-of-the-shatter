# Orçamento de triângulos do Arqueiro modular (LOD0)

Medido com `verificar_glb.py` sobre os GLBs de `godot/art/models/personagens/arqueiro/` (JSON glTF: 27 ossos Rig_Humanoid_Chibi, 1 material, UV presente, 0 animações, 1 textura embutida). Orçamento: `docs/tecnico/04_arquitetura.md`, seção 17.4 (peça: alvo / teto).

| Módulo | Triângulos | Alvo | Teto | Situação |
|---|---|---|---|---|
| Capuz (Head) | 962 | 500 a 900 | 1.400 | acima do alvo, dentro do teto |
| Peitoral (Chest) | 1.998 | 900 a 1.500 | 2.200 | dentro do teto (era 2.706; Decimate collapse, delimitado por UV) |
| Calça (Legs) | 1.099 | 500 a 800 | 1.200 | dentro do teto (era 2.114; Decimate collapse, delimitado por UV) |
| Luvas (Hands) | 196 | 300 a 500 | 750 | abaixo do alvo |
| Botas (Feet) | 438 | 300 a 500 | 750 | ok |
| Soma das 5 peças | 4.693 | 2.500 a 4.200 | n/d | acima do alvo (4.200), dentro do teto; com a cabeça do corpo (~1.020) fica em ~5.700, abaixo de 6.500 |
| Arco | 900 | sem linha própria | n/d | estático |
| Aljava | 800 | sem linha própria | n/d | estático |

Corpo base (outro agente): 2.500 triângulos medidos no FBX (cabeça 1.020). Pior caso com a cabeça do corpo visível: 4.693 + 1.020 = ~5.700 (alvo do herói 4.000 a 6.500, teto 10.000). Com arco e aljava (900 + 800): ~7.400.

## Texturas (traje: Peitoral, Calça, Luvas, Botas)

Um único arquivo `T_Archer_Starter_BC.png` 512x512 (514 KB) e `T_Archer_Starter_M.png` 256x256, em `godot/art/models/personagens/arqueiro/`, gerados por `grade_traje.py` a partir da fonte 1024 (gradação de cor + redução com nitidez). Os 4 GLBs referenciam esse arquivo por uri externo (não vai mais embutido: GLBs de 26 KB a 166 KB, antes ~1,4 a 1,6 MB cada). O Capuz ainda embute a textura 1024 original (outro agente); para unificar basta usar `textura=c.TEX_TRAJE` em `build_capuz.py`. Os arquivos `Arqueiro_<Peca>_T_Archer_Starter_BC.png(.import)` antigos (extraídos pelo Godot) ficaram obsoletos e podem ser apagados.

Outros desvios: 17.4 prevê Chest 512², Legs 256², Hands/Feet 128²; o traje compartilha 512² (atlas único, as 4 peças juntas), aceitável como um material só. Altura do modelo: 1,50 m (pé em y=0), não 1,82 m.
