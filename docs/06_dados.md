# 06 — Dados: esquemas, tabelas CSV e save

Responsável: Data Engineer. Status desta entrega: conteúdo real com `rules.csv` (58 chaves: as 41 de `constants.h` e as 17 de docs/13), `meta.csv` (`content_version = 1`) e as tabelas do GDD preenchidas. Tabelas novas e colunas novas: seção 5a. Fixtures de teste em `ShatterCore/tests/data/`. Validador em `tools/validate_data.py`, guia em `tools/README_dados.md`.

## 1. Fontes e escopo

- Lidos: `CLAUDE.md`; `docs/02_requisitos.md` (RF-01 a RF-65 e seção 5, critérios); `docs/04_arquitetura.md` (seções 1, 6, 8, 10, 12, 13, 14, 16); `docs/00_plano_existente.md` (defesa, idle, relógio, progressão, save); headers de `ShatterCore/include/shatter/`.
- Fora de escopo: textos de interface (`Loc/`, Narrative & Content), código C++ e migrações de banco (não há banco; o save é um arquivo JSON).
- Valores de teste dos fixtures (vida do Guerreiro, dano, pesos de loot) são só para exercitar o validador. Não são balanceamento e não entram no conteúdo real.

## 2. Convenções de arquivo

- UTF-8 sem BOM. Separador vírgula. A primeira linha é o cabeçalho, com os nomes exatos e na ordem do esquema.
- Sem aspas e sem vírgula dentro de célula (erro `E_QUOTE`). Texto livre não entra nas tabelas: vai para `Loc/`.
- Número com ponto decimal e sem separador de milhar. Booleano é `true` ou `false`.
- Célula vazia vale o padrão do esquema. Em coluna obrigatória, vazio é erro (`E_REQUIRED`).
- Lista usa `|` (ex.: `attack|melee|physical`). Item vazio ou repetido é erro.
- Modificador: `stat:kind:valor` ou `stat:kind:valor:tag+tag` (ex.: `life:flat:10`, `damage:increased:0.15:melee+attack`). `kind` é `flat`, `increased` ou `more`.
- Crescimento de atributo: `stat:base:porNível` (ex.: `life:80:8`), um por stat.
- Grupo de encontro: `enemy.id:min:max:chanceElite` (ex.: `enemy.hollow_sentinel:1:2:0.1`), com `min <= max` e chance em `[0,1]`.
- Enum: minúsculas com `_`. Os valores válidos estão nos esquemas e em `schemas/_enums.json` (listas `@stats`, `@slots`, `@tags`, `@modKinds`, `@shapes`).

## 3. Convenção de IDs

- Formato: `[a-z0-9_]+(\.[a-z0-9_]+)+`, em inglês e minúsculas, com pelo menos dois segmentos (`IsValidContentId` em `types.h`).
- Prefixo por tabela: `class.`, `skill.`, `effect.`, `enemy.`, `family.`, `affix.`, `item_base.`, `unique.`, `loot.`, `enc.`, `map.`. Os IDs de conteúdo aparecem nas colunas `id` e nas referências.
- Habilidade de classe: `skill.<segmento da classe>.<nome>`, com `classId = class.<segmento>` (ex.: `skill.warrior.iron_cut` com `class.warrior`).
- Habilidade sem classe: `skill.enemy.*` (ataque de inimigo, só para `enemy_attacks.csv`) ou `skill.common.*` (aprendível por qualquer classe).
- Estabilidade: um ID publicado não muda nem some. Para descontinuar, marca-se como obsoleto. Renomear só com pedido explícito do brief. O `content_lock.json` (seção 5) fiscaliza isso quando existir.
- Unicidade: um ID aparece em uma só tabela e uma vez. Duplicata entre tabelas também é `E_DUP_ID`.
- Textos de interface não são IDs. Ficam em `Loc/` com a chave `ID.name` ou `ID.desc`.

## 4. Tabelas do ContentDB

Ordem de carga: a mesma da lista de `LoadTableCsv` em `content.h`. Cada tabela segue as colunas do esquema em `EchoesOfTheShatter/Content/Data/schemas/<tabela>.schema.json`. Esses arquivos são a fonte única; a tabela abaixo é gerada deles.

| Tabela | Estado nesta entrega | Chave primária | Estrutura C++ (`content.h`) |
|---|---|---|---|
| `rules.csv` | completo (41 chaves) | chave (`key`) | `RulesConstants` |
| `meta.csv` | completo (`content_version = 1`) | chave (`key`) | `ContentDB::ContentVersion` |
| `classes.csv` | só cabeçalho | `id` | `ClassData` |
| `class_stats.csv` | só cabeçalho | `classId` + `stat` | `ClassData::stats` (`StatGrowth`) |
| `skills.csv` | só cabeçalho | `id` | `SkillData` + `IdleProfile` |
| `effects.csv` | só cabeçalho | `id` | `EffectData` |
| `enemies.csv` | só cabeçalho | `id` | `EnemyData` |
| `enemy_attacks.csv` | só cabeçalho | (sem PK; a ordem do CSV é a ordem da escolha) | `EnemyData::attacks` (`EnemyAttack`) |
| `affixes.csv` | só cabeçalho | `id` | `AffixData` |
| `item_bases.csv` | só cabeçalho | `id` | `ItemBaseData` |
| `uniques.csv` | só cabeçalho | `id` | `UniqueData` |
| `loot_tables.csv` | só cabeçalho | `id` | `LootTableData` |
| `loot_entries.csv` | só cabeçalho | (sem PK) | `LootTableData::entries` (`LootEntry`) |
| `encounters.csv` | só cabeçalho | `id` | `EncounterTemplate` |
| `maps.csv` | só cabeçalho | `id` | `MapData` |

Os exemplos de cada tabela vêm do fixture em `ShatterCore/tests/data/` (uma linha de cada tabela que tem dados ali). Para `effects.csv`, `affixes.csv` e `uniques.csv`, o exemplo é ilustrativo e não está no fixture. Ele foi validado à parte, numa cópia temporária do fixture, para garantir que o formato é aceito.

### Tabelas (geradas dos esquemas)

### `rules.csv` (constantes de regra)

Chaves de `RulesConstants` (`constants.h`). O validador exige as 58, nomes exatos, sem chave extra. Valores com a fonte de cada um. Os marcados PROVISÓRIO são números que o plano não fecha (pendência, seção 9).

- Chave primária: `key`.
- Formato key-value (`key,value`). Todas as chaves são obrigatórias.

