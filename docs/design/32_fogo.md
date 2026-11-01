# 32 — Árvore de FOGO do Arqueiro (Flecha Ardente, Flecha Meteoro, Muralha de Brasas, Arauto das Cinzas)

Parte do plano `32_arqueiro_elementos_poe2.md`. O tornado fica só com a árvore de Raio. Esta thread entrega **arquivos novos**; CSVs, `loc_2d.csv`, `enemy_2d.gd`, `efeitos_arqueiro_2d.gd` e `test_2d.gd` ficam com a thread integradora, que aplica as linhas abaixo.

## O que foi entregue
- `godot/scripts2d/efeitos_arqueiro_fogo_2d.gd` — `executar(efeito, jogador, def, nivel, mira)` (mesmo contrato do arqueiro) para `tiro_ardente`, `meteoro` e `muralha`; `ao_abate(jogador, pos, sobra, def)` do Arauto; `aura(jogador)` e `overlay_queimadura(inimigo)`.
- `godot/scripts2d/fogo_util_2d.gd` (folhas de quadros e helpers) e `fogo_anim_2d.gd` (toca uma folha em linha). **Sem PNG o efeito cai num desenho de código**, então o jogo e o teste headless funcionam antes da arte chegar.
- Arte: prompts em `tools/arte/fx_arqueiro/fogo/` (`mk_prompts.py` → `prompts_fogo.json`, `fatiar.py` corta e remove o magenta). Saída em `godot/art2d/fx/fogo/<nome>.png`.

## Habilidades e como funcionam
| Peça | Efeito (CSV) | Comportamento |
|---|---|---|
| **Flecha Ardente** (T1) | `tiro_ardente` | Flecha com cabeça em chamas. Ao sumir (acerto), queima quem estiver colado (status `queimadura` que já existe: dano em pulsos de 0,5 s) e solta o impacto. Não precisa mexer em `arrow_2d.gd`. |
| **Flecha Meteoro** (T2) | `meteoro` | Marca o chão (círculo vermelho crescente), a bola cai em ~0,55 s, explode em área (dano + queimadura) e deixa **brasas** pela `duracao` que reaplicam queimadura a quem ficar. |
| **Muralha de Brasas** (T3) | `muralha` | Linha de chamas à frente do arqueiro (`alcance` de comprimento, `raio` de meia largura, `qtd` segmentos visuais). A cada 0,5 s fere e queima quem cruza. Ult candidata (manual) se o Will escolher. |
| **Arauto das Cinzas** (Herald) | `herald_cinzas` (passiva de gatilho) | Dano que **sobra num abate** (overkill) vira explosão de fogo em volta: `sobra * valor`, raio `raio`, queimadura. `minimo` evita explodir por sobra irrisória. Aura leve no arqueiro enquanto equipado. |

## Linhas para o integrador

### `habilidades_arqueiro.csv` (ramo novo `fogo`; números iniciais, ajustar no playtest)
```
id,ramo,tipo,tier,pai,pontos,nivel_max,efeito,cd,custo,dano,qtd,angulo,raio,duracao,alcance,valor,escala,stat,modo,icone
flecha_ardente,fogo,ativa,1,,1,3,tiro_ardente,5,0,1.6,,,,3,,4,0.15,,,flecha_ardente
flecha_meteoro,fogo,ativa,2,flecha_ardente,2,3,meteoro,10,0,3.2,,,140,3,600,3,0.15,,,flecha_meteoro
muralha_brasas,fogo,ativa,3,flecha_meteoro,3,3,muralha,14,0,1.0,10,,44,5,320,4,0.15,,,muralha_brasas
arauto_cinzas,fogo,passiva,3,flecha_ardente,3,3,herald_cinzas,,,,,,110,3,,0.5,0.1,,,arauto_cinzas
```
Notas: em `flecha_ardente`, `dano` = multiplicador da flecha, `duracao` = segundos de queimadura, `valor` = dano por segundo da queimadura. Em `meteoro`, `dano` = multiplicador de `arrow_damage` na explosão, `duracao` = tempo das brasas, `valor` = dps. Em `muralha`, `dano` = por pulso (0,5 s), `qtd` = segmentos visuais. No Arauto: `raio` da explosão, `duracao` da queimadura, `valor` = fração da sobra (a coluna `minimo`/`dps` do código usa o padrão se faltar; se quiser, acrescente as colunas ao CSV).
A passiva `herald_cinzas` precisa de um tratamento próprio (não é `stat`): o integrador liga o gatilho abaixo e cuida do slot/gema.

