# Formas visuais das habilidades do Arqueiro (auditoria de 11/11/2026)

Regra do Will: no máximo 1/3 das habilidades pode ter como visual principal um projétil em linha reta saindo do herói.
Resultado: **6 de 41 ativas (15%)** leem como flecha reta; as outras 35 têm forma própria.

| Família de forma | Habilidades (id → efeito) |
|---|---|
| Flecha reta (6) | power_shot (virote que arrasta), sniper_shot (linha instantânea com mira travando), poison_arrow, frost_arrow, flecha_ardente, shock_arrow (as quatro últimas são o tiro básico elementado, não habilidade de slot) |
| 1 Do céu | arrow_rain, corrosive_rain, flecha_meteoro, ice_comet, thunder_burst, sky_storm |
| 2 Área no chão | spike_trap (mandíbulas), toxic_mines, acid_geyser, ice_spikes, muralha_brasas, ring_of_fire, smoke_bomb, ice_prison |
| 3 Vórtice | storm_tornado, toxic_tornado, blizzard (nuvem que acompanha) |
| 4 Cadeia | chain_lightning, plague_spread (veneno salta de um para outro) |
| 5 Orbital e invocação | storm_orbs, hunters_mark (falcão), lightning_rod (sentinela/para-raios), herald_plague, herald_ice, herald_thunder, arauto_cinzas |
| 6 Feixe e cone | **icicle_lance (agora Raio Glacial, feixe contínuo que varre)**, flame_breath (cone), glacial_shard, frost_nova e adrenaline (anel de choque) |
| 7 Explosão em estágios | explosive_arrow (pote que semeia bombas), fuse_bomb (rastilho), backstep_shot (duplo de sombra que explode) |
| 8 Retorno e curva | fan_of_arrows (lâminas que voltam), rapid_volley (revoada que faz curva), fire_serpent (serpente ondulada) |

## O que mudou nesta rodada
- `icicle_lance` era a "Lança de Gelo", uma linha instantânea (reta). Virou o **Raio Glacial**: um feixe contínuo de 3 tons, borda dura, que varre um arco à frente por 1,4 s, com rastro e ponta no chão, e acumula geada em quem cruza.
- O feixe é genérico: `scripts2d/efeito_feixe_2d.gd` (`Feixe.lancar(jogador, dir, {cor, comp, larg, arco, dur, tick, dano, ao_acertar})`). Guerreiro e Mago podem usar com outra paleta e outro `ao_acertar`.
- Correção: o Meteoro tentava mexer no sprite de queda depois de liberado (erro a cada quadro, 6 mil por corrida de captura).

## Prova
Prancha com 12 formas lado a lado e vídeo do jogo real em `/mnt/project-files/capturas/habilidades-arqueiro/` (fora do Git).
