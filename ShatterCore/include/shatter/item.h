// ShatterCore — instância de item (o que vai para o baú, o equipamento e o save).
#pragma once

#include <cstdint>
#include <string_view>
#include <vector>

#include "shatter/types.h"

namespace shatter {

// Posições de equipamento (11). AA usa as 8 primeiras mais Legs; Ring2 e Belt ficam reservadas para o 1.0.
enum class ItemSlot : std::uint8_t {
    MainHand = 0,
    OffHand,
    Head,
    Body,
    Hands,
    Feet,
    Amulet,
    Ring,
    Ring2,   // 1.0
    Belt,    // 1.0
    Legs,    // ADIÇÃO (C-10, docs/04 17.4): calça; no FIM do enum para não deslocar índices da API C nem do save
    Count
};
inline constexpr int kItemSlotCount = static_cast<int>(ItemSlot::Count);
bool ParseItemSlot(std::string_view text, ItemSlot& out);  // "main_hand", "off_hand", "head", "body", "hands", "feet", "amulet", "ring", "ring2", "belt", "legs"
const char* ToString(ItemSlot s);

// Afixo rolado: valor já sorteado dentro da faixa [min,max] do AffixData.
struct RolledAffix {
    ContentId affixId;
    double value = 0.0;
};

// Item concreto. Tudo por ID; nada de texto traduzido (o nome é montado na UI
// a partir das chaves de localização + gênero da base).
struct ItemInstance {
    std::uint64_t uid = 0;            // único dentro do save (gerado por SaveData::NextItemUid)
    ContentId baseId;                 // item_base.*
    Rarity rarity = Rarity::Normal;
    int itemLevel = 1;
    ContentId uniqueId;               // vazio se não for Único
    std::vector<RolledAffix> affixes; // ordem estável (prefixos antes de sufixos, ordem de rolagem)
    bool hasInscription = false;      // Fixar Inscrição: no máximo 1 por item
};

// Pilha de recurso (ouro, materiais, páginas, sigilos comuns...). id = "currency.gold",
// "material.shard", "material.memory_ash", "page.skill.warrior.cleave"...
struct StackEntry {
    ContentId id;
    std::int64_t amount = 0;
};

}  // namespace shatter
