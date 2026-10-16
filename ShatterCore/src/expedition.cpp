// ShatterCore — simulador de expedição idle (docs/00 seção 7 e 10, docs/04 seção 12).
// Encontro a encontro, passo fixo de RulesConstants::simStep, com ResolveHit, EffectContainer,
// BuildStatBlock e RollLootTable do jogo em tempo real. Cada encontro i usa fluxos próprios
// Pcg32::ForStream(seed, Combat|Loot|Events, i); o estado que cruza encontros é ExpeditionProgress.
// Só + - * / e sqrt em caminhos que afetam o resultado (sem pow/exp/log/sin).
#include "shatter/expedition.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>

#include "shatter/damage.h"
#include "shatter/effects.h"

namespace shatter {

namespace {

constexpr double kEps = 1e-9;

double Clamp01(double v) { return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v); }

void AddStack(std::vector<StackEntry>& stacks, const ContentId& id, std::int64_t amount) {
    for (StackEntry& s : stacks) {
        if (s.id == id) {
            s.amount += amount;
            return;
        }
    }
    stacks.push_back({id, amount});
}

// ---------------------------------------------------------------------------
// Preparação (uma vez por chamada de SimulateRange)
// ---------------------------------------------------------------------------
struct Setup {
    const ContentDB* db = nullptr;
    const ExpeditionRequest* req = nullptr;
    const ClassData* cls = nullptr;
    const MapData* map = nullptr;
    StatBlock playerStats;
    std::vector<const SkillData*> bar;      // habilidades da barra (posições não vazias, em ordem)
    std::vector<int> ranks;                 // rank de cada uma (1..3)
    std::array<double, kDamageTypeCount> weaponDamage{};
    std::vector<const EffectData*> triggerEffects;  // ruleEffect dos Únicos equipados com gatilho
    std::vector<const EncounterTemplate*> encounters;
    std::vector<double> encounterWeights;
    double limit = 0.0;
    std::int64_t startPotions = 0;
};

StopReason BuildSetup(const ContentDB& db, const ExpeditionRequest& req, Setup& su) {
    su.db = &db;
    su.req = &req;
    const CharacterState& ch = req.snapshot.character;
    su.cls = db.FindClass(ch.classId);
    su.map = db.FindMap(req.mapId);
    if (su.cls == nullptr || su.map == nullptr) return StopReason::ContentMismatch;
    if (!BuildStatBlock(db, ch, su.playerStats, nullptr)) return StopReason::ContentMismatch;
    if (!IsIdleCompatible(db, ch, nullptr)) return StopReason::IncompatibleBuild;

    for (const ContentId& id : ch.skillBar) {
        if (id.empty()) continue;
        const SkillData* s = db.FindSkill(id);
        if (s == nullptr) return StopReason::ContentMismatch;
        int rank = 1;
        for (const LearnedSkill& ls : ch.skills) {
            if (ls.skillId == id) rank = ls.rank < 1 ? 1 : (ls.rank > 3 ? 3 : ls.rank);
        }
        su.bar.push_back(s);
        su.ranks.push_back(rank);
    }
    const auto& mh = ch.equipment[static_cast<std::size_t>(ItemSlot::MainHand)];
    if (mh) {
        if (const ItemBaseData* b = db.FindItemBase(mh->baseId)) su.weaponDamage = b->weaponDamage;
    }
    for (const auto& item : ch.equipment) {
        if (!item || item->uniqueId.empty()) continue;
        const UniqueData* u = db.FindUnique(item->uniqueId);
        if (u == nullptr || u->ruleEffectId.empty()) continue;
        const EffectData* e = db.FindEffect(u->ruleEffectId);
        if (e != nullptr && e->trigger != TriggerKind::None) su.triggerEffects.push_back(e);
    }
    // Rotação de encontros: só os encontros comuns do mapa. O encontro de chefe (bossEncounter)
    // não entra na patrulha (decisão: chefes exigem reação; ver docs/09_mudancas_contrato.md).
    for (const ContentId& id : su.map->encounters) {
        const EncounterTemplate* e = db.FindEncounter(id);
        if (e == nullptr) return StopReason::ContentMismatch;
        // Todo encontro precisa gerar ao menos um inimigo existente (senão duraria 0 s e nunca terminaria).
        bool spawns = false;
        for (const EncounterGroup& g : e->groups) spawns = spawns || (g.countMin >= 1 && db.FindEnemy(g.enemyId) != nullptr);
        if (!spawns) return StopReason::ContentMismatch;
        su.encounters.push_back(e);
        su.encounterWeights.push_back(e->weight);
    }
    if (su.encounters.empty() || su.bar.empty()) return StopReason::IncompatibleBuild;

    const RulesConstants& r = db.Rules();
    double lim = req.effectiveSeconds;
    lim = std::min(lim, static_cast<double>(req.durationHours) * 3600.0);
    lim = std::min(lim, r.maxOfflineHours * 3600.0);
    su.limit = lim < 0.0 ? 0.0 : lim;
    su.startPotions = ch.potions;
    return StopReason::None;
}

// ---------------------------------------------------------------------------
// Simulação de UM encontro
// ---------------------------------------------------------------------------
struct EnemyInst {
    const EnemyData* data = nullptr;
    bool elite = false;
    bool alive = true;
    StatBlock stats;
    EffectContainer fx;
    double life = 0.0;
    double attackTimer = 0.0;
};

struct CarryState {  // o que atravessa encontros (espelho de ExpeditionProgress)
    double life = -1.0;
    double resource = -1.0;
    double barrier = 0.0;
    std::int64_t potions = -1;
    int raresDropped = 0;
};

struct EncounterRun {
    EncounterReceipt receipt;
    CarryState after;
    bool fits = true;
    bool stopRetreat = false;
};

void MergeLoot(LootDrop& into, LootDrop&& from) {
    for (ItemInstance& it : from.items) into.items.push_back(std::move(it));
    for (const StackEntry& s : from.stacks) AddStack(into.stacks, s.id, s.amount);
    into.raresDropped += from.raresDropped;
}

class EncounterSim {
public:
    EncounterSim(const Setup& su, std::uint32_t index, const CarryState& in, double startTime, double budget,
                 DamageArray* takenByType)
        : su_(su), db_(*su.db), rules_(su.db->Rules()), index_(index), in_(in), startTime_(startTime),
          budget_(budget), takenByType_(takenByType),
          combat_(Pcg32::ForStream(su.req->seed, RngStream::Combat, index)),
          loot_(Pcg32::ForStream(su.req->seed, RngStream::Loot, index)),
          events_(Pcg32::ForStream(su.req->seed, RngStream::Events, index)) {}

