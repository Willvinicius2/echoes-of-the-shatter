# 32 — Árvore de VENENO do Arqueiro (plano, arte e linhas para integrar)

Thread da árvore de veneno (parte do doc 32). Entrega: efeitos em `godot/scripts2d/efeitos_arqueiro_veneno_2d.gd`, arte em `godot/art2d/fx/veneno/` (prompts e pós-processo em `tools/arte/fx_arqueiro/veneno/`) e as linhas abaixo, que a thread integradora aplica nos CSVs, no `loc_2d.csv`, no `enemy_2d.gd` e no `test_2d.gd`. Nenhum desses cinco foi editado aqui.

## Peças (ids em inglês, nomes em português)
| id | Peça | Tier | Pai | O que faz |
|---|---|---|---|---|
| `poison_arrow` | Flecha Peçonhenta (tiro) | 1 | — | Flecha com veneno empilhável (dano contínuo, status `veneno` que já existe no inimigo). |
| `venom_orb` | Bola de Veneno (ativa A) | 2 | `poison_arrow` | Lança uma bola para o alto; ela cai no alvo, vira poça que fere e lentifica e, ao fim, estoura em nuvem. |
| `corrosive_rain` | Chuva Corrosiva (ativa B, ult candidata) | 3 | `venom_orb` | Zona grande de pulsos de dano que também corroem: o inimigo recebe mais dano (status `marca`, sem código novo no inimigo). |
| `herald_plague` | Arauto da Peste (Herald) | 3 | `poison_arrow` | Inimigo envenenado que morre espalha o veneno aos vizinhos (nuvem de peste). |

Reaproveitado: status `veneno` e `marca`/`lentidao` de `enemy_2d.gd`; `lancar_flecha`, `veneno_dps/veneno_t` da `arrow_2d.gd`. `venom_tips` (passiva existente) soma com a Flecha Peçonhenta (mesmo campo `poison_dps`).

## Linhas propostas: `godot/data2d/habilidades_arqueiro.csv`
Colunas: `id,ramo,tipo,tier,pai,pontos,nivel_max,efeito,cd,custo,dano,qtd,angulo,raio,duracao,alcance,valor,escala,stat,modo,icone`. Números são ponto de partida para o balanceamento; ramo `veneno` é novo (a integradora decide se vira ramo ou entra em `cacada`).
```
poison_arrow,veneno,ativa,1,,1,3,tiro_veneno,3,0,1.0,0,,,3,,4,0.15,,,poison_arrow
venom_orb,veneno,ativa,2,poison_arrow,2,3,bola_veneno,9,0,1.2,4,,110,3.2,450,0.35,0.15,,,venom_orb
corrosive_rain,veneno,ativa,3,venom_orb,3,3,chuva_corrosiva,14,0,0.9,6,,150,4.5,450,0.25,0.12,,,corrosive_rain
herald_plague,veneno,passiva,3,poison_arrow,3,3,arauto,,,,,,140,3,,4,0.2,,,herald_plague
```
Leitura das colunas pelos efeitos: `dano` = multiplicador do dano da flecha; `valor` = dps do veneno (flecha), fração de lentidão (poça) ou de dano extra recebido (chuva); `duracao` = duração do veneno ou da zona; `qtd` = número de pulsos da zona; `raio`/`alcance` em px; `escala` = quanto cada nível soma (convenção do CSV). O Herald lê `raio`, `duracao`, `valor` da própria linha.

## Linhas propostas: `habilidades_mira.csv`
```
arqueiro,poison_arrow,proximo,0,760,1
arqueiro,venom_orb,proximo,0,600,2
arqueiro,corrosive_rain,proximo,1,600,2
```
(`corrosive_rain` como ult candidata: `ult=1`, manual; se o Will não escolher, vira `0`). O Herald é passiva de gatilho, sem linha de mira.

## Ligação no código (feita pela integradora)
1. `efeitos_arqueiro_2d.gd`: no `match`, `"tiro_veneno", "bola_veneno", "chuva_corrosiva": return Veneno.executar(efeito, jogador, def, nivel, mira)` com `const Veneno = preload("res://scripts2d/efeitos_arqueiro_veneno_2d.gd")`.
2. Herald: no ponto em que `enemy_2d.gd` morre (estado MORTO em `take_damage`), se o jogador tem `herald_plague` equipado: `Veneno.arauto_peste_morte(self, def_do_herald)` (a função confere se o inimigo tinha `veneno`). Aura no arqueiro: `Veneno.aura_arauto(jogador)` ao equipar.
3. Overlay do inimigo envenenado: em `aplicar_status`, quando `tipo == "veneno"`, `Veneno.overlay_status(self, dur)` (idempotente).
4. Tudo funciona sem PNG (cai em partículas verdes do `Feel`), então a integração não depende da arte.

## Loc (`loc_2d.csv`), chaves e texto pt-BR
```
skill.poison_arrow.name,Flecha Peçonhenta
skill.poison_arrow.desc,Acerta e envenena o alvo: dano contínuo que se acumula
skill.venom_orb.name,Bola de Veneno
skill.venom_orb.desc,Lança uma bola ao alto que cai e vira poça venenosa; ao fim, estoura em nuvem
skill.corrosive_rain.name,Chuva Corrosiva
skill.corrosive_rain.desc,Chuva de ácido em área: fere e faz os inimigos receberem mais dano
skill.herald_plague.name,Arauto da Peste
skill.herald_plague.desc,Inimigo envenenado que morre espalha o veneno aos vizinhos
```
`icones.csv` (cor do halo): `poison_arrow,seta,#7ddc3c,...`, `venom_orb,...`, `corrosive_rain,...`, `herald_plague,...` (verde #7ddc3c).

## Testes sugeridos para `test_2d.gd`
Os 4 ids existem no CSV com pai válido; `FOLHAS` do script bate com os PNG (largura = quadros x largura do quadro) quando o PNG existe; `executar("tiro_veneno", ...)` deixa `veneno_dps > 0` na flecha; `arauto_peste_morte` passa `veneno` a um vizinho dentro do raio e não a um fora.

## Arte
Folhas em linha, fundo transparente, pintura à mão (doc 26), luz do alto à esquerda, verde tóxico `#7ddc3c`. Geradas no Codex (gpt-image), fundo magenta removido por `tools/arte/ui_gpt_image/key.py`, fatiadas por `tools/arte/fx_arqueiro/veneno/prep.py`.
| Arquivo | Quadros x px | Uso |
|---|---|---|
| `fx_veneno_flecha.png` | 6 x 64 | projétil da Flecha Peçonhenta (loop) |
| `fx_veneno_impacto.png` | 8 x 96 | impacto |
| `fx_veneno_bola.png` | 6 x 64 | bola de veneno no ar (loop) |
| `fx_veneno_poca.png` | 8 x 192 | poça no chão (loop) |
| `fx_veneno_nuvem.png` | 8 x 192 | estouro final da poça |
| `fx_veneno_chuva.png` | 8 x 192 | zona da Chuva Corrosiva (loop) |
| `fx_veneno_status.png` | 6 x 96 | overlay no inimigo envenenado |
| `fx_veneno_arauto_aura.png` | 6 x 128 | aura do Herald no arqueiro |
| `fx_veneno_arauto_gatilho.png` | 8 x 128 | explosão da peste na morte |
| `godot/art2d/ui/icone_{poison_arrow,venom_orb,corrosive_rain,herald_plague}.png` | 128 | ícones de gema/HUD |
Estado da arte: ver o fim deste documento (atualizado a cada rodada de revisão).
