# Orçamento de triângulos do Arqueiro modular (LOD0)

Medido com `verificar_glb.py` sobre os GLBs de `godot/art/models/personagens/arqueiro/` (JSON glTF: 27 ossos Rig_Humanoid_Chibi, 1 material, UV presente, 0 animações, 1 textura embutida). Orçamento: `docs/tecnico/04_arquitetura.md`, seção 17.4 (peça: alvo / teto).

| Módulo | Triângulos | Alvo | Teto | Situação |
|---|---|---|---|---|
| Capuz (Head) | 962 | 500 a 900 | 1.400 | acima do alvo, dentro do teto |
| Peitoral (Chest) | 2.706 | 900 a 1.500 | 2.200 | ACIMA DO TETO (+506) |
| Calça (Legs) | 2.114 | 500 a 800 | 1.200 | ACIMA DO TETO (+914) |
| Luvas (Hands) | 196 | 300 a 500 | 750 | abaixo do alvo |
| Botas (Feet) | 438 | 300 a 500 | 750 | ok |
| Soma das 5 peças | 6.416 | 2.500 a 4.200 | n/d | acima do alvo; sem o corpo já fica no limite de 6.500 |
| Arco | 900 | sem linha própria | n/d | estático |
| Aljava | 800 | sem linha própria | n/d | estático |

Corpo base (outro agente): 2.500 triângulos medidos no FBX (cabeça 1.020). Pior caso com a cabeça do corpo visível: 6.416 + 1.020 = ~7.400 (alvo do herói 4.000 a 6.500, teto 10.000). Com arco e aljava: ~9.100, perto do teto.

Outros desvios: `T_Archer_Starter_BC` é 1024x1024 (17.4 prevê Chest 512², Head/Legs 256², Hands/Feet 128²) e vai embutida inteira em cada um dos 5 GLBs (~1,4 MB cada). Altura do modelo: 1,50 m (pé em y=0), não 1,82 m.
