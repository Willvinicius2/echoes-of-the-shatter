// ShatterCore — efeitos temporários com acúmulo, DoT e recarga interna.
#include "shatter/effects.h"

#include <algorithm>

namespace shatter {

namespace {
constexpr double kTimeEps = 1e-9;  // tolerância para acúmulo de passos fixos (0,1 s não é exato em binário)

std::string FxSource(const ContentId& id) { return "fx:" + id; }
}  // namespace

bool ParseStackRule(std::string_view text, StackRule& out) {
    if (text == "refresh") { out = StackRule::Refresh; return true; }
    if (text == "stack_n") { out = StackRule::StackN; return true; }
    if (text == "strongest_only") { out = StackRule::StrongestOnly; return true; }
    return false;
}

namespace {

// Reescreve no StatBlock os mods de TODAS as instâncias ativas de um efeito, na ordem de aplicação.
// (várias instâncias compartilham a mesma source "fx:<id>"; reconstruir evita remover mods alheios.)
void RebuildMods(const std::vector<ActiveEffect>& active, const ContentId& effectId, const EffectData* data,
                 StatBlock& target) {
    const std::string src = FxSource(effectId);
    target.RemoveModifiersFrom(src);
    if (data == nullptr) return;
    // Efeito de defesa (tag guard): o dano recebido só cai quando o golpe vem de dentro do arco (damage.h, fromGuardArc).
    // Só os mods de DamageTaken ganham a exigência; a lentidão de andar com a guarda erguida vale sempre.
    const bool guard = HasTag(data->tags, Tag::Guard);
    for (const ActiveEffect& a : active) {
        if (a.effectId != effectId) continue;
        for (const Modifier& m : data->modifiers) {
            Modifier mod = m;
            mod.value = m.value * a.magnitude;
            if (guard && mod.stat == StatId::DamageTaken) mod.requiredTags |= Mask(Tag::Guard);
            mod.source = src;
            target.AddModifier(mod);
        }
    }
}

}  // namespace

bool EffectContainer::Apply(const EffectData& data, std::string_view sourceEntity, double magnitude,
                            TriggerKind triggeredBy, StatBlock& target, const RulesConstants& rules) {
    // Cadeia: um efeito disparado não pode ser disparado pelo mesmo tipo de gatilho.
    if (triggeredBy != TriggerKind::None && data.trigger == triggeredBy) return false;

    const bool gated = data.trigger != TriggerKind::None || triggeredBy != TriggerKind::None;
    if (gated) {
        for (const auto& cd : internalCooldowns_) {
            if (cd.first == data.id && cd.second > kTimeEps) return false;
        }
    }

    bool applied = true;
    if (data.duration > 0.0) {
        ActiveEffect* existing = nullptr;
        int count = 0;
        ActiveEffect* oldest = nullptr;
        for (ActiveEffect& a : active_) {
            if (a.effectId != data.id) continue;
            ++count;
            if (existing == nullptr) existing = &a;
            if (oldest == nullptr || a.applyOrder < oldest->applyOrder) oldest = &a;
        }
        ActiveEffect fresh;
        fresh.effectId = data.id;
        fresh.sourceEntity = std::string(sourceEntity);
        fresh.magnitude = magnitude;
        fresh.remaining = data.duration;
        fresh.tickAccumulator = 0.0;

        switch (data.stackRule) {
            case StackRule::Refresh:
                if (existing != nullptr) {
                    existing->magnitude = magnitude;
                    existing->remaining = data.duration;
                    existing->sourceEntity = fresh.sourceEntity;
                } else {
                    fresh.applyOrder = nextApplyOrder_++;
                    active_.push_back(fresh);
                }
                break;
            case StackRule::StackN: {
                const int maxStacks = data.maxStacks < 1 ? 1 : data.maxStacks;
                if (count >= maxStacks && oldest != nullptr) {
                    const std::uint32_t order = oldest->applyOrder;
                    active_.erase(std::remove_if(active_.begin(), active_.end(),
                                                 [&](const ActiveEffect& a) {
                                                     return a.effectId == data.id && a.applyOrder == order;
                                                 }),
                                  active_.end());
                }
                fresh.applyOrder = nextApplyOrder_++;
                active_.push_back(fresh);
                break;
            }
            case StackRule::StrongestOnly:
                if (existing == nullptr) {
                    fresh.applyOrder = nextApplyOrder_++;
                    active_.push_back(fresh);
                } else if (magnitude > existing->magnitude) {
                    existing->magnitude = magnitude;
                    existing->remaining = data.duration;
                    existing->sourceEntity = fresh.sourceEntity;
                } else if (magnitude == existing->magnitude) {
                    existing->remaining = data.duration;  // empate renova a duração
                } else {
                    applied = false;  // mais fraco que o ativo: ignorado
                }
                break;
        }
        if (applied) RebuildMods(active_, data.id, &data, target);
    }

    if (applied && gated) {
        const double icd = std::max(data.internalCooldown, rules.triggerInternalCooldown);
        bool found = false;
        for (auto& cd : internalCooldowns_) {
            if (cd.first == data.id) {
                cd.second = icd;
                found = true;
                break;
            }
        }
        if (!found) internalCooldowns_.emplace_back(data.id, icd);
    }
    return applied;
}

void EffectContainer::Tick(double dt, const std::unordered_map<ContentId, const EffectData*>& lookup,
                           StatBlock& target, std::vector<EffectEvent>& outEvents) {
    if (dt <= 0.0) return;
    // 1) ticks de dano (ordem de aplicação).
    for (ActiveEffect& a : active_) {
        const auto it = lookup.find(a.effectId);
        if (it == lookup.end() || it->second == nullptr) continue;
        const EffectData& d = *it->second;
        const double step = std::min(dt, a.remaining > 0.0 ? a.remaining : 0.0);
        a.remaining -= dt;
        if (d.tickInterval <= 0.0 || step <= 0.0) continue;
        a.tickAccumulator += step;
        while (a.tickAccumulator + kTimeEps >= d.tickInterval) {
            a.tickAccumulator -= d.tickInterval;
            EffectEvent ev;
            ev.kind = EffectEvent::Kind::DamageTick;
            ev.effectId = a.effectId;
            bool any = false;
            for (int t = 0; t < kDamageTypeCount; ++t) {
                const double v = d.damagePerTick[static_cast<std::size_t>(t)] * a.magnitude;
                ev.damage[static_cast<std::size_t>(t)] = v;
                any = any || v > 0.0;
            }
            if (any) outEvents.push_back(ev);
        }
    }
    // 2) expiração (efeitos desconhecidos no lookup também expiram).
    std::vector<ContentId> touched;
    for (auto it = active_.begin(); it != active_.end();) {
        const bool known = lookup.find(it->effectId) != lookup.end();
        if (!known || it->remaining <= kTimeEps) {
            EffectEvent ev;
            ev.kind = EffectEvent::Kind::Expired;
            ev.effectId = it->effectId;
            outEvents.push_back(ev);
            if (std::find(touched.begin(), touched.end(), it->effectId) == touched.end())
                touched.push_back(it->effectId);
            it = active_.erase(it);
        } else {
            ++it;
        }
    }
    for (const ContentId& id : touched) {
        const auto it = lookup.find(id);
        RebuildMods(active_, id, it != lookup.end() ? it->second : nullptr, target);
        if (it == lookup.end()) target.RemoveModifiersFrom(FxSource(id));
    }
    // 3) recargas internas (em ordem de inserção).
    for (auto& cd : internalCooldowns_) cd.second -= dt;
    internalCooldowns_.erase(std::remove_if(internalCooldowns_.begin(), internalCooldowns_.end(),
                                            [](const std::pair<ContentId, double>& cd) { return cd.second <= kTimeEps; }),
                             internalCooldowns_.end());
}

int EffectContainer::RefreshAll(std::string_view effectId, double duration) {
    int n = 0;
    for (ActiveEffect& a : active_) {
        if (a.effectId != effectId) continue;
        a.remaining = duration;
        ++n;
    }
    return n;
}

int EffectContainer::Remove(std::string_view effectId, const EffectData* data, StatBlock& target) {
    int n = 0;
    for (auto it = active_.begin(); it != active_.end();) {
        if (it->effectId == effectId) {
            it = active_.erase(it);
            ++n;
        } else {
            ++it;
        }
    }
    if (n > 0) RebuildMods(active_, ContentId(effectId), data, target);
    return n;
}

bool EffectContainer::Has(std::string_view effectId) const {
    for (const ActiveEffect& a : active_) {
        if (a.effectId == effectId) return true;
    }
    return false;
}

int EffectContainer::StackCount(std::string_view effectId) const {
    int n = 0;
    for (const ActiveEffect& a : active_) {
        if (a.effectId == effectId) ++n;
    }
    return n;
}

void EffectContainer::Clear(StatBlock& target) {
    for (const ActiveEffect& a : active_) target.RemoveModifiersFrom(FxSource(a.effectId));
    active_.clear();
    internalCooldowns_.clear();
}

}  // namespace shatter
