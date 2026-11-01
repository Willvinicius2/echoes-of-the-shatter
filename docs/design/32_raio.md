# 32. Árvore de Raio do Arqueiro

Parte do doc 32 (`32_arqueiro_elementos_poe2.md`). Esta thread entrega só arquivos novos; as linhas dos arquivos compartilhados estão abaixo para a integradora aplicar. Todo número fica no CSV; o código só tem tempos visuais.

## Peças
| Id | Tipo | Efeito (coluna `efeito`) | O que faz |
|---|---|---|---|
| `shock_arrow` | tiro, T1 | `flecha_eletrica` | Flecha com dano normal; ao acertar aplica **choque** (inimigo recebe `valor` a mais de dano por `duracao` s) e mostra faíscas por cima dele. |
| `chain_lightning` | ativa A, T2, pai `shock_arrow` | `raio_encadeado` | Acerta o inimigo mais perto da mira e salta até `qtd` alvos (cada salto a no máximo `raio` px do anterior), perdendo `valor` do dano por salto, aplicando choque. Sem alvo no alcance não gasta recarga. |
| `storm_tornado` | ativa B, T3, pai `chain_lightning` (ult candidata) | `tornado` | A flecha sobe e cai no ponto mirado (coluna de raio, 0,55 s); nasce um tornado que **puxa** os inimigos (`valor` px/s) e fere em pulsos de 0,5 s por `duracao` s num `raio`. |
| `herald_thunder` | passiva Herald, T2, pai `shock_arrow` | `arauto` | Inimigo que morre em choque solta um raio e fere vizinhos num `raio`, aplicando choque neles. Aura leve no arqueiro enquanto equipado. |

## Linhas para `godot/data2d/habilidades_arqueiro.csv` (ramo novo `raio`)
Colunas: `id,ramo,tipo,tier,pai,pontos,nivel_max,efeito,cd,custo,dano,qtd,angulo,raio,duracao,alcance,valor,escala,stat,modo,icone`. Números são **propostas** para a integradora ajustar.
```
shock_arrow,raio,ativa,1,,1,3,flecha_eletrica,4,0,1.2,,,,3,,0.15,0.15,,,shock_arrow
chain_lightning,raio,ativa,2,shock_arrow,2,3,raio_encadeado,9,0,1.6,4,,220,3,600,0.2,0.15,,,chain_lightning
storm_tornado,raio,ativa,3,chain_lightning,3,3,tornado,16,0,0.9,,,150,4,650,90,0.15,,,storm_tornado
herald_thunder,raio,passiva,2,shock_arrow,2,3,arauto,,,1.5,,,180,3,,,,,,herald_thunder
```
`dano` do tornado é por pulso. `escala` é o ganho por nível (igual às outras ativas).

## `habilidades_mira.csv` (autocast)
```
arqueiro,shock_arrow,proximo,0,760,1
arqueiro,chain_lightning,proximo,0,600,1
arqueiro,storm_tornado,proximo,0,650,2
```
(`storm_tornado` pede 2+ alvos para valer a pena; se virar ult, `ult` = 1 e o disparo passa a ser manual.) O Herald não usa a mira.

## Código a integrar (edição mínima, só a integradora)
1. `efeitos_arqueiro_2d.gd`: no `match efeito`, acrescentar o ramo
   `"flecha_eletrica", "raio_encadeado", "tornado": return preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd").executar(efeito, jogador, def, nivel, mira)`.
2. `enemy_2d.gd` (status): em `_recalcular_status`, `dano_mult` passa a somar também `_status["choque"]["v"]` (mesmo padrão da `marca`). Na morte (onde `estado = Estado.MORTO`), chamar `preload("res://scripts2d/efeitos_arqueiro_raio_2d.gd").ao_morrer(self)` **antes** de limpar `_status`. Sem isso o choque é só visual e o Arauto não dispara.
3. Herald: ao equipar/desequipar a gema, `EfeitosRaio.ativar_arauto(jogador, def_da_linha)` (`def` vazio desliga). `habilidades_2d.gd` precisa tratar `efeito == "arauto"` como passiva de gatilho, não stat.
4. `test_2d.gd`: carregar o script, conferir que as 4 linhas do CSV existem e que `"flecha_eletrica"`, `"raio_encadeado"`, `"tornado"` estão em `EFEITOS`.

## `loc_2d.csv` (chaves; texto em pt-BR, ajustar à voz do jogo)
```
skill.shock_arrow.name,Flecha Elétrica
skill.shock_arrow.desc,Flecha que causa choque: o inimigo recebe mais dano por alguns segundos.
skill.chain_lightning.name,Raio Encadeado
skill.chain_lightning.desc,A flecha vira raio e salta entre inimigos próximos, perdendo força a cada salto.
skill.storm_tornado.name,Tornado de Tempestade
skill.storm_tornado.desc,Atira para o alto; a flecha cai e vira um tornado que arrasta e fere os inimigos.
skill.herald_thunder.name,Arauto do Trovão
skill.herald_thunder.desc,Inimigo que morre em choque solta um raio que fere os vizinhos.
status.choque,Choque
```

## `icones.csv`
Ids `shock_arrow`, `chain_lightning`, `storm_tornado`, `herald_thunder` → `godot/art2d/ui/icone_<id>.png` (128 px). Os prompts em `tools/arte/fx_arqueiro/raio/prompts_raio.json` têm os 4 ícones com ids `icone_flecha_eletrica`, `icone_raio_encadeado`, `icone_tornado_tempestade`, `icone_arauto_trovao`: renomear na exportação para os ids acima.

## Arte
Folhas em `godot/art2d/fx/raio/` (quadros em linha, fundo transparente):
| Arquivo | Quadros | Tamanho do quadro | Uso |
|---|---|---|---|
| `flecha_eletrica_proj.png` | 6 | 64x32 | projétil, loop |
| `raio_impacto.png` | 8 | 96x96 | impacto de cada salto e do Arauto |
| `raio_arco.png` | 4 | 128x32 | segmento esticado entre dois alvos |
| `choque_overlay.png` | 6 | 64x64 | faíscas sobre o inimigo em choque |
| `tornado_tempestade.png` | 8 | 128x160 | tornado, loop |
| `raio_coluna.png` | 6 | 64x192 | raio do céu (queda do tornado e Arauto) |
| `arauto_trovao_aura.png` | 6 | 96x96 | aura no arqueiro |

**Estado: provisória.** O ambiente desta thread (nuvem) não tem o Codex CLI nem acesso ao gpt-image, então as folhas foram desenhadas em código (`tools/arte/fx_arqueiro/raio/gerar_procedural.py`) para o jogo já funcionar. Elas **não** passaram pela revisora e não valem como arte final. A arte pintada sai no PC do Will:
`python docs\arte\referencias-geracao\scripts\gerar.py tools\arte\fx_arqueiro\raio\prompts_raio.json D:\openclaude\_trabalho-claude\fx-raio`, depois `tools/arte/ui_gpt_image/key.py` (remove o magenta) e recorte em quadros iguais. Substituir os PNGs de mesmo nome (o código lê quadros pela largura total / nº de quadros, então os nomes e contagens de quadros precisam bater com a tabela).

## Não verificado
Não havia Godot na nuvem: `efeitos_arqueiro_raio_2d.gd` não foi executado nem passou pelo `test_2d.gd`. A integradora deve rodar o teste headless e o CI `cliente2d` ao integrar.
