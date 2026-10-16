# KayKit Character Animations 1.1 (só as animações)

- **Origem:** KayKit : Character Animations (1.1), de Kay Lousberg (www.kaylousberg.com).
- **Licença:** Creative Commons Zero (CC0) — domínio público, uso pessoal, educacional e comercial. Texto original em `License.txt` (esta pasta). O crédito ("Kay Lousberg, www.kaylousberg.com") não é obrigatório; fica aqui por cortesia e vai nos créditos do jogo.
- **Escopo:** só as animações. **Nenhum modelo KayKit entra no jogo** (decisão do dono). Os FBX desta pasta carregam apenas o esqueleto de referência de cada rig; os clipes são retargetados pelo avatar Humanoid para o nosso `Rig_Humanoid_Chibi`.
- **Importação:** `CharacterAssetPostprocessor` (Humanoid, avatar do próprio FBX) e `KayKitAnimationImport` (só os clipes listados abaixo; sem root motion; pé no chão pelo "Based Upon: Feet"). Reproduzível: menu Echoes ▸ Importar animações KayKit.
- **Pacotes importados:** `Rig_Medium_{General,MovementBasic,MovementAdvanced,CombatMelee}` e `Rig_Large_{General,MovementBasic,CombatMelee,Simulation}`. Os demais (CombatRanged, Special, Tools, Simulation Medium, Rig_Large Special/Advanced) não foram trazidos: nenhum clipe deles é necessário ainda.

## Clipes usados e onde

| Estado | Warrior e humanoides (Rig_Medium) | Guardião (Rig_Large) |
|---|---|---|
| Idle | General `Idle_A` | General `Idle_A` |
| Walk / Run | MovementBasic `Walking_A` / `Running_A` | MovementBasic `Walking_A` / `Running_A` |
| Golpe básico (iron_cut) | CombatMelee `Melee_1H_Attack_Slice_Horizontal` | — |
| Investida (charge) | CombatMelee `Melee_1H_Attack_Stab` | MovementBasic `Running_A` (**placeholder**) |
| Fenda de Pedra (stone_rift) | CombatMelee `Melee_2H_Attack_Chop` | — |
| Escudada (shield_bash) | CombatMelee `Melee_Block_Attack` | CombatMelee `Melee_Block_Attack` |
| Martelo | — | CombatMelee `Melee_2H_Slam` |
| Sentinela (sentinel_strike) | CombatMelee `Melee_1H_Attack_Chop` | — |
| Arauto (herald_slam) | CombatMelee `Melee_2H_Attack_Chop` | — |
| Dodge (rolamento) | MovementAdvanced `Dodge_Forward` | — |
| Hit | General `Hit_A` | General `Hit_A` |
| Death | General `Death_A` (Warrior) / `Death_B` (inimigos) | General `Death_A` |
| Stun | `Hit_B` (**placeholder**) | `Hit_A` (**placeholder**) |
| Rugido de fase | — | Simulation `Flexing` (**placeholder**) |

## Faltando (viram pedido de Mixamo ou de animação própria no Blender)

Stun/atordoado (todos), rugido de fase do Guardião, Investida do Escudo do Guardião (o rig grande não tem avanço com escudo), qualquer animação do Arqueiro Espectral (flutua, sem pernas: rig Generic, sem clipe Humanoid que sirva) e do Cão-de-Cinza (quadrúpede, graybox).