    EncounterRun Run() {
        EncounterRun out;
        EncounterReceipt& rc = out.receipt;
        rc.index = index_;
        rc.startTime = startTime_;
        {
            const double band = rules_.vigorBandHours * 3600.0;
            int b = band > 0.0 ? static_cast<int>(std::floor(startTime_ / band)) : 0;
            rc.vigorBand = static_cast<std::uint8_t>(b < 0 ? 0 : (b > 2 ? 2 : b));
        }

        // Escolha do encontro e composição dos grupos (fluxo Events).
        const int pick = PickWeighted(su_.encounterWeights, events_);
        const EncounterTemplate& tmpl = *su_.encounters[static_cast<std::size_t>(pick < 0 ? 0 : pick)];
        rc.templateId = tmpl.id;
        level_ = su_.map->monsterLevel;
        for (const EncounterGroup& g : tmpl.groups) {
            const EnemyData* ed = db_.FindEnemy(g.enemyId);
            if (ed == nullptr) continue;
            const int n = events_.RangeInt(g.countMin, g.countMax);
            for (int k = 0; k < n; ++k) {
                EnemyInst e;
                e.data = ed;
                e.elite = events_.Chance(g.eliteChance) || ed->isElite;
                BuildEnemyStatBlock(*ed, level_, e.stats);
                e.life = e.stats.Get(StatId::Life);
                enemies_.push_back(std::move(e));
            }
        }
        isBossEncounter_ = tmpl.isBoss;

        // Jogador.
        ps_ = su_.playerStats;
        double maxLife = ps_.Get(StatId::Life);
        double maxRes = ps_.Get(StatId::Resource);
        life_ = in_.life < 0.0 ? maxLife : std::min(in_.life, maxLife);
        resource_ = in_.resource < 0.0 ? maxRes : std::min(in_.resource, maxRes);
        barrier_ = in_.barrier;
        potions_ = in_.potions < 0 ? su_.startPotions : in_.potions;

        // Travessia até o grupo: regeneração e decaimento fora de combate.
        const double travel = tmpl.travelTime;
        if (travel > budget_ + kEps) { out.fits = false; return out; }
        life_ = std::min(maxLife, life_ + ps_.Get(StatId::LifeRegen) * travel);
        resource_ += ps_.Get(StatId::ResourceRegen) * travel;
        resource_ -= su_.cls->resourceDecayOutOfCombat * travel;
        resource_ = std::max(0.0, std::min(maxRes, resource_));

        const bool fast = rules_.useFastStepNonBoss && !isBossEncounter_;
        const double dt = fast ? rules_.simStepFastNonBoss : rules_.simStep;
        cooldowns_.assign(su_.bar.size(), 0.0);
        playerTimer_ = su_.bar[0]->idle.approachTime;
        activeSlot_ = 0;

        double combatTime = 0.0;
        bool retreated = false;
        while (aliveCount() > 0) {
            combatTime += dt;
            if (travel + combatTime > budget_ + kEps) { out.fits = false; return out; }
            Step(dt);
            maxLife = ps_.Get(StatId::Life);
            maxRes = ps_.Get(StatId::Resource);
            if (life_ > maxLife) life_ = maxLife;
            if (resource_ > maxRes) resource_ = maxRes;
            if (life_ <= 0.0 || (life_ < rules_.retreatLifeFraction * maxLife && potions_ <= 0)) {
                retreated = true;
                break;
            }
        }
        if (life_ < 0.0) life_ = 0.0;

        rc.duration = travel + combatTime;
        rc.kills = kills_;
        rc.elitesKilled = elites_;
        rc.potionsUsed = potionsUsed_;
        rc.healFailures = healFailures_;
        rc.damageTaken = damageTaken_;
        rc.damageDealt = damageDealt_;
        rc.lifeFractionAtEnd = maxLife > 0.0 ? life_ / maxLife : 0.0;
        if (retreated) {
            // "O loot já obtido nunca é perdido" (plano, seção 7): ficam o XP e o loot dos inimigos mortos
            // antes do recuo; só o loot de área (prêmio por concluir o encontro) não sai.
            rc.outcome = EncounterOutcome::Retreated;
            rc.xpRaw = xp_;
            rc.loot = std::move(drop_);
            out.stopRetreat = true;
        } else {
            rc.outcome = EncounterOutcome::Cleared;
            rc.xpRaw = xp_;
            if (su_.map && !su_.map->areaLootTable.empty()) {
                if (const LootTableData* t = db_.FindLootTable(su_.map->areaLootTable)) RollInto(*t);
            }
            rc.loot = std::move(drop_);
            out.stopRetreat = life_ < rules_.retreatLifeFraction * maxLife && potions_ <= 0;
        }
        out.after.life = life_;
        out.after.resource = resource_;
        out.after.barrier = barrier_;
        out.after.potions = potions_;
        out.after.raresDropped = in_.raresDropped + rc.loot.raresDropped;
        return out;
    }

private:
    int aliveCount() const {
        int n = 0;
        for (const EnemyInst& e : enemies_) n += e.alive ? 1 : 0;
        return n;
    }