| Chave | Tipo | Faixa | Padrão | Origem |
|---|---|---|---|---|
| `crit_multiplier_base` | number | ≥ 1 | 1.5 | req RF-06 (crítico de 100 = 150) |
| `evasion_cap` | number | ≥ 0, ≤ 1 | 0.7 | plano, seção Defesa (teto 70%) |
| `block_cap` | number | ≥ 0, ≤ 1 | 0.5 | plano, seção Defesa (teto 50%) |
| `block_mitigation` | number | ≥ 0, ≤ 1 | 1.0 | PROVISÓRIO. Arquitetura 04 §11 e §15: bloqueio anula o golpe |
| `resist_cap` | number | ≥ 0, ≤ 0.95 | 0.75 | plano, seção Defesa (teto 75%) |
| `resist_floor` | number | ≥ -5, ≤ 0 | -1.0 | Arquitetura 04 §11 (decisão, não está no plano): −100% |
| `armor_damage_factor` | number | > 0 | 5.0 | PROVISÓRIO. Arquitetura 04 §11: k = 5 em A/(A + k·D); o plano não traz a fórmula |
| `armor_max_reduction` | number | ≥ 0, ≤ 0.99 | 0.9 | PROVISÓRIO. Arquitetura 04 §11: teto de 90% |
| `trigger_icd_min` | number | ≥ 0.25, ≤ 10 | 0.25 | plano, Defesa (recarga interna mínima 0,25 s) |
| `cooldown_min` | number | ≥ 0.1, ≤ 10 | 0.1 | plano, Defesa (recarga mínima 0,1 s) |
| `realtime_step` | number | > 0, ≤ 0.1 | 0.016666666666666666 | Arquitetura 04 §6.2 (passo fixo 1/60 s) |
| `sim_step` | number | > 0, ≤ 1 | 0.1 | plano, Simulador e RF-41 (0,1 s) |
| `sim_step_fast` | number | > 0, ≤ 1 | 0.25 | plano, Desempenho (0,25 s, só se o bench passar de 2 s) |
| `sim_fast_enabled` | bool | — | false | plano, Desempenho (desligado) |
| `max_offline_hours` | number | > 0, ≤ 48 | 12.0 | plano, Relógio e RF-47 (12 h) |
| `max_expedition_hours` | number | > 0, ≤ 48 | 12.0 | RF-39 (1 a 12 h) |
| `min_expedition_hours` | number | > 0, ≤ 48 | 1.0 | RF-39 (1 h) |
| `max_ai_rules` | int | ≥ 1, ≤ 16 | 6 | RF-39 (6 regras) |
| `max_rares_per_expedition` | int | ≥ 0, ≤ 100 | 4 | RF-34 (4 Raros) |
| `xp_cap_levels_above_area` | int | ≥ 0, ≤ 10 | 2 | RF-33 (2 níveis acima da área) |
| `ai_base_dodge` | number | ≥ 0, ≤ 1 | 0.5 | PROVISÓRIO. Não definido no plano nem nos requisitos. Arquitetura 04 §12 usa como premissa |
| `retreat_life_fraction` | number | ≥ 0, ≤ 1 | 0.25 | PROVISÓRIO. Arquitetura 04 §12 e §15 (20%) |
| `vigor_h1_4` | number | ≥ 0, ≤ 1 | 1.0 | RF-36 (100%) |
| `vigor_h5_8` | number | ≥ 0, ≤ 1 | 0.7 | RF-36 (70%) |
| `vigor_h9_12` | number | ≥ 0, ≤ 1 | 0.4 | RF-36 (40%) |
| `vigor_band_hours` | number | > 0, ≤ 12 | 4.0 | RF-36 (faixas de 4 h) |
| `fervor_xp_mult` | number | ≥ 1 | 3.0 | RF-32 (XP ×3) |
| `fervor_gold_mat_mult` | number | ≥ 1 | 1.25 | RF-32 (ouro e materiais ×1,25) |
| `fervor_rare_mult` | number | ≥ 1 | 2.0 | RF-32 (chance de Raro ×2) |
| `charges_max` | int | ≥ 1, ≤ 100 | 12 | RF-35 (máximo 12 guardadas) |
| `charges_per_hour` | int | ≥ 1, ≤ 12 | 1 | RF-35 (1 carga por hora) |
| `charges_clear_area` | int | ≥ 0, ≤ 12 | 1 | RF-35 (+1 ao limpar na mão) |
| `charges_boss` | int | ≥ 0, ≤ 12 | 2 | RF-35 (+2 ao vencer o chefe) |
| `charges_new_area` | int | ≥ 0, ≤ 12 | 3 | RF-35 (+3 ao conquistar área nova) |
| `charges_daily_rest` | int | ≥ 0, ≤ 12 | 4 | RF-35 (+4 por descanso no dia UTC) |
| `clock_rollback_tolerance_s` | number | ≥ 0 | 300.0 | RF-48 (5 min) |
| `steam_clock_max_skew_s` | number | ≥ 0 | 600.0 | plano, Relógio (10 min) |
| `xp_base` | number | > 0 | 100.0 | plano, Progressão e RF-05 (100) |
| `xp_scale` | number | ≥ 0 | 60.0 | plano, Progressão e RF-05 (60) |
| `xp_exponent` | number | ≥ 0, ≤ 3, múltiplo de 0.5 | 1.5 | plano, Progressão e RF-05 (1,5) |
| `max_level` | int | ≥ 1, ≤ 100 | 30 | plano (nível 30) |
| `dodge_max_charges` | int | ≥ 1 | 3 | docs/13 item 1: Esquiva: cargas maximas |
| `dodge_recharge` | number | ≥ 0 | 1.5 | docs/13 item 1: Esquiva: recarga por carga (s), em serie |
| `dodge_duration` | number | ≥ 0 | 0.35 | docs/13 item 1: Esquiva: duracao total (s) |
| `dodge_iframes` | number | ≥ 0 | 0.2 | docs/13 item 1: Esquiva: invulnerabilidade (s), dentro da duracao |
| `dodge_distance` | number | ≥ 0 | 400 | docs/13 item 1 [HIPÓTESE]: Esquiva: distancia (uu) [HIPOTESE] |
| `dodge_cost_resource` | number | ≥ 0 | 0 | docs/13 item 1: Esquiva: custo de Impeto (0; o custo e uma carga) |
| `dodge_buffer` | number | ≥ 0 | 0.1 | docs/13 item 1 [HIPÓTESE]: Esquiva: buffer de entrada (s) [HIPOTESE] |
| `dodge_perfect_resource` | number | ≥ 0 | 10 | docs/13 item 1 [HIPÓTESE]: Esquiva perfeita: Impeto ganho (opcional) [HIPOTESE] |
| `guard_break_stagger_seconds` | number | ≥ 0 | 1.5 | docs/13 item 3: Guarda Quebrada: atordoamento (stagger, s) |
| `guard_break_stagger_damage_taken` | number | ≥ 0 | 0.3 | docs/13 item 3: Guarda Quebrada: dano recebido extra durante o stagger |
| `guard_break_immunity_boss` | number | ≥ 0 | 8 | docs/13 item 3: Guarda Quebrada: imunidade a nova quebra no chefe (s) |
| `guard_break_immunity_other` | number | ≥ 0 | 4 | docs/13 item 3: Guarda Quebrada: imunidade em elite e Arauto (s) |
| `boss_shield_down_seconds` | number | ≥ 0 | 5 | docs/13 item 3: Escudo do chefe caido apos Guarda Quebrada (s) |
| `elite_life_mult` | number | ≥ 1 | 2.0 | docs/13 item 5: Elite sorteada: multiplicador de vida |
| `elite_damage_mult` | number | ≥ 1 | 1.2 | docs/13 item 5: Elite sorteada: multiplicador de dano |
| `elite_xp_mult` | number | ≥ 1 | 3.0 | docs/13 item 5: Elite sorteada: multiplicador de XP |
| `potion_lockout` | number | ≥ 0 | 1.0 | docs/13 item 2: Trava global entre usos de pocao (s) |

Regras de conteúdo:

- `min_expedition_hours <= max_expedition_hours`.
- `max_expedition_hours <= max_offline_hours` (aviso).
- Vigor não crescente por faixa (aviso). `sim_step_fast >= sim_step`.
- `3 × vigor_band_hours >= max_expedition_hours`.
- `charges_per_hour × max_expedition_hours <= charges_max` (aviso).

Exemplo (`ShatterCore/tests/data/rules.csv`):

```csv
key,value
crit_multiplier_base,1.5
evasion_cap,0.7
```

### `meta.csv`

- Chave primária: `key`.
- Formato key-value (`key,value`). Todas as chaves são obrigatórias.

| Chave | Tipo | Faixa | Descrição |
|---|---|---|---|
| `content_version` | int | ≥ 1 | Versão do conteúdo; sobe a cada release que muda dados. Gravada em todo save e expedição. |

Regras de conteúdo:

- `content_version` é inteiro e mínimo 1 (seção 5).

Exemplo (`ShatterCore/tests/data/meta.csv`):

```csv
key,value
content_version,1
```


### `classes.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,resourceId,startingSkill,specializations,resourceOnHit,resourceOnBlock,resourceDecayOutOfCombat,regenMultWhileMoving`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `class.*` | sim | — | — | ID da classe |
| `resourceId` | enum: `resource.momentum`, `resource.focus`, `resource.mana` | sim | — | — | Recurso da classe |
| `startingSkill` | ID → `skills.csv` | sim | — | — | Habilidade inicial |
| `specializations` | lista (`\|`) de ID `spec.*` | não | — | — | Especializações (IDs, sem tabela no protótipo) |
| `resourceOnHit` | número (ponto decimal) | não | ≥ 0 | 0 | Recurso ganho ao acertar |
| `resourceOnBlock` | número (ponto decimal) | não | ≥ 0 | 0 | Recurso ganho ao bloquear |
| `resourceDecayOutOfCombat` | número (ponto decimal) | não | ≥ 0 | 0 | Recurso perdido por s fora de combate |
| `regenMultWhileMoving` | número (ponto decimal) | não | ≥ 0, ≤ 1 | 1 | Multiplicador de regen andando (Foco: 0.3) |

Regras de conteúdo:

- Cada classe precisa de `life` e `resource` em `class_stats.csv`.
- `startingSkill` tem que ser de outra classe ou sem classe, e ter `unlockLevel = 1`.

Exemplo (`ShatterCore/tests/data/classes.csv`):

```csv
id,resourceId,startingSkill,specializations,resourceOnHit,resourceOnBlock,resourceDecayOutOfCombat,regenMultWhileMoving
class.warrior,resource.momentum,skill.warrior.iron_cut,,10,10,5,1
```

### `class_stats.csv`

- Chave primária: `classId` + `stat`.
- Cabeçalho exato: `classId,stat,base,perLevel`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `classId` | ID → `classes.csv` | sim | — | — | Classe |
| `stat` | enum stats: `life`, `life_regen`, `resource`, `resource_regen`, `armor`, `evasion_chance`, `block_chance`, `resist_fire`, `resist_cold`, `resist_lightning`, `damage`, `attack_speed`, `cast_speed`, `crit_chance`, `crit_multiplier`, `move_speed`, `cooldown_recovery`, `area_of_effect`, `projectile_count`, `damage_taken`, `potion_effect` | sim | — | — | Atributo (StatId) |
| `base` | número (ponto decimal) | sim | — | — | Valor no nível 1 |
| `perLevel` | número (ponto decimal) | não | — | 0 | Ganho por nível |

Regras de conteúdo:

- `life` com base maior que 0.

Exemplo (`ShatterCore/tests/data/class_stats.csv`):

```csv
classId,stat,base,perLevel
class.warrior,life,100,10
class.warrior,resource,100,0
```

