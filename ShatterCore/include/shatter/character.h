// ShatterCore — estado persistente do personagem e snapshot congelado.
// O mesmo builder (BuildStatBlock) monta os atributos no UE e no simulador idle.
#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "shatter/content.h"
#include "shatter/item.h"
#include "shatter/progress.h"
#include "shatter/stats.h"
#include "shatter/types.h"

namespace shatter {

struct LearnedSkill {
    ContentId skillId;
    int rank = 1;                        // 1..3 no AA
    std::vector<ContentId> sigils;       // Sigilos encaixados (máx. por nível: 1/2/3)
};

// Personagem como fica no save.
struct CharacterState {
    std::string name;                    // nome escolhido pelo jogador (UTF-8)
    ContentId classId;
    ContentId specId;                    // vazio antes do nível 10
    int level = 1;
    double xp = 0.0;                     // XP dentro do nível atual
    std::vector<ContentId> passives;     // nós da árvore
    std::vector<LearnedSkill> skills;
    std::array<ContentId, 6> skillBar{}; // 6 no AA (4 no demo)
    std::array<std::optional<ItemInstance>, kItemSlotCount> equipment{};
    // Mochila (docs/16 4.1): capacidade em rules.csv (inventory_capacity). Etapa 3; no save só aparece se não estiver vazia.
    std::vector<ItemInstance> backpack;
    std::vector<ContentId> conqueredMaps;// domínio manual (início ao fim + chefe)
    int highestTierCleared = 0;
    // Save v2 (docs/13, itens 2 e 9): espaços de poção (um por potions.csv, normalizados ao usar) e vitórias por chefe.
    std::vector<PotionSlotState> potionSlots;
    std::vector<BossProgressEntry> bossProgress;
    double playTimeSeconds = 0.0;
};

// Snapshot congelado no início da expedição (build + regras de IA ficam fixas).
// É uma CÓPIA autocontida do personagem: o simulador não lê o save vivo.
struct CharacterSnapshot {
    CharacterState character;
    std::uint32_t contentVersion = 0;    // conteúdo com o qual o snapshot foi feito
};

// Monta o StatBlock: bases da classe por nível + implícitos e afixos dos itens +
// passivas + Sigilos/Únicos. Ordem fixa de inserção dos mods (determinismo):
// classe → itens por ItemSlot crescente (implícito, afixos na ordem) → únicos → passivas na ordem do vetor.
// Implementação: src/character.cpp. Retorna false (e preenche error) se algum ID não existir.
bool BuildStatBlock(const ContentDB& db, const CharacterState& c, StatBlock& out, std::string* error = nullptr);

// ADIÇÃO (docs/tecnico/09_mudancas_contrato.md): atributos de um inimigo no nível de monstro `level`
// (base + perLevel × (nível − 1) de cada StatGrowth, sem mods). O mesmo builder no simulador idle e,
// pela API C, no combate em tempo real. Nível < 1 conta como 1.
void BuildEnemyStatBlock(const EnemyData& enemy, int level, StatBlock& out);

// Verifica se o golpe 1 do kit da classe (basic_kits.csv), as habilidades da barra (Q/E/R), Sigilos e Únicos equipados têm
// IdleProfile suportado. Os outros golpes do kit (combo 2 e 3, golpe forte) não entram (docs/18 §8 item 8). Preenche `blockingIds` com o que bloqueia (UI: "X ainda não funciona em patrulha").
bool IsIdleCompatible(const ContentDB& db, const CharacterState& c, std::vector<ContentId>* blockingIds);

// A habilidade é só do kit básico da classe e NÃO é o golpe 1: golpes 2 e 3 do combo e golpe forte (basic_kits.csv).
// Existem só no tempo real; o idle (compatibilidade e selo de calibração) as ignora (docs/18 §8 item 8).
bool IsKitOnlySkill(const ContentDB& db, const ContentId& classId, const ContentId& skillId);

}  // namespace shatter
