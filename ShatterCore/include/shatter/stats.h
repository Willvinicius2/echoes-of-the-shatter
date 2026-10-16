// ShatterCore — atributos e modificadores.
// Fórmula única para todo atributo:
//   valor = max(0, (base + Σflat) × (1 + Σincreased) × Π(1 + more))
// Increased e More são frações (0.20 = +20%; -0.30 = 30% "menos").
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "shatter/types.h"

namespace shatter {

// Lista fechada de atributos do motor. Adicionar = acrescentar no FIM (o índice
// não é salvo em disco; o save e os CSV usam o nome em texto, ver ToString/ParseStatId).
enum class StatId : std::uint16_t {
    Life = 0,          // vida máxima
    LifeRegen,         // vida por segundo
    Resource,          // recurso máximo (Ímpeto/Foco/Mana conforme a classe)
    ResourceRegen,     // recurso por segundo (regra de parado/andando fica na ClassData)
    Armor,             // reduz só dano físico (ver damage.h)
    EvasionChance,     // fração [0,1]; só contra ataques; teto em RulesConstants
    BlockChance,       // fração [0,1]; teto em RulesConstants
    ResistFire,        // fração; teto em RulesConstants (75%)
    ResistCold,
    ResistLightning,
    Damage,            // dano; SEMPRE consultado com tags (habilidade | tipo de dano)
    AttackSpeed,       // multiplicador de velocidade de ataque (base 1)
    CastSpeed,         // multiplicador de velocidade de conjuração (base 1)
    CritChance,        // fração [0,1]
    CritMultiplier,    // multiplicador do crítico (base vem de RulesConstants: 1.5)
    MoveSpeed,         // multiplicador (base 1)
    CooldownRecovery,  // multiplicador de recarga (base 1; maior = recarrega mais rápido)
    AreaOfEffect,      // multiplicador de área (base 1)
    ProjectileCount,   // projéteis extras (base 0, só flat faz sentido)
    DamageTaken,       // multiplicador do dano recebido (base 1; "menos dano recebido")
    PotionEffect,      // multiplicador da cura de poção (base 1)
    Count
};
inline constexpr int kStatCount = static_cast<int>(StatId::Count);

bool ParseStatId(std::string_view text, StatId& out);  // "life", "life_regen", "resist_fire"...
const char* ToString(StatId id);

enum class ModKind : std::uint8_t {
    Flat = 0,       // soma na base
    Increased = 1,  // soma com os outros Increased antes de multiplicar
    More = 2,       // multiplica separado
};
bool ParseModKind(std::string_view text, ModKind& out);  // "flat" | "increased" | "more"

// Um modificador. Só vale para consultas cujas tags contenham TODAS as requiredTags.
struct Modifier {
    StatId stat = StatId::Life;
    ModKind kind = ModKind::Flat;
    double value = 0.0;
    TagMask requiredTags = 0;  // 0 = vale sempre
    ContentId source;          // quem deu o mod (affix.life_flat, passive.n12, effect.burn...). Só para UI/depuração.
};

// Fórmula canônica (a única no projeto). Nunca negativa.
inline double ComputeStatValue(double base, double sumFlat, double sumIncreased, double productMore) {
    const double v = (base + sumFlat) * (1.0 + sumIncreased) * productMore;
    return v > 0.0 ? v : 0.0;
}

// Conjunto de atributos de uma entidade (personagem ou inimigo).
// - Bases vêm de ClassData/EnemyData + nível.
// - Mods vêm de itens, árvore, Sigilos, efeitos ativos.
// - Cache por (stat, tags) com dirty flag; qualquer Add/Remove/SetBase invalida tudo.
// Ordem de soma dos mods = ordem de inserção (determinismo de ponto flutuante).
class StatBlock {
public:
    StatBlock();

    void SetBase(StatId stat, double value);
    double GetBase(StatId stat) const;

    void AddModifier(const Modifier& mod);
    void AddModifiers(const std::vector<Modifier>& mods);
    // Remove todos os mods cuja source == sourceId (ex.: tirar um item, efeito expirou). Devolve quantos removeu.
    std::size_t RemoveModifiersFrom(std::string_view sourceId);
    void ClearModifiers();
    const std::vector<Modifier>& Modifiers() const { return mods_; }

    // Valor final sem tags de contexto (só mods com requiredTags == 0 entram).
    double Get(StatId stat) const;
    // Valor final no contexto de tags (habilidade e/ou tipo de dano).
    double GetTagged(StatId stat, TagMask contextTags) const;
    // Mesmo cálculo, mas com outra base (usado para dano: base = dano da habilidade daquele tipo).
    double ApplyTagged(StatId stat, TagMask contextTags, double baseOverride) const;

    // Somas brutas (para tooltip "de onde vem este número").
    struct Breakdown {
        double base = 0.0;
        double sumFlat = 0.0;
        double sumIncreased = 0.0;
        double productMore = 1.0;
        double final = 0.0;
    };
    Breakdown Explain(StatId stat, TagMask contextTags) const;

    bool IsDirty() const { return dirty_; }
    std::uint64_t Revision() const { return revision_; }  // muda a cada alteração; o UE usa para saber quando reler

private:
    void Invalidate();

    std::array<double, kStatCount> base_{};
    std::vector<Modifier> mods_;
    mutable std::unordered_map<std::uint64_t, double> cache_;  // chave = (stat << 32) | tags
    mutable bool dirty_ = true;
    std::uint64_t revision_ = 0;
};

}  // namespace shatter
