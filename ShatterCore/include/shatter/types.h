// ShatterCore — tipos básicos compartilhados.
// Regra: nenhum header de ShatterCore inclui nada do Unreal. Só STL, C++17.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>

namespace shatter {

// Versão do próprio motor de regras (não confundir com content_version nem save_version).
inline constexpr std::uint32_t kCoreVersionMajor = 0;
inline constexpr std::uint32_t kCoreVersionMinor = 1;

// ---------------------------------------------------------------------------
// IDs de conteúdo
// ---------------------------------------------------------------------------
// IDs estáveis em texto, em inglês, minúsculos, segmentos separados por ponto:
//   "skill.warrior.iron_cut", "affix.life_flat", "enemy.hollow_sentinel".
// Nunca renomear depois de publicado: o save guarda o ID, não caminho de arquivo.
using ContentId = std::string;

// true se o ID segue o formato: [a-z0-9_]+ ( '.' [a-z0-9_]+ )+  (pelo menos 2 segmentos).
inline bool IsValidContentId(std::string_view id) {
    if (id.empty() || id.front() == '.' || id.back() == '.') return false;
    bool sawDot = false;
    char prev = '\0';
    for (char c : id) {
        const bool ok = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '.';
        if (!ok) return false;
        if (c == '.') {
            if (prev == '.') return false;
            sawDot = true;
        }
        prev = c;
    }
    return sawDot;
}

// ---------------------------------------------------------------------------
// Tags (bitmask). Decidem quais modificadores valem para cada habilidade.
// ---------------------------------------------------------------------------
using TagMask = std::uint32_t;

enum class Tag : TagMask {
    None       = 0,
    Attack     = 1u << 0,
    Spell      = 1u << 1,
    Melee      = 1u << 2,
    Projectile = 1u << 3,
    Area       = 1u << 4,
    Fire       = 1u << 5,
    Cold       = 1u << 6,
    Lightning  = 1u << 7,
    Physical   = 1u << 8,
};
inline constexpr int kTagCount = 9;

constexpr TagMask Mask(Tag t) { return static_cast<TagMask>(t); }
constexpr TagMask operator|(Tag a, Tag b) { return Mask(a) | Mask(b); }
constexpr TagMask operator|(TagMask a, Tag b) { return a | Mask(b); }
// Todas as tags exigidas estão presentes? (exigência vazia = vale para tudo)
constexpr bool HasAllTags(TagMask have, TagMask required) { return (have & required) == required; }
constexpr bool HasTag(TagMask have, Tag t) { return (have & Mask(t)) != 0; }

// Conversão para/de texto usado nos CSV ("attack", "spell", "melee", "projectile",
// "area", "fire", "cold", "lightning", "physical"). Lista no CSV separada por '|'.
// Implementação: src/types.cpp. Retorna false se alguma tag for desconhecida.
bool ParseTagList(std::string_view text, TagMask& out);
std::string TagListToString(TagMask mask);

// ---------------------------------------------------------------------------
// Tipos de dano
// ---------------------------------------------------------------------------
enum class DamageType : std::uint8_t {
    Physical  = 0,
    Fire      = 1,
    Cold      = 2,
    Lightning = 3,
};
inline constexpr int kDamageTypeCount = 4;

constexpr int Index(DamageType t) { return static_cast<int>(t); }
constexpr bool IsElemental(DamageType t) { return t != DamageType::Physical; }
// Tag correspondente ao tipo de dano (Physical→Tag::Physical, Fire→Tag::Fire...).
constexpr Tag TagOf(DamageType t) {
    switch (t) {
        case DamageType::Physical:  return Tag::Physical;
        case DamageType::Fire:      return Tag::Fire;
        case DamageType::Cold:      return Tag::Cold;
        case DamageType::Lightning: return Tag::Lightning;
    }
    return Tag::None;
}
bool ParseDamageType(std::string_view text, DamageType& out);   // "physical"|"fire"|"cold"|"lightning"
const char* ToString(DamageType t);

// ---------------------------------------------------------------------------
// Raridade
// ---------------------------------------------------------------------------
enum class Rarity : std::uint8_t {
    Normal = 0,  // "Comum" na interface pt-BR
    Magic  = 1,  // até 2 afixos
    Rare   = 2,  // até 4 afixos
    Unique = 3,  // atributos fixos + efeito + contrapartida
};
inline constexpr int kRarityCount = 4;
bool ParseRarity(std::string_view text, Rarity& out);   // "normal"|"magic"|"rare"|"unique"
const char* ToString(Rarity r);

// ---------------------------------------------------------------------------
// Tempo de simulação
// ---------------------------------------------------------------------------
// Tempo em segundos (double). O tempo real do UE é convertido em passos fixos
// antes de chegar ao motor (ver docs/04_arquitetura.md, "Determinismo").
using Seconds = double;

// Horário Unix em segundos, sempre UTC.
using UnixSeconds = std::int64_t;

}  // namespace shatter