    void RollInto(const LootTableData& table) {
        LootContext ctx;
        ctx.mode = LootMode::Idle;
        ctx.areaLevel = level_;
        ctx.quantityMult = 1.0;
        ctx.raresAlreadyDropped = in_.raresDropped + drop_.raresDropped;
        ctx.maxRares = rules_.maxRaresPerExpedition;
        ctx.nextItemUid = nullptr;
        MergeLoot(drop_, RollLootTable(db_, table, ctx, loot_));
    }

    void ApplyPlayerHit(const HitResult& r) {
        life_ = r.defenderLifeAfter;
        barrier_ = r.defenderBarrierAfter;
        damageTaken_ += r.totalDamage;
        if (takenByType_) {
            for (int t = 0; t < kDamageTypeCount; ++t)
                (*takenByType_)[static_cast<std::size_t>(t)] += r.afterMitigation[static_cast<std::size_t>(t)];
        }
    }

    void FireTrigger(TriggerKind kind) {
        for (const EffectData* e : su_.triggerEffects) {
            if (e->trigger != kind) continue;
            if (!combat_.Chance(e->triggerChance)) continue;
            if (pfx_.Apply(*e, "unique", 1.0, TriggerKind::None, ps_, rules_)) barrier_ += e->barrier;
        }
    }

    void KillEnemy(std::size_t i) {
        EnemyInst& e = enemies_[i];
        if (!e.alive) return;
        e.alive = false;
        ++kills_;
        if (e.elite) ++elites_;
        xp_ += e.data->xpBase + e.data->xpPerLevel * static_cast<double>(level_ - 1);
        if (!e.data->lootTableId.empty()) {
            if (const LootTableData* t = db_.FindLootTable(e.data->lootTableId)) RollInto(*t);
        }
        FireTrigger(TriggerKind::OnKill);
    }

    std::size_t FirstAlive() const {
        for (std::size_t i = 0; i < enemies_.size(); ++i)
            if (enemies_[i].alive) return i;
        return 0;
    }

    int FindSlot(const ContentId& id) const {
        for (std::size_t i = 0; i < su_.bar.size(); ++i)
            if (su_.bar[i]->id == id) return static_cast<int>(i);
        return -1;
    }

    bool CanUse(int slot) const {
        const std::size_t s = static_cast<std::size_t>(slot);
        return cooldowns_[s] <= kEps && resource_ + kEps >= su_.bar[s]->cost;
    }

    bool ConditionHolds(const AiRule& r) const {
        const double maxLife = ps_.Get(StatId::Life);
        const double maxRes = ps_.Get(StatId::Resource);
        switch (r.condition) {
            case AiCondition::Always: return true;
            case AiCondition::LifeBelow: return maxLife > 0.0 && life_ / maxLife < r.param;
            case AiCondition::ResourceAbove: return maxRes > 0.0 && resource_ / maxRes > r.param;
            case AiCondition::ResourceBelow: return maxRes > 0.0 && resource_ / maxRes < r.param;
            case AiCondition::EnemiesAtLeast: return static_cast<double>(aliveCount()) >= r.param;
            case AiCondition::TargetIsElite: return enemies_[FirstAlive()].elite;
            case AiCondition::TargetIsBoss: return isBossEncounter_ || enemies_[FirstAlive()].data->isBoss;
            case AiCondition::EffectMissing: return !pfx_.Has(r.refId);
        }
        return false;
    }

