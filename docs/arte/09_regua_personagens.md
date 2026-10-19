# Régua comum dos personagens 3D

Vale para os 3 heróis e para os inimigos. Tudo no mesmo estilo do mapa da Cripta (pintado à mão, chanfrado, luz quente do alto-esquerda).

| Item | Valor |
|---|---|
| Altura (chão até a coroa do elmo/capuz) | 1,50 m (herói); inimigos pela folha, mesma régua |
| Cabeça / corpo | chibi do Spell Brigade: cabeça ~27% da altura (cabeça 0,88x do modelo bruto) |
| Silhueta do Guerreiro | pesada: tronco 1,24x de largura e 1,16x de profundidade, braços 1,10x e 0,075 m para fora, pernas 1,14x |
| Mago | silhueta vertical e estreita, capuz alto, cajado com cristal (nunca lanterna) |
| Arqueiro | magro e ágil: ombros estreitos, pernas longas, postura inclinada |
| Chanfro | Bevel de 0,0035 m, 2 segmentos, limite de ângulo 40°, normais ponderadas (depois do esqueleto) |
| Textura | 1 material por peça, albedo 1024 pintado (sem fotografia/ruído de projeção), máscara M 512 |
| Brilho de borda | **nenhum**: `_RimIntensity`, `_FresnelStrength` e `_FresnelBlend` = 0 nos materiais de personagem. Contorno branco vinha disso mais do MSAA desligado |
| Aura | só no chão e em volta (`HeroAura`: anel suave + partículas), na cor do herói; nunca no contorno do modelo |
| Rig | `Rig_Humanoid_Chibi` (Humanoid); as proporções se aplicam malha e ossos juntos com `art-src/modelos/scripts/v3_forma.py` |

Cores de aura: Guerreiro vermelho, Mago azul-violeta, Arqueiro verde.
