using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// ============================================================================================
    ///  IMPLEMENTAÇÃO PROVISÓRIA DO MOTOR DE REGRAS — STUB EM C# PURO.
    ///  Existe só para o protótipo rodar antes da DLL do ShatterCore (docs/04_arquitetura.md, seção 9).
    ///  Lê os mesmos CSV do core e porta as fórmulas dos headers (stats.h, damage.h, effects.h, rng.h).
    ///  NÃO é a fonte de verdade das regras: em caso de diferença, vale o ShatterCore. Quando a
    ///  implementação P/Invoke existir, troque em <see cref="RulesCoreFactory"/> e apague a pasta Stub/.
    /// ============================================================================================
    /// Determinístico: mesma seed + mesmos CSV = mesma sequência de golpes.
    /// </summary>
    public sealed class StubRulesCore : IRulesCore
    {
        public const string Name = "stub-csharp";

        /// <summary>Piso da velocidade de ação, o mesmo de src/expedition.cpp (técnico, evita divisão por zero).</summary>
        const double MinActionSpeed = 0.01;

        StubContent content;
        static readonly PotionInfo[] NoPotions = Array.Empty<PotionInfo>();

        public uint ApiVersion => 0;
        public string ImplementationName => Name;
        public bool IsProvisional => true;
        public bool IsLoaded => content != null;
        public uint ContentVersion => content?.ContentVersion ?? 0;
        public CombatRules Combat => RequireContent().Combat;

        /// <summary>Valores de docs/13 usados porque a chave ou coluna ainda não existe no CSV.</summary>
        public IReadOnlyList<string> LoadWarnings => content?.PendingValuesUsed ?? (IReadOnlyList<string>)Array.Empty<string>();

        public IReadOnlyList<PotionInfo> Potions => content != null ? (IReadOnlyList<PotionInfo>)content.Potions : NoPotions;

        public RulesStatus LoadContent(string dataDirectory, List<RulesError> errors)
        {
            if (errors == null) throw new ArgumentNullException(nameof(errors));
            if (string.IsNullOrEmpty(dataDirectory))
            {
                errors.Add(new RulesError(RulesStatus.InvalidArgument, string.Empty, 0, "data directory is empty"));
                return RulesStatus.InvalidArgument;
            }
            var before = errors.Count;
            var loaded = StubContent.Load(dataDirectory, errors);
            if (errors.Count > before)
            {
                for (var i = before; i < errors.Count; i++)
                {
                    if (errors[i].Status == RulesStatus.IoError) return RulesStatus.IoError;
                }
                return RulesStatus.ContentInvalid;
            }
            content = loaded;
            return RulesStatus.Ok;
        }

        public ClassInfo FindClass(string id) => Find(RequireContent().Classes, id);
        public SkillInfo FindSkill(string id) => Find(RequireContent().Skills, id);
        public EnemyInfo FindEnemy(string id) => Find(RequireContent().Enemies, id);
        public ItemBaseInfo FindItemBase(string id) => Find(RequireContent().ItemBases, id);

        public string ItemVisualSetId(string baseId, string uniqueId) => "vset.starter";
        public PotionInfo FindPotion(string id) => Find(RequireContent().PotionsById, id);

        public IStatBlock CreateHeroStats(in HeroBuild build)
        {
            var c = RequireContent();
            if (!c.ClassStats.TryGetValue(build.ClassId ?? string.Empty, out var growth))
                throw new ArgumentException($"unknown class '{build.ClassId}'");
            var level = Math.Max(1, build.Level);
            var stats = new StubStatBlock();
            for (var i = 0; i < growth.Count; i++) stats.SetBase(growth[i].Stat, growth[i].At(level));

            // Ordem fixa: itens na ordem recebida (o core usa ItemSlot crescente; character.h).
            var equipment = build.EquipmentBaseIds;
            if (equipment != null)
            {
                for (var i = 0; i < equipment.Count; i++)
                {
                    var id = equipment[i];
                    if (string.IsNullOrEmpty(id)) continue;
                    if (!c.ItemImplicits.TryGetValue(id, out var mods))
                        throw new ArgumentException($"unknown item base '{id}'");
                    for (var m = 0; m < mods.Count; m++) stats.AddModifier(mods[m]);
                }
            }
            return stats;
        }

        public IStatBlock CreateEmptyStats()
        {
            return new StubStatBlock();
        }

        public IStatBlock CreateEnemyStats(string enemyId, int level)
        {
            var c = RequireContent();
            if (!c.EnemyStats.TryGetValue(enemyId ?? string.Empty, out var growth))
                throw new ArgumentException($"unknown enemy '{enemyId}'");
            var lvl = Math.Max(1, level);
            var stats = new StubStatBlock();
            for (var i = 0; i < growth.Count; i++) stats.SetBase(growth[i].Stat, growth[i].At(lvl));
            return stats;
        }

        public IPotionBelt CreatePotionBelt() => new StubPotionBelt(Potions, RequireContent().Combat.PotionLockoutSeconds);

        public IDodgeCharges CreateDodge() => new StubDodge(RequireContent().Combat);

        // Elite e chefe só existem no core: o stub devolve "sem elite" e não tem chefe.
        public EliteProfile RollElite(ref RngState eventsRng)
        {
            StubPcg32.NextUnit(ref eventsRng); // consome 1 número, como o core
            return default;
        }

        public EliteProfile GetEliteProfile(string modifierId, bool rolled) => default;

        public double ApplyElite(IStatBlock enemyStats, in EliteProfile profile) => 0.0;

        public bool SupportsBoss => false;

        public IBossController CreateBoss(string enemyId, int level, ulong seed)
        {
            throw new NotSupportedException("the stub has no boss state machine; use the native core (shatter_boss_*)");
        }

        public IEffectSet CreateEffectSet(IStatBlock target, EnemyInfo enemyOrNull) => CreateEffectSet(target, enemyOrNull, false);

        public IEffectSet CreateEffectSet(IStatBlock target, EnemyInfo enemyOrNull, bool rolledElite)
        {
            var c = RequireContent();
            if (!(target is StubStatBlock stub)) throw new ArgumentException("target must come from this rules core");
            return new StubEffectSet(c, stub, IsStunImmune(enemyOrNull) || rolledElite);
        }

        /// <summary>Conteudo carregado (usado pelo NativeRulesCore para o que a API C v1 ainda nao traz); nulo antes de LoadContent.</summary>
        internal StubContent ContentOrNull => content;

        /// <summary>Imunidade a atordoamento (docs/13, item 3), pendente no core: elite, chefe e familia construct.</summary>
        internal static bool IsStunImmune(EnemyInfo enemyOrNull)
        {
            return enemyOrNull != null
                && (enemyOrNull.IsElite || enemyOrNull.IsBoss
                    || string.Equals(enemyOrNull.FamilyId, StubPendingRules.StunImmuneFamily, StringComparison.Ordinal));
        }

        public RngState CreateRng(ulong seed, RngStream stream, ulong index) => StubPcg32.ForStream(seed, stream, index);

        public uint NextBelow(ref RngState rng, uint bound) => StubPcg32.NextBelow(ref rng, bound);

        public double NextUnit(ref RngState rng) => StubPcg32.NextUnit(ref rng);

        public int PickAttack(ref RngState rng, EnemyInfo enemy)
        {
            if (enemy == null || enemy.Attacks.Count == 0) return -1;
            var total = 0.0;
            for (var i = 0; i < enemy.Attacks.Count; i++) total += enemy.Attacks[i].Weight;
            var roll = StubPcg32.NextUnit(ref rng) * total;
            for (var i = 0; i < enemy.Attacks.Count; i++)
            {
                roll -= enemy.Attacks[i].Weight;
                if (roll < 0.0) return i;
            }
            return enemy.Attacks.Count - 1;
        }

        public HitResult ResolveHit(in HitRequest request, ref RngState combatRng)
        {
            return StubDamage.ResolveHit(request, RequireContent().Rules, ref combatRng);
        }

        public DamageByType GetSkillBaseDamage(SkillInfo skill, ItemBaseInfo weaponOrNull)
        {
            if (skill == null) return default;
            if (skill.ScalesWithWeapon && weaponOrNull != null) return weaponOrNull.WeaponDamage;
            return skill.BaseDamage;
        }

        public ActionTiming GetActionTiming(IStatBlock stats, SkillInfo skill, string eliteModifierIdOrNull) => GetActionTiming(stats, skill);

        public ActionTiming GetActionTiming(IStatBlock stats, SkillInfo skill)
        {
            if (skill == null) return default;
            // Como src/expedition.cpp (UseSkill): velocidade sem tags, conjuração para feitiço, piso de 0,01.
            var speed = stats != null
                ? stats.Get((skill.Tags & SkillTags.Spell) != 0 ? StatId.CastSpeed : StatId.AttackSpeed)
                : 1.0;
            if (speed < MinActionSpeed) speed = MinActionSpeed;
            return new ActionTiming(skill.Windup / speed, skill.Impact / speed, skill.Recovery / speed);
        }

        public double GetEffectiveCooldown(IStatBlock stats, SkillInfo skill)
        {
            // EffectiveCooldown do effects.h com CooldownRecovery sem tags (como src/expedition.cpp).
            if (skill == null || skill.Cooldown <= 0.0) return 0.0;
            var recovery = stats != null ? stats.Get(StatId.CooldownRecovery) : 1.0;
            if (recovery <= 0.0) recovery = 1.0;
            var cd = skill.Cooldown / recovery;
            var min = RequireContent().Rules.MinCooldown;
            return cd < min ? min : cd;
        }

        public double GetEffectiveCost(IStatBlock stats, SkillInfo skill)
        {
            if (skill == null) return 0.0;
            return skill.Cost > 0.0 ? skill.Cost : 0.0;
        }

        public double GetMoveSpeedUu(IStatBlock stats, double baseMoveSpeedUu)
        {
            var mult = stats != null ? stats.Get(StatId.MoveSpeed) : 1.0;
            var v = baseMoveSpeedUu * mult;
            return v > 0.0 ? v : 0.0;
        }

        public bool CanAct(IStatBlock stats) => stats == null || stats.Get(StatId.AttackSpeed) > 0.0;

        public bool CanMove(IStatBlock stats) => stats == null || stats.Get(StatId.MoveSpeed) > 0.0;

        public Vitals CreateVitals(IStatBlock stats, ClassInfo classOrNull)
        {
            var v = new Vitals { Life = stats.Get(StatId.Life) };
            // Recurso que esvazia fora de combate (Ímpeto) começa no repouso, vazio; os demais começam cheios.
            v.Resource = classOrNull != null && classOrNull.ResourceDecayOutOfCombat > 0.0 ? 0.0 : stats.Get(StatId.Resource);
            return v;
        }

        public void TickVitals(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull, double dt, bool inCombat)
        {
            if (vitals.Life <= 0.0) return;
            var maxLife = stats.Get(StatId.Life);
            var regen = stats.Get(StatId.LifeRegen);
            if (regen > 0.0) vitals.Life = Math.Min(maxLife, vitals.Life + regen * dt);
            if (vitals.Life > maxLife) vitals.Life = maxLife;

            var maxResource = stats.Get(StatId.Resource);
            var resourceRegen = stats.Get(StatId.ResourceRegen);
            if (resourceRegen > 0.0) vitals.Resource = Math.Min(maxResource, vitals.Resource + resourceRegen * dt);
            if (!inCombat && classOrNull != null && classOrNull.ResourceDecayOutOfCombat > 0.0)
                vitals.Resource = Math.Max(0.0, vitals.Resource - classOrNull.ResourceDecayOutOfCombat * dt);
            if (vitals.Resource > maxResource) vitals.Resource = maxResource;

            if (vitals.BarrierSecondsLeft > 0.0)
            {
                vitals.BarrierSecondsLeft -= dt;
                if (vitals.BarrierSecondsLeft <= 0.0)
                {
                    vitals.BarrierSecondsLeft = 0.0;
                    vitals.Barrier = 0.0;
                }
            }
        }

        public void GainResource(ref Vitals vitals, IStatBlock stats, double amount)
        {
            if (amount <= 0.0) return;
            vitals.Resource = Math.Min(stats.Get(StatId.Resource), vitals.Resource + amount);
        }

        public bool TrySpendResource(ref Vitals vitals, double amount)
        {
            if (amount <= 0.0) return true;
            if (vitals.Resource + 1e-9 < amount) return false;
            vitals.Resource = Math.Max(0.0, vitals.Resource - amount);
            return true;
        }

        public PotionOutcome ResolvePotion(PotionInfo potion, IStatBlock stats, in Vitals vitals)
        {
            var maxLife = stats.Get(StatId.Life);
            if (potion == null) return new PotionOutcome(vitals.Life, vitals.Barrier, vitals.BarrierSecondsLeft, 0.0);
            switch (potion.Kind)
            {
                case PotionKind.Heal:
                {
                    var heal = maxLife * potion.FractionOfMaxLife * stats.Get(StatId.PotionEffect);
                    var after = Math.Min(maxLife, vitals.Life + heal);
                    return new PotionOutcome(after, vitals.Barrier, vitals.BarrierSecondsLeft, after - vitals.Life);
                }
                case PotionKind.Barrier:
                {
                    // Não acumula: reaplicar renova (docs/13, item 2).
                    var barrier = maxLife * potion.FractionOfMaxLife * stats.Get(StatId.PotionEffect);
                    return new PotionOutcome(vitals.Life, barrier, potion.Duration, 0.0);
                }
                default:
                    return new PotionOutcome(vitals.Life, vitals.Barrier, vitals.BarrierSecondsLeft, 0.0);
            }
        }

        /// <summary>
        /// Libera o conteúdo. StatBlocks e efeitos criados continuam sendo dos seus donos
        /// (cada um descarta o seu), como os SafeHandles da API C.
        /// </summary>
        public void Dispose()
        {
            content = null;
        }

        StubContent RequireContent()
        {
            if (content == null) throw new InvalidOperationException("rules content not loaded (call LoadContent first)");
            return content;
        }

        static T Find<T>(Dictionary<string, T> table, string id) where T : class
        {
            if (string.IsNullOrEmpty(id)) return null;
            return table.TryGetValue(id, out var value) ? value : null;
        }
    }
}