### `skills.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,classId,specId,tags,shape,scalesWithWeapon,baseDamagePhysical,baseDamageFire,baseDamageCold,baseDamageLightning,coefficientRank1,coefficientRank2,coefficientRank3,cost,cooldown,windup,impact,recovery,range,radius,projectiles,onHitEffects,selfEffects,idleSupported,idleAvgTargetsHit,idleFractionOfGroupHit,idleApproachTime,idleUptime,idleDodgeTelegraphedBonus,idleDamageTakenMult,idleParitySampleSize,unlockLevel,coneAngle,knockback,projectileSpeed,idleCalibration`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `skill.*` | sim | — | — | skill.<classe>.<nome> ou skill.enemy.<nome> |
| `classId` | ID → `classes.csv` | não | — | — | Classe dona (vazio = qualquer/inimigo) |
| `specId` | ID `spec.*` | não | — | — | Especialização (vazio = básica) |
| `tags` | tags (`\|`): `attack`, `spell`, `melee`, `projectile`, `area`, `fire`, `cold`, `lightning`, `physical` | sim | — | — | Tags da habilidade |
| `shape` | enum shapes: `melee`, `cone`, `projectile`, `area`, `dash`, `self`, `channel`, `trap` | sim | — | — | Forma espacial |
| `scalesWithWeapon` | bool (`true`/`false`) | não | — | false | Dano base vem da arma |
| `baseDamagePhysical` | número (ponto decimal) | não | ≥ 0 | 0 | Dano base (physical) |
| `baseDamageFire` | número (ponto decimal) | não | ≥ 0 | 0 | Dano base (fire) |
| `baseDamageCold` | número (ponto decimal) | não | ≥ 0 | 0 | Dano base (cold) |
| `baseDamageLightning` | número (ponto decimal) | não | ≥ 0 | 0 | Dano base (lightning) |
| `coefficientRank1` | número (ponto decimal) | não | ≥ 0 | 1 | Coeficiente rank 1 |
| `coefficientRank2` | número (ponto decimal) | não | ≥ 0 | 1 | Coeficiente rank 2 |
| `coefficientRank3` | número (ponto decimal) | não | ≥ 0 | 1 | Coeficiente rank 3 |
| `cost` | número (ponto decimal) | não | ≥ 0 | 0 | Custo de recurso |
| `cooldown` | número (ponto decimal) | não | ≥ 0 | 0 | Recarga (s); 0 ou >= cooldown_min |
| `windup` | número (ponto decimal) | não | ≥ 0 | 0 | Preparação (s) |
| `impact` | número (ponto decimal) | não | ≥ 0 | 0 | Até o impacto após windup (s) |
| `recovery` | número (ponto decimal) | não | ≥ 0 | 0 | Recuperação (s) |
| `range` | número (ponto decimal) | não | ≥ 0 | 0 | Alcance (uu) |
| `radius` | número (ponto decimal) | não | ≥ 0 | 0 | Raio (uu) |
| `projectiles` | inteiro | não | ≥ 1, ≤ 50 | 1 | Projéteis |
| `onHitEffects` | lista (`\|`) de ID → `effects.csv` | não | — | — | Efeitos ao acertar |
| `selfEffects` | lista (`\|`) de ID → `effects.csv` | não | — | — | Efeitos em quem usa |
| `idleSupported` | bool (`true`/`false`) | não | — | false | Tem IdleProfile validado |
| `idleAvgTargetsHit` | número (ponto decimal) | não | ≥ 0 | 1 | Alvos médios atingidos |
| `idleFractionOfGroupHit` | número (ponto decimal) | não | ≥ 0, ≤ 1 | 0 | Fração do grupo atingida (0 = usar avg) |
| `idleApproachTime` | número (ponto decimal) | não | ≥ 0 | 0 | s para alcançar alvos |
| `idleUptime` | número (ponto decimal) | não | ≥ 0, ≤ 1 | 1 | Fração do tempo usável |
| `idleDodgeTelegraphedBonus` | número (ponto decimal) | não | ≥ 0, ≤ 1 | 0 | Soma à esquiva base da IA |
| `idleDamageTakenMult` | número (ponto decimal) | não | ≥ 0 | 1 | Multiplicador de dano recebido |
| `idleParitySampleSize` | inteiro | não | ≥ 0 | 0 | Nº de encontros da calibração (0 = não calibrado) |
| `unlockLevel` | inteiro | não | ≥ 1, ≤ 100 | 1 | Nível de liberação |
| `coneAngle` | número | não | ≥ 0, ≤ 360 | 0 | Angulo do cone (graus, total) |
| `knockback` | número | não | ≥ 0 | 0 | Empurrao ao acertar (uu) |
| `projectileSpeed` | número | não | ≥ 0 | 0 | Velocidade do projetil (uu/s) |
| `idleCalibration` | enum: `none`, `manual_estimate`, `bot_parity` | não | — | none | Calibracao do perfil idle: none / manual_estimate / bot_parity |

Regras de conteúdo:

- `cooldown` entre 0 e `cooldown_min`: erro. `idleSupported=true` exige `idleParitySampleSize > 0`.
- `classId` define o prefixo do ID (`skill.<classe>.*`). Sem classe, o ID é `skill.enemy.*` ou `skill.common.*`.
- Coeficientes não decrescentes (aviso). Com `scalesWithWeapon=true`, `baseDamage*` é ignorado (aviso).
- `windup + impact + recovery = 0` (aviso, exceto `shape = self`).
- Idle suportado sem alvos (`idleAvgTargetsHit` e `idleFractionOfGroupHit` zerados): erro.

Exemplo (`ShatterCore/tests/data/skills.csv`):

```csv
id,classId,specId,tags,shape,scalesWithWeapon,baseDamagePhysical,baseDamageFire,baseDamageCold,baseDamageLightning,coefficientRank1,coefficientRank2,coefficientRank3,cost,cooldown,windup,impact,recovery,range,radius,projectiles,onHitEffects,selfEffects,idleSupported,idleAvgTargetsHit,idleFractionOfGroupHit,idleApproachTime,idleUptime,idleDodgeTelegraphedBonus,idleDamageTakenMult,idleParitySampleSize,unlockLevel
skill.warrior.iron_cut,class.warrior,,attack|melee|physical,melee,,10,,,,1,1.1,1.2,0,0.5,0.2,0.1,0.2,60,,1,,,false,,,,,,,,1
skill.enemy.sentinel_strike,,,attack|melee|physical,melee,,8,,,,,,,0,0,0.7,0.1,0.5,50,,1,,,false,,,,,,,,1
```

### `effects.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,duration,tickInterval,stackRule,maxStacks,damagePerTickPhysical,damagePerTickFire,damagePerTickCold,damagePerTickLightning,modifiers,barrier,trigger,triggerChance,internalCooldown,tags,interruptsAction`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `effect.*` | sim | — | — | ID do efeito |
| `duration` | número (ponto decimal) | não | ≥ 0 | 0 | Duração (s); 0 = instantâneo |
| `tickInterval` | número (ponto decimal) | não | ≥ 0 | 0 | Intervalo de tick (s); 0 = sem tick |
| `stackRule` | enum: `refresh`, `stack_n`, `strongest_only` | não | — | refresh | Regra de acúmulo |
| `maxStacks` | inteiro | não | ≥ 1, ≤ 100 | 1 | Máx. instâncias (stack_n) |
| `damagePerTickPhysical` | número (ponto decimal) | não | ≥ 0 | 0 | Dano por tick (physical) |
| `damagePerTickFire` | número (ponto decimal) | não | ≥ 0 | 0 | Dano por tick (fire) |
| `damagePerTickCold` | número (ponto decimal) | não | ≥ 0 | 0 | Dano por tick (cold) |
| `damagePerTickLightning` | número (ponto decimal) | não | ≥ 0 | 0 | Dano por tick (lightning) |
| `modifiers` | modificadores (`\|`) `stat:kind:valor[:tag+tag]` | não | — | — | Mods enquanto ativo |
| `barrier` | número (ponto decimal) | não | ≥ 0 | 0 | Barreira concedida |
| `trigger` | enum: `none`, `on_hit`, `on_crit`, `on_block`, `on_kill`, `on_take_damage` | não | — | none | Gatilho automático |
| `triggerChance` | número (ponto decimal) | não | ≥ 0, ≤ 1 | 1 | Chance do gatilho |
| `internalCooldown` | número (ponto decimal) | não | ≥ 0 | 0 | Recarga interna (s); efetivo = max(valor, trigger_icd_min) |
| `tags` | tags (`\|`): `attack`, `spell`, `melee`, `projectile`, `area`, `fire`, `cold`, `lightning`, `physical` | não | — | — | Tags do dano do efeito |
| `interruptsAction` | bool | não | — | false | Interrompe preparacao/telegraph do alvo |

Regras de conteúdo:

- `damagePerTick*` maior que 0 exige `tickInterval > 0`. `tickInterval > 0` exige `duration > 0`.
- `maxStacks` só vale com `stackRule = stack_n` (aviso). `triggerChance` só vale com `trigger` (aviso).
- `internalCooldown` abaixo de `trigger_icd_min`: o core usa o mínimo (aviso).

`effects.csv`, exemplo ilustrativo:

```csv
id,duration,tickInterval,stackRule,maxStacks,damagePerTickPhysical,damagePerTickFire,damagePerTickCold,damagePerTickLightning,modifiers,barrier,trigger,triggerChance,internalCooldown,tags
effect.burn,4,1,refresh,1,,3,,,,0,none,1,0,fire
```

### `enemies.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,familyId,stats,xpBase,xpPerLevel,lootTableId,isBoss,isElite,moveSpeed,aggroRange,stunImmune,shieldArcDegrees,turnRateDegPerSec,turnRateDegPerSecPhase2,guardBreakStaggerSeconds,guardBreakImmunitySeconds,modifierId`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `enemy.*` | sim | — | — | ID do inimigo |
| `familyId` | ID `family.*` | sim | — | — | Família |
| `stats` | crescimentos (`\|`) `stat:base:porNível` | sim | — | — | Atributos por nível: stat:base:perLevel\|... |
| `xpBase` | número (ponto decimal) | não | ≥ 0 | 0 | XP no nível 1 |
| `xpPerLevel` | número (ponto decimal) | não | ≥ 0 | 0 | XP extra por nível |
| `lootTableId` | ID → `loot_tables.csv` | não | — | — | Tabela de loot |
| `isBoss` | bool (`true`/`false`) | não | — | false | Chefe |
| `isElite` | bool (`true`/`false`) | não | — | false | Elite fixa |
| `moveSpeed` | número (ponto decimal) | não | ≥ 0 | 0 | Velocidade (uu/s) |
| `aggroRange` | número (ponto decimal) | não | ≥ 0 | 0 | Alcance de aggro (uu) |
| `stunImmune` | bool | não | — | false | Imune a atordoamento (elite, Arauto e chefe) |
| `shieldArcDegrees` | número | não | ≥ 0, ≤ 360 | 0 | Arco do escudo frontal (graus, total; 0 = sem escudo) |
| `turnRateDegPerSec` | número | não | ≥ 0 | 0 | Giro (graus/s) na fase 1 ou fixo |
| `turnRateDegPerSecPhase2` | número | não | ≥ 0 | 0 | Giro (graus/s) na fase 2 |
| `guardBreakStaggerSeconds` | número | não | ≥ 0 | 0 | Atordoamento da Guarda Quebrada (s) |
| `guardBreakImmunitySeconds` | número | não | ≥ 0 | 0 | Imunidade a nova Guarda Quebrada (s) |
| `modifierId` | ref `elite_modifiers.csv` | não | — | — | Modificador fixo de elite (elite_modifiers.csv) |