    void UseSkill(int slot, double dt) {
        const SkillData& s = *su_.bar[static_cast<std::size_t>(slot)];
        const IdleProfile& prof = s.idle;
        const int rank = su_.ranks[static_cast<std::size_t>(slot)];
        activeSlot_ = slot;

        double speed = ps_.Get(HasTag(s.tags, Tag::Spell) ? StatId::CastSpeed : StatId::AttackSpeed);
        if (speed < 0.01) speed = 0.01;
        double d = (s.windup + s.impact + s.recovery) / speed;
        const double uptime = prof.uptime > 0.0 ? prof.uptime : 1.0;
        d /= uptime;
        if (d < dt) d = dt;
        playerTimer_ += d;

        resource_ -= s.cost;
        if (resource_ < 0.0) resource_ = 0.0;
        cooldowns_[static_cast<std::size_t>(slot)] =
            s.cooldown > 0.0 ? EffectiveCooldown(s.cooldown, ps_.Get(StatId::CooldownRecovery), rules_) : 0.0;

        for (const ContentId& id : s.selfEffects) {
            const EffectData* e = db_.FindEffect(id);
            if (e != nullptr && pfx_.Apply(*e, "player", 1.0, TriggerKind::None, ps_, rules_)) barrier_ += e->barrier;
        }

        // Alvos atingidos: média do perfil, realizada por acumulador (sem RNG).
        const int alive = aliveCount();
        double expected = prof.fractionOfGroupHit > 0.0 ? prof.fractionOfGroupHit * static_cast<double>(alive)
                                                        : prof.avgTargetsHit;
        if (expected > static_cast<double>(alive)) expected = static_cast<double>(alive);
        targetAcc_ += expected;
        int n = static_cast<int>(std::floor(targetAcc_ + kEps));
        targetAcc_ -= static_cast<double>(n);
        if (n < 1) n = 1;
        if (n > alive) n = alive;

        DamageArray base = s.scalesWithWeapon ? su_.weaponDamage : s.baseDamage;
        const double coef = s.coefficientByRank[static_cast<std::size_t>(rank - 1)];
        const double maxRes = ps_.Get(StatId::Resource);

        int hit = 0;
        for (std::size_t i = 0; i < enemies_.size() && hit < n; ++i) {
            EnemyInst& e = enemies_[i];
            if (!e.alive) continue;
            ++hit;
            HitInput in;
            in.attacker = &ps_;
            in.defender = &e.stats;
            in.skillTags = s.tags;
            in.baseDamage = base;
            in.coefficient = coef;
            in.defenderLife = e.life;
            in.defenderBarrier = 0.0;
            const HitResult r = ResolveHit(in, rules_, combat_);
            e.life = r.defenderLifeAfter;
            damageDealt_ += r.totalDamage;
            if (r.landed) {
                resource_ = std::min(maxRes, resource_ + su_.cls->resourceOnHit);
                for (const ContentId& id : s.onHitEffects) {
                    const EffectData* fx = db_.FindEffect(id);
                    if (fx != nullptr) e.fx.Apply(*fx, "player", 1.0, TriggerKind::None, e.stats, rules_);
                }
                FireTrigger(TriggerKind::OnHit);
                if (r.critical) FireTrigger(TriggerKind::OnCrit);
            }
            if (r.killed) KillEnemy(i);
        }
    }

    void PlayerAct(double dt) {
        const std::size_t maxRules = rules_.maxAiRules < 0 ? 0 : static_cast<std::size_t>(rules_.maxAiRules);
        const auto& rules = su_.req->rules;
        bool potionFailedThisStep = false;
        for (std::size_t i = 0; i < rules.size() && i < maxRules; ++i) {
            const AiRule& r = rules[i];
            if (!ConditionHolds(r)) continue;
            if (r.action == AiAction::UsePotion) {
                if (potions_ <= 0) {
                    potionFailedThisStep = true;
                    if (!potionFailing_) ++healFailures_;  // conta uma vez por episódio de falha
                    potionFailing_ = true;
                    continue;  // regra inválida: segue para a próxima
                }
                const double maxLife = ps_.Get(StatId::Life);
                life_ = std::min(maxLife, life_ + su_.req->potionHealFraction * maxLife * ps_.Get(StatId::PotionEffect));
                --potions_;
                ++potionsUsed_;
                playerTimer_ += dt;  // beber consome um passo
                potionFailing_ = false;
                return;
            }
            const int slot = FindSlot(r.refId);
            if (slot < 0 || !CanUse(slot)) continue;
            if (!potionFailedThisStep) potionFailing_ = false;
            UseSkill(slot, dt);
            return;
        }
        if (!potionFailedThisStep) potionFailing_ = false;
        if (CanUse(0)) {
            UseSkill(0, dt);
            return;
        }
        playerTimer_ = 0.0;  // sem ação possível neste passo
    }

