# 32. Árvore de Gelo do Arqueiro

Parte do plano `32_arqueiro_elementos_poe2.md`. Esta thread entrega: `godot/scripts2d/efeitos_arqueiro_gelo_2d.gd`, os prompts e o fatiador em `tools/arte/fx_arqueiro/gelo/` e as folhas em `godot/art2d/fx/gelo/` (quando aprovadas). Números abaixo são **propostas** para o CSV; o código não tem número de balanceamento (só os limites visuais e `MAX_ACUMULOS`, que é regra de status, ver 3.1).

## 1. As quatro peças
| id | Nome (loc) | Tipo | Efeito | Como funciona |
|---|---|---|---|---|
| `frost_arrow` | Flecha Gélida | ativa T1 (autocast) | `gelo_flecha` | Flecha de dano normal. Cada acerto soma 1 acúmulo de **frio**: lentidão (`valor` por acúmulo, até 70%). No 4º acúmulo o inimigo **congela** (atordoamento por metade da `duracao`). |
| `glacial_shard` | Estilhaço Glacial | ativa T2 (autocast) | `gelo_estilhaco` | Flecha que, ao acertar, racha em `qtd` lascas que voam para os alvos mais próximos do acertado (até `raio`), cada uma com `valor` × dano e +1 de frio. É o "tiro que se espalha". |
| `ice_prison` | Prisão de Gelo | ativa T3, **ult candidata** (manual) | `gelo_prisao` | Área no ponto mirado: golpe de dano e **congela** tudo por `duracao`. |
| `herald_ice` | Arauto do Gelo | passiva (Herald, ocupa slot) | `herald_gelo` | Inimigo **congelado** que morre explode: dano em área e +1 de frio nos vizinhos (que podem congelar em cadeia). |

## 2. Linhas para os CSVs (aplicar pela thread integradora)
`godot/data2d/habilidades_arqueiro.csv` (ramo novo `gelo`; colunas como no cabeçalho atual):
```
frost_arrow,gelo,ativa,1,,1,3,gelo_flecha,5,0,1.0,0,,,3.0,,0.15,0.1,,,frost_arrow
glacial_shard,gelo,ativa,2,frost_arrow,2,3,gelo_estilhaco,8,0,1.2,3,,260,3.0,,0.5,0.12,,,glacial_shard
ice_prison,gelo,ativa,3,glacial_shard,3,3,gelo_prisao,20,0,1.5,,,170,2.0,450,,0.12,,,ice_prison
herald_ice,gelo,passiva,3,frost_arrow,3,3,herald_gelo,,,1.5,,,150,3.0,,0.15,0.12,,,herald_ice
```
Leitura das colunas: `dano` = multiplicador do `arrow_damage`; `qtd` = lascas; `raio` = busca das lascas, área da prisão ou da explosão; `duracao` = tempo do frio (e do congelamento da prisão); `valor` = lentidão por acúmulo (frio) ou fração de dano da lasca; `escala` = ganho por nível, como as outras linhas. `herald_ice` usa `efeito=herald_gelo` (a integradora liga a `arauto_varrer`, ver 4); `modo`/`stat` ficam vazios porque não é passiva de atributo.

`godot/data2d/habilidades_mira.csv` (`classe,id,mira,ult,alcance,min_alvos`):
```
arqueiro,frost_arrow,proximo,0,760,1
arqueiro,glacial_shard,proximo,0,760,2
arqueiro,ice_prison,grupo,1,450,3
```
(`herald_ice` não entra: passiva.)