Regras de conteúdo:

- `stats` precisa de `life` com base maior que 0.
- Todo inimigo precisa de ao menos uma linha em `enemy_attacks.csv`.
- `isBoss` e `isElite` juntos: aviso.

Exemplo (`ShatterCore/tests/data/enemies.csv`):

```csv
id,familyId,stats,xpBase,xpPerLevel,lootTableId,isBoss,isElite,moveSpeed,aggroRange
enemy.hollow_sentinel,family.soldier_echo,life:80:8|armor:10:0,10,2,loot.crypt.common,false,false,2,6
```

### `enemy_attacks.csv`

- Chave primária: `enemyId` + `skillId`.
- Cabeçalho exato: `enemyId,skillId,weight,telegraphed`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `enemyId` | ID → `enemies.csv` | sim | — | — | Inimigo |
| `skillId` | ID → `skills.csv` | sim | — | — | Habilidade usada |
| `weight` | número (ponto decimal) | não | > 0 | 1 | Peso de escolha (> 0) |
| `telegraphed` | bool (`true`/`false`) | não | — | false | Telegrafado (IA pode esquivar) |

Regras de conteúdo:

- `enemyId` e `skillId` precisam existir (ref).

Exemplo (`ShatterCore/tests/data/enemy_attacks.csv`):

```csv
enemyId,skillId,weight,telegraphed
enemy.hollow_sentinel,skill.enemy.sentinel_strike,1,true
```

### `affixes.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,kind,stat,modKind,requiredTags,minValue,maxValue,minItemLevel,weight,allowedSlots,group,craftInscription`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `affix.*` | sim | — | — | ID do afixo |
| `kind` | enum: `prefix`, `suffix` | sim | — | — | Prefixo/sufixo |
| `stat` | enum stats: `life`, `life_regen`, `resource`, `resource_regen`, `armor`, `evasion_chance`, `block_chance`, `resist_fire`, `resist_cold`, `resist_lightning`, `damage`, `attack_speed`, `cast_speed`, `crit_chance`, `crit_multiplier`, `move_speed`, `cooldown_recovery`, `area_of_effect`, `projectile_count`, `damage_taken`, `potion_effect` | sim | — | — | Atributo |
| `modKind` | enum modKinds: `flat`, `increased`, `more` | sim | — | — | Tipo de modificador |
| `requiredTags` | tags (`\|`): `attack`, `spell`, `melee`, `projectile`, `area`, `fire`, `cold`, `lightning`, `physical` | não | — | — | Tags exigidas do mod gerado |
| `minValue` | número (ponto decimal) | sim | — | — | Valor mínimo |
| `maxValue` | número (ponto decimal) | sim | — | — | Valor máximo (>= min) |
| `minItemLevel` | inteiro | não | ≥ 1, ≤ 100 | 1 | Nível mínimo de item |
| `weight` | número (ponto decimal) | não | > 0 | 1 | Peso de sorteio (> 0) |
| `allowedSlots` | lista (`\|`) de enum: `main_hand`, `off_hand`, `head`, `body`, `hands`, `feet`, `amulet`, `ring`, `ring2`, `belt` | não | — | — | Posições permitidas (vazio = todas) |
| `group` | texto (regex `^[a-z0-9_]+$`) | não | — | — | Grupo exclusivo |
| `craftInscription` | bool (`true`/`false`) | não | — | false | Disponível em Fixar Inscrição |

Regras de conteúdo:

- `minValue <= maxValue`.

`affixes.csv`, exemplo ilustrativo:

```csv
id,kind,stat,modKind,requiredTags,minValue,maxValue,minItemLevel,weight,allowedSlots,group,craftInscription
affix.life_flat,prefix,life,flat,,10,20,1,10,body|head,life,false
```

### `item_bases.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,slot,itemLevel,implicitMods,weaponDamagePhysical,weaponDamageFire,weaponDamageCold,weaponDamageLightning,attackTime,weaponTags,grammaticalGender`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `item_base.*` | sim | — | — | ID da base |
| `slot` | enum slots: `main_hand`, `off_hand`, `head`, `body`, `hands`, `feet`, `amulet`, `ring`, `ring2`, `belt` | sim | — | — | Posição |
| `itemLevel` | inteiro | não | ≥ 1, ≤ 100 | 1 | Nível do item |
| `implicitMods` | modificadores (`\|`) `stat:kind:valor[:tag+tag]` | não | — | — | Propriedade da base |
| `weaponDamagePhysical` | número (ponto decimal) | não | ≥ 0 | 0 | Dano da arma (physical) |
| `weaponDamageFire` | número (ponto decimal) | não | ≥ 0 | 0 | Dano da arma (fire) |
| `weaponDamageCold` | número (ponto decimal) | não | ≥ 0 | 0 | Dano da arma (cold) |
| `weaponDamageLightning` | número (ponto decimal) | não | ≥ 0 | 0 | Dano da arma (lightning) |
| `attackTime` | número (ponto decimal) | não | ≥ 0 | 0 | s por ataque (armas) |
| `weaponTags` | tags (`\|`): `attack`, `spell`, `melee`, `projectile`, `area`, `fire`, `cold`, `lightning`, `physical` | não | — | — | melee ou projectile (armas) |
| `grammaticalGender` | enum: `m`, `f` | não | — | m | Gênero gramatical |

Regras de conteúdo:

- `main_hand` exige `attackTime > 0`, dano de arma maior que 0 e `weaponTags` exatamente `melee` ou `projectile`.
- Outros slots não podem ter dano de arma, tempo de ataque nem `weaponTags`.

Exemplo (`ShatterCore/tests/data/item_bases.csv`):

```csv
id,slot,itemLevel,implicitMods,weaponDamagePhysical,weaponDamageFire,weaponDamageCold,weaponDamageLightning,attackTime,weaponTags,grammaticalGender
item_base.iron_sword,main_hand,1,,10,,,,1.0,melee,m
```

### `uniques.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,baseId,fixedMods,ruleEffectId,idleSupported,idleParitySampleSize,idleCalibration`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `unique.*` | sim | — | — | ID do Único |
| `baseId` | ID → `item_bases.csv` | sim | — | — | Base |
| `fixedMods` | modificadores (`\|`) `stat:kind:valor[:tag+tag]` | não | — | — | Atributos fixos |
| `ruleEffectId` | ID → `effects.csv` | não | — | — | Efeito que muda a build |
| `idleSupported` | bool (`true`/`false`) | não | — | false | Tem perfil idle testado |
| `idleParitySampleSize` | inteiro | não | ≥ 0 | 0 | Amostra da calibracao idle (encontros medidos) |
| `idleCalibration` | enum: `none`, `manual_estimate`, `bot_parity` | não | — | none | Calibracao do perfil idle: none / manual_estimate / bot_parity |

Regras de conteúdo:

- Sem regra própria. Pendências P2 (paridade do idle) e P5 (só do chefe).

`uniques.csv`, exemplo ilustrativo:

```csv
id,baseId,fixedMods,ruleEffectId,idleSupported
unique.bell_warden_blade,item_base.iron_sword,damage:increased:0.2:melee,effect.burn,false
```

### `loot_tables.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,rolls,dropChance,rarityWeightNormal,rarityWeightMagic,rarityWeightRare`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `loot.*` | sim | — | — | ID da tabela |
| `rolls` | inteiro | não | ≥ 1, ≤ 100 | 1 | Sorteios por chamada |
| `dropChance` | número (ponto decimal) | não | ≥ 0, ≤ 1 | 1 | Chance de cada sorteio cair |
| `rarityWeightNormal` | número (ponto decimal) | não | ≥ 0 | 80 | Peso Normal |
| `rarityWeightMagic` | número (ponto decimal) | não | ≥ 0 | 18 | Peso Mágico |
| `rarityWeightRare` | número (ponto decimal) | não | ≥ 0 | 2 | Peso Raro |

Regras de conteúdo:

- `rarityWeightNormal + Magic + Rare` maior que 0.
- Precisa de ao menos uma linha em `loot_entries.csv`.
- Subtabelas sem ciclo e com profundidade até 8.

Exemplo (`ShatterCore/tests/data/loot_tables.csv`):

```csv
id,rolls,dropChance,rarityWeightNormal,rarityWeightMagic,rarityWeightRare
loot.crypt.common,1,1,80,18,2
```

### `loot_entries.csv`

- Chave primária: nenhuma (a ordem é a do CSV).
- Cabeçalho exato: `tableId,kind,refId,weight,minAmount,maxAmount,minAreaLevel,maxAreaLevel,manualOnly,fixedChance,guaranteeFirstKill,pityKills`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `tableId` | ID → `loot_tables.csv` | sim | — | — | Tabela dona |
| `kind` | enum: `item_base`, `unique`, `stack`, `spec_book`, `map_stone`, `echo_fragment`, `table`, `nothing` | sim | — | — | Tipo de entrada |
| `refId` | ID | não | — | — | Alvo (depende de kind; vazio só em nothing) |
| `weight` | número (ponto decimal) | não | > 0 | 1 | Peso (> 0) |
| `minAmount` | inteiro | não | ≥ 1 | 1 | Quantidade mínima (stack) |
| `maxAmount` | inteiro | não | ≥ 1 | 1 | Quantidade máxima (stack) |
| `minAreaLevel` | inteiro | não | ≥ 1, ≤ 999 | 1 | Nível de área mínimo |
| `maxAreaLevel` | inteiro | não | ≥ 1, ≤ 999 | 999 | Nível de área máximo |
| `manualOnly` | bool (`true`/`false`) | não | — | false | Nunca cai no idle |
| `fixedChance` | número | não | ≥ 0, ≤ 1 | 0 | Chance fixa de cair, independe do peso (0 a 1) |
| `guaranteeFirstKill` | bool | não | — | false | Garante a 1a vitoria sobre o chefe |
| `pityKills` | inteiro | não | ≥ 0 | 0 | Vitorias seguidas sem drop que garantem o item (0 = sem protecao) |

