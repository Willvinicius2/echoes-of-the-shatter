// ShatterCore — efeitos temporários (queimadura, lentidão, marca, barreira, quebra de guarda).
// Um EffectData é dado de conteúdo; um ActiveEffect é a instância numa entidade.
// O EffectContainer avança no tempo em passos fixos (Tick) e devolve eventos
// (dano de DoT, expiração) para o chamador aplicar — mesma lógica no UE e no idle.
#pragma once

#include <array>
#include <cstdint>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "shatter/constants.h"
#include "shatter/stats.h"
#include "shatter/types.h"

namespace shatter {

enum class StackRule : std::uint8_t {
    Refresh = 0,        // reaplicar renova a duração; 1 instância
    StackN = 1,         // até maxStacks instâncias independentes; acima disso substitui a mais antiga
    StrongestOnly = 2,  // só a mais forte (maior magnitude) fica ativa; empate renova a duração
};
bool ParseStackRule(std::string_view text, StackRule& out);  // "refresh" | "stack_n" | "strongest_only"

// Quando o efeito dispara sozinho (efeitos "ao X").
enum class TriggerKind : std::uint8_t {
    None = 0,     // aplicado direto por habilidade/golpe
    OnHit,
    OnCrit,
    OnBlock,
    OnKill,
    OnTakeDamage,
};

struct EffectData {
    ContentId id;                         // "effect.burn", "effect.chill", "effect.glass_barrier"
    double duration = 0.0;                // s; 0 = instantâneo
    double tickInterval = 0.0;            // s; 0 = sem tick
    StackRule stackRule = StackRule::Refresh;
    int maxStacks = 1;                    // usado só por StackN
    // Dano por tick (DoT), por tipo; escalado por magnitude da aplicação.
    std::array<double, kDamageTypeCount> damagePerTick{};
    // Mods enquanto ativo (lentidão = MoveSpeed More -0.3; Postura Firme = DamageTaken More -0.3...).
    // value é multiplicado pela magnitude da aplicação.
    std::vector<Modifier> modifiers;
    double barrier = 0.0;                 // barreira concedida ao aplicar (× magnitude)
    TriggerKind trigger = TriggerKind::None;
    double triggerChance = 1.0;           // chance ao disparar (consome RNG de combate)
    // Recarga interna. O valor efetivo é max(internalCooldown, RulesConstants::triggerInternalCooldown) = mín. 0,25 s.
    double internalCooldown = 0.0;
    TagMask tags = 0;                     // tags do dano do efeito (Fire para queimadura...)
};

// Instância ativa.
struct ActiveEffect {
    ContentId effectId;
    ContentId sourceEntity;   // quem aplicou (para StrongestOnly e créditos)
    double magnitude = 1.0;   // multiplicador sobre os valores de EffectData
    double remaining = 0.0;   // s
    double tickAccumulator = 0.0;
    std::uint32_t applyOrder = 0;  // ordem de aplicação (desempate determinístico)
};

// Eventos gerados num Tick, em ordem determinística (ordem de aplicação).
struct EffectEvent {
    enum class Kind : std::uint8_t { DamageTick, Expired } kind = Kind::DamageTick;
    ContentId effectId;
    std::array<double, kDamageTypeCount> damage{};  // só DamageTick; dano bruto (o chamador passa por ResolveHit com isDamageOverTime)
};

// Contêiner de efeitos de UMA entidade.
// Regras invariantes:
//  - um efeito disparado (trigger != None) NÃO pode disparar outro efeito do mesmo TriggerKind
//    na mesma cadeia (o chamador passa `triggeredBy` em Apply);
//  - recarga interna mínima de 0,25 s por (efeito, entidade);
//  - mods ativos são escritos no StatBlock com source = "fx:" + effectId e removidos ao expirar.
class EffectContainer {
public:
    // Aplica um efeito. Devolve false se bloqueado por recarga interna ou regra de cadeia.
    // `triggeredBy`: TriggerKind que causou esta aplicação (None se aplicação direta).
    bool Apply(const EffectData& data, std::string_view sourceEntity, double magnitude,
               TriggerKind triggeredBy, StatBlock& target, const RulesConstants& rules);

    // Avança dt segundos (sempre o passo fixo). Ordem: ticks de dano → expiração → recargas.
    void Tick(double dt, const std::unordered_map<ContentId, const EffectData*>& lookup,
              StatBlock& target, std::vector<EffectEvent>& outEvents);

    bool Has(std::string_view effectId) const;
    int StackCount(std::string_view effectId) const;
    const std::vector<ActiveEffect>& Active() const { return active_; }
    void Clear(StatBlock& target);

private:
    std::vector<ActiveEffect> active_;
    std::unordered_map<ContentId, double> internalCooldowns_;  // effectId → s restantes
    std::uint32_t nextApplyOrder_ = 0;
};

// Recarga efetiva de habilidade: max(minCooldown, base / CooldownRecovery).
inline double EffectiveCooldown(double baseCooldown, double cooldownRecovery, const RulesConstants& rules) {
    const double rec = cooldownRecovery > 0.0 ? cooldownRecovery : 1.0;
    const double cd = baseCooldown / rec;
    return cd < rules.minCooldown ? rules.minCooldown : cd;
}

}  // namespace shatter
