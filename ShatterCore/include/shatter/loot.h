// ShatterCore — rolagem de loot. Usa SÓ o fluxo de RNG Loot.
// Mesma função no jogo manual (com Fervor) e no idle (sem Fervor, com limites).
#pragma once

#include <cstdint>
#include <vector>

#include "shatter/content.h"
#include "shatter/item.h"
#include "shatter/progress.h"
#include "shatter/rng.h"
#include "shatter/types.h"

namespace shatter {

enum class LootMode : std::uint8_t {
    Manual = 0,  // Fervor: ouro/materiais ×1,25, chance de Raro ×2, acesso a manualOnly
    Idle = 1,    // taxa base; entradas manualOnly ignoradas; Raros contam para o teto
};

struct LootContext {
    LootMode mode = LootMode::Manual;
    int areaLevel = 1;               // nível de monstro da área (filtra minAreaLevel/maxAreaLevel e itemLevel)
    double quantityMult = 1.0;       // modificadores de Pedra de Rota (+15% cada). O Vigor do idle NÃO entra aqui: é aplicado em FinalizeExpedition
    int raresAlreadyDropped = 0;     // idle: Raros já obtidos na expedição
    int maxRares = -1;               // idle: teto (RulesConstants::maxRaresPerExpedition); -1 = sem teto
    std::uint64_t* nextItemUid = nullptr;  // contador do save; se nulo, uid = 0 (o chamador atribui depois)
    // ADIÇÃO (docs/13, item 9): progresso do chefe que acabou de morrer (só Manual). Com ele, as entradas FIXAS da tabela
    // (fixedChance / guaranteeFirstKill / pityKills) são avaliadas e o contador é atualizado NESTA chamada
    // (kills + 1; killsSinceUnique zera se a entrada fixa caiu, senão + 1). Sem ele, entradas fixas só rolam fixedChance.
    BossProgressEntry* bossProgress = nullptr;
};

struct LootDrop {
    std::vector<ItemInstance> items;
    std::vector<StackEntry> stacks;  // agregados por id, em ordem de primeira aparição
    int raresDropped = 0;
};

// Rola uma tabela (com subtabelas, profundidade máx. 8). Regras:
//  - cada roll: Chance(dropChance) → escolha ponderada entre entradas válidas (filtro de nível e de modo);
//  - Idle: entradas manualOnly e kinds Unique/SpecBook/MapStone/EchoFragment NUNCA saem (dupla checagem);
//  - ItemBase: raridade por rarityWeights; no Manual o peso de Rare × fervorRareChanceMult;
//    no Idle, se o teto de Raros já foi atingido, Rare vira Magic (sem nova rolagem);
//  - Stack: quantidade uniforme [min,max] × quantityMult × (Manual ? fervorGoldMatMult : 1), arredondada para baixo, mín. 1;
//  - afixos via RollAffixes.
// Consome uma quantidade variável de números do fluxo Loot — por isso o fluxo é separado.
LootDrop RollLootTable(const ContentDB& db, const LootTableData& table, const LootContext& ctx, Pcg32& lootRng);

// Sorteia os afixos de um item. Magic: 1–2; Rare: 3–4 (AA: "até 4").
// Peso por AffixData::weight; respeita minItemLevel, allowedSlots, grupos exclusivos,
// e no máximo 2 prefixos + 2 sufixos. Valor uniforme em [minValue, maxValue]
// (inteiros se min e max forem inteiros — ex. +10 de vida).
std::vector<RolledAffix> RollAffixes(const ContentDB& db, const ItemBaseData& base, Rarity rarity,
                                     int itemLevel, Pcg32& lootRng);

// ADIÇÃO (docs/16 seção 11, Encantador): usa o fluxo que o chamador passar (Crafting no Encantador, nunca Loot).
// Afixos que ainda podem entrar num item (slot, nível, grupo e limite 2 prefixos + 2 sufixos), na ordem do CSV, dado o
// que o item já tem. `onlyCraftInscription` restringe aos afixos com craftInscription = true.
std::vector<const AffixData*> EligibleAffixes(const ContentDB& db, const ItemBaseData& base, int itemLevel,
                                              const std::vector<RolledAffix>& current, bool onlyCraftInscription);
// Valor uniforme na faixa do afixo (inteiro se min e max forem inteiros). Consome 1 número.
double RollAffixValue(const AffixData& a, Pcg32& rng);
// Como RollAffixes, mas com a quantidade fixa `count` e afixos já mantidos (`kept`, ex.: o travado do Reforjar). Devolve
// menos que `count` só se o conjunto elegível acabar. Prefixos antes de sufixos.
std::vector<RolledAffix> RollAffixesFixed(const ContentDB& db, const ItemBaseData& base, int itemLevel, int count,
                                          const std::vector<RolledAffix>& kept, Pcg32& rng);

// Escolha ponderada genérica: índice em [0, weights.size()) ou -1 se soma <= 0.
// Consome exatamente 1 número. Exposta para o teste estatístico de 1 milhão de sorteios.
int PickWeighted(const std::vector<double>& weights, Pcg32& rng);

// Converte os afixos rolados + implícitos do item em Modifiers (source = "item:<uid>").
std::vector<Modifier> ItemModifiers(const ContentDB& db, const ItemInstance& item);

}  // namespace shatter
