# KayKit Character Animations 1.1 (só as animações)

- **Origem:** KayKit : Character Animations (1.1), de Kay Lousberg (www.kaylousberg.com).
- **Licença:** Creative Commons Zero (CC0) — domínio público, uso pessoal, educacional e comercial. Texto original em `License.txt` (esta pasta). O crédito ("Kay Lousberg, www.kaylousberg.com") não é obrigatório; fica aqui por cortesia e vai nos créditos do jogo.
- **Escopo:** só as animações. **Nenhum modelo KayKit entra no jogo** (decisão do dono). Os FBX desta pasta carregam apenas o esqueleto de referência de cada rig; os clipes são retargetados pelo avatar Humanoid para o nosso `Rig_Humanoid_Chibi`.
- **Importação:** `CharacterAssetPostprocessor` (Humanoid, avatar do próprio FBX) e `KayKitAnimationImport` (só os clipes listados abaixo; sem root motion; pé no chão pelo "Based Upon: Feet"). Reproduzível: menu Echoes ▸ Importar animações KayKit.
- **Pacotes importados:** `Rig_Medium_{General,MovementBasic,MovementAdvanced,CombatMelee,CombatRanged}` e `Rig_Large_{General,MovementBasic,CombatMelee,Simulation}`. Os demais (Special, Tools, Simulation Medium, Rig_Large Special/Advanced) não foram trazidos: nenhum clipe deles é necessário ainda. `CombatRanged` entrou com o Arqueiro e o Mago (docs/18, seção 5).

## Clipes usados e onde

| Estado | Warrior e humanoides (Rig_Medium) | Guardião (Rig_Large) |
|---|---|---|
| Idle | General `Idle_A` | General `Idle_A` |
| Walk / Run | MovementBasic `Walking_A` / `Running_A` | MovementBasic `Walking_A` / `Running_A` |
| Golpe básico (iron_cut) | CombatMelee `Melee_1H_Attack_Slice_Horizontal` | — |
| Investida (charge) | CombatMelee `Melee_1H_Attack_Stab` | MovementBasic `Running_A` (**placeholder**) |
| Fenda de Pedra (stone_rift) | CombatMelee `Melee_2H_Attack_Chop` | — |
| Escudada (shield_bash) | CombatMelee `Melee_Block_Attack` | CombatMelee `Melee_Block_Attack` |
| Martelo | — | Rig_Medium CombatMelee `Melee_2H_Attack_Chop` (retargetado; o `Melee_2H_Slam` do rig grande deita o corpo na horizontal) |
| Sentinela (sentinel_strike) | CombatMelee `Melee_1H_Attack_Chop` | — |
| Arauto (herald_slam) | CombatMelee `Melee_2H_Attack_Chop` | — |
| Dodge (rolamento) | MovementAdvanced `Dodge_Forward` | — |
| Hit | General `Hit_A` | General `Hit_A` |
| Death | General `Death_A` (Warrior) / `Death_B` (inimigos) | General `Death_A` |
| Stun | `Hit_B` (**placeholder**) | `Hit_A` (**placeholder**) |
| Rugido de fase | — | Simulation `Flexing` (**placeholder**) |

## Combo, carga, defesa e classes (docs/18, seção 5)

| Estado | Clipe (Rig_Medium) | Controller |
|---|---|---|
| Corte de Ferro / Golpe de Volta / Golpe de Fecho | CombatMelee `Melee_1H_Attack_Slice_Horizontal` / `Melee_1H_Attack_Slice_Diagonal` / `Melee_1H_Attack_Jump_Chop` | AC_Warrior (Action: Basic, Combo2, Combo3) |
| Golpe Pesado (carga e soltura) | CombatMelee `Melee_2H_Attack_Slice`: congelado em `holdAt` na carga (camada Upper) e solto de `holdAt` ao fim (Action: HeavyRelease) | AC_Warrior |
| Defesa (erguer, segurar, golpe absorvido) | CombatMelee `Melee_Block`, `Melee_Blocking` (laço), `Melee_Block_Hit` | AC_Warrior e AC_Archer (Upper); o Mago usa CombatRanged `Ranged_Magic_Raise` congelado no último quadro |
| Pernas de quem defende ou carrega | MovementBasic `Walking_A`; MovementAdvanced `Walking_Backwards`, `Running_Strafe_Left` e `Running_Strafe_Right` a 55% | blend 2D AimLocomotion (camada Base) |
| Arqueiro | CombatRanged `Ranged_Bow_Draw` + `Ranged_Bow_Release`, `Ranged_Bow_Aiming_Idle`, `Ranged_Bow_Draw_Up` + `Ranged_Bow_Release_Up`; corre com MovementAdvanced `Running_HoldingBow`; Salto = `Dodge_Backward` | AC_Archer |
| Mago | CombatRanged `Ranged_Magic_Shoot`, `Ranged_Magic_Spellcasting` (+ `_Long` na carga), `Ranged_Magic_Summon`; corre com MovementBasic `Running_B` | AC_Mage |

## Faltando (viram pedido de Mixamo ou de animação própria no Blender)

Stun/atordoado (todos), rugido de fase do Guardião, Investida do Escudo do Guardião (o rig grande não tem avanço com escudo), qualquer animação do Arqueiro Espectral (flutua, sem pernas: rig Generic, sem clipe Humanoid que sirva) e do Cão-de-Cinza (quadrúpede, graybox).
