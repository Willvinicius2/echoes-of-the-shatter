// ShatterCore — resolução de um golpe (ordem do plano, seção 10; ver damage.h).
// Só + - * / e comparações: sem pow/exp/log/sin (determinismo entre compiladores).
#include "shatter/damage.h"

#include <algorithm>

namespace shatter {

double ArmorReduction(double armor, double physicalDamage, const RulesConstants& rules) {
    if (armor <= 0.0 || physicalDamage <= 0.0) return 0.0;
    const double denom = armor + rules.armorDamageFactor * physicalDamage;
    if (denom <= 0.0) return 0.0;
    const double red = armor / denom;
    return red < rules.armorMaxReduction ? red : rules.armorMaxReduction;
}

double ClampResistance(double resist, const RulesConstants& rules) {
    if (resist > rules.resistCap) return rules.resistCap;
    if (resist < rules.resistFloor) return rules.resistFloor;
    return resist;
}

namespace {

// Resistência SEM o piso em zero de StatBlock::Get: resistência negativa (fraqueza) precisa
// chegar até resistFloor. Mesma fórmula canônica, sem o max(0, ...).
double RawResist(const StatBlock& s, StatId id) {
    const StatBlock::Breakdown b = s.Explain(id, 0);
    return (b.base + b.sumFlat) * (1.0 + b.sumIncreased) * b.productMore;
}

StatId ResistStat(DamageType t) {
    switch (t) {
        case DamageType::Fire: return StatId::ResistFire;
        case DamageType::Cold: return StatId::ResistCold;
        case DamageType::Lightning: return StatId::ResistLightning;
        case DamageType::Physical: break;
    }
    return StatId::ResistFire;  // nunca usado para físico
}

double Clamp01(double v) { return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v); }

}  // namespace

HitResult ResolveHit(const HitInput& in, const RulesConstants& rules, Pcg32& combatRng) {
    HitResult r;
    r.defenderLifeAfter = in.defenderLife;
    r.defenderBarrierAfter = in.defenderBarrier;
    if (in.attacker == nullptr || in.defender == nullptr) return r;
    const StatBlock& atk = *in.attacker;
    const StatBlock& def = *in.defender;

    // Passos 1 e 2: base × coeficiente e modificadores por tag (só tipos com dano base).
    for (int t = 0; t < kDamageTypeCount; ++t) {
        const double base = in.baseDamage[static_cast<std::size_t>(t)] * in.coefficient;
        if (base <= 0.0) {
            r.afterModifiers[static_cast<std::size_t>(t)] = 0.0;
            continue;
        }
        const TagMask tags = in.skillTags | TagOf(static_cast<DamageType>(t));
        r.afterModifiers[static_cast<std::size_t>(t)] = atk.ApplyTagged(StatId::Damage, tags, base);
    }

    bool evaded = false;
    bool blocked = false;
    if (!in.isDamageOverTime) {
        // Sempre 3 números, nesta ordem: crítico, evasão, bloqueio.
        const bool critRoll = combatRng.Chance(Clamp01(atk.GetTagged(StatId::CritChance, in.skillTags)));
        const double evasion = std::min(Clamp01(def.Get(StatId::EvasionChance)), rules.evasionCap);
        const bool evadeRoll = combatRng.Chance(evasion);
        const double block = std::min(Clamp01(def.Get(StatId::BlockChance)), rules.blockCap);
        const bool blockRoll = combatRng.Chance(block);

        // Passo 3: crítico.
        if (critRoll) {
            r.critical = true;
            const double mult = atk.ApplyTagged(StatId::CritMultiplier, in.skillTags, rules.critMultiplierBase);
            for (double& d : r.afterModifiers) d *= mult;
        }
        // Passo 4: evasão (só ataques).
        evaded = HasTag(in.skillTags, Tag::Attack) && evadeRoll;
        // Passo 5: bloqueio.
        blocked = !evaded && in.canBeBlocked && blockRoll;
    }

    if (evaded) {
        r.outcome = HitOutcome::Evaded;
        r.landed = false;
        return r;  // dano 0; vida e barreira inalteradas
    }
    r.landed = true;
    r.outcome = blocked ? HitOutcome::Blocked : HitOutcome::Hit;

    DamageArray dmg = r.afterModifiers;
    if (blocked) {
        const double keep = 1.0 - rules.blockMitigation;
        for (double& d : dmg) d *= keep;
    }

    // Passo 6: armadura, só na parcela física.
    {
        double& phys = dmg[static_cast<std::size_t>(Index(DamageType::Physical))];
        phys *= 1.0 - ArmorReduction(def.Get(StatId::Armor), phys, rules);
    }
    // Passo 7: resistência por tipo elemental.
    for (int t = 1; t < kDamageTypeCount; ++t) {
        const DamageType type = static_cast<DamageType>(t);
        const double res = ClampResistance(RawResist(def, ResistStat(type)), rules);
        dmg[static_cast<std::size_t>(t)] *= 1.0 - res;
    }
    // Passo 8: dano recebido.
    const double taken = def.GetTagged(StatId::DamageTaken, in.fromGuardArc ? Mask(Tag::Guard) : TagMask{0});
    double total = 0.0;
    for (int t = 0; t < kDamageTypeCount; ++t) {
        dmg[static_cast<std::size_t>(t)] *= taken;
        total += dmg[static_cast<std::size_t>(t)];
    }
    r.afterMitigation = dmg;
    r.totalDamage = total;

    // Passo 9: barreira primeiro, depois vida (mínimo 0).
    const double barrier = in.defenderBarrier > 0.0 ? in.defenderBarrier : 0.0;
    r.absorbedByBarrier = std::min(barrier, total);
    r.defenderBarrierAfter = barrier - r.absorbedByBarrier;
    const double rest = total - r.absorbedByBarrier;
    const double life = in.defenderLife > 0.0 ? in.defenderLife : 0.0;
    r.lifeLost = std::min(life, rest);
    r.defenderLifeAfter = life - r.lifeLost;
    r.killed = life > 0.0 && r.defenderLifeAfter <= 0.0;
    return r;
}

}  // namespace shatter