Regras de conteúdo:

- `kind = nothing` não usa `refId`.
- `stack` exige prefixo `currency.`, `material.`, `page.` ou `sigil.common.`. `material.echo_fragment` não é stack.
- `item_base`, `unique` e `table` exigem o prefixo e o ID existente na tabela correspondente.
- `unique`, `spec_book`, `map_stone` e `echo_fragment` exigem `manualOnly = true` (regra 4 do idle).
- `minAmount` e `maxAmount` só valem para `stack` (aviso). `minAmount <= maxAmount` e `minAreaLevel <= maxAreaLevel`.

Exemplo (`ShatterCore/tests/data/loot_entries.csv`):

```csv
tableId,kind,refId,weight,minAmount,maxAmount,minAreaLevel,maxAreaLevel,manualOnly
loot.crypt.common,item_base,item_base.iron_sword,10,1,1,1,999,false
loot.crypt.common,stack,currency.gold,90,5,15,1,999,false
```

### `encounters.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,groups,weight,travelTime,isBoss`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `enc.*` | sim | — | — | ID do encontro |
| `groups` | grupos (`\|`) `enemy:min:max:chanceElite` | sim | — | — | enemyId:countMin:countMax:eliteChance\|... |
| `weight` | número (ponto decimal) | não | > 0 | 1 | Peso de escolha (> 0) |
| `travelTime` | número (ponto decimal) | não | ≥ 0 | 0 | Travessia até o próximo grupo (s) |
| `isBoss` | bool (`true`/`false`) | não | — | false | Encontro de chefe |

Regras de conteúdo:

- `groups` não vazio; cada `enemyId` existe em `enemies.csv`.
- `isBoss = true` exige chefe no grupo, e grupo com chefe exige `isBoss = true`.

Exemplo (`ShatterCore/tests/data/encounters.csv`):

```csv
id,groups,weight,travelTime,isBoss
enc.crypt.patrol_a,enemy.hollow_sentinel:1:2:0.1,1,5,false
```

### `maps.csv`

