// ShatterCore — jogo manual da Cripta: estado do mundo, baús, encontros sorteados, XP por morte e Fervor
// (pacote "core da Cripta"; docs/14 seção 5, docs/16 4.5, docs/09 seção 14). Regra do core; o cliente só mostra.
//
// - Estado do mundo: por área, os objetos abertos (baús, parede secreta, atalho) por ID de objeto, e o contador de visitas.
//   O estado vai no save (campo opcional `world_state`) e NÃO volta ao voltar a um checkpoint.
// - Semente da visita: nasce no core (função de craft_seed efetivo, mapa e contador de visitas); o chamador não a escolhe.
// - Encontros: quantidade entre min e max por grupo e a elite (chanceElite) por espaço, determinísticos pela semente da visita
//   (fluxo Events). O mesmo encontro na mesma visita dá a mesma formação, também depois de voltar a um checkpoint.
// - XP: por morte, do enxerto de enemies.csv (xpBase + xpPerLevel x (nível - 1)), x multiplicadores de elite e x Fervor.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "shatter/content.h"
#include "shatter/rng.h"
#include "shatter/save.h"

namespace shatter {

// ---------------------------------------------------------------------------
// Estado do mundo
// ---------------------------------------------------------------------------
const WorldAreaState* FindWorldArea(const SaveData& s, std::string_view mapId);
bool IsWorldObjectOpen(const SaveData& s, std::string_view mapId, std::string_view objectId);
// Marca (ou desmarca) o objeto. Cria a área se faltar. false (sem mudar nada) se o ID é inválido ou se passaria do limite
// (kMaxWorldAreas, kMaxWorldObjects). Idempotente.
bool SetWorldObjectOpen(SaveData& s, const ContentId& mapId, const ContentId& objectId, bool open);

// Começa uma visita à área: incrementa o contador e devolve a semente da visita. false se o mapa não existe ou o limite de
// áreas estourou. A semente é função pura de (craft_seed efetivo do save, mapa, contador): recarregar o save e começar a visita
// de novo dá outra visita (outro contador), mas a MESMA visita dá sempre a mesma formação.
bool BeginAreaVisit(const ContentDB& db, SaveData& s, const ContentId& mapId, std::uint64_t* visitSeed);
std::uint64_t VisitSeed(const SaveData& s, std::string_view mapId, std::uint32_t visit);

// ---------------------------------------------------------------------------
// Baús e loot de encontro
// ---------------------------------------------------------------------------
// Tabela do baú: chests.csv; baú sem linha (ou de outro mapa) usa a areaLootTable do mapa. "" se nem isso existe.
std::string ChestLootTable(const ContentDB& db, std::string_view mapId, std::string_view chestId);
// areaLootTable do mapa (loot extra por encontro concluído). "" se não houver.
std::string AreaLootTable(const ContentDB& db, std::string_view mapId);

// ---------------------------------------------------------------------------
// Encontros
// ---------------------------------------------------------------------------
struct RolledSlot {
    bool elite = false;            // este espaço virou elite (troca um comum por elite)
    ContentId modifierId;          // modificador sorteado (vazio se a elite não tem modificador com peso)
};
struct RolledGroup {
    ContentId enemyId;
    std::vector<RolledSlot> slots; // `count` = slots.size(): um grupo de n inimigos usa os n primeiros espaços do layout
};
struct RolledEncounter {
    ContentId encounterId;
    bool isBoss = false;
    std::vector<RolledGroup> groups;
};
// Sorteia o encontro da visita: n entre countMin e countMax por grupo; por espaço, Chance(eliteChance) e, se virou elite, o
// modificador (RollEliteModifier). Ordem de consumo do fluxo Events: grupos na ordem do CSV, espaços na ordem. Inimigo que já
// é elite fixo (isElite) nunca vira "elite sorteado". false se o encontro não existe.
bool RollEncounter(const ContentDB& db, std::string_view encounterId, std::uint64_t visitSeed, RolledEncounter& out);

// ---------------------------------------------------------------------------
// XP por morte e Fervor
// ---------------------------------------------------------------------------
// XP de uma morte, sem Fervor: (xpBase + xpPerLevel x (nível - 1)) x multiplicador de elite. Elite sorteado (`eliteRolled`):
// elite_xp_mult x modificador; elite fixo (enemies.csv isElite): só o do modificador do inimigo (ou `modifierId` se vier);
// chefe e comuns: o próprio valor do inimigo. Inimigo desconhecido: -1.
double KillXpBase(const ContentDB& db, std::string_view enemyId, int monsterLevel, bool eliteRolled, std::string_view modifierId);

struct XpAward {
    bool ok = false;               // inimigo e personagem existem
    double awarded = 0.0;          // XP concedido (com Fervor)
    int levelBefore = 0, levelAfter = 0;
    int levelCap = 0;              // teto de nível da área (monsterLevel + xp_cap_levels_above_area, até max_level)
    double xpInLevel = 0.0;        // XP dentro do nível depois
    double xpToNext = 0.0;         // XP que falta para o próximo nível a partir do início do nível (0 no teto)
};
// Concede o XP de uma morte no jogo manual. `fervor`: aplica fervor_xp_mult (XP +200% com o valor do CSV).
XpAward AwardKillXp(const ContentDB& db, SaveData& s, std::size_t characterIndex, std::string_view mapId,
                    std::string_view enemyId, int monsterLevel, bool eliteRolled, std::string_view modifierId, bool fervor);
// Nível e XP do personagem para a HUD e para o herói usar o nível do save. `mapId` vazio = teto max_level.
XpAward CharacterProgress(const ContentDB& db, const SaveData& s, std::size_t characterIndex, std::string_view mapId);

struct FervorInfo {
    double xpMult = 1.0, goldMatMult = 1.0, rareMult = 1.0;       // multiplicadores de rules.csv
    double xpBonus = 0.0, goldMatBonus = 0.0, rareBonus = 0.0;    // mult - 1 (XP +200% = 2,0)
};
FervorInfo GetFervorInfo(const ContentDB& db);

}  // namespace shatter