### `habilidades_mira.csv`
```
arqueiro,flecha_ardente,proximo,0,760,1
arqueiro,flecha_meteoro,grupo,0,600,1
arqueiro,muralha_brasas,proximo,0,420,1
```
(`herald_cinzas` não tem mira: é passiva.)

### `efeitos_arqueiro_2d.gd` (delegação mínima, só a integradora)
```gdscript
const FogoScript = preload("res://scripts2d/efeitos_arqueiro_fogo_2d.gd")
# dentro do match, antes do `_:`
"tiro_ardente", "meteoro", "muralha":
    return FogoScript.executar(efeito, jogador, def, nivel, mira)
```

### `enemy_2d.gd` (gatilhos)
1. **Overlay de queimadura**: ao `aplicar_status("queimadura", …)` pela primeira vez, chamar `FogoScript.overlay_queimadura(self)` e guardar o nó; removê-lo quando o status acabar (o status `queimadura` e seu dano já existem em `_tick_status`).
2. **Overkill**: em `take_damage`, ao morrer, `sobra = dano_recebido - vida_antes`; se o Arauto estiver equipado, `FogoScript.ao_abate(jogador, global_position, sobra, def_arauto)`. A queimadura que mata também conta, com `sobra` = dano do pulso que passou da vida.
3. **Aura**: ao equipar o Arauto, `FogoScript.aura(jogador)`; guardar o retorno e `queue_free()` ao desequipar.

### `loc_2d.csv`
```
skill.flecha_ardente.name,Flecha Ardente
skill.flecha_ardente.desc,Flecha em chamas que acerta e faz o inimigo queimar
skill.flecha_meteoro.name,Flecha Meteoro
skill.flecha_meteoro.desc,Dispara para o alto; um meteoro cai na área e deixa o chão em brasas
skill.muralha_brasas.name,Muralha de Brasas
skill.muralha_brasas.desc,Linha de fogo no chão que queima quem a cruza
skill.arauto_cinzas.name,Arauto das Cinzas
skill.arauto_cinzas.desc,O dano que sobra ao abater um inimigo vira uma explosão de fogo em volta
```

### `icones.csv`
Ícones 128 px em `godot/art2d/ui/icone_<id>.png` (copiar de `art2d/fx/fogo/icone_*.png` quando aprovados; ids `flecha_ardente`, `flecha_meteoro`, `muralha_brasas`, `arauto_cinzas`).

### `test_2d.gd` (sugestão de checagens)
- Cada `efeito` do ramo fogo é aceito por `executar` com um jogador falso (`jogador_falso_2d.gd`) sem `push_error`.
- `tiro_ardente`: depois do acerto, o inimigo tem `tem_status("queimadura")`.
- `meteoro`: antes do tempo de queda o inimigo não leva dano; depois leva dano e fica queimado.
- `muralha`: inimigo dentro da linha leva dano em até 0,5 s; fora da linha não.
- `ao_abate` com `sobra` abaixo de `minimo` não causa dano; acima, fere vizinhos no `raio`.

## Folhas de efeito (todas pintadas, fundo transparente, quadros em linha)
| Arquivo | Quadros × px | Uso |
|---|---|---|
| `flecha_proj.png` | 6 × 96, loop | cabeça e rastro da Flecha Ardente |
| `flecha_impacto.png` | 8 × 128 | impacto do tiro |
| `queimadura.png` | 6 × 96, loop | overlay no inimigo queimando |
| `meteoro_queda.png` | 6 × 128, loop | bola caindo |
| `meteoro_impacto.png` | 8 × 256 | explosão e cratera |
| `brasas_chao.png` | 6 × 256, loop | chão em brasas |
| `muralha_chama.png` | 8 × 128, loop | um segmento da muralha |
| `arauto_aura.png` | 6 × 128, loop | aura do Herald |
| `arauto_explosao.png` | 8 × 256 | explosão de cinzas |
| `icone_*.png` ×4 | 128 | ícones no molde do doc 29 |

Estado da arte: ver a seção "Estado" abaixo, atualizada quando as folhas passarem pela revisora.

## Estado
- Código, prompts e as 9 folhas + 4 ícones gerados e commitados em `godot/art2d/fx/fogo/` (prancha de conferência: `/mnt/project-files/arqueiro/fogo/prancha_fogo.png`). Aguardando a revisora. Resíduo roxo suave nas bordas de fumaça (magenta); dá para endurecer o `key` se a revisora pedir.
- Arauto das Cinzas, ajuste pela referência PoE 2: o abate só explode se a sobra passar de uma fração mínima da vida máxima do inimigo (proposta ~20%); a queimadura do Arauto não empilha, só renova. Se o integrador preferir, trocar `minimo` (absoluto) por `min_overkill_pct` no CSV e converter em `ao_abate`.
