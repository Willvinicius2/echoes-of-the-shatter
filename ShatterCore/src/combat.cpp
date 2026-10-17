// ShatterCore — regras de combate novas do protótipo (docs/13, itens 1 a 11). Ver include/shatter/combat.h.
// Sem exceções, sem estado global. Só + - * / e sqrt em tudo que afeta resultado (sem pow/exp/log/sin da libm).
#include "shatter/combat.h"

#include <algorithm>
#include <cmath>

#include "shatter/loot.h"

namespace shatter {

namespace {

constexpr double kEps = 1e-9;
constexpr double kPi = 3.14159265358979323846;

double ClampMin0(double v) { return v > 0.0 ? v : 0.0; }

}  // namespace

// ===============================================================================================
// Trigonometria determinística
// ===============================================================================================
double DetCos(double x) {
    const double x2 = x * x;
    double term = 1.0, sum = 1.0;
    for (int k = 1; k <= 14; ++k) {
        term *= -x2 / (static_cast<double>(2 * k - 1) * static_cast<double>(2 * k));
        sum += term;
    }
    return sum;
}

double DetSin(double x) {
    const double x2 = x * x;
    double term = x, sum = x;
    for (int k = 1; k <= 14; ++k) {
        term *= -x2 / (static_cast<double>(2 * k) * static_cast<double>(2 * k + 1));
        sum += term;
    }
    return sum;
}

// ===============================================================================================
// Recarga em série
// ===============================================================================================
void TickSeriesRecharge(int& charges, int maxCharges, double& remaining, double period, double dt) {
    if (charges >= maxCharges) {
        remaining = 0.0;
        return;
    }
    if (period <= 0.0) {
        charges = maxCharges;
        remaining = 0.0;
        return;
    }
    if (remaining <= 0.0) remaining = period;
    double t = dt > 0.0 ? dt : 0.0;
    while (charges < maxCharges) {
        if (remaining > t + kEps) {
            remaining -= t;
            return;
        }
        t -= remaining;
        if (t < 0.0) t = 0.0;
        ++charges;
        remaining = charges < maxCharges ? period : 0.0;
    }
    remaining = 0.0;
}

// ===============================================================================================
// Vitals
// ===============================================================================================
Vitals CreateVitals(const StatBlock& stats, const ClassData* cls) {
    Vitals v;
    v.life = stats.Get(StatId::Life);
    v.resource = (cls != nullptr && cls->resourceDecayOutOfCombat > 0.0) ? 0.0 : stats.Get(StatId::Resource);
    return v;
}

void TickVitals(Vitals& v, const StatBlock& stats, const ClassData* cls, double dt, bool inCombat, bool moving) {
    if (v.life <= 0.0 || dt <= 0.0) return;
    const double maxLife = stats.Get(StatId::Life);
    const double regen = stats.Get(StatId::LifeRegen);
    if (regen > 0.0) v.life = std::min(maxLife, v.life + regen * dt);
    if (v.life > maxLife) v.life = maxLife;

    const double maxRes = stats.Get(StatId::Resource);
    double resRegen = stats.Get(StatId::ResourceRegen);
    if (moving && cls != nullptr) resRegen *= cls->regenMultWhileMoving;
    if (resRegen > 0.0) v.resource = std::min(maxRes, v.resource + resRegen * dt);
    if (!inCombat && cls != nullptr && cls->resourceDecayOutOfCombat > 0.0)
        v.resource = std::max(0.0, v.resource - cls->resourceDecayOutOfCombat * dt);
    if (v.resource > maxRes) v.resource = maxRes;

    TickPotionBarrier(v.barrier, v.potionBarrier, v.barrierSecondsLeft, dt);
}

FleeStep FleeState::Step(double dt, double life, double maxLife, bool hasTarget, bool dead) {
    FleeStep s;
    if (profile_.lifeFraction <= 0.0) return s;
    if (dead) {
        fleeing_ = false;
        remaining_ = 0.0;
        return s;
    }
    if (fleeing_) {
        remaining_ -= dt;
        if (remaining_ <= 0.0 || !hasTarget) {
            fleeing_ = false;
            remaining_ = 0.0;
            s.ended = true;
        }
    } else if (hasTarget && !(profile_.oncePerLife && hasFled_) && maxLife > 0.0 && life < profile_.lifeFraction * maxLife) {
        fleeing_ = true;
        hasFled_ = true;
        remaining_ = profile_.seconds;
        s.started = true;
    }
    s.fleeing = fleeing_;
    s.remaining = remaining_;
    return s;
}

void ApplyPotionBarrier(double& barrier, double& potionAmount, double& remaining, double newAmount, double seconds) {
    barrier = std::max(0.0, barrier - potionAmount) + newAmount;
    potionAmount = newAmount;
    remaining = seconds;
}

void TickPotionBarrier(double& barrier, double& potionAmount, double& remaining, double dt) {
    if (remaining > 0.0 && potionAmount <= 0.0) potionAmount = barrier;  // sem divisão informada: tudo é da poção
    if (potionAmount > barrier) potionAmount = barrier;                   // o dano gastou a parte da poção
    if (remaining <= 0.0) {
        potionAmount = 0.0;
        return;
    }
    remaining -= dt;
    if (remaining <= kEps) {
        barrier = std::max(0.0, barrier - potionAmount);
        potionAmount = 0.0;
        remaining = 0.0;
    }
}

void GainResource(Vitals& v, const StatBlock& stats, double amount) {
    if (!(amount > 0.0)) return;
    v.resource = std::min(stats.Get(StatId::Resource), v.resource + amount);
}

double ResourceOnHit(const ClassData* cls) { return cls != nullptr ? cls->resourceOnHit : 0.0; }
double ResourceOnBlock(const ClassData* cls) { return cls != nullptr ? cls->resourceOnBlock : 0.0; }
void GainResourceOnHit(Vitals& v, const StatBlock& stats, const ClassData* cls) { GainResource(v, stats, ResourceOnHit(cls)); }
void GainResourceOnBlock(Vitals& v, const StatBlock& stats, const ClassData* cls) { GainResource(v, stats, ResourceOnBlock(cls)); }

bool TrySpendResource(Vitals& v, double amount) {
    if (!(amount > 0.0)) return true;
    if (v.resource + kEps < amount) return false;
    v.resource = std::max(0.0, v.resource - amount);
    return true;
}

// ===============================================================================================
// Tempos de ação
// ===============================================================================================
ActionTimingInfo ComputeActionTiming(const ContentDB& db, const SkillData& skill, const StatBlock& stats,
                                     const EliteProfile* elite) {
    ActionTimingInfo t;
    const StatId speedStat = HasTag(skill.tags, Tag::Spell) ? StatId::CastSpeed : StatId::AttackSpeed;
    double speed = stats.Get(speedStat);
    double windupSpeed = speed;
    double recoveryMult = 1.0;
    if (elite != nullptr) {
        // Elite: o resultado NÃO depende de o bloco já ter os mods "elite" (ApplyEliteToStats) ou não. A velocidade-base é a
        // do bloco sem eles; o telegraph (windup) usa só ela (o modificador não muda a preparação); impacto e recuperação
        // usam base × attackSpeedMult; a recuperação ainda × recoveryMult.
        StatBlock plain = stats;
        plain.RemoveModifiersFrom("elite");
        windupSpeed = plain.Get(speedStat);
        speed = windupSpeed * (elite->attackSpeedMult > 0.0 ? elite->attackSpeedMult : 1.0);
        recoveryMult = elite->recoveryMult;
    }
    if (speed < 0.01) speed = 0.01;
    if (windupSpeed < 0.01) windupSpeed = 0.01;
    t.windup = skill.windup / windupSpeed;
    t.impact = skill.impact / speed;
    t.recovery = skill.recovery * recoveryMult / speed;
    t.cooldown = skill.cooldown > 0.0 ? EffectiveCooldown(skill.cooldown, stats.Get(StatId::CooldownRecovery), db.Rules()) : 0.0;
    t.cost = ClampMin0(skill.cost);
    return t;
}

double MoveSpeedUu(const StatBlock& stats, double baseMoveSpeedUu) {
    // Herói: class_stats.csv guarda move_speed em uu/s (450) e o StatBlock já devolve uu/s: base <= 0 usa o atributo direto.
    // Inimigo: EnemyData::moveSpeed (uu/s) × atributo (multiplicador, base 1).
    const double mult = stats.Get(StatId::MoveSpeed);
    return ClampMin0(baseMoveSpeedUu > 0.0 ? baseMoveSpeedUu * mult : mult);
}

std::array<double, kDamageTypeCount> ComputeSkillBaseDamage(const ContentDB& db, const SkillData& skill,
                                                            const ItemBaseData* weaponOrNull) {
    if (!skill.scalesWithWeapon) return skill.baseDamage;
    if (weaponOrNull != nullptr) return weaponOrNull->weaponDamage;
    std::array<double, kDamageTypeCount> unarmed{};
    unarmed[static_cast<std::size_t>(Index(DamageType::Physical))] = db.Rules().unarmedWeaponDamagePhysical;
    return unarmed;
}

bool CanAct(const StatBlock& stats) { return stats.Get(StatId::AttackSpeed) > 0.0; }
bool CanMove(const StatBlock& stats) { return stats.Get(StatId::MoveSpeed) > 0.0; }

int PickEnemyAttack(const EnemyData& enemy, Pcg32& rng) {
    std::vector<double> w;
    w.reserve(enemy.attacks.size());
    for (const EnemyAttack& a : enemy.attacks) w.push_back(a.weight);
    return PickWeighted(w, rng);
}

// ===============================================================================================
// Poções
// ===============================================================================================
PotionBelt MakeFullPotionBelt(const ContentDB& db) {
    PotionBelt b;
    for (const PotionData& p : db.Potions()) {
        PotionSlotState s;
        s.potionId = p.id;
        s.charges = p.maxCharges;
        b.slots.push_back(std::move(s));
    }
    return b;
}

PotionBelt MakePotionBelt(const ContentDB& db, const std::vector<PotionSlotState>& saved) {
    PotionBelt b;
    for (const PotionData& p : db.Potions()) {
        PotionSlotState s;
        s.potionId = p.id;
        s.charges = p.maxCharges;
        for (const PotionSlotState& q : saved) {
            if (q.potionId != p.id) continue;
            s.charges = std::max(0, std::min(q.charges, p.maxCharges));
            // Recarga salva maior que o período (save adulterado) é cortada: a carga volta em no máximo rechargeSeconds.
            s.rechargeRemaining = q.rechargeRemaining > 0.0 ? std::min(q.rechargeRemaining, p.rechargeSeconds) : 0.0;
            break;
        }
        if (s.charges >= p.maxCharges) s.rechargeRemaining = 0.0;
        else if (s.rechargeRemaining <= 0.0) s.rechargeRemaining = p.rechargeSeconds;
        b.slots.push_back(std::move(s));
    }
    return b;
}

void RefillPotions(const ContentDB& db, PotionBelt& belt) {
    belt = MakePotionBelt(db, belt.slots);
    for (PotionSlotState& s : belt.slots) {
        const PotionData* p = db.FindPotion(s.potionId);
        if (p == nullptr) continue;
        s.charges = p->maxCharges;
        s.rechargeRemaining = 0.0;
    }
    belt.lockoutRemaining = 0.0;
}

void TickPotions(const ContentDB& db, PotionBelt& belt, double dt) {
    if (!(dt > 0.0)) return;
    if (belt.lockoutRemaining > 0.0) {
        belt.lockoutRemaining -= dt;
        if (belt.lockoutRemaining < kEps) belt.lockoutRemaining = 0.0;
    }
    for (PotionSlotState& s : belt.slots) {
        const PotionData* p = db.FindPotion(s.potionId);
        if (p == nullptr) continue;
        TickSeriesRecharge(s.charges, p->maxCharges, s.rechargeRemaining, p->rechargeSeconds, dt);
    }
}

bool AddChargeOnEliteKill(const ContentDB& db, PotionBelt& belt) {
    PotionSlotState* best = nullptr;
    const PotionData* bestData = nullptr;
    for (PotionSlotState& s : belt.slots) {
        const PotionData* p = db.FindPotion(s.potionId);
        if (p == nullptr || !p->refillOnEliteKill || s.charges >= p->maxCharges) continue;  // cheia não conta
        if (best == nullptr || s.charges < best->charges) {  // empate: a primeira do CSV
            best = &s;
            bestData = p;
        }
    }
    if (best == nullptr) return false;
    ++best->charges;
    if (best->charges >= bestData->maxCharges) best->rechargeRemaining = 0.0;
    return true;
}

int PotionCharges(const PotionBelt& belt, std::string_view potionId) {
    for (const PotionSlotState& s : belt.slots) {
        if (s.potionId == potionId) return s.charges;
    }
    return 0;
}

const PotionData* DefaultHealPotion(const ContentDB& db) {
    for (const PotionData& p : db.Potions()) {
        if (p.kind == PotionKind::Heal) return &p;
    }
    return nullptr;
}

PotionOutcome ResolvePotion(const PotionData& potion, double maxLife, double potionEffect) {
    PotionOutcome o;
    const double amount = maxLife * potion.fractionOfMaxLife * potionEffect;
    if (potion.kind == PotionKind::Heal) {
        o.healAmount = ClampMin0(amount);
    } else {
        o.barrierAmount = ClampMin0(amount);
        o.barrierSeconds = potion.duration;
    }
    o.useTime = potion.useTime;
    o.moveSpeedWhileUsing = potion.moveSpeedWhileUsing;
    return o;
}

double ApplyPotionOutcome(Vitals& v, const PotionOutcome& po, double maxLife) {
    double healed = 0.0;
    if (po.healAmount > 0.0) {
        const double after = std::min(maxLife, v.life + po.healAmount);
        if (after > v.life) {
            healed = after - v.life;
            v.life = after;
        }
    }
    if (po.barrierAmount > 0.0)
        ApplyPotionBarrier(v.barrier, v.potionBarrier, v.barrierSecondsLeft, po.barrierAmount, po.barrierSeconds);
    return healed;
}

PotionUseStatus UsePotion(const ContentDB& db, PotionBelt& belt, std::string_view potionId, double maxLife,
                          double potionEffect, PotionOutcome* out) {
    const PotionData* p = db.FindPotion(potionId);
    if (p == nullptr) return PotionUseStatus::UnknownPotion;
    PotionSlotState* slot = nullptr;
    for (PotionSlotState& s : belt.slots) {
        if (s.potionId == potionId) slot = &s;
    }
    if (slot == nullptr) return PotionUseStatus::UnknownPotion;
    if (belt.lockoutRemaining > kEps) return PotionUseStatus::LockedOut;
    if (slot->charges <= 0) return PotionUseStatus::NoCharges;
    const bool wasFull = slot->charges >= p->maxCharges;
    --slot->charges;
    if (wasFull) slot->rechargeRemaining = p->rechargeSeconds;
    const double lockout = p->globalLockout > 0.0 ? p->globalLockout : db.Rules().potionLockout;
    belt.lockoutRemaining = lockout;
    if (out != nullptr) {
        *out = ResolvePotion(*p, maxLife, potionEffect);
        out->lockout = lockout;
    }
    return PotionUseStatus::Ok;
}

// ===============================================================================================
// Esquiva
// ===============================================================================================
void NormalizeDodge(const RulesConstants& rules, DodgeState& d) {
    if (d.charges < 0 || d.charges > rules.dodgeMaxCharges) d.charges = rules.dodgeMaxCharges;
    if (d.charges >= rules.dodgeMaxCharges) d.rechargeRemaining = 0.0;
}

void TickDodge(const RulesConstants& rules, DodgeState& d, double dt) {
    NormalizeDodge(rules, d);
    if (!(dt > 0.0)) return;
    if (d.active) {
        d.elapsed += dt;
        if (d.elapsed + kEps >= rules.dodgeDuration) d.active = false;
    }
    TickSeriesRecharge(d.charges, rules.dodgeMaxCharges, d.rechargeRemaining, rules.dodgeRecharge, dt);
}

namespace {
void SpendDodgeCharge(const RulesConstants& rules, DodgeState& d) {
    const bool wasFull = d.charges >= rules.dodgeMaxCharges;
    --d.charges;
    if (wasFull) d.rechargeRemaining = rules.dodgeRecharge;
}
}  // namespace

DodgeStartStatus TryStartDodge(const RulesConstants& rules, DodgeState& d, double resourceAvailable) {
    NormalizeDodge(rules, d);
    if (d.active) return DodgeStartStatus::Active;
    if (d.charges <= 0) return DodgeStartStatus::NoCharges;
    if (rules.dodgeCostResource > resourceAvailable + kEps) return DodgeStartStatus::NotEnoughResource;
    SpendDodgeCharge(rules, d);
    d.active = true;
    d.elapsed = 0.0;
    return DodgeStartStatus::Ok;
}

bool DodgeInvulnerable(const RulesConstants& rules, const DodgeState& d) {
    return d.active && d.elapsed + kEps < rules.dodgeIframes;
}

bool DodgeSpendCharge(const RulesConstants& rules, DodgeState& d) {
    NormalizeDodge(rules, d);
    if (d.charges <= 0) return false;
    SpendDodgeCharge(rules, d);
    return true;
}

double DodgePerfectReward(const RulesConstants& rules, const DodgeState& d) {
    return DodgeInvulnerable(rules, d) ? rules.dodgePerfectResource : 0.0;
}

// ===============================================================================================
// Stun e Guarda Quebrada
// ===============================================================================================
StatusProfile MakeStatusProfile(const ContentDB& db, const EnemyData* enemy, bool isElite) {
    StatusProfile p;
    const RulesConstants& r = db.Rules();
    p.staggerSeconds = r.guardBreakStaggerSeconds;
    p.immunitySeconds = r.guardBreakImmunityOther;
    if (enemy == nullptr) return p;
    p.isBoss = enemy->isBoss;
    p.stunImmune = enemy->stunImmune || enemy->isBoss || isElite || enemy->isElite;
    if (enemy->guardBreakStaggerSeconds > 0.0) p.staggerSeconds = enemy->guardBreakStaggerSeconds;
    if (enemy->guardBreakImmunitySeconds > 0.0) p.immunitySeconds = enemy->guardBreakImmunitySeconds;
    else p.immunitySeconds = enemy->isBoss ? r.guardBreakImmunityBoss : r.guardBreakImmunityOther;
    return p;
}

StatusApply ActionStatus::ApplyEffect(const ContentDB& db, const EffectData& effect, std::string_view source,
                                      double magnitude, TriggerKind triggeredBy, EffectContainer& fx,
                                      StatBlock& target, bool allowStagger) {
    StatusApply r;
    const RulesConstants& rules = db.Rules();
    if (effect.interruptsAction) {
        if (profile_.stunImmune) {
            r.stunBlocked = true;
            return r;
        }
        r.applied = fx.Apply(effect, source, magnitude, triggeredBy, target, rules);
        if (r.applied) {
            stunRemaining_ = std::max(stunRemaining_, effect.duration);
            r.stunned = true;
            r.interrupted = true;
            r.stunSeconds = effect.duration;
        }
        return r;
    }
    r.applied = fx.Apply(effect, source, magnitude, triggeredBy, target, rules);
    if (effect.id != kEffectGuardBreak) return r;

    if (r.applied) fx.RefreshAll(effect.id, effect.duration);  // timer único: os acúmulos expiram juntos
    r.guardBreakStacks = fx.StackCount(effect.id);
    const int maxStacks = effect.maxStacks < 1 ? 1 : effect.maxStacks;
    if (r.applied && allowStagger && profile_.stunImmune && r.guardBreakStacks >= maxStacks &&
        immunityRemaining_ <= kEps && staggerRemaining_ <= kEps) {
        BeginStagger(db, profile_.staggerSeconds, target);
        immunityRemaining_ = profile_.immunitySeconds;
        fx.Remove(effect.id, &effect, target);  // consome os acúmulos
        r.guardBreakStacks = 0;
        r.staggered = true;
        r.interrupted = true;
        r.removeBarrier = true;
        r.staggerSeconds = profile_.staggerSeconds;
    }
    return r;
}

bool ActionStatus::BeginStagger(const ContentDB& db, double seconds, StatBlock& target) {
    if (staggerRemaining_ > kEps) return false;
    staggerRemaining_ = seconds;
    Modifier bonus;
    bonus.stat = StatId::DamageTaken;
    bonus.kind = ModKind::Increased;
    bonus.value = db.Rules().guardBreakStaggerDamageTaken;
    bonus.source = "stagger";
    target.AddModifier(bonus);
    return true;
}

bool ActionStatus::Tick(double dt, StatBlock& target) {
    if (!(dt > 0.0)) return false;
    bool staggerEnded = false;
    if (stunRemaining_ > 0.0) {
        stunRemaining_ -= dt;
        if (stunRemaining_ < kEps) stunRemaining_ = 0.0;
    }
    if (staggerRemaining_ > 0.0) {
        staggerRemaining_ -= dt;
        if (staggerRemaining_ < kEps) {
            staggerRemaining_ = 0.0;
            target.RemoveModifiersFrom("stagger");
            staggerEnded = true;
        }
    }
    if (immunityRemaining_ > 0.0) {
        immunityRemaining_ -= dt;
        if (immunityRemaining_ < kEps) immunityRemaining_ = 0.0;
    }
    return staggerEnded;
}

// ===============================================================================================
// Elite
// ===============================================================================================
const EliteModifierData* RollEliteModifier(const ContentDB& db, Pcg32& eventsRng) {
    const std::vector<EliteModifierData>& mods = db.EliteModifiers();
    std::vector<double> w;
    w.reserve(mods.size());
    for (const EliteModifierData& m : mods) w.push_back(m.weightPrototype);
    const int pick = PickWeighted(w, eventsRng);  // consome sempre 1 número
    return pick < 0 ? nullptr : &mods[static_cast<std::size_t>(pick)];
}

EliteProfile MakeEliteProfile(const ContentDB& db, const EliteModifierData* mod, bool rolled) {
    EliteProfile p;
    const RulesConstants& r = db.Rules();
    p.rolled = rolled;
    if (rolled) {
        p.lifeMult = r.eliteLifeMult;
        p.damageMult = r.eliteDamageMult;
        p.xpMult = r.eliteXpMult;
    }
    if (mod != nullptr) {
        p.modifierId = mod->id;
        p.lifeMult *= mod->lifeMult;
        p.damageMult *= mod->damageMult;
        p.xpMult *= mod->xpMult;
        p.barrierFractionOfLife = mod->barrierFractionOfLife;
        p.moveSpeedMult = mod->moveSpeedMult;
        p.attackSpeedMult = mod->attackSpeedMult;
        p.recoveryMult = mod->recoveryMult;
        p.deathExplosionRadius = mod->deathExplosionRadius;
        p.deathExplosionDamage = mod->deathExplosionDamage;
        p.deathExplosionFuse = mod->deathExplosionFuse;
    }
    return p;
}

void ApplyEliteToStats(const EliteProfile& p, StatBlock& stats) {
    stats.RemoveModifiersFrom("elite");  // idempotente: reaplicar no mesmo bloco (reinício no checkpoint) não multiplica de novo
    auto addMore = [&](StatId stat, double mult) {
        if (mult == 1.0) return;
        Modifier m;
        m.stat = stat;
        m.kind = ModKind::More;
        m.value = mult - 1.0;
        m.source = "elite";
        stats.AddModifier(m);
    };
    addMore(StatId::Life, p.lifeMult);
    addMore(StatId::Damage, p.damageMult);
    addMore(StatId::MoveSpeed, p.moveSpeedMult);
    addMore(StatId::AttackSpeed, p.attackSpeedMult);
}

double EliteBarrier(const EliteProfile& p, double maxLife) { return ClampMin0(p.barrierFractionOfLife * maxLife); }

const ContentId& EliteLootTable(const EnemyData& enemy, bool rolled) {
    if (rolled && !enemy.eliteLootTableId.empty()) return enemy.eliteLootTableId;
    return enemy.lootTableId;
}

// ===============================================================================================
// Chefe
// ===============================================================================================
BossFight::BossFight(const ContentDB& db, const EnemyData& boss, int level, std::uint64_t seed)
    : db_(&db), boss_(&boss), rng_(Pcg32::ForStream(seed, RngStream::Events, 0)) {
    for (const BossPhaseData& ph : db.BossPhases()) {
        if (ph.bossId != boss.id) continue;
        auto it = phases_.begin();
        while (it != phases_.end() && (*it)->phase < ph.phase) ++it;
        phases_.insert(it, &ph);
    }
    for (const BossPatternData& pt : db.BossPatterns()) {
        if (pt.bossId == boss.id) patterns_.push_back(&pt);
    }
    patternCooldown_.assign(patterns_.size(), 0.0);
    StatBlock sb;
    BuildEnemyStatBlock(boss, level, sb);
    maxLife_ = sb.Get(StatId::Life);
    status_.Init(MakeStatusProfile(db, &boss, false));
    Reset(nullptr);
}

const BossPhaseData* BossFight::PhaseData(int phase) const {
    for (const BossPhaseData* p : phases_) {
        if (p->phase == phase) return p;
    }
    return nullptr;
}

double BossFight::PhaseThresholdLife(int phase) const {
    const BossPhaseData* p = PhaseData(phase);
    return p == nullptr ? 0.0 : p->lifeThreshold * maxLife_;
}

void BossFight::Reset(StatBlock* stats) {
    if (stats != nullptr) stats->RemoveModifiersFrom("stagger");
    life_ = maxLife_;
    phase_ = 1;
    state_ = BossState::Idle;
    timer_ = 0.0;
    shieldDown_ = 0.0;
    pendingTransition_ = false;
    lastPattern_ = -1;
    repeatCount_ = 0;
    current_ = nullptr;
    faceSnap_ = true;
    summonMarked_ = summonDone_ = false;
    summonCount_ = 0;
    summonEnemy_.clear();
    std::fill(patternCooldown_.begin(), patternCooldown_.end(), 0.0);
    status_.Init(status_.Profile());
    const BossPhaseData* p1 = PhaseData(1);
    turnRate_ = p1 != nullptr && p1->turnRate > 0.0 ? p1->turnRate : boss_->turnRateDegPerSec;
}

void BossFight::BeginWaiting(bool intro) {
    state_ = BossState::Waiting;
    const BossPhaseData* ph = PhaseData(phase_);
    if (intro && ph != nullptr && ph->transitionSeconds > 0.0) {
        timer_ = ph->transitionSeconds;
        return;
    }
    const double lo = ph != nullptr ? ph->decisionDelayMin : 0.0;
    const double hi = ph != nullptr ? ph->decisionDelayMax : 0.0;
    timer_ = rng_.RangeReal(lo, hi < lo ? lo : hi);
}

void BossFight::Start() {
    if (state_ != BossState::Idle || phases_.empty()) return;
    faceSnap_ = true;
    BeginWaiting(true);
}

void BossFight::Rotate(double dt, const Context& ctx) {
    const double dx = ctx.player.x - ctx.boss.x, dz = ctx.player.z - ctx.boss.z;
    const double len = std::sqrt(dx * dx + dz * dz);
    if (len < kEps) return;
    const Vec2 dir{dx / len, dz / len};
    if (faceSnap_) {
        facing_ = dir;
        faceSnap_ = false;
        return;
    }
    double step = turnRate_ * dt * (kPi / 180.0);
    if (step <= 0.0) return;
    if (step > kPi) step = kPi;
    const double dot = facing_.x * dir.x + facing_.z * dir.z;
    if (dot >= DetCos(step)) {
        facing_ = dir;
        return;
    }
    const double cross = facing_.x * dir.z - facing_.z * dir.x;
    const double ang = cross >= 0.0 ? step : -step;
    const double c = DetCos(ang), s = DetSin(ang);
    Vec2 f{facing_.x * c - facing_.z * s, facing_.x * s + facing_.z * c};
    const double n = std::sqrt(f.x * f.x + f.z * f.z);
    if (n > kEps) {
        f.x /= n;
        f.z /= n;
    }
    facing_ = f;
}

bool BossFight::ShieldCovers(Vec2 bossPos, Vec2 origin) const {
    if (!ShieldUp() || boss_->shieldArcDegrees <= 0.0) return false;
    const double dx = origin.x - bossPos.x, dz = origin.z - bossPos.z;
    const double len = std::sqrt(dx * dx + dz * dz);
    if (len < kEps) return false;
    double half = boss_->shieldArcDegrees * 0.5 * (kPi / 180.0);
    if (half > kPi) half = kPi;
    return facing_.x * dx + facing_.z * dz >= DetCos(half) * len;
}

void BossFight::StartTransition(std::vector<BossEvent>& out) {
    pendingTransition_ = false;
    const BossPhaseData* next = PhaseData(phase_ + 1);
    if (next == nullptr) {
        BeginWaiting(false);
        return;
    }
    phase_ = next->phase;
    turnRate_ = next->turnRate > 0.0 ? next->turnRate
                                     : (phase_ >= 2 && boss_->turnRateDegPerSecPhase2 > 0.0 ? boss_->turnRateDegPerSecPhase2
                                                                                            : boss_->turnRateDegPerSec);
    state_ = BossState::Transition;
    transitionLength_ = next->transitionSeconds;
    timer_ = next->transitionSeconds;
    summonCount_ = next->summonCount;
    summonEnemy_ = next->summonEnemyId;
    summonAtFraction_ = next->summonAtFraction;
    summonMarked_ = summonDone_ = false;
    current_ = nullptr;
    BossEvent ev;
    ev.kind = BossEvent::Kind::PhaseTransitionStart;
    ev.phase = phase_;
    ev.seconds = transitionLength_;
    out.push_back(ev);
    if (summonCount_ > 0 && !summonEnemy_.empty()) {
        BossEvent m;
        m.kind = BossEvent::Kind::SummonMarker;
        m.phase = phase_;
        m.enemyId = summonEnemy_;
        m.count = summonCount_;
        m.seconds = transitionLength_ * summonAtFraction_;
        out.push_back(m);
        summonMarked_ = true;
    }
    if (transitionLength_ <= kEps) {
        if (summonMarked_) {
            BossEvent s;
            s.kind = BossEvent::Kind::SummonSpawn;
            s.phase = phase_;
            s.enemyId = summonEnemy_;
            s.count = summonCount_;
            out.push_back(s);
        }
        BossEvent e;
        e.kind = BossEvent::Kind::PhaseTransitionEnd;
        e.phase = phase_;
        out.push_back(e);
        BeginWaiting(false);
    }
}

void BossFight::PickAndStart(const Context& ctx, std::vector<BossEvent>& out) {
    std::vector<std::size_t> cand;
    for (std::size_t i = 0; i < patterns_.size(); ++i) {
        if (patterns_[i]->phase == phase_) cand.push_back(i);
    }
    if (cand.empty()) {
        BeginWaiting(false);
        return;
    }
    const double dx = ctx.player.x - ctx.boss.x, dz = ctx.player.z - ctx.boss.z;
    const double dist = std::sqrt(dx * dx + dz * dz);
    const bool inFront = dist < kEps || facing_.x * dx + facing_.z * dz >= 0.0;

    auto weightsFor = [&](bool strict) {
        std::vector<double> w;
        w.reserve(cand.size());
        for (std::size_t i : cand) {
            const BossPatternData& p = *patterns_[i];
            double weight = p.weight;
            if (strict) {
                if (patternCooldown_[i] > kEps) weight = 0.0;
                if (p.maxRepeat > 0 && static_cast<int>(i) == lastPattern_ && repeatCount_ >= p.maxRepeat) weight = 0.0;
            }
            if (p.ignoreIfBehind && !inFront) weight = 0.0;
            if (weight > 0.0 && inFront) {
                const SkillData* sk = db_->FindSkill(p.skillId);
                if (sk != nullptr && dist <= sk->range) weight *= p.playerNearWeightMult;
            }
            w.push_back(weight);
        }
        return w;
    };
    int pick = PickWeighted(weightsFor(true), rng_);
    if (pick < 0) pick = PickWeighted(weightsFor(false), rng_);
    if (pick < 0) pick = 0;
    const std::size_t idx = cand[static_cast<std::size_t>(pick)];
    const BossPatternData& p = *patterns_[idx];
    const SkillData* sk = db_->FindSkill(p.skillId);

    if (static_cast<int>(idx) == lastPattern_) ++repeatCount_;
    else repeatCount_ = 1;
    lastPattern_ = static_cast<int>(idx);
    patternCooldown_[idx] = p.cooldown;
    current_ = &p;
    state_ = BossState::Telegraph;
    timer_ = p.telegraphSeconds > 0.0 ? p.telegraphSeconds : (sk != nullptr ? sk->windup : 0.0);
    impactSeconds_ = sk != nullptr ? sk->impact : 0.0;
    recoverySeconds_ = p.recoverySeconds > 0.0 ? p.recoverySeconds : (sk != nullptr ? sk->recovery : 0.0);

    BossEvent ev;
    ev.kind = BossEvent::Kind::PatternStart;
    ev.phase = phase_;
    ev.patternId = p.id;
    ev.skillId = p.skillId;
    ev.seconds = timer_;
    out.push_back(ev);
}

void BossFight::Step(double dt, const Context& ctx, StatBlock& stats, std::vector<BossEvent>& out) {
    if (state_ == BossState::Idle || state_ == BossState::Dead || !(dt > 0.0)) return;

    if (shieldDown_ > 0.0) {
        shieldDown_ -= dt;
        if (shieldDown_ < kEps) {
            shieldDown_ = 0.0;
            BossEvent ev;
            ev.kind = BossEvent::Kind::ShieldUp;
            ev.phase = phase_;
            out.push_back(ev);
        }
    }
    for (double& c : patternCooldown_) c = c > dt ? c - dt : 0.0;

    if (status_.Tick(dt, stats)) {
        BossEvent ev;
        ev.kind = BossEvent::Kind::StaggerEnd;
        ev.phase = phase_;
        out.push_back(ev);
        if (state_ == BossState::Stagger) BeginWaiting(false);
    }

    if (faceSnap_ || state_ == BossState::Waiting || state_ == BossState::Recovery) Rotate(dt, ctx);

    switch (state_) {
        case BossState::Waiting:
            if (pendingTransition_) {
                StartTransition(out);
                break;
            }
            timer_ -= dt;
            if (timer_ <= kEps) PickAndStart(ctx, out);
            break;
        case BossState::Telegraph:
            timer_ -= dt;
            if (timer_ <= kEps) {
                state_ = BossState::Impact;
                timer_ = impactSeconds_;
                BossEvent ev;
                ev.kind = BossEvent::Kind::PatternImpact;
                ev.phase = phase_;
                ev.patternId = current_ != nullptr ? current_->id : ContentId();
                ev.skillId = current_ != nullptr ? current_->skillId : ContentId();
                ev.seconds = impactSeconds_;
                out.push_back(ev);
            }
            break;
        case BossState::Impact:
            timer_ -= dt;
            if (timer_ <= kEps) {
                state_ = BossState::Recovery;
                timer_ = recoverySeconds_;
            }
            break;
        case BossState::Recovery:
            timer_ -= dt;
            if (timer_ <= kEps) {
                BossEvent ev;
                ev.kind = BossEvent::Kind::PatternEnd;
                ev.phase = phase_;
                ev.patternId = current_ != nullptr ? current_->id : ContentId();
                out.push_back(ev);
                current_ = nullptr;
                if (pendingTransition_) StartTransition(out);
                else BeginWaiting(false);
            }
            break;
        case BossState::Transition: {
            timer_ -= dt;
            const double elapsed = transitionLength_ - timer_;
            if (summonMarked_ && !summonDone_ && elapsed + kEps >= transitionLength_ * summonAtFraction_) {
                summonDone_ = true;
                BossEvent ev;
                ev.kind = BossEvent::Kind::SummonSpawn;
                ev.phase = phase_;
                ev.enemyId = summonEnemy_;
                ev.count = summonCount_;
                out.push_back(ev);
            }
            if (timer_ <= kEps) {
                BossEvent ev;
                ev.kind = BossEvent::Kind::PhaseTransitionEnd;
                ev.phase = phase_;
                out.push_back(ev);
                BeginWaiting(false);
            }
            break;
        }
        case BossState::Stagger:
        case BossState::Idle:
        case BossState::Dead:
            break;
    }
}

BossFight::DamageResult BossFight::ApplyDamage(double amount, Vec2 bossPos, Vec2 origin, std::vector<BossEvent>& out) {
    DamageResult r;
    r.lifeAfter = life_;
    if (state_ == BossState::Dead || state_ == BossState::Idle) return r;
    if (state_ == BossState::Transition) {
        r.invulnerable = true;
        return r;
    }
    if (!(amount > 0.0)) return r;
    if (ShieldCovers(bossPos, origin)) {
        r.shieldBlocked = true;
        return r;
    }
    double applied = std::min(amount, life_);
    const BossPhaseData* next = PhaseData(phase_ + 1);
    if (next != nullptr) {
        const double floorLife = PhaseThresholdLife(phase_ + 1);
        if (life_ - applied <= floorLife + kEps) {
            applied = ClampMin0(life_ - floorLife);
            r.clampedByPhase = true;
            pendingTransition_ = true;
        }
    }
    life_ -= applied;
    r.applied = applied;
    if (next == nullptr && life_ <= kEps) {
        life_ = 0.0;
        state_ = BossState::Dead;
        r.killed = true;
        BossEvent ev;
        ev.kind = BossEvent::Kind::Died;
        ev.phase = phase_;
        out.push_back(ev);
    } else if (pendingTransition_ && state_ == BossState::Waiting) {
        StartTransition(out);  // parado entre ações: o rugido começa agora; no meio de um golpe, ao fim dele
    }
    r.lifeAfter = life_;
    return r;
}

StatusApply BossFight::ApplyEffect(const ContentDB& db, const EffectData& effect, std::string_view source,
                                   double magnitude, EffectContainer& fx, StatBlock& stats,
                                   std::vector<BossEvent>& out) {
    const bool allow = state_ == BossState::Waiting || state_ == BossState::Telegraph || state_ == BossState::Impact ||
                       state_ == BossState::Recovery;
    StatusApply r = status_.ApplyEffect(db, effect, source, magnitude, TriggerKind::None, fx, stats, allow);
    if (r.staggered) EnterStagger(r.staggerSeconds, out);
    return r;
}

void BossFight::EnterStagger(double seconds, std::vector<BossEvent>& out) {
    if (state_ == BossState::Telegraph || state_ == BossState::Impact || state_ == BossState::Recovery) {
        BossEvent ev;
        ev.kind = BossEvent::Kind::PatternInterrupted;
        ev.phase = phase_;
        ev.patternId = current_ != nullptr ? current_->id : ContentId();
        out.push_back(ev);
    }
    current_ = nullptr;
    state_ = BossState::Stagger;
    BossEvent st;
    st.kind = BossEvent::Kind::StaggerStart;
    st.phase = phase_;
    st.seconds = seconds;
    out.push_back(st);
    const BossPhaseData* ph = PhaseData(phase_);
    shieldDown_ = ph != nullptr && ph->shieldSeconds > 0.0 ? ph->shieldSeconds : db_->Rules().bossShieldDownSeconds;
    BossEvent sd;
    sd.kind = BossEvent::Kind::ShieldDown;
    sd.phase = phase_;
    sd.seconds = shieldDown_;
    out.push_back(sd);
}

bool BossFight::OnWallHit(StatBlock& stats, std::vector<BossEvent>& out) {
    if (state_ != BossState::Impact || current_ == nullptr) return false;
    const SkillData* sk = db_->FindSkill(current_->skillId);
    if (sk == nullptr || !(sk->wallStaggerSeconds > 0.0)) return false;
    if (!status_.BeginStagger(*db_, sk->wallStaggerSeconds, stats)) return false;
    EnterStagger(sk->wallStaggerSeconds, out);
    return true;
}

// ===============================================================================================
// Drop do Único
// ===============================================================================================
LootDrop RollBossLoot(const ContentDB& db, const EnemyData& boss, int areaLevel, BossProgressEntry& progress,
                      std::uint64_t* nextItemUid, Pcg32& lootRng) {
    const LootTableData* table = db.FindLootTable(boss.lootTableId);
    if (table == nullptr) {
        ++progress.kills;
        ++progress.killsSinceUnique;
        return LootDrop();
    }
    LootContext ctx;
    ctx.mode = LootMode::Manual;
    ctx.areaLevel = areaLevel;
    ctx.nextItemUid = nextItemUid;
    ctx.bossProgress = &progress;
    return RollLootTable(db, *table, ctx, lootRng);
}

}  // namespace shatter