`godot/data2d/loc_2d.csv` (chave,texto):
```
skill.frost_arrow.name,Flecha Gélida
skill.frost_arrow.desc,Acerta e acumula frio: o inimigo fica lento e, no quarto acúmulo, congela
skill.glacial_shard.name,Estilhaço Glacial
skill.glacial_shard.desc,A flecha racha ao acertar e lascas de gelo saltam para os inimigos próximos
skill.ice_prison.name,Prisão de Gelo
skill.ice_prison.desc,Congela todos os inimigos na área mirada por alguns segundos
skill.herald_ice.name,Arauto do Gelo
skill.herald_ice.desc,Inimigo congelado que morre explode em estilhaços e gela os vizinhos
status.frio,Frio
status.congelado,Congelado
ramo.gelo,Gelo
```
Ícones: `icone` aponta para `icone_<id>`; ver `godot/data2d/icones.csv` (linhas `frost_arrow`, `glacial_shard`, `ice_prison`, `herald_ice` → `res://art2d/ui/icones/...`, mesmo molde dos outros).

## 3. Contrato com o resto do jogo
### 3.1 Status (sem editar `enemy_2d.gd`)
O script usa só o que existe: `aplicar_status("lentidao", dur, fração)` e `aplicar_status("atordoamento", dur)`, mais `set_meta("frio_acumulos")` e `set_meta("congelado_ate")` no inimigo. `MAX_ACUMULOS = 4` é regra de status; se a integradora preferir, vira coluna do CSV. Opcional, melhor para a UI: um status `frio` de verdade em `enemy_2d.gd`.

### 3.2 Hook na flecha (sem editar `arrow_2d.gd`)
A flecha é uma `Area2D`; o script liga `body_entered` depois do tratamento da própria flecha. Funciona com `pierce` (liga uma vez por flecha, dispara a cada inimigo). Se o dano da flecha mata o inimigo antes do hook, `acumular_frio` ignora inimigo morto.

### 3.3 Despacho e Herald
Em `efeitos_arqueiro_2d.gd` (edição mínima, da integradora), dentro do `match efeito`:
```
"gelo_flecha", "gelo_estilhaco", "gelo_prisao":
    return preload("res://scripts2d/efeitos_arqueiro_gelo_2d.gd").executar(efeito, jogador, def, nivel, mira)
```
Herald (passiva sem `executar`): enquanto a gema/passiva estiver equipada, chamar `EfeitosGelo.arauto_varrer(jogador, def)` a cada ~0,5 s (varre o grupo `hurtable` e liga o `died` de cada inimigo uma única vez; `arauto_vigiar(inimigo, jogador, def)` serve para ligar no nascimento do inimigo). A explosão só dispara se o inimigo estava congelado (`esta_congelado`).

### 3.4 Testes sugeridos para `test_2d.gd` (integradora)
Carregar o script; criar inimigo fake com `aplicar_status`; chamar `acumular_frio` 4× e conferir `tem_status("atordoamento")`; `esta_congelado` verdadeiro logo após `congelar`.

## 4. Arte (folhas simples em linha, fundo transparente)
Prompts em `tools/arte/fx_arqueiro/gelo/prompts_gelo.json` (efeitos) e `prompts_icones_gelo.json` (4 ícones, molde do doc 29). Geração: `gerar.py` com Codex/gpt-image no PC do Will, depois `montar.py` (fatia, tira o magenta, iguala os quadros).

| Folha | Quadros | Uso |
|---|---|---|
| `gelo_flecha` | 6 | cabeça e rastro da flecha (loop) |
| `gelo_impacto` | 8 | impacto das lascas |
| `gelo_lasca` | 4 | lasca voando (loop) |
| `gelo_status_frio` | 6 | overlay de frio no inimigo (loop) |
| `gelo_congelado` | 4 | bloco de gelo sobre o inimigo congelado (loop) |
| `gelo_prisao` | 8 | animação da Prisão de Gelo |
| `gelo_explosao` | 8 | explosão do Arauto |
| `gelo_aura` | 6 | aura leve do arqueiro com o Arauto equipado |

Sem as folhas o script desenha um brilho azul (fallback), então o jogo e o teste não quebram. A aura (`gelo_aura`) é usada pela integradora no arqueiro, junto do Herald.
