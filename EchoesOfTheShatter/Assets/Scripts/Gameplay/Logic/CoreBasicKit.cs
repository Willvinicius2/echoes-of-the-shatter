using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// <see cref="IBasicKit"/> sobre o core: as chaves globais de <see cref="CombatRules"/> (rules.csv) e a linha da classe em
    /// <see cref="BasicKitInfo"/> (basic_kits.csv), com as habilidades já resolvidas. Nenhum número próprio.
    /// </summary>
    public sealed class CoreBasicKit : IBasicKit
    {
        readonly CombatRules rules;
        readonly BasicKitInfo info;

        CoreBasicKit(CombatRules rules, BasicKitInfo info, IReadOnlyList<SkillInfo> chain, SkillInfo heavy)
        {
            this.rules = rules;
            this.info = info;
            LightChain = chain;
            HeavySkill = heavy;
        }

        /// <summary>null se a classe não tem kit ou se uma habilidade do kit não existe no core.</summary>
        public static CoreBasicKit Create(IRulesCore core, string classId)
        {
            if (core == null || string.IsNullOrEmpty(classId)) return null;
            var info = core.FindBasicKit(classId);
            if (info == null) return null;
            var chain = new List<SkillInfo>(info.LightChain.Count);
            for (var i = 0; i < info.LightChain.Count; i++)
            {
                var skill = core.FindSkill(info.LightChain[i]);
                if (skill == null) return null;
                chain.Add(skill);
            }
            var heavy = core.FindSkill(info.HeavySkill);
            if (chain.Count == 0 || heavy == null) return null;
            return new CoreBasicKit(core.Combat, info, chain, heavy);
        }

        public double ComboWindow => rules.ComboWindowSeconds;
        public double ComboWindowAfterDodge => rules.ComboWindowAfterDodgeSeconds;
        public double AttackBuffer => rules.AttackBufferSeconds;
        public double HeavyHoldThreshold => rules.HeavyHoldThresholdSeconds;
        public double LightWindupCreditMax => rules.LightWindupCreditMax;
        public double GuardLowerTime => rules.GuardLowerTimeSeconds;
        public IReadOnlyList<SkillInfo> LightChain { get; }
        public SkillInfo HeavySkill { get; }
        public double HeavyChargeTime => info.HeavyChargeSeconds;
        public double HeavyMaxMult => info.HeavyMaxMultiplier;
        public string ChargeEffect => info.ChargeEffect;
        public string GuardEffect => info.GuardEffect;
        public double GuardArcDegrees => info.GuardArcDegrees;
        public double GuardMaxHold => info.GuardMaxHoldSeconds;
        public double GuardCooldown => info.GuardCooldownSeconds;
        public double GuardPerfectWindow => info.GuardPerfectWindowSeconds;
        public double GuardPerfectCooldown => info.GuardPerfectCooldownSeconds;
        public IReadOnlyList<string> GuardPerfectEffects => info.GuardPerfectEffects;
        public double GuardPerfectResource => info.GuardPerfectResource;
        public double GuardDrainPerDamage => info.GuardDrainPerDamage;
    }
}
