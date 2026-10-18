// ShatterCore — Vendedor e Frasco de Recarga (docs/16 seção 11.2). Regra do core; o cliente só mostra.
// Vender usa o valor do inventário (SellValue). Os 10 últimos itens vendidos ficam na recompra (SaveData::vendorBuyback,
// o mais recente primeiro) e recomprar custa vendor_buyback_price_factor x o valor pago, arredondado para cima. Ouro, Lascas e
// Frasco de Recarga são pilhas em SaveData::currencies. Nenhuma função usa RNG.
#pragma once

#include <cstdint>
#include <string_view>

#include "shatter/combat.h"
#include "shatter/content.h"
#include "shatter/craft.h"
#include "shatter/inventory.h"
#include "shatter/save.h"

namespace shatter {

inline constexpr const char* kRefillFlaskId = "consumable.refill_flask";

enum class VendorResult : std::uint8_t {
    Ok = 0,
    NotFound,         // uid (venda, recompra) ou id de estoque desconhecido
    Full,             // Mochila cheia (recompra)
    NoGold,
    CarryCap,         // passaria do máximo que o jogador leva
    BadQuantity,      // quantidade < 1
    UnknownContent,   // item com base ou afixo que não existe mais
};

// Estado da recompra para a UI. `wouldEvict`: a próxima venda expulsa o item mais antigo (que deixa de existir);
// `evictRarity` é a dele (a UI pede confirmação extra para Raro e Único).
struct BuybackInfo {
    int count = 0, capacity = 0;
    bool wouldEvict = false;
    Rarity evictRarity = Rarity::Normal;
};
BuybackInfo GetBuybackInfo(const ContentDB& db, const SaveData& s);

// Vende da Mochila ou do Baú (equipado não vende): paga SellValue, põe o item na recompra e, se passou do limite, expulsa
// o mais antigo. Idempotente por uid (repetir dá NotFound e não paga de novo).
VendorResult VendorSell(const ContentDB& db, SaveData& s, std::size_t characterIndex, Container from, std::uint64_t uid,
                        std::int64_t* goldGained = nullptr, bool* evicted = nullptr, Rarity* evictedRarity = nullptr);
// Preço de recompra de um item que rendeu `paid` Ouro.
std::int64_t BuybackPrice(const ContentDB& db, std::int64_t paid);
// Recompra por uid (idempotente: o item sai da lista; repetir dá NotFound). Cobra o preço e põe o item de volta na Mochila.
VendorResult VendorBuyback(const ContentDB& db, SaveData& s, std::size_t characterIndex, std::uint64_t uid,
                           std::int64_t* goldSpent = nullptr);
// Compra `qty` do estoque `stockId` (vendor_stock.csv); respeita carryCap e o Ouro.
VendorResult VendorBuy(const ContentDB& db, SaveData& s, std::string_view stockId, std::int64_t qty, std::int64_t* goldSpent = nullptr);

// Contexto de uso do frasco: a luta do Guardião testa as cargas do docs/13 e a expedição não usa frasco.
enum class FlaskContext : std::uint8_t { Run = 0, Arena = 1, Idle = 2 };
enum class FlaskResult : std::uint8_t {
    Ok = 0,
    NoFlask,        // sem frasco carregado
    ArenaLocked,
    IdleForbidden,
    PotionsFull,    // nenhuma poção com menos que o máximo: o frasco não é gasto
    LockedOut,      // trava global de poção
    UnknownContent, // sem poções no conteúdo
};
struct FlaskOutcome {
    FlaskResult result = FlaskResult::NoFlask;
    int potionIndex = -1;       // posição da poção restaurada em belt.slots (ordem de potions.csv)
    int chargesAfter = 0;
    int flasksLeft = 0;
};
// Restaura refill_flask_charges cargas da poção com MENOS cargas (empate: a primeira do CSV, a Vida), sem passar do
// máximo, gasta 1 frasco e inicia a trava global. Recusa não muda nada.
FlaskOutcome UseRefillFlask(const ContentDB& db, SaveData& s, PotionBelt& belt, FlaskContext context);

}  // namespace shatter