- Chave primária: `id`.
- Cabeçalho exato: `id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `map.*` | sim | — | — | ID do mapa |
| `monsterLevel` | inteiro | sim | ≥ 1, ≤ 100 | — | Nível de monstro |
| `tier` | inteiro | não | ≥ 0, ≤ 5 | 0 | 0 = campanha; 1..5 endgame |
| `encounters` | lista (`\|`) de ID → `encounters.csv` | sim | — | — | Encontros da rota |
| `bossEncounter` | ID → `encounters.csv` | não | — | — | Encontro do chefe |
| `areaLootTable` | ID → `loot_tables.csv` | não | — | — | Loot extra por encontro |
| `idleAllowed` | bool (`true`/`false`) | não | — | true | Pode ser rota de expedição |

Regras de conteúdo:

- Encontro de chefe vai em `bossEncounter`, não em `encounters`; `bossEncounter` precisa de `isBoss = true`.
- Mapa `map.endgame.*` com tier 0: aviso.

Exemplo (`ShatterCore/tests/data/maps.csv`):

```csv
id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed
map.act1.crypt,1,0,enc.crypt.patrol_a,,loot.crypt.common,true
```


## 5a. Tabelas e colunas acrescidas (docs/13, itens 1 a 9)

Fonte: `docs/13_design_pendencias.md`, seção 'Para o Data Engineer'. Nomes de tabela, coluna e chave são os do docs/13. Tabelas novas: `potions`, `elite_modifiers`, `boss_phases`, `boss_patterns`, `enemy_ai`. Colunas novas: as das seções 'Cabeçalho exato' das tabelas `skills`, `enemies`, `effects`, `uniques` e `loot_entries` (acima, já atualizadas), e `class_stats` (linha nova `class.warrior,move_speed,450,0`).

Vazio numa célula = padrão do esquema. Um peso vazio em `loot_entries` só vale com `fixedChance` > 0 (Único do Guardião, item 9).

### `potions.csv`

Poções do jogador (docs/13 item 2). Vida (tecla 1) e Resguardo (tecla 2).

- Chave primária: `id`.
- Cabeçalho exato: `id,kind,fractionOfMaxLife,duration,maxCharges,rechargeSeconds,useTime,moveSpeedWhileUsing,globalLockout,refillOnEliteKill,hotkeySlot`.
- Cura e barreira no mesmo esquema. Vazio em `duration` para cura. `moveSpeedWhileUsing` 0,5 nas duas (docs/13 diz 'igual' à Vida; ver relatório).

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `potion.*` | sim | — | — | ID da pocao |
| `kind` | enum: `heal`, `barrier` | sim | — | — | heal (cura) ou barrier (barreira) |
| `fractionOfMaxLife` | número | sim | ≥ 0, ≤ 1 | — | Fracao da vida maxima (cura ou barreira) |
| `duration` | número | não | ≥ 0 | 0 | Duracao da barreira (s); vazio = nao se aplica |
| `maxCharges` | inteiro | sim | ≥ 1 | — | Cargas maximas |
| `rechargeSeconds` | número | sim | > 0 | — | Recarga por carga (s), em serie |
| `useTime` | número | sim | > 0 | — | Tempo de uso (s) |
| `moveSpeedWhileUsing` | número | não | ≥ 0, ≤ 1 | 1 | Fracao da velocidade de movimento durante o uso |
| `globalLockout` | número | não | ≥ 0 | 0 | Trava global entre usos de pocao (s) |
| `refillOnEliteKill` | bool | não | — | false | Matar elite da +1 carga (a pocao com menos cargas) |
| `hotkeySlot` | inteiro | sim | ≥ 1, ≤ 9 | — | Tecla (1 a 9) |

Checagens do validador: `potion_rules`.

### `elite_modifiers.csv`

Modificadores de elite (docs/13 item 5). Volátil fica com peso 0 (desligado no protótipo).

- Chave primária: `id`.
- Cabeçalho exato: `id,weightPrototype,lifeMult,damageMult,xpMult,barrierFractionOfLife,moveSpeedMult,attackSpeedMult,recoveryMult,deathExplosionRadius,deathExplosionDamage,deathExplosionFuse`.
- Vazio em `lifeMult`, `damageMult`, `xpMult`, `moveSpeedMult`, `attackSpeedMult` e `recoveryMult` = 1 (sem efeito). Os multiplicadores base de elite estão em `rules.csv`.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `modifier.elite.*` | sim | — | — | ID do modificador |
| `weightPrototype` | número | não | ≥ 0 | 0 | Peso de sorteio no prototipo (0 = desligado) |
| `lifeMult` | número | não | > 0 | 1 | Multiplicador de vida extra (1 = nenhum) |
| `damageMult` | número | não | > 0 | 1 | Multiplicador de dano extra (1 = nenhum) |
| `xpMult` | número | não | > 0 | 1 | Multiplicador de XP extra (1 = nenhum) |
| `barrierFractionOfLife` | número | não | ≥ 0, ≤ 1 | 0 | Barreira, fracao da vida maxima (0 = nenhuma) |
| `moveSpeedMult` | número | não | > 0 | 1 | Multiplicador de velocidade de movimento |
| `attackSpeedMult` | número | não | > 0 | 1 | Multiplicador de velocidade de ataque |
| `recoveryMult` | número | não | > 0 | 1 | Multiplicador de recuperacao |
| `deathExplosionRadius` | número | não | ≥ 0 | 0 | Explosao ao morrer: raio (uu); 0 = nenhuma |
| `deathExplosionDamage` | número | não | ≥ 0 | 0 | Explosao ao morrer: dano fisico |
| `deathExplosionFuse` | número | não | ≥ 0 | 0 | Explosao ao morrer: marca antes do disparo (s) |

Checagens do validador: `modifier_rules`.

### `boss_phases.csv`

Fases do Guardião (docs/13 item 4). Chave: bossId + phase.

- Chave primária: `bossId`, `phase`.
- Cabeçalho exato: `bossId,phase,lifeThreshold,transitionSeconds,summonEnemyId,summonCount,shieldSeconds,turnRate,decisionDelayMin,decisionDelayMax`.
- `lifeThreshold` é a fração da vida em que a fase começa (fase 1 = 1,0; fase 2 = 0,5). `shieldSeconds` ficou vazio: o docs/13 não dá valor por fase (a queda do escudo de 5 s está em `rules.csv`, `boss_shield_down_seconds`).

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `bossId` | ref `enemies.csv` | sim | — | — | Chefe (enemies.csv, isBoss=true) |
| `phase` | inteiro | sim | ≥ 1 | — | Numero da fase (1, 2, ...) |
| `lifeThreshold` | número | sim | > 0, ≤ 1 | — | Fracao da vida em que a fase comeca (1 = inicio) |
| `transitionSeconds` | número | não | ≥ 0 | 0 | Rugido de transicao (s), invulneravel |
| `summonEnemyId` | ref `enemies.csv` | não | — | — | Inimigo invocado na transicao (vazio = nenhum) |
| `summonCount` | inteiro | não | ≥ 0 | 0 | Quantidade invocada (sem reinvocacao) |
| `shieldSeconds` | número | não | ≥ 0 | 0 | Escudo: duracao (s); vazio = nao definido no docs/13 |
| `turnRate` | número | não | ≥ 0 | 0 | Giro (graus/s) nesta fase |
| `decisionDelayMin` | número | não | ≥ 0 | 0 | Atraso minimo entre acoes (s) |
| `decisionDelayMax` | número | não | ≥ 0 | 0 | Atraso maximo entre acoes (s) |

Checagens do validador: `boss_phase_rules`.

### `boss_patterns.csv`

Padrões do Guardião por fase (docs/13 item 4). Chave: id + phase (o mesmo id aparece na fase 1 e na 2, com telegraph diferente).

- Chave primária: `id`, `phase`.
- Cabeçalho exato: `id,bossId,phase,skillId,weight,telegraphSeconds,recoverySeconds,cooldown,maxRepeat,playerNearWeightMult,ignoreIfBehind`.
- `playerNearWeightMult` 2 e `ignoreIfBehind` true só no escudo (docs/13 item 4.3). `maxRepeat` 2 em todos (regra de repetição).

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `id` | ID `pattern.*` | sim | — | — | ID do padrao |
| `bossId` | ref `enemies.csv` | sim | — | — | Chefe dono |
| `phase` | inteiro | sim | ≥ 1 | — | Fase em que o padrao vale |
| `skillId` | ref `skills.csv` | sim | — | — | Habilidade executada |
| `weight` | número | sim | > 0 | — | Peso de sorteio (> 0) |
| `telegraphSeconds` | número | não | ≥ 0 | 0 | Telegraph (s) |
| `recoverySeconds` | número | não | ≥ 0 | 0 | Recuperacao (s) |
| `cooldown` | número | não | ≥ 0 | 0 | Recarga propria (s); vazio = nenhuma |
| `maxRepeat` | inteiro | não | ≥ 0 | 0 | Maximo de repeticoes seguidas (0 = sem limite) |
| `playerNearWeightMult` | número | não | ≥ 0 | 1 | Multiplicador de peso se o jogador esta perto e na frente |
| `ignoreIfBehind` | bool | não | — | false | Nao sorteia se o jogador esta atras |

Checagens do validador: `boss_pattern_rules`.

### `enemy_ai.csv`

IA de Cão-de-Cinza, Cão Veloz e Arqueiro (docs/13 item 6). O Cão Veloz tem intervalo de ficha x0,8 do comum, já calculado.

- Chave primária: `enemyId`.
- Cabeçalho exato: `enemyId,aggroRange,alertRadius,leashRange,leashSeconds,preferredMin,preferredMax,retreatBelow,retreatMaxSeconds,circleMin,circleMax,circleSpeed,attackTokens,tokenIntervalMin,tokenIntervalMax,fleeLifeFraction,fleeSeconds,fleeOncePerLife,attackCooldown,maxSimultaneousShooters`.
- `aggroRange` repete `enemies.csv`; o validador exige igualdade quando preenchido. Sem valor no docs/13 para `alertRadius` do Arqueiro, `leashRange` e `leashSeconds` dele: vazios.

| Coluna | Tipo | Obrig. | Faixa | Padrão | Descrição |
|---|---|---|---|---|---|
| `enemyId` | ref `enemies.csv` | sim | — | — | Inimigo (enemies.csv) |
| `aggroRange` | número | não | ≥ 0 | 0 | Alcance de aggro (uu); se preenchido, deve ser igual ao de enemies.csv |
| `alertRadius` | número | não | ≥ 0 | 0 | Raio de alerta do bando (uu) |
| `leashRange` | número | não | ≥ 0 | 0 | Distancia para voltar ao ponto (uu) |
| `leashSeconds` | número | não | ≥ 0 | 0 | Tempo alem de leashRange para voltar (s) |
| `preferredMin` | número | não | ≥ 0 | 0 | Faixa ideal minima (uu) |
| `preferredMax` | número | não | ≥ 0 | 0 | Faixa ideal maxima (uu) |
| `retreatBelow` | número | não | ≥ 0 | 0 | Recua se o jogador esta abaixo desta distancia (uu) |
| `retreatMaxSeconds` | número | não | ≥ 0 | 0 | Tempo maximo de recuo (s) |
| `circleMin` | número | não | ≥ 0 | 0 | Cerco: distancia minima (uu) |
| `circleMax` | número | não | ≥ 0 | 0 | Cerco: distancia maxima (uu) |
| `circleSpeed` | número | não | ≥ 0 | 0 | Cerco: velocidade de giro (uu/s) |
| `attackTokens` | inteiro | não | ≥ 0 | 0 | Fichas de ataque simultaneas |
| `tokenIntervalMin` | número | não | ≥ 0 | 0 | Intervalo minimo de ficha (s) |
| `tokenIntervalMax` | número | não | ≥ 0 | 0 | Intervalo maximo de ficha (s) |
| `fleeLifeFraction` | número | não | ≥ 0, ≤ 1 | 0 | Foge com vida abaixo desta fracao |
| `fleeSeconds` | número | não | ≥ 0 | 0 | Duracao da fuga (s) |
| `fleeOncePerLife` | bool | não | — | false | Foge so uma vez por vida |
| `attackCooldown` | número | não | ≥ 0 | 0 | Recarga entre disparos/ataques (s) |
| `maxSimultaneousShooters` | inteiro | não | ≥ 0 | 0 | Atiradores simultaneos |

Checagens do validador: `enemy_ai_rules`.

### Nota sobre o Único do Guardião (`loot_entries.csv`)

A linha `loot.crypt.guardian,unique,unique.empty_throne_maul` ficou sem peso (sai do sorteio ponderado), com `fixedChance` 0,2, `guaranteeFirstKill` true e `pityKills` 5. O validador exige que `unique` esteja só em tabela ligada a chefe (`isBoss=true` em `enemies.csv`) e que peso vazio venha com `fixedChance` > 0.

### Calibração do idle (`idleCalibration`)

`none` (padrão), `manual_estimate` ou `bot_parity`. `idleSupported=true` exige calibração diferente de `none` e `idleParitySampleSize` > 0. As 4 habilidades do Guerreiro e o Único estão em `manual_estimate` com amostra 20 (estimativa, selo na tela de previsão).

### Save v2 (proposta, não ativa)

Esquema em `schemas/save_v2.schema.json`, ao lado de `save_v1`. Não é usado pelo core até aprovação.

- `characters[].potions` (inteiro) sai e vira `potion_slots`: lista de exatamente 2 `{potion_id, charges, recharge_remaining}` (Vida e Resguardo).
- Novo `characters[].boss_progress`: lista de `{enemy_id, kills, kills_since_unique}` por personagem (contador do Único, RF-55).
- `ExpeditionRequest.potion_heal_fraction` sai (a cura vem de `potions.csv`). `rules[].ref_id` já existe em v1 e serve para `use_potion`.
- Cargas e relógios de esquiva não são salvos: reiniciam cheios ao carregar (docs/13 item 11).
- `tutorial_flags` do exemplo `migrate_1_to_2` NÃO entra na v2 (não aprovado). A função `migrate_1_to_2` do validador e o fixture `migration/v1_to_v2_expected.json` ainda o geram: são do core/fixtures e continuam como estão até decisão.


## 5. content_version e conteúdo publicado

- `meta.csv`: `content_version` é inteiro, mínimo 1, e sobe a cada release que muda dados. Ele é gravado em todo save (`content_version`) e em todo pedido de expedição (`request.content_version` e `snapshot.content_version`).
- Save com `content_version` maior que o do jogo é recusado sem alterar o arquivo (`E_TOO_NEW`, RNF-10). Expedição iniciada com versão antiga é simulada com o conteúdo atual. Se um ID do snapshot foi removido, a parada é `ContentMismatch` (arquitetura, seção 12).
- `content_lock.json` (ainda não existe, porque não há release) é criado por `validate_data.py --update-lock` na primeira release. Ele guarda os IDs publicados e o digest dos CSV. O validador falha se um ID publicado sumiu, ou se os dados mudaram sem `content_version` subir.

## 6. Save JSON (save_v1)

Arquivo `slot_N.json`, com envelope `{format, save_version, sha256, data}` nessa ordem.

- `format` = `echoes-of-the-shatter-save`. `save_version` = 1 (`kCurrentSaveVersion`).
- `sha256` = SHA-256 da forma compacta canônica de `data` (chaves na ordem de escrita, sem espaços). O validador espelha essa regra em `canonical()`. O core tem que produzir o mesmo hash para `ShatterCore/tests/data/saves/save_v1.json`.
- uid de item, seed, hash de resultado e `next_item_uid` são texto decimal, porque são uint64 (arquitetura, seção 8). Contagens e tempos de jogo são inteiros ou números. Tempo Unix é inteiro.
- O save guarda IDs estáveis, nunca caminhos de asset (RF-56).
- O esquema completo é `schemas/save_v1.schema.json`. Abaixo, os campos de cada objeto, gerados dele.

Campos por objeto (`save_v1.schema.json`). A árvore segue o `SaveData` de `save.h`, e os objetos aninhados seguem `character.h` e `expedition.h`.

Envelope (raiz): `format`, `save_version`, `sha256`, `data`, exatamente nessa ordem e sem campo extra.

#### `SaveData`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `save_version` | fixo `1` | sim | — | Igual ao `save_version` do envelope. |
| `content_version` | inteiro | sim | ≥ 0, ≤ 4294967295 | Não pode passar do `content_version` do jogo (RNF-10). |
| `characters` | lista de objeto `CharacterState` | sim | — |  |
| `stash` | lista de objeto `ItemInstance` | sim | — |  |
| `currencies` | lista de objeto `StackEntry` | sim | — |  |
| `marker_charges` | inteiro | sim | ≥ 0 | Não pode passar de `charges_max`. |
| `last_rest_day` | inteiro | sim | — | Dia UTC do último descanso (inteiro). |
| `last_seen_utc` | inteiro | sim | ≥ 0 | Tempo Unix em UTC (RF-46). |
| `next_item_uid` | uint64 em texto decimal | sim | — | Maior que o maior uid em uso. Gerado pelo jogo. |
| `expedition_slots` | inteiro | sim | ≥ 1, ≤ 2 | 1 no AA; 2º slot é recompensa de endgame. |
| `expeditions` | lista de objeto `SavedExpedition` (0 a 2 itens) | sim | — |  |
| `codex_seen_uniques` | lista de ID (texto) | sim | — | IDs de únicos já vistos (Codex). |
| `books_seen` | lista de ID (texto) | sim | — | IDs de livros já vistos (proteção contra azar). |

#### `CharacterState`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `name` | texto | sim | tamanho ≥ 1 |  |
| `class_id` | ID (texto) | sim | — |  |
| `spec_id` | ID ou vazio | sim | — | Vazio antes do nível 10. |
| `level` | inteiro | sim | ≥ 1 |  |
| `xp` | número | sim | ≥ 0 |  |
| `passives` | lista de ID (texto) | sim | — |  |
| `skills` | lista de objeto `LearnedSkill` | sim | — |  |
| `skill_bar` | lista de ID ou vazio (6 a 6 itens) | sim | — | 6 posições no AA. Vazio = posição livre. |
| `equipment` | objeto com as 10 posições de `ItemSlot`, cada uma `null` ou `ItemInstance` | sim | — | 10 posições (`ItemSlot`). `ring2` e `belt` são reservadas para 1.0. |
| `conquered_maps` | lista de ID (texto) | sim | — |  |
| `highest_tier_cleared` | inteiro | sim | ≥ 0, ≤ 5 |  |
| `potions` | inteiro | sim | ≥ 0 | Estoque de poção. Sem fonte de dados ainda (P1). |
| `play_time_seconds` | número | sim | ≥ 0 |  |

#### `ItemInstance`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `uid` | uint64 em texto decimal | sim | — | uid 0 é reservado (erro semântico). Único no save. |
| `base_id` | ID (texto) | sim | — |  |
| `rarity` | enum: `normal`, `magic`, `rare`, `unique` | sim | — |  |
| `item_level` | inteiro | sim | ≥ 1, ≤ 100 |  |
| `unique_id` | ID ou vazio | sim | — | Vazio, salvo se `rarity = unique`. |
| `affixes` | lista de objeto `RolledAffix` | sim | — | Limite por raridade: normal 0, mágico 2, raro 4, único 0. |
| `has_inscription` | bool | sim | — |  |

#### `RolledAffix`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `affix_id` | ID (texto) | sim | — |  |
| `value` | número | sim | — |  |

#### `StackEntry`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `id` | ID (texto) | sim | — |  |
| `amount` | inteiro | sim | ≥ 0 |  |

#### `LearnedSkill`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `skill_id` | ID (texto) | sim | — |  |
| `rank` | inteiro | sim | ≥ 1, ≤ 3 |  |
| `sigils` | lista de ID (texto) | sim | — |  |

#### `CharacterSnapshot`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `character` | objeto `CharacterState` | sim | — |  |
| `content_version` | inteiro | sim | ≥ 0, ≤ 4294967295 | Versão do conteúdo no início da expedição. |

#### `ExpeditionRequest`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `snapshot` | objeto `CharacterSnapshot` | sim | — |  |
| `map_id` | ID ou vazio | sim | — |  |
| `objective` | enum: `xp`, `gold`, `materials` | sim | — |  |
| `rules` | lista de objeto `AiRule` (0 a 6 itens) | sim | — | Até `max_ai_rules` (6) regras, avaliadas em ordem. |
| `potion_heal_fraction` | número | sim | ≥ 0, ≤ 1 |  |
| `seed` | uint64 em texto decimal | sim | — | uint64 em texto decimal. |
| `start_utc` | inteiro | sim | — | Tempo Unix em UTC. |
| `duration_hours` | inteiro | sim | ≥ 1, ≤ 12 |  |
| `effective_seconds` | número | sim | ≥ 0 | Até `duration_hours × 3600`. |
| `content_version` | inteiro | sim | ≥ 0, ≤ 4294967295 |  |

#### `AiRule`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `condition` | enum: `always`, `life_below`, `resource_above`, `resource_below`, `enemies_at_least`, `target_is_elite`, `target_is_boss`, `effect_missing` | sim | — |  |
| `param` | número | sim | — |  |
| `action` | enum: `use_potion`, `use_skill` | sim | — |  |
| `ref_id` | ID ou vazio | sim | — | Obrigatório para `use_skill` e `effect_missing`. |

#### `SavedExpedition`

| Campo | Tipo | Obrig. | Faixa | Observação |
|---|---|---|---|---|
| `status` | enum: `none`, `running`, `collected` | sim | — | `none`, `running` ou `collected` (`ExpeditionStatus`). |
| `character_index` | inteiro | sim | ≥ -1 |  |
| `request` | objeto `ExpeditionRequest` | sim | — |  |
| `collected_result_hash` | uint64 em texto decimal | sim | — | `0` = sem coleta. Diferente de `0` só se `collected`. |

Exemplo: `ShatterCore/tests/data/saves/save_v1.json` (um Guerreiro, um item, uma expedição em andamento). O envelope completo fica no arquivo, com indentação de 2 espaços.

Regras semânticas que o validador aplica além do esquema (`save_semantics`):

- uid de item diferente de zero e único no save. `next_item_uid` maior que o maior uid em uso.
- Afixos por raridade: normal 0, mágico até 2, raro até 4, único 0. `unique_id` só em item de raridade `unique`.
- IDs existem no conteúdo: classe, habilidades aprendidas e na barra, mapas conquistados, bases de item, afixos e únicos.
- Barra de habilidades só com habilidades aprendidas. `level` até `max_level`. `marker_charges` até `charges_max`.
- No máximo 1 expedição em `running`. `effective_seconds` até `duration_hours × 3600`.
- Expedição `collected` exige `collected_result_hash` diferente de `"0"`. `running` exige `"0"`.
- Regras de IA até `max_ai_rules`. `use_skill` e `effect_missing` exigem `ref_id`.
- Fixtures: `saves/save_v1.json` (um Guerreiro, um item, uma expedição em andamento) passa. `saves/invalid/checksum_altered.json` tem o hash adulterado e falha com `E_CHECKSUM`.

## 7. Política de migração v→v+1

1. Cada mudança de formato vira uma função `migrate_N_to_N+1` que atua sobre o objeto `data`, não sobre o envelope. Ela é registrada na tabela `Migrations()` (`save.h`): índice i = passo de (i+1) para (i+2). `Migrate` aplica em sequência, de `from` até `to`.
2. Sem perda: nenhum campo é apagado sem substituto. O valor antigo vai para o campo novo (ex.: para o primeiro elemento de uma lista). Por isso é possível escrever a função inversa para teste. O jogo nunca sobrescreve o arquivo original antes de a migração carregar e validar em memória.
3. Gravação: o save migrado é gravado via `.tmp`, com conferência, rotação de 3 backups e `rename` (RF-52). O original fica em `.bak` durante a rotação.
4. Versão futura (`save_version` maior que a do jogo): recusar com `TooNew`, sem alterar o arquivo.
5. Cada versão publicada tem `ShatterCore/tests/data/saves/save_vN.json`, que tem que carregar na versão atual (RF-56). A migração N→N+1 tem que produzir o esperado guardado em `saves/migration/`.

Exemplo (`migrate_1_to_2`, implementado no validador como referência; a versão 2 não existe no jogo):

```
characters[].potions (int)  ->  characters[].potion_slots = [
    {"potion_id": "potion.life", "count": <potions>},
    {"potion_id": "",            "count": 0}
]
raiz: tutorial_flags = []     (inserido logo após books_seen)
nada é apagado: o valor antigo de potions vai para o 1º slot
```

Esse exemplo só ilustra a técnica. O desenho de slots de poção é uma pendência (P1). Ele não deve virar versão 2 sem decisão do Tech Lead. O resultado esperado está em `saves/migration/v1_to_v2_expected.json`, e o validador compara o resultado com ele (`--self-test`, passo 5).

## 8. Validação

Comandos (da raiz do repositório, com Python 3.14 no PATH):

```
python tools/validate_data.py                  # Content/Data (conteúdo real)
python tools/validate_data.py --self-test      # conteúdo real + fixtures válidos + inválidos + saves + migração
python tools/validate_data.py --data X         # outra pasta de CSV
python tools/validate_data.py --save slot_1.json --content EchoesOfTheShatter/Content/Data
```

O que é checado: cabeçalho exato; tipo, faixa e enum de cada célula; PK única; referências existentes (`ref`, listas `ref`, `groups`, `mods`); regras entre colunas (`min <= max`, pesos > 0, idle exige amostra de paridade, arma exige dano e tempo de ataque, cooldown >= `cooldown_min`, Vigor não crescente, `sim_step_fast >= sim_step`, cargas que cobrem a expedição máxima, chefe com `isBoss` e encontro de chefe no mapa, ciclo de subtabela de loot e profundidade até 8, Fragmento de Eco fora de `stack`, itens de topo com `manualOnly`); classe com `life` e `resource` e recurso válido; fixtures inválidos falhando com linha e código esperados; save com esquema, hash e regras semânticas.

Resultado: o validador passa no conteúdo real e nos fixtures válidos, e cada fixture inválido falha com o código esperado (saída completa na seção 11).

Validação ad hoc (fora do repositório): 11 mutações de um save válido (uid zero, raridade inválida, nível zero, campo extra, slot faltando, duas expedições em execução, referência de habilidade inexistente, mais de 6 regras, `next_item_uid` como número, duração de 13 h, efeito maior que a duração). Todas foram recusadas com o código certo.

## 9. Pendências para o Tech Lead

Itens onde headers, esquemas, validador ou documentos não fecham entre si. Nenhum foi resolvido no header, conforme combinado.

- **P1. Poção (cura, estoque e recarga) sem fonte de dados.** `expedition.h:65` diz que `potionHealFraction` "vem de dados", mas não há chave em `rules.csv`, nem tabela de itens ou poções. `character.h:37` guarda `potions` sem tabela de origem. RF-19 pede que "cargas e recarga batem com o CSV", e RF-39 usa poções nas regras. Pedido: decidir se a poção vira tabela própria ou chaves de `rules.csv` (e se a cura é fração de vida máxima, como o comentário sugere).
- **P2. Único não tem amostra de paridade.** `content.h:229` diz que todo único com `idle.supported` precisa de `paritySampleSize > 0`, mas `UniqueData` (`content.h:139`) não tem esse campo, e `IdleProfile` (`content.h:59`) só existe em `SkillData`. Por isso o validador não consegue checar únicos. Pedido: campo de paridade em `uniques.csv`, ou regra de que único nunca entra no idle.
- **P3. IDs referenciados sem tabela.** O validador só confere o prefixo, não a existência, para: `family.*` (`enemies.familyId`); `spec.*` (`classes.specializations` e `skills.specId`, ligação nas duas direções); nós da árvore de passivas (`CharacterState.passives`); `sigil.*` (`LearnedSkill.sigils`, e `sigil.common.*` em `stack`); `currency.*`, `material.*`, `page.*` (`stack` e `currencies` do save); `book.spec.*` e `map_stone.*` (`LootEntryKind`); `material.echo_fragment`; `resource.*` (enum fixo no esquema de classes). Pedido: criar as tabelas, ou aceitar IDs livres com checagem só de formato.
- **P4. Dados de combate em tempo real sem tabela nem campo.** Esquiva (RF-15 e plano linha 548: 0,35 s, 0,2 s de invulnerabilidade, 3 cargas, 1,5 s de recarga). Telegraph de ataque de inimigo: `enemy_attacks.telegraphed` é só booleano, e RF-23 pede 0,7 a 1,2 s. Padrões por fase do chefe (plano linha 1243; arquitetura seção 10.4) e a fase 2 do Guardião (RF-23). Parâmetros de IA de RF-20 (limiar de fuga do Cão-de-Cinza, distância mínima do Arqueiro Fantasma). Variantes de elite (RF-22: escudo, veloz, explode ao morrer; plano linha 606). Nada disso está em `content.h`.
- **P5. Único só do Guardião (RF-27) não é aplicável.** Nenhuma coluna liga `uniques` a uma tabela de chefe. Hoje uma tabela qualquer pode ter `kind = unique` com `manualOnly = true`. Pedido: regra de que único só aparece em tabela de encontro de chefe, checada pelo validador.
- **P6. Local dos textos (`Loc/`).** A arquitetura, seção 7 (linha 273), manda `Content/Data/Loc*.csv`, na raiz de `Data`. O validador lê `Content/Data/Loc/` (`read_loc_dir`) e aceita só `key, pt_BR, en`. O `ContentDB::LoadDirectory` (`content.h:226`) lê todo `*.csv` da pasta, então um `Loc*.csv` na raiz daria `E_UNKNOWN_TABLE` no ContentDB. Pedido: confirmar a subpasta `Loc/` e atualizar a seção 7. A arquitetura, seção 16, cita `tools/build_loc.py`, que ainda não existe.
- **P7. CI roda o validador sem o autoteste.** A arquitetura, seção 14 (linha 501), chama `python3 tools/validate_data.py`, que só valida `Content/Data`. Os fixtures inválidos, o save v1 e a migração não rodam no CI. Pedido: trocar para `python3 tools/validate_data.py --self-test`.
- **P8. Tags de habilidade: obrigatórias no esquema, opcionais no header.** `SkillData::tags = 0` (`content.h`) é um valor válido, mas `skills.schema.json` marca `tags` como obrigatório (`E_REQUIRED`). Pedido: decidir qual vale.
- **P9. Crescimento do inimigo inline.** Classe usa `class_stats.csv`, mas inimigo guarda o crescimento em `enemies.stats` (formato `growths`). O `content.h` não tem tabela `enemy_stats`. Pedido: confirmar a forma inline (proposta desta entrega) ou criar a tabela.
- **P10. Exemplo de migração v1→v2 não aprovado.** O `migrate_1_to_2` do validador (`potion_slots` e `tutorial_flags`) é ilustrativo. Não é decisão de design e não entrou no core. Pedido: manter, ajustar ou remover quando houver a primeira mudança real de formato.
- **P11. Valores provisórios.** Em `rules.csv`, marcados como PROVISÓRIO: `block_mitigation`, `armor_damage_factor`, `armor_max_reduction`, `ai_base_dodge`, `retreat_life_fraction`. `resist_floor = -1.0` é decisão da arquitetura (seção 11), não do plano. Confirmar no playtest ou com o Game Designer.

## 10. Divergências encontradas no GDD e nos requisitos

- **D1. Posições de equipamento.** RF-30 e a tabela da seção 2.1 de `02_requisitos.md` (linha 45) falam em 5 posições no protótipo. O header diz "AA usa as 8 primeiras" e o esquema aceita os 10 slots (incluindo `ring2` e `belt`, reservados para 1.0). Não é erro de dado, mas o conteúdo do protótipo pode usar `ring2` e `belt` sem o validador avisar. Confirmar.
- **D2. Idle ≈ 35% do XP por hora.** RF-32 e plano linha 802 dão 35%. Com Fervor ×3, a conta dá 33,3%. O 35% é meta de calibração (plano linha 1508), não chave. Por isso não há chave no `rules.csv` para ele, o que está certo.
- **D3. Esquiva, poção e fase do chefe** não têm dados (ver P4 e P1). Os valores estão no plano e nos requisitos.
- **D4. Único só do Guardião (RF-27)** não é garantido pelos dados (ver P5).

Verificado sem divergência: XP por nível (RF-05: 100, 160, 269,7 e 580), Vigor 100/70/40% em faixas de 4 h (RF-36), Cargas do Marco +1/hora, teto 12, +1 limpar, +2 chefe, +3 área nova, +4 descanso (RF-35 e RF-50), teto de Raros 4, teto de XP de 2 níveis (RF-33), passo de 0,1 s e 0,25 s (plano linha 1250 e 1254), relógio de 5 min e 10 min (RF-48 e plano linha 1267), defesa 70/50/75% (plano linha 1230) e 0,25 s de recarga interna (plano linha 1236).

## 11. Saída final do validador

Comando: `python tools/validate_data.py --self-test` (da raiz do repositório, Python 3.14). Saída colada na íntegra:

```
### validate_data.py --self-test
== Content/Data (EchoesOfTheShatter\Content\Data)
   info   content_version = 1
   info   pasta Loc/ não existe: checagem de chaves de localização pulada
   info   linhas: affixes.csv=0, class_stats.csv=0, classes.csv=0, effects.csv=0, encounters.csv=0, enemies.csv=0, enemy_attacks.csv=0, item_bases.csv=0, loot_entries.csv=0, loot_tables.csv=0, maps.csv=0, skills.csv=0, uniques.csv=0
   info   content_lock.json ausente: nenhum conteúdo publicado ainda (crie com --update-lock na 1ª release)
   -> OK: 0 erro(s), 0 aviso(s)