    void EnemyAct(EnemyInst& e, double dt) {
        const EnemyData& ed = *e.data;
        std::vector<double> w;
        w.reserve(ed.attacks.size());
        for (const EnemyAttack& a : ed.attacks) w.push_back(a.weight);
        const int pick = PickWeighted(w, combat_);
        if (pick < 0) {
            e.attackTimer = 0.0;
            return;
        }
        const EnemyAttack& atk = ed.attacks[static_cast<std::size_t>(pick)];
        const SkillData* s = db_.FindSkill(atk.skillId);
        if (s == nullptr) return;
        double speed = e.stats.Get(StatId::AttackSpeed);
        if (speed < 0.01) speed = 0.01;
        double d = (s->windup + s->impact + s->recovery) / speed;
        if (d < dt) d = dt;
        e.attackTimer += d;

        const IdleProfile& prof = su_.bar[static_cast<std::size_t>(activeSlot_)]->idle;
        if (atk.telegraphed) {
            const double p = Clamp01(rules_.aiBaseDodgeTelegraphed + prof.dodgeTelegraphedBonus);
            if (combat_.Chance(p)) return;  // a IA esquivou
        }
        HitInput in;
        in.attacker = &e.stats;
        in.defender = &ps_;
        in.skillTags = s->tags;
        in.baseDamage = s->baseDamage;
        in.coefficient = s->coefficientByRank[0] * prof.damageTakenMult;
        in.defenderLife = life_;
        in.defenderBarrier = barrier_;
        const HitResult r = ResolveHit(in, rules_, combat_);
        ApplyPlayerHit(r);
        if (r.landed) {
            for (const ContentId& id : s->onHitEffects) {
                const EffectData* fx = db_.FindEffect(id);
                if (fx != nullptr) pfx_.Apply(*fx, "enemy", 1.0, TriggerKind::None, ps_, rules_);
            }
            FireTrigger(TriggerKind::OnTakeDamage);
        }
        if (r.outcome == HitOutcome::Blocked) {
            resource_ = std::min(ps_.Get(StatId::Resource), resource_ + su_.cls->resourceOnBlock);
            FireTrigger(TriggerKind::OnBlock);
        }
    }

    void Step(double dt) {
        const auto& lookup = db_.EffectLookup();
        // Regeneração.
        life_ = std::min(ps_.Get(StatId::Life), life_ + ps_.Get(StatId::LifeRegen) * dt);
        resource_ = std::min(ps_.Get(StatId::Resource), resource_ + ps_.Get(StatId::ResourceRegen) * dt);

        // Efeitos no jogador (DoT recebido).
        fxEvents_.clear();
        pfx_.Tick(dt, lookup, ps_, fxEvents_);
        for (const EffectEvent& ev : fxEvents_) {
            if (ev.kind != EffectEvent::Kind::DamageTick || enemies_.empty()) continue;
            const EffectData* ed = db_.FindEffect(ev.effectId);
            HitInput in;
            in.attacker = &enemies_[0].stats;  // fonte representativa (o DoT não guarda a origem)
            in.defender = &ps_;
            in.skillTags = ed ? ed->tags : 0;
            in.baseDamage = ev.damage;
            in.isDamageOverTime = true;
            in.defenderLife = life_;
            in.defenderBarrier = barrier_;
            ApplyPlayerHit(ResolveHit(in, rules_, combat_));
        }
        // Efeitos nos inimigos (DoT causado).
        for (std::size_t i = 0; i < enemies_.size(); ++i) {
            EnemyInst& e = enemies_[i];
            if (!e.alive) continue;
            fxEvents_.clear();
            e.fx.Tick(dt, lookup, e.stats, fxEvents_);
            for (const EffectEvent& ev : fxEvents_) {
                if (ev.kind != EffectEvent::Kind::DamageTick || !e.alive) continue;
                const EffectData* ed = db_.FindEffect(ev.effectId);
                HitInput in;
                in.attacker = &ps_;
                in.defender = &e.stats;
                in.skillTags = ed ? ed->tags : 0;
                in.baseDamage = ev.damage;
                in.isDamageOverTime = true;
                in.defenderLife = e.life;
                const HitResult r = ResolveHit(in, rules_, combat_);
                e.life = r.defenderLifeAfter;
                damageDealt_ += r.totalDamage;
                if (r.killed) KillEnemy(i);
            }
        }
        if (aliveCount() == 0) return;

        // Jogador.
        for (double& c : cooldowns_) c = c > dt ? c - dt : 0.0;
        playerTimer_ -= dt;
        if (playerTimer_ <= kEps) PlayerAct(dt);

        // Inimigos, em ordem.
        for (std::size_t i = 0; i < enemies_.size(); ++i) {
            EnemyInst& e = enemies_[i];
            if (!e.alive) continue;
            e.attackTimer -= dt;
            if (e.attackTimer <= kEps) EnemyAct(e, dt);
            if (life_ <= 0.0) break;
        }
    }

