using System;

namespace Echoes.Interop
{
    /// <summary>
    /// PROVISÓRIO (stub). Porte do <c>shatter::ResolveHit</c> na ordem do damage.h e da seção 11 do
    /// docs/04_arquitetura.md. Consome SEMPRE 3 números do RNG (crítico, evasão, bloqueio), exceto DoT.
    /// Quando a DLL existir, esta classe sai e o golpe passa a ser <c>shatter_resolve_hit</c>.
    /// </summary>
    internal static class StubDamage
    {
        public static HitResult ResolveHit(in HitRequest input, StubRulesConstants rules, ref RngState rng)
        {
            var attacker = input.Attacker as StubStatBlock;
            var defender = input.Defender as StubStatBlock;
            if (attacker == null || defender == null)
                throw new ArgumentException("HitRequest needs stub stat blocks for attacker and defender");

            var result = new HitResult();
            var tags = input.SkillTags;

            // 1–2. base × coeficiente e modificadores por tag.
            var afterMods = new DamageByType();
            for (var t = 0; t < DamageByType.Count; t++)
            {
                var baseValue = input.BaseDamage[t] * input.Coefficient;
                if (baseValue <= 0.0) continue;
                var typeTag = StubParse.TagOf((DamageType)t);
                afterMods[t] = attacker.ApplyTagged(StatId.Damage, tags | typeTag, baseValue);
            }

            var evaded = false;
            var blocked = false;
            if (!input.IsDamageOverTime)
            {
                // 3–5. Sempre 3 números, nesta ordem.
                var critRoll = StubPcg32.NextUnit(ref rng);
                var evadeRoll = StubPcg32.NextUnit(ref rng);
                var blockRoll = StubPcg32.NextUnit(ref rng);

                if (critRoll < attacker.GetTagged(StatId.CritChance, tags))
                {
                    result.Critical = true;
                    var mult = attacker.ApplyTagged(StatId.CritMultiplier, tags, rules.CritMultiplierBase);
                    for (var t = 0; t < DamageByType.Count; t++) afterMods[t] = afterMods[t] * mult;
                }

                if ((tags & SkillTags.Attack) != 0)
                {
                    var evasion = Math.Min(defender.Get(StatId.EvasionChance), rules.EvasionCap);
                    evaded = evadeRoll < evasion;
                }

                if (!evaded && input.CanBeBlocked)
                {
                    var block = Math.Min(defender.Get(StatId.BlockChance), rules.BlockCap);
                    blocked = blockRoll < block;
                }
            }
            result.AfterModifiers = afterMods;

            if (evaded)
            {
                result.Outcome = HitOutcome.Evaded;
                result.Landed = false;
                result.DefenderLifeAfter = input.DefenderLife;
                result.DefenderBarrierAfter = input.DefenderBarrier;
                return result;
            }

            var mitigated = afterMods;
            if (blocked)
            {
                result.Outcome = HitOutcome.Blocked;
                for (var t = 0; t < DamageByType.Count; t++) mitigated[t] = mitigated[t] * (1.0 - rules.BlockMitigation);
            }
            result.Landed = true;

            // 6. armadura, só físico: redução = min(máx, A / (A + k·D)).
            var physical = mitigated.Physical;
            if (physical > 0.0)
            {
                var armor = defender.Get(StatId.Armor);
                mitigated.Physical = physical * (1.0 - ArmorReduction(armor, physical, rules));
            }

            // 7. resistência por elemento.
            mitigated.Fire = mitigated.Fire * (1.0 - ClampResistance(defender.Get(StatId.ResistFire), rules));
            mitigated.Cold = mitigated.Cold * (1.0 - ClampResistance(defender.Get(StatId.ResistCold), rules));
            mitigated.Lightning = mitigated.Lightning * (1.0 - ClampResistance(defender.Get(StatId.ResistLightning), rules));

            // 8. dano recebido do defensor.
            var taken = defender.Get(StatId.DamageTaken);
            for (var t = 0; t < DamageByType.Count; t++) mitigated[t] = mitigated[t] * taken;

            result.AfterMitigation = mitigated;
            var total = mitigated.Total;
            result.TotalDamage = total;

            // 9. barreira primeiro, depois vida (mínimo 0).
            var barrier = input.DefenderBarrier;
            var absorbed = Math.Min(barrier, total);
            var rest = total - absorbed;
            var lifeBefore = input.DefenderLife;
            var lifeAfter = Math.Max(0.0, lifeBefore - rest);
            result.AbsorbedByBarrier = absorbed;
            result.DefenderBarrierAfter = barrier - absorbed;
            result.LifeLost = lifeBefore - lifeAfter;
            result.DefenderLifeAfter = lifeAfter;
            result.Killed = lifeBefore > 0.0 && lifeAfter <= 0.0;
            return result;
        }

        public static double ArmorReduction(double armor, double physicalDamage, StubRulesConstants rules)
        {
            if (armor <= 0.0 || physicalDamage <= 0.0) return 0.0;
            var reduction = armor / (armor + rules.ArmorDamageFactor * physicalDamage);
            return Math.Min(rules.ArmorMaxReduction, reduction);
        }

        public static double ClampResistance(double resist, StubRulesConstants rules)
        {
            if (resist < rules.ResistFloor) return rules.ResistFloor;
            if (resist > rules.ResistCap) return rules.ResistCap;
            return resist;
        }
    }
}
