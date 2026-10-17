// ShatterCore — estado de progresso por personagem que vai para o save v2 (docs/13, itens 2 e 9).
#pragma once

#include <cstdint>
#include <vector>

#include "shatter/types.h"

namespace shatter {

// Um espaço de poção (potions.csv). Salvo como {potion_id, charges, recharge_remaining}.
// A trava global entre usos (potion_lockout) e as cargas de esquiva NÃO são salvas: reiniciam ao carregar.
struct PotionSlotState {
    ContentId potionId;
    int charges = 0;
    double rechargeRemaining = 0.0;   // s até a próxima carga (recarga em série); 0 = não está recarregando
};

// Contador de vitórias sobre um chefe, por personagem. Salvo como {enemy_id, kills, kills_since_unique}.
struct BossProgressEntry {
    ContentId enemyId;
    int kills = 0;                    // vitórias totais
    int killsSinceUnique = 0;         // vitórias seguidas sem cair o Único (zera ao cair)
};

// Teto dos contadores (save v2 recusa acima disso; o core satura aqui em vez de estourar int).
inline constexpr int kMaxBossCounter = 1000000;

// Entrada do chefe, a PRIMEIRA com o id (nullptr se não houver). Leitura e gravação usam esta mesma busca.
inline const BossProgressEntry* FindBossProgress(const std::vector<BossProgressEntry>& list, const ContentId& enemyId) {
    for (const BossProgressEntry& e : list) {
        if (e.enemyId == enemyId) return &e;
    }
    return nullptr;
}

// Entrada do chefe (criada se faltar). O ponteiro vale até a próxima alteração do vetor.
inline BossProgressEntry& FindOrAddBossProgress(std::vector<BossProgressEntry>& list, const ContentId& enemyId) {
    for (BossProgressEntry& e : list) {
        if (e.enemyId == enemyId) return e;
    }
    BossProgressEntry fresh;
    fresh.enemyId = enemyId;
    list.push_back(fresh);
    return list.back();
}

}  // namespace shatter