    const Setup& su_;
    const ContentDB& db_;
    const RulesConstants& rules_;
    std::uint32_t index_;
    CarryState in_;
    double startTime_;
    double budget_;
    DamageArray* takenByType_;
    Pcg32 combat_, loot_, events_;

    int level_ = 1;
    bool isBossEncounter_ = false;
    std::vector<EnemyInst> enemies_;
    StatBlock ps_;
    EffectContainer pfx_;
    std::vector<EffectEvent> fxEvents_;
    std::vector<double> cooldowns_;
    double playerTimer_ = 0.0;
    int activeSlot_ = 0;
    double targetAcc_ = 0.0;
    double life_ = 0.0, resource_ = 0.0, barrier_ = 0.0;
    std::int64_t potions_ = 0;
    bool potionFailing_ = false;

    int kills_ = 0, elites_ = 0, potionsUsed_ = 0, healFailures_ = 0;
    double damageTaken_ = 0.0, damageDealt_ = 0.0, xp_ = 0.0;
    LootDrop drop_;
};

// ---------------------------------------------------------------------------
// Execução em faixa
// ---------------------------------------------------------------------------
ExpeditionProgress RunRange(const ContentDB& db, const ExpeditionRequest& req, const ExpeditionProgress& start,
                            std::uint32_t firstEncounter, std::uint32_t count, DamageArray* takenByType) {
    ExpeditionProgress p = start;
    if (p.stop != StopReason::None) return p;
    if (firstEncounter != p.nextEncounter) {
        p.stop = StopReason::ContentMismatch;
        return p;
    }
    Setup su;
    const StopReason pre = BuildSetup(db, req, su);
    if (pre != StopReason::None) {
        p.stop = pre;
        return p;
    }
    for (std::uint32_t n = 0; n < count && p.stop == StopReason::None; ++n) {
        CarryState carry;
        carry.life = p.life;
        carry.resource = p.resource;
        carry.barrier = p.barrier;
        carry.potions = p.potionsLeft;
        carry.raresDropped = p.raresDropped;
        EncounterSim sim(su, p.nextEncounter, carry, p.elapsed, su.limit - p.elapsed, takenByType);
        EncounterRun run = sim.Run();
        if (!run.fits) {
            p.stop = StopReason::DurationReached;
            break;
        }
        p.elapsed += run.receipt.duration;
        p.life = run.after.life;
        p.resource = run.after.resource;
        p.barrier = run.after.barrier;
        p.potionsLeft = run.after.potions;
        p.raresDropped = run.after.raresDropped;
        p.receipts.push_back(std::move(run.receipt));
        ++p.nextEncounter;
        if (run.stopRetreat) p.stop = StopReason::Retreat;
    }
    return p;
}

// ---------------------------------------------------------------------------
// Hash canônico (independente de std::hash e de plataforma)
// ---------------------------------------------------------------------------
class Hasher {
public:
    void U64(std::uint64_t v) { h_ = Mix64(h_ ^ Mix64(v + 0x9E3779B97F4A7C15ull)); }
    void I64(std::int64_t v) { U64(static_cast<std::uint64_t>(v)); }
    void Dbl(double d) {
        if (d == 0.0) d = 0.0;  // normaliza -0
        std::uint64_t bits = 0;
        std::memcpy(&bits, &d, sizeof(bits));
        U64(bits);
    }
    void Str(const std::string& s) {
        std::uint64_t f = 0xCBF29CE484222325ull;  // FNV-1a
        for (const char c : s) {
            f ^= static_cast<std::uint8_t>(c);
            f *= 0x100000001B3ull;
        }
        U64(f);
        U64(s.size());
    }
    std::uint64_t Value() const { return h_ == 0 ? 1 : h_; }

private:
    std::uint64_t h_ = 0x6A09E667F3BCC908ull;
};

void HashItem(Hasher& h, const ItemInstance& it) {
    h.U64(it.uid);
    h.Str(it.baseId);
    h.U64(static_cast<std::uint64_t>(it.rarity));
    h.I64(it.itemLevel);
    h.Str(it.uniqueId);
    h.U64(it.affixes.size());
    for (const RolledAffix& a : it.affixes) {
        h.Str(a.affixId);
        h.Dbl(a.value);
    }
    h.U64(it.hasInscription ? 1 : 0);
}

}  // namespace

