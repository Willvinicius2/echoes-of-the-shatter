// ShatterCore — inventário, equipamento, comparação, venda e pegar do chão (docs/16 seção 4; Etapa 3).
//
// Tudo é regra do core; o cliente só mostra. Números (capacidades, preços, posições liberadas) vêm de rules.csv.
// Contêineres: Mochila (CharacterState::backpack), Baú compartilhado (SaveData::stash) e Equipamento
// (CharacterState::equipment). Itens não empilham. Ouro e Lascas são pilhas (SaveData::currencies) e não ocupam espaço.
// Nenhuma função aqui usa RNG; o resultado depende só do estado e do conteúdo (determinismo).
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "shatter/character.h"
#include "shatter/content.h"
#include "shatter/item.h"
#include "shatter/save.h"
#include "shatter/stats.h"

namespace shatter {

inline constexpr const char* kGoldId = "currency.gold";

enum class InvResult : std::uint8_t {
    Ok = 0,
    NotFound,        // uid inexistente no contêiner pedido, ou personagem inexistente
    Full,            // Mochila (ou Baú) sem espaço; nada muda
    SlotMismatch,    // a base do item não cabe nessa posição
    SlotLocked,      // posição bloqueada no protótipo (rules.csv: equip_slot_*)
    SlotEmpty,       // desequipar posição vazia
    UnknownContent,  // base, afixo ou Único do item não existem no conteúdo
};

enum class Container : std::uint8_t { Backpack = 0, Stash = 1 };

// Capacidades e contagens (capacidade de rules.csv).
struct InventoryInfo {
    int backpackCapacity = 0, backpackUsed = 0;
    int stashCapacity = 0, stashUsed = 0;
};
InventoryInfo GetInventoryInfo(const ContentDB& db, const SaveData& s, std::size_t characterIndex);

// Procura o item por uid no contêiner. nullptr se não houver.
const ItemInstance* FindInContainer(const SaveData& s, std::size_t characterIndex, Container where, std::uint64_t uid);

// Acrescenta na Mochila. Full se a capacidade acabou (nada muda).
InvResult BackpackAdd(const ContentDB& db, SaveData& s, std::size_t characterIndex, ItemInstance item);
// Acrescenta no Baú. Full se a capacidade acabou.
InvResult StashAdd(const ContentDB& db, SaveData& s, ItemInstance item);

// Ordem estável por posição (ordem de ItemSlot), raridade (Único primeiro), itemLevel (maior primeiro), baseId e uid.
// Só reordena a Mochila; nada some.
InvResult SortBackpack(const ContentDB& db, SaveData& s, std::size_t characterIndex);

// Move entre Mochila e Baú (destino cheio = Full; nada muda).
InvResult MoveItem(const ContentDB& db, SaveData& s, std::size_t characterIndex, std::uint64_t uid, Container to);

// Posição padrão da base (Ring: a primeira livre entre Ring e Ring2; ocupadas, Ring). Slot inexistente: Count.
ItemSlot DefaultSlotFor(const ContentDB& db, const CharacterState& c, const ItemInstance& item);

struct EquipOutcome {
    InvResult result = InvResult::Ok;
    ItemSlot slot = ItemSlot::Count;          // posição usada
    bool displaced = false;                    // havia um item antigo
    std::uint64_t displacedUid = 0;            // ... que voltou para a Mochila
};
// Equipa o item da Mochila na posição `slot` (Count = a padrão da base). Valida a posição (liberada em rules.csv e
// compatível com a base; Ring serve em Ring2). O item antigo volta para a Mochila (sempre cabe: o novo acabou de sair
// dela). Se `stats` não for nulo, só os modificadores dos itens trocados saem/entram (o resto do bloco fica).
EquipOutcome Equip(const ContentDB& db, SaveData& s, std::size_t characterIndex, std::uint64_t uid, ItemSlot slot,
                   StatBlock* stats = nullptr);
// Desequipa para a Mochila (Full se não houver espaço; nada muda).
EquipOutcome Unequip(const ContentDB& db, SaveData& s, std::size_t characterIndex, ItemSlot slot,
                     StatBlock* stats = nullptr);

// Diferença de um item contra o equipado na mesma posição (tooltip). Itens fora do equipamento; nada é alterado.
struct StatDelta {
    StatId stat = StatId::Life;
    double before = 0.0, after = 0.0;
};
struct ItemComparison {
    InvResult result = InvResult::Ok;
    ItemSlot slot = ItemSlot::Count;
    std::uint64_t equippedUid = 0;      // 0 = posição vazia
    std::vector<StatDelta> deltas;      // só os atributos que mudam, em ordem de StatId
    bool isWeapon = false;
    double weaponDpsBefore = 0.0, weaponDpsAfter = 0.0;  // dano da arma x velocidade de ataque (docs/16 4.3)
};
// `item` pode estar na Mochila, no Baú, no chão ou em qualquer lugar: a comparação é hipotética.
ItemComparison CompareItem(const ContentDB& db, const CharacterState& c, const ItemInstance& item, ItemSlot slot);

// Valor de venda: sell_price[raridade] x (1 + sell_level_factor x (itemLevel - 1)), arredondado, nunca negativo.
// Calculável sem vendedor: o uso do Ouro é decisão do dono (docs/16 Q3-3).
std::int64_t SellValue(const ContentDB& db, const ItemInstance& item);
// Vende da Mochila ou do Baú: o item some e o valor entra em currency.gold (mesmo SaveData; idempotente: a segunda
// chamada com o mesmo uid dá NotFound e não paga de novo). Equipado não vende (desequipe antes).
InvResult SellItem(const ContentDB& db, SaveData& s, std::size_t characterIndex, Container from, std::uint64_t uid,
                   std::int64_t* goldGained = nullptr);
// Destrói o item da Mochila ou do Baú.
InvResult DiscardItem(SaveData& s, std::size_t characterIndex, Container from, std::uint64_t uid);

// Pegar do chão: Mochila; cheia e item Único -> Baú (nunca fica sem dono); senão Full (o item continua no chão).
enum class PickupDest : std::uint8_t { Backpack = 0, Stash = 1, Full = 2 };
PickupDest PickupItem(const ContentDB& db, SaveData& s, std::size_t characterIndex, ItemInstance item);

// Conjunto visual do item (docs/04 17.4): uniques.visualSetId, depois item_bases.visualSetId, depois "vset.starter".
std::string ItemVisualSetId(const ContentDB& db, const ItemInstance& item);
inline constexpr const char* kFallbackVisualSet = "vset.starter";

}  // namespace shatter