== fixtures válidos (ShatterCore\tests\data)
   info   content_version = 1
   info   pasta Loc/ não existe: checagem de chaves de localização pulada
   info   linhas: affixes.csv=0, class_stats.csv=2, classes.csv=1, effects.csv=0, encounters.csv=1, enemies.csv=1, enemy_attacks.csv=1, item_bases.csv=1, loot_entries.csv=2, loot_tables.csv=1, maps.csv=1, skills.csv=2, uniques.csv=0
   -> OK: 0 erro(s), 0 aviso(s)
== fixture inválido invalid/dup_skill_id (deve falhar)
   ERRO   skills.csv:4 [E_DUP_ID] chave skill.warrior.iron_cut repetida (primeira na linha 2)
   -> FALHOU: 1 erro(s), 0 aviso(s)
   ok: falhou como esperado (skills.csv:4 [E_DUP_ID])
== fixture inválido invalid/encounter_unknown_enemy (deve falhar)
   ERRO   encounters.csv:2 [E_FK] groups: 'enemy.missing_sentinel' não existe em enemies.csv
   -> FALHOU: 1 erro(s), 0 aviso(s)
   ok: falhou como esperado (encounters.csv:2 [E_FK])
== fixture inválido invalid/rule_out_of_range (deve falhar)
   ERRO   rules.csv:3 [E_RANGE] evasion_cap: 1.5 > máximo 1
   -> FALHOU: 1 erro(s), 0 aviso(s)
   ok: falhou como esperado (rules.csv:3 [E_RANGE])
== save saves/save_v1.json
   info   ShatterCore\tests\data\saves\save_v1.json: save_version 1, 1 personagem(ns), 0 item(ns) no baú
   -> OK: 0 erro(s), 0 aviso(s)
== save saves/invalid/checksum_altered.json (deve falhar)
   info   ShatterCore\tests\data\saves\invalid\checksum_altered.json: save_version 1, 1 personagem(ns), 0 item(ns) no baú
   ERRO   ShatterCore\tests\data\saves\invalid\checksum_altered.json [E_CHECKSUM] SHA-256 não confere (arquivo 000000000000…, calculado 7659b0dbfd4a…)
   -> FALHOU: 1 erro(s), 0 aviso(s)
   ok: falhou como esperado
== migração de referência v1->v2: OK (igual a migration/v1_to_v2_expected.json)
### resultado: OK
```
