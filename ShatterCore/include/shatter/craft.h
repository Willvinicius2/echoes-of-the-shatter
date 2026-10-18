// ShatterCore — Encantador (Melhorias de equipamento, docs/16 seção 11). Toda regra mora aqui; o cliente só mostra.
//
// Cinco operações sobre um item do jogador (Mochila, Baú ou equipado): Refinar, Reforjar (com trava de 1 afixo),
// Adicionar afixo (escolha entre candidatos), Lapidar (sem sorteio) e Desmontar. Custo em Ouro e Lascas, cobrado e aplicado
// de forma atômica: PlanCraft só LÊ o save e decide tudo; CommitCraft só escreve e não tem como falhar no meio. Uma operação
// que não chega ao Commit deixa o save byte a byte igual.
// Sorteio: fluxo próprio RngStream::Crafting, semente = função pura de (craft_seed, uid, craft_steps do item, operação).
// Nenhum sorteio toca o fluxo Loot. Nenhum número de balanceamento aqui: tudo em rules.csv e craft_costs.csv.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "shatter/content.h"
#include "shatter/item.h"
#include "shatter/rng.h"
#include "shatter/save.h"

namespace shatter {

inline constexpr const char* kShardsId = "material.shards";

enum class CraftResult : std::uint8_t {
    Ok = 0,
    NotFound,           // uid fora da Mochila, do Baú e do equipamento do personagem
    Unique,             // Único é intocável (nem Desmontar)
    WrongRarity,        // a operação não aceita esta raridade
    AffixLimit,         // Adicionar: o item já está no limite de afixos da raridade
    AlreadyInscribed,   // Adicionar: já recebeu um afixo adicionado (1 por item)
    PolishMax,          // Lapidar: passos esgotados ou valor já no máximo da faixa
    NoCandidate,        // sem afixo elegível (Refinar/Adicionar)
    NoGold,
    NoShards,
    EquippedDismantle,  // Desmontar não aceita item equipado
    UnknownContent,     // base, afixo ou linha de custo inexistente
    BadIndex,           // afixo travado, afixo a lapidar ou candidato fora da faixa
};

enum class ItemWhere : std::uint8_t { Backpack = 0, Stash = 1, Equipped = 2 };

// Semente efetiva das melhorias: craft_seed do save; se ainda for 0 (save antigo ou jogo novo), uma função estável do
// primeiro personagem (nome e classe). EnsureCraftSeed grava o MESMO valor, então fixar a semente não muda sorteio algum.
std::uint64_t EffectiveCraftSeed(const SaveData& s);
void EnsureCraftSeed(SaveData& s);
// Gerador da operação: função pura (sem contador global). Mesmo item no mesmo estado dá o mesmo resultado.
Pcg32 CraftRng(std::uint64_t craftSeed, std::uint64_t itemUid, std::uint16_t craftSteps, CraftOp op);

// Saldo de uma pilha em SaveData::currencies (0 se não existe).
std::int64_t CurrencyAmount(const SaveData& s, std::string_view id);
// Soma `delta` (pode ser negativo) à pilha, criando-a se preciso. Nunca passa de INT64_MAX/2 nem fica abaixo de 0.
void CurrencyAdd(SaveData& s, const ContentId& id, std::int64_t delta);

struct CraftPlan {
    CraftResult result = CraftResult::NotFound;
    CraftOp op = CraftOp::Refine;
    std::uint64_t uid = 0;
    ItemWhere where = ItemWhere::Backpack;
    int slot = -1;                 // Equipped: ItemSlot
    std::size_t index = 0;         // posição no contêiner (Mochila ou Baú)
    ItemInstance after;            // o item depois da operação (Desmontar: não usado)
    std::int64_t gold = 0;         // custo (já com nível, Reforjar e trava); preenchido mesmo se faltar saldo
    std::int64_t shards = 0;
    std::int64_t shardsGain = 0;   // Desmontar
    int changedAffix = -1;         // Lapidar: afixo mexido; Adicionar: o afixo novo
    // Só para a prévia (UI): faixa do resultado e variações de custo.
    int affixCountMin = 0, affixCountMax = 0;     // Refinar: quantos afixos pode sair
    int polishStep = 0;                           // Lapidar: passo que seria dado (1..polish_max_steps)
    double polishFrom = 0.0, polishTo = 0.0;      // Lapidar: valor atual -> valor novo
    std::int64_t shardsWithLock = 0, shardsNoLock = 0;  // Reforjar: Lascas com e sem trava (Ouro é o mesmo)
    int reforgesBefore = 0;                       // Reforjar: quantos Reforjares a peça já levou
};

struct AffixCandidate {
    ContentId affixId;
    double minValue = 0.0, maxValue = 0.0;
};
struct AffixOffer {
    CraftResult result = CraftResult::NotFound;
    std::vector<AffixCandidate> candidates;   // até add_affix_candidates, na ordem do sorteio
    std::int64_t gold = 0, shards = 0;        // custo de Adicionar neste item
};

// Planeja SEM alterar nada. `arg`: Reforjar = índice do afixo travado (-1 = nenhum); Adicionar = índice do candidato;
// Lapidar = índice do afixo; demais ignoram. Se result != Ok nada deve ser confirmado. Faltar saldo dá NoGold/NoShards
// mas deixa os custos preenchidos (a UI mostra em vermelho).
CraftPlan PlanCraft(const ContentDB& db, const SaveData& s, std::size_t characterIndex, std::uint64_t uid, CraftOp op, int arg);
// Confirma um plano com result Ok: cobra e aplica (tudo ou nada). Plano que não é Ok não faz nada.
void CommitCraft(SaveData& s, std::size_t characterIndex, const CraftPlan& plan);

// Candidatos de Adicionar afixo: os mesmos enquanto o item não mudar (mesma semente). Não altera o save.
AffixOffer OfferAddAffix(const ContentDB& db, const SaveData& s, std::size_t characterIndex, std::uint64_t uid);

// Plano + confirmação numa chamada. `outcome` (opcional) recebe o plano para o chamador mostrar custo e destaque.
CraftResult CraftRefine(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, CraftPlan* outcome = nullptr);
CraftResult CraftReforge(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, int lockedAffixIndex,
                         CraftPlan* outcome = nullptr);
CraftResult CraftAddAffix(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, int candidateIndex,
                          CraftPlan* outcome = nullptr);
CraftResult CraftPolish(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, int affixIndex,
                        CraftPlan* outcome = nullptr);
CraftResult CraftDismantle(const ContentDB& db, SaveData& s, std::size_t ci, std::uint64_t uid, CraftPlan* outcome = nullptr);

// O personagem tem uma expedição Running (a build congelada só vale na próxima): a UI avisa; não bloqueia.
bool HasRunningExpedition(const SaveData& s, std::size_t characterIndex);

}  // namespace shatter