// ---------------------------------------------------------------------------
// API pública
// ---------------------------------------------------------------------------
StartCheck CanStartExpedition(const ContentDB& db, const CharacterState& c, const ContentId& mapId, int durationHours,
                              int chargesAvailable, bool anotherRunning, std::size_t ruleCount,
                              std::vector<ContentId>* blockingIds) {
    const RulesConstants& r = db.Rules();
    const MapData* map = db.FindMap(mapId);
    if (map == nullptr || db.FindClass(c.classId) == nullptr) return StartCheck::UnknownContent;
    if (durationHours < 1 || static_cast<double>(durationHours) < r.minExpeditionHours ||
        static_cast<double>(durationHours) > r.maxExpeditionHours)
        return StartCheck::InvalidDuration;
    if (ruleCount > static_cast<std::size_t>(r.maxAiRules < 0 ? 0 : r.maxAiRules)) return StartCheck::TooManyRules;
    if (anotherRunning) return StartCheck::AnotherExpeditionRunning;
    const bool conquered = std::find(c.conqueredMaps.begin(), c.conqueredMaps.end(), mapId) != c.conqueredMaps.end();
    // Endgame: só até 1 tier abaixo do maior tier vencido na mão.
    const bool tierOk = map->tier == 0 || map->tier <= c.highestTierCleared - 1;
    if (!map->idleAllowed || !conquered || !tierOk) return StartCheck::MapNotConquered;
    if (chargesAvailable < durationHours * r.chargesPerHour) return StartCheck::NotEnoughCharges;
    if (!IsIdleCompatible(db, c, blockingIds)) return StartCheck::IdleIncompatible;
    return StartCheck::Ok;
}

ExpeditionProgress SimulateRange(const ContentDB& db, const ExpeditionRequest& req, const ExpeditionProgress& start,
                                 std::uint32_t firstEncounter, std::uint32_t count) {
    return RunRange(db, req, start, firstEncounter, count, nullptr);
}

ExpeditionResult SimulateExpedition(const ContentDB& db, const ExpeditionRequest& req) {
    const ExpeditionProgress p =
        RunRange(db, req, ExpeditionProgress(), 0, std::numeric_limits<std::uint32_t>::max(), nullptr);
    return FinalizeExpedition(db, req, p);
}

void ApplyWindowStop(ExpeditionProgress& progress, const OfflineWindow& window) {
    if (window.endedByRollback && progress.stop == StopReason::DurationReached) progress.stop = StopReason::ClockRollback;
}

ExpeditionResult FinalizeExpedition(const ContentDB& db, const ExpeditionRequest& req,
                                    const ExpeditionProgress& progress) {
    const RulesConstants& rules = db.Rules();
    ExpeditionResult res;
    res.stop = progress.stop;
    res.effectiveSeconds = progress.elapsed;
    res.receipts = progress.receipts;
    res.raresDropped = 0;

    // Teto de nível: área + xpLevelCapAboveArea, limitado por maxLevel.
    const MapData* map = db.FindMap(req.mapId);
    int capLevel = rules.maxLevel;
    if (map != nullptr) capLevel = std::min(capLevel, map->monsterLevel + rules.xpLevelCapAboveArea);
    int level = req.snapshot.character.level;
    double xpIn = req.snapshot.character.xp;

    std::vector<double> stackSums;           // Vigor aplicado em double; arredondado para baixo no fim
    std::vector<ContentId> stackIds;

    for (const EncounterReceipt& rc : progress.receipts) {
        if (rc.outcome == EncounterOutcome::Cleared) ++res.encountersCleared;
        res.kills += rc.kills;
        res.potionsUsed += rc.potionsUsed;
        res.healFailures += rc.healFailures;
        res.raresDropped += rc.loot.raresDropped;
        const double vigor = rules.vigorByBand[rc.vigorBand < 3 ? rc.vigorBand : 2];

        for (const ItemInstance& it : rc.loot.items) res.items.push_back(it);  // itens não sofrem Vigor
        for (const StackEntry& s : rc.loot.stacks) {
            std::size_t k = 0;
            for (; k < stackIds.size(); ++k)
                if (stackIds[k] == s.id) break;
            if (k == stackIds.size()) {
                stackIds.push_back(s.id);
                stackSums.push_back(0.0);
            }
            stackSums[k] += static_cast<double>(s.amount) * vigor;
        }

        // XP: Vigor, depois teto de nível.
        double x = rc.xpRaw * vigor;
        if (level >= capLevel) {
            if (x > 0.0) res.xpCapped = true;
            continue;
        }
        while (x > 0.0) {
            const double need = db.XpToNextLevel(level) - xpIn;
            if (x + kEps >= need) {
                res.xpGained += need > 0.0 ? need : 0.0;
                x -= need;
                xpIn = 0.0;
                ++level;
                if (level >= capLevel) {
                    res.xpCapped = true;
                    break;
                }
            } else {
                res.xpGained += x;
                xpIn += x;
                x = 0.0;
            }
        }
    }
    for (std::size_t k = 0; k < stackIds.size(); ++k) {
        const std::int64_t amount = static_cast<std::int64_t>(std::floor(stackSums[k] + kEps));
        if (amount > 0) res.stacks.push_back({stackIds[k], amount});
    }

    // Dica (uma chave de localização; prioridade em expedition.h).
    const std::int64_t potionsLeft = progress.potionsLeft < 0 ? req.snapshot.character.potions : progress.potionsLeft;
    if (res.stop == StopReason::Retreat && potionsLeft > 0) res.tipKeys.push_back(kTipLowLife);
    else if (res.stop == StopReason::Retreat || res.healFailures > 0) res.tipKeys.push_back(kTipMorePotions);
    else res.tipKeys.push_back(kTipAllGood);

    // Hash canônico do resultado.
    Hasher h;
    h.U64(static_cast<std::uint64_t>(res.stop));
    h.Dbl(res.effectiveSeconds);
    h.I64(res.encountersCleared);
    h.I64(res.kills);
    h.I64(res.potionsUsed);
    h.I64(res.healFailures);
    h.Dbl(res.xpGained);
    h.U64(res.xpCapped ? 1 : 0);
    h.I64(res.raresDropped);
    h.U64(res.items.size());
    for (const ItemInstance& it : res.items) HashItem(h, it);
    h.U64(res.stacks.size());
    for (const StackEntry& s : res.stacks) {
        h.Str(s.id);
        h.I64(s.amount);
    }
    h.U64(res.receipts.size());
    for (const EncounterReceipt& rc : res.receipts) {
        h.U64(rc.index);
        h.Str(rc.templateId);
        h.U64(static_cast<std::uint64_t>(rc.outcome));
        h.Dbl(rc.startTime);
        h.Dbl(rc.duration);
        h.I64(rc.kills);
        h.I64(rc.elitesKilled);
        h.I64(rc.potionsUsed);
        h.I64(rc.healFailures);
        h.Dbl(rc.damageTaken);
        h.Dbl(rc.damageDealt);
        h.Dbl(rc.xpRaw);
        h.Dbl(rc.lifeFractionAtEnd);
        h.U64(rc.vigorBand);
        h.U64(rc.loot.items.size());
        for (const ItemInstance& it : rc.loot.items) HashItem(h, it);
        for (const StackEntry& s : rc.loot.stacks) {
            h.Str(s.id);
            h.I64(s.amount);
        }
        h.I64(rc.loot.raresDropped);
    }
    res.resultHash = h.Value();
    return res;
}

