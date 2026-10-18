using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Tabelas de conteúdo que o combate usa, lidas dos mesmos CSV do ShatterCore
    /// (<c>ContentDB</c>, content.h). Validação mínima: IDs, duplicatas e referências usadas aqui.
    /// A validação completa é do <c>Finalize()</c> do core e do tools/validate_data.py.
    /// </summary>
    internal sealed class StubContent
    {
        static readonly string[] RequiredTables =
        {
            "meta.csv", "rules.csv", "classes.csv", "class_stats.csv", "skills.csv",
            "effects.csv", "enemies.csv", "enemy_attacks.csv", "item_bases.csv",
        };

        public readonly StubRulesConstants Rules = new StubRulesConstants();
        public readonly CombatRules Combat = new CombatRules();
        public readonly Dictionary<string, double> RuleValues = new Dictionary<string, double>(StringComparer.Ordinal);
        public readonly Dictionary<string, ClassInfo> Classes = new Dictionary<string, ClassInfo>(StringComparer.Ordinal);
        public readonly Dictionary<string, List<StubStatGrowth>> ClassStats = new Dictionary<string, List<StubStatGrowth>>(StringComparer.Ordinal);
        public readonly Dictionary<string, SkillInfo> Skills = new Dictionary<string, SkillInfo>(StringComparer.Ordinal);
        public readonly Dictionary<string, StubEffectData> Effects = new Dictionary<string, StubEffectData>(StringComparer.Ordinal);
        public readonly Dictionary<string, EnemyInfo> Enemies = new Dictionary<string, EnemyInfo>(StringComparer.Ordinal);
        public readonly Dictionary<string, List<StubStatGrowth>> EnemyStats = new Dictionary<string, List<StubStatGrowth>>(StringComparer.Ordinal);
        public readonly Dictionary<string, ItemBaseInfo> ItemBases = new Dictionary<string, ItemBaseInfo>(StringComparer.Ordinal);
        public readonly Dictionary<string, List<StubModifier>> ItemImplicits = new Dictionary<string, List<StubModifier>>(StringComparer.Ordinal);
        public readonly Dictionary<string, PotionInfo> PotionsById = new Dictionary<string, PotionInfo>(StringComparer.Ordinal);
        public readonly List<PotionInfo> Potions = new List<PotionInfo>();
        public readonly List<string> PendingValuesUsed = new List<string>();
        public uint ContentVersion;

        public static StubContent Load(string directory, List<RulesError> errors)
        {
            var content = new StubContent();
            var errorsAtEntry = errors.Count;
            var tables = new Dictionary<string, StubCsvTable>(StringComparer.Ordinal);
            for (var i = 0; i < RequiredTables.Length; i++)
            {
                var name = RequiredTables[i];
                var path = Path.Combine(directory, name);
                if (!File.Exists(path))
                {
                    errors.Add(new RulesError(RulesStatus.IoError, name, 0, $"file not found: {path}"));
                    continue;
                }
                var text = File.ReadAllText(path, Encoding.UTF8);
                tables[name] = StubCsvTable.Parse(name, text, errors);
            }
            if (errors.Count > errorsAtEntry) return content;

            content.LoadMeta(tables["meta.csv"], errors);
            content.LoadRules(tables["rules.csv"], errors);
            content.LoadEffects(tables["effects.csv"], errors);
            content.LoadSkills(tables["skills.csv"], errors);
            content.LoadClasses(tables["classes.csv"], tables["class_stats.csv"], errors);
            content.LoadEnemies(tables["enemies.csv"], tables["enemy_attacks.csv"], errors);
            content.LoadItemBases(tables["item_bases.csv"], errors);
            content.LoadPotions(directory, errors);
            return content;
        }

        double PendingRule(string key)
        {
            if (RuleValues.TryGetValue(key, out var value)) return value;
            PendingValuesUsed.Add("rules.csv:" + key);
            return StubPendingRules.RuleKeys[key];
        }

        void LoadMeta(StubCsvTable table, List<RulesError> errors)
        {
            foreach (var row in table.Rows)
            {
                if (table.GetString(row, "key") != "content_version") continue;
                var v = table.GetInt(row, "value", 0, errors);
                ContentVersion = (uint)Math.Max(0, v);
            }
            if (ContentVersion == 0)
                errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, 0, "content_version missing"));
        }

        void LoadRules(StubCsvTable table, List<RulesError> errors)
        {
            foreach (var row in table.Rows)
            {
                var key = table.GetString(row, "key");
                var text = table.GetString(row, "value");
                if (key.Length == 0) continue;
                // Booleanos e textos de rules.csv não interessam ao combate; só números entram.
                if (StubCsvTable.TryParseDouble(text, out var value)) RuleValues[key] = value;
            }

            Rules.CritMultiplierBase = Required(table, "crit_multiplier_base", errors);
            Rules.EvasionCap = Required(table, "evasion_cap", errors);
            Rules.BlockCap = Required(table, "block_cap", errors);
            Rules.BlockMitigation = Required(table, "block_mitigation", errors);
            Rules.ResistCap = Required(table, "resist_cap", errors);
            Rules.ResistFloor = Required(table, "resist_floor", errors);
            Rules.ArmorDamageFactor = Required(table, "armor_damage_factor", errors);
            Rules.ArmorMaxReduction = Required(table, "armor_max_reduction", errors);
            Rules.TriggerInternalCooldown = Required(table, "trigger_icd_min", errors);
            Rules.MinCooldown = Required(table, "cooldown_min", errors);
            Rules.FixedStep = Required(table, "realtime_step", errors);

            Combat.FixedStep = Rules.FixedStep;
            Combat.MinCooldown = Rules.MinCooldown;
            Combat.DodgeMaxCharges = (int)Math.Round(PendingRule("dodge_max_charges"));
            Combat.DodgeRechargeSeconds = PendingRule("dodge_recharge");
            Combat.DodgeDurationSeconds = PendingRule("dodge_duration");
            Combat.DodgeInvulnerableSeconds = PendingRule("dodge_iframes");
            Combat.DodgeDistanceUu = PendingRule("dodge_distance");
            Combat.DodgeResourceCost = PendingRule("dodge_cost_resource");
            Combat.InputBufferSeconds = PendingRule("dodge_buffer");
            Combat.DodgePerfectResource = PendingRule("dodge_perfect_resource");
            Combat.DodgeCancelRecoveryFraction = PendingRule("dodge_cancel_recovery_fraction");
            Combat.PotionLockoutSeconds = PendingRule("potion_lockout");
            Combat.OutOfCombatSeconds = PendingRule("out_of_combat_seconds");
            // Combate básico (docs/18 1.2): sem padrão próprio; ausente fica 0 (o stub não roda o combo).
            Combat.ComboWindowSeconds = RuleOrZero("combo_window");
            Combat.ComboWindowAfterDodgeSeconds = RuleOrZero("combo_window_after_dodge");
            Combat.AttackBufferSeconds = RuleOrZero("attack_buffer");
            Combat.HeavyHoldThresholdSeconds = RuleOrZero("heavy_hold_threshold");
            Combat.LightWindupCreditMax = RuleOrZero("light_windup_credit_max");
            Combat.GuardLowerTimeSeconds = RuleOrZero("guard_lower_time");
            Combat.DashShotRangeUu = RuleOrZero("dash_shot_range");
            Combat.HeroMoveAccelSeconds = RuleOrZero("hero_move_accel_seconds");
            Combat.HeroMoveDecelSeconds = RuleOrZero("hero_move_decel_seconds");
        }

        double RuleOrZero(string key) => RuleValues.TryGetValue(key, out var value) ? value : 0.0;

        double Required(StubCsvTable table, string key, List<RulesError> errors)
        {
            if (RuleValues.TryGetValue(key, out var value)) return value;
            errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, 0, $"missing key '{key}'"));
            return 0.0;
        }

        void LoadEffects(StubCsvTable table, List<RulesError> errors)
        {
            foreach (var row in table.Rows)
            {
                var id = table.GetString(row, "id");
                if (!CheckId(table, row, id, Effects.ContainsKey(id), errors)) continue;
                var data = new StubEffectData { Id = id };
                data.Duration = table.GetDouble(row, "duration", 0, errors);
                data.TickInterval = table.GetDouble(row, "tickInterval", 0, errors);
                switch (table.GetString(row, "stackRule", "refresh"))
                {
                    case "refresh": data.StackRule = StubStackRule.Refresh; break;
                    case "stack_n": data.StackRule = StubStackRule.StackN; break;
                    case "strongest_only": data.StackRule = StubStackRule.StrongestOnly; break;
                    default:
                        errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, "unknown stackRule"));
                        break;
                }
                data.MaxStacks = table.GetInt(row, "maxStacks", 1, errors);
                var dot = new DamageByType
                {
                    Physical = table.GetDouble(row, "damagePerTickPhysical", 0, errors),
                    Fire = table.GetDouble(row, "damagePerTickFire", 0, errors),
                    Cold = table.GetDouble(row, "damagePerTickCold", 0, errors),
                    Lightning = table.GetDouble(row, "damagePerTickLightning", 0, errors),
                };
                data.DamagePerTick = dot;
                if (!StubParse.TryModifiers(table.GetString(row, "modifiers"), "fx:" + id, data.Modifiers, out var modError))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, modError));
                data.Barrier = table.GetDouble(row, "barrier", 0, errors);
                data.Triggered = table.GetString(row, "trigger", "none") != "none";
                data.InternalCooldown = table.GetDouble(row, "internalCooldown", 0, errors);
                if (!StubParse.TryTags(table.GetString(row, "tags"), '|', out var tags))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, "unknown tag"));
                data.Tags = tags;
                if (table.HasColumn("interruptsAction"))
                {
                    data.IsStun = table.GetBool(row, "interruptsAction", false, errors);
                }
                else
                {
                    data.IsStun = StubPendingRules.StunEffects.Contains(id);
                    if (data.IsStun) PendingValuesUsed.Add("effects.csv:interruptsAction(" + id + ")");
                }
                Effects.Add(id, data);
            }
        }

        void LoadSkills(StubCsvTable table, List<RulesError> errors)
        {
            var hasCone = table.HasColumn("coneAngle");
            var hasProjectileSpeed = table.HasColumn("projectileSpeed");
            foreach (var row in table.Rows)
            {
                var id = table.GetString(row, "id");
                if (!CheckId(table, row, id, Skills.ContainsKey(id), errors)) continue;
                var skill = new SkillInfo { Id = id, ClassId = table.GetString(row, "classId") };
                if (!StubParse.TryTags(table.GetString(row, "tags"), '|', out var tags))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, "unknown tag"));
                skill.Tags = tags;
                if (!StubParse.TryShape(table.GetString(row, "shape"), out var shape))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, "unknown shape"));
                skill.Shape = shape;
                skill.ScalesWithWeapon = table.GetBool(row, "scalesWithWeapon", false, errors);
                if (table.HasColumn("pierce")) skill.Pierce = table.GetInt(row, "pierce", 0, errors);
                if (table.HasColumn("explosionRadius")) skill.ExplosionRadiusUu = table.GetDouble(row, "explosionRadius", 0, errors);
                if (table.HasColumn("knockback")) skill.KnockbackUu = table.GetDouble(row, "knockback", 0, errors);
                skill.BaseDamage = new DamageByType
                {
                    Physical = table.GetDouble(row, "baseDamagePhysical", 0, errors),
                    Fire = table.GetDouble(row, "baseDamageFire", 0, errors),
                    Cold = table.GetDouble(row, "baseDamageCold", 0, errors),
                    Lightning = table.GetDouble(row, "baseDamageLightning", 0, errors),
                };
                skill.CoefficientRank1 = table.GetDouble(row, "coefficientRank1", 1, errors);
                skill.CoefficientRank2 = table.GetDouble(row, "coefficientRank2", skill.CoefficientRank1, errors);
                skill.CoefficientRank3 = table.GetDouble(row, "coefficientRank3", skill.CoefficientRank2, errors);
                skill.Cost = table.GetDouble(row, "cost", 0, errors);
                skill.Cooldown = table.GetDouble(row, "cooldown", 0, errors);
                skill.Windup = table.GetDouble(row, "windup", 0, errors);
                skill.Impact = table.GetDouble(row, "impact", 0, errors);
                skill.Recovery = table.GetDouble(row, "recovery", 0, errors);
                skill.RangeUu = table.GetDouble(row, "range", 0, errors);
                skill.RadiusUu = table.GetDouble(row, "radius", 0, errors);
                skill.Projectiles = table.GetInt(row, "projectiles", 1, errors);
                skill.OnHitEffects = StubParse.SplitList(table.GetString(row, "onHitEffects"));
                skill.SelfEffects = StubParse.SplitList(table.GetString(row, "selfEffects"));
                skill.UnlockLevel = table.GetInt(row, "unlockLevel", 1, errors);

                if (hasCone)
                {
                    skill.ConeAngleDegrees = table.GetDouble(row, "coneAngle", StubPendingRules.DefaultConeAngleDegrees, errors);
                }
                else if (skill.Shape == SkillShape.Cone || skill.Shape == SkillShape.Melee)
                {
                    skill.ConeAngleDegrees = StubPendingRules.ConeAngleBySkill.TryGetValue(id, out var angle)
                        ? angle
                        : StubPendingRules.DefaultConeAngleDegrees;
                    PendingValuesUsed.Add("skills.csv:coneAngle(" + id + ")");
                }

                if (hasProjectileSpeed)
                {
                    skill.ProjectileSpeedUu = table.GetDouble(row, "projectileSpeed", 0, errors);
                }
                else if (skill.Shape == SkillShape.Projectile && StubPendingRules.ProjectileSpeedBySkill.TryGetValue(id, out var speed))
                {
                    skill.ProjectileSpeedUu = speed;
                    PendingValuesUsed.Add("skills.csv:projectileSpeed(" + id + ")");
                }

                Skills.Add(id, skill);
            }

            // Referências a efeitos.
            foreach (var row in table.Rows)
            {
                var id = table.GetString(row, "id");
                if (!Skills.TryGetValue(id, out var skill)) continue;
                CheckEffectRefs(table, row, skill.OnHitEffects, errors);
                CheckEffectRefs(table, row, skill.SelfEffects, errors);
            }
        }

        void CheckEffectRefs(StubCsvTable table, in StubCsvTable.Row row, IReadOnlyList<string> ids, List<RulesError> errors)
        {
            for (var i = 0; i < ids.Count; i++)
            {
                if (!Effects.ContainsKey(ids[i]))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, $"unknown effect '{ids[i]}'"));
            }
        }

        void LoadClasses(StubCsvTable classes, StubCsvTable stats, List<RulesError> errors)
        {
            foreach (var row in classes.Rows)
            {
                var id = classes.GetString(row, "id");
                if (!CheckId(classes, row, id, Classes.ContainsKey(id), errors)) continue;
                var info = new ClassInfo
                {
                    Id = id,
                    ResourceId = classes.GetString(row, "resourceId"),
                    StartingSkill = classes.GetString(row, "startingSkill"),
                    ResourceOnHit = classes.GetDouble(row, "resourceOnHit", 0, errors),
                    ResourceOnBlock = classes.GetDouble(row, "resourceOnBlock", 0, errors),
                    ResourceDecayOutOfCombat = classes.GetDouble(row, "resourceDecayOutOfCombat", 0, errors),
                    RegenMultWhileMoving = classes.GetDouble(row, "regenMultWhileMoving", 1, errors),
                };
                if (info.StartingSkill.Length > 0 && !Skills.ContainsKey(info.StartingSkill))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, classes.Name, row.Line, $"unknown skill '{info.StartingSkill}'"));
                Classes.Add(id, info);
                ClassStats.Add(id, new List<StubStatGrowth>());
            }

            var hasMoveSpeed = new HashSet<string>(StringComparer.Ordinal);
            foreach (var row in stats.Rows)
            {
                var classId = stats.GetString(row, "classId");
                var statName = stats.GetString(row, "stat");
                if (!ClassStats.TryGetValue(classId, out var list))
                {
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, stats.Name, row.Line, $"unknown class '{classId}'"));
                    continue;
                }
                var baseValue = stats.GetDouble(row, "base", 0, errors);
                var perLevel = stats.GetDouble(row, "perLevel", 0, errors);
                if (statName == "move_speed")
                {
                    // docs/13 item 12: velocidade em uu/s fica na classe; o atributo MoveSpeed segue multiplicador (base 1).
                    Classes[classId].MoveSpeedUu = baseValue;
                    hasMoveSpeed.Add(classId);
                    continue;
                }
                if (!StubParse.TryStat(statName, out var stat))
                {
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, stats.Name, row.Line, $"unknown stat '{statName}'"));
                    continue;
                }
                list.Add(new StubStatGrowth { Stat = stat, Base = baseValue, PerLevel = perLevel });
            }

            foreach (var pair in Classes)
            {
                if (hasMoveSpeed.Contains(pair.Key)) continue;
                pair.Value.MoveSpeedUu = StubPendingRules.ClassMoveSpeedUu;
                PendingValuesUsed.Add("class_stats.csv:move_speed(" + pair.Key + ")");
            }
        }

        void LoadEnemies(StubCsvTable enemies, StubCsvTable attacks, List<RulesError> errors)
        {
            var hasTurnRate = enemies.HasColumn("turnRateDegPerSec");
            foreach (var row in enemies.Rows)
            {
                var id = enemies.GetString(row, "id");
                if (!CheckId(enemies, row, id, Enemies.ContainsKey(id), errors)) continue;
                var info = new EnemyInfo
                {
                    Id = id,
                    FamilyId = enemies.GetString(row, "familyId"),
                    XpBase = enemies.GetDouble(row, "xpBase", 0, errors),
                    XpPerLevel = enemies.GetDouble(row, "xpPerLevel", 0, errors),
                    LootTableId = enemies.GetString(row, "lootTableId"),
                    IsBoss = enemies.GetBool(row, "isBoss", false, errors),
                    IsElite = enemies.GetBool(row, "isElite", false, errors),
                    ModifierId = enemies.HasColumn("modifierId") ? enemies.GetString(row, "modifierId") : string.Empty,
                    EliteLootTableId = enemies.HasColumn("eliteLootTableId") ? enemies.GetString(row, "eliteLootTableId") : string.Empty,
                    MoveSpeedUu = enemies.GetDouble(row, "moveSpeed", 0, errors),
                    AggroRangeUu = enemies.GetDouble(row, "aggroRange", 0, errors),
                };
                if (hasTurnRate)
                {
                    info.TurnRateDegreesPerSecond = enemies.GetDouble(row, "turnRateDegPerSec", StubPendingRules.DefaultTurnRateDegreesPerSecond, errors);
                }
                else
                {
                    info.TurnRateDegreesPerSecond = StubPendingRules.TurnRateByEnemy.TryGetValue(id, out var rate)
                        ? rate
                        : StubPendingRules.DefaultTurnRateDegreesPerSecond;
                    PendingValuesUsed.Add("enemies.csv:turnRateDegPerSec(" + id + ")");
                }
                var growth = new List<StubStatGrowth>();
                if (!StubParse.TryStatGrowth(enemies.GetString(row, "stats"), growth, out var growthError))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, enemies.Name, row.Line, growthError));
                Enemies.Add(id, info);
                EnemyStats.Add(id, growth);
            }

            var lists = new Dictionary<string, List<EnemyAttackInfo>>(StringComparer.Ordinal);
            foreach (var row in attacks.Rows)
            {
                var enemyId = attacks.GetString(row, "enemyId");
                var skillId = attacks.GetString(row, "skillId");
                if (!Enemies.ContainsKey(enemyId))
                {
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, attacks.Name, row.Line, $"unknown enemy '{enemyId}'"));
                    continue;
                }
                if (!Skills.TryGetValue(skillId, out var skill))
                {
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, attacks.Name, row.Line, $"unknown skill '{skillId}'"));
                    continue;
                }
                var weight = attacks.GetDouble(row, "weight", 1, errors);
                if (weight <= 0.0)
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, attacks.Name, row.Line, "weight must be > 0"));
                if (!lists.TryGetValue(enemyId, out var list))
                {
                    list = new List<EnemyAttackInfo>();
                    lists.Add(enemyId, list);
                }
                list.Add(new EnemyAttackInfo(skill, weight, attacks.GetBool(row, "telegraphed", false, errors)));
            }
            foreach (var pair in lists) Enemies[pair.Key].Attacks = pair.Value.ToArray();
        }

        void LoadItemBases(StubCsvTable table, List<RulesError> errors)
        {
            foreach (var row in table.Rows)
            {
                var id = table.GetString(row, "id");
                if (!CheckId(table, row, id, ItemBases.ContainsKey(id), errors)) continue;
                var info = new ItemBaseInfo
                {
                    Id = id,
                    Slot = table.GetString(row, "slot"),
                    ItemLevel = table.GetInt(row, "itemLevel", 1, errors),
                    WeaponDamage = new DamageByType
                    {
                        Physical = table.GetDouble(row, "weaponDamagePhysical", 0, errors),
                        Fire = table.GetDouble(row, "weaponDamageFire", 0, errors),
                        Cold = table.GetDouble(row, "weaponDamageCold", 0, errors),
                        Lightning = table.GetDouble(row, "weaponDamageLightning", 0, errors),
                    },
                    AttackTime = table.GetDouble(row, "attackTime", 0, errors),
                    GrammaticalGender = table.GetString(row, "grammaticalGender"),
                };
                var mods = new List<StubModifier>();
                if (!StubParse.TryModifiers(table.GetString(row, "implicitMods"), id, mods, out var modError))
                    errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, modError));
                ItemBases.Add(id, info);
                ItemImplicits.Add(id, mods);
            }
        }

        void LoadPotions(string directory, List<RulesError> errors)
        {
            // potions.csv ainda não existe (docs/13, item 2). Quando existir, ler aqui com as colunas do documento.
            var path = Path.Combine(directory, "potions.csv");
            if (File.Exists(path))
            {
                var table = StubCsvTable.Parse("potions.csv", File.ReadAllText(path, Encoding.UTF8), errors);
                foreach (var row in table.Rows)
                {
                    var id = table.GetString(row, "id");
                    if (!CheckId(table, row, id, PotionsById.ContainsKey(id), errors)) continue;
                    var potion = new PotionInfo
                    {
                        Id = id,
                        Kind = table.GetString(row, "kind") == "barrier" ? PotionKind.Barrier : PotionKind.Heal,
                        FractionOfMaxLife = table.GetDouble(row, "fractionOfMaxLife", 0, errors),
                        Duration = table.GetDouble(row, "duration", 0, errors),
                        MaxCharges = table.GetInt(row, "maxCharges", 0, errors),
                        RechargeSeconds = table.GetDouble(row, "rechargeSeconds", 0, errors),
                        UseTime = table.GetDouble(row, "useTime", 0, errors),
                        MoveSpeedWhileUsing = table.GetDouble(row, "moveSpeedWhileUsing", 1, errors),
                        EliteKillRefillCharges = table.GetBool(row, "refillOnEliteKill", false, errors) ? 1 : 0,
                        HotkeySlot = table.GetInt(row, "hotkeySlot", 0, errors),
                    };
                    PotionsById.Add(id, potion);
                    Potions.Add(potion);
                }
            }
            else
            {
                var pending = StubPendingRules.CreatePotions();
                for (var i = 0; i < pending.Length; i++)
                {
                    PotionsById.Add(pending[i].Id, pending[i]);
                    Potions.Add(pending[i]);
                }
                PendingValuesUsed.Add("potions.csv (tabela inteira)");
            }
            Potions.Sort((a, b) => a.HotkeySlot.CompareTo(b.HotkeySlot));
        }

        static bool CheckId(StubCsvTable table, in StubCsvTable.Row row, string id, bool duplicate, List<RulesError> errors)
        {
            if (!StubParse.IsValidContentId(id))
            {
                errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, $"invalid id '{id}'"));
                return false;
            }
            if (duplicate)
            {
                errors.Add(new RulesError(RulesStatus.ContentInvalid, table.Name, row.Line, $"duplicate id '{id}'"));
                return false;
            }
            return true;
        }
    }
}