ExpeditionForecast ForecastExpedition(const ContentDB& db, const ExpeditionRequest& req, std::uint64_t baseSeed,
                                      int samples) {
    ExpeditionForecast f;
    if (samples < 1) return f;
    std::vector<double> xp, gold;
    xp.reserve(static_cast<std::size_t>(samples));
    gold.reserve(static_cast<std::size_t>(samples));
    DamageArray taken{};
    int retreats = 0;
    for (int k = 0; k < samples; ++k) {
        ExpeditionRequest r = req;
        r.seed = DeriveSeed(baseSeed, RngStream::Events, static_cast<std::uint64_t>(k));
        const ExpeditionProgress p =
            RunRange(db, r, ExpeditionProgress(), 0, std::numeric_limits<std::uint32_t>::max(), &taken);
        const ExpeditionResult res = FinalizeExpedition(db, r, p);
        xp.push_back(res.xpGained);
        double g = 0.0;
        for (const StackEntry& s : res.stacks)
            if (s.id == "currency.gold") g += static_cast<double>(s.amount);
        gold.push_back(g);
        if (res.stop == StopReason::Retreat) ++retreats;
    }
    std::sort(xp.begin(), xp.end());
    std::sort(gold.begin(), gold.end());
    // Faixa conservadora: p10 arredonda para baixo e p90 para cima (a faixa cobre >= 80% das amostras).
    const std::size_t n = xp.size();
    const std::size_t lo = static_cast<std::size_t>(std::floor(0.10 * static_cast<double>(n - 1)));
    const std::size_t mid = static_cast<std::size_t>(std::floor(0.50 * static_cast<double>(n - 1) + 0.5));
    const std::size_t hi = std::min(n - 1, static_cast<std::size_t>(std::ceil(0.90 * static_cast<double>(n - 1))));
    f.xpP10 = xp[lo]; f.xpP50 = xp[mid]; f.xpP90 = xp[hi];
    f.goldP10 = gold[lo]; f.goldP50 = gold[mid]; f.goldP90 = gold[hi];
    f.retreatProbability = static_cast<double>(retreats) / static_cast<double>(samples);
    int worst = 0;
    for (int t = 1; t < kDamageTypeCount; ++t)
        if (taken[static_cast<std::size_t>(t)] > taken[static_cast<std::size_t>(worst)]) worst = t;
    f.worstResistGap = static_cast<DamageType>(worst);
    return f;
}

}  // namespace shatter
