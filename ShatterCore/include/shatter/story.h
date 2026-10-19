// ShatterCore — história da campanha: regiões, Ecos da Queda, missões e veredito Exorcizar/Devorar (docs/design/21 e 22).
//
// - Tabelas em Content/Data/Story/ (regions, echoes, quests, verdicts, story_rules). Ficam em subpasta: ContentDB não as lê.
// - Estado no save: `SaveData::story` (campo OPCIONAL `story`; só gravado se houver algo, como `world_state`: saves antigos
//   mantêm os mesmos bytes e hash, sem subir a versão do save).
// - O veredito é irreversível e vale para o save inteiro (todos os heróis). Nenhum número fica no código: Fome máxima,
//   Fome ganha e bônus vêm das tabelas.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "shatter/content.h"
#include "shatter/save.h"
#include "shatter/types.h"

namespace shatter {

struct StoryRegion {                   // regions.csv
    ContentId id;
    int order = 0;
    ContentId mapId, generalId, exorcizeVerdict, devourVerdict;
};
struct StoryEcho {                     // echoes.csv
    ContentId id, regionId;
    std::string kind;                  // weapon | memory
    ContentId revealsSkill;            // golpe do General que o Eco revela
    int minToReveal = 1;
};
struct StoryQuest {                    // quests.csv
    ContentId id, regionId, giver;
    std::string objectiveType;         // talk | collect_echo | reach_map_boss | verdict
    ContentId objectiveTarget;
    int objectiveCount = 1;
    ContentId requires_;
    std::string reward;
};
enum class VerdictChoice : std::uint8_t { Exorcise = 0, Devour = 1 };
struct StoryVerdict {                  // verdicts.csv
    ContentId id, regionId;
    VerdictChoice choice = VerdictChoice::Exorcise;
    int hungerDelta = 0;
    int statBonusPct = 0;
    ContentId grantsRelic, grantsSignature;
    std::string regionState, hubState; // purified|stain ; chave de hub
    std::string lastWordsKey;
};

class StoryDB {
public:
    // Tabelas: "regions.csv", "echoes.csv", "quests.csv", "verdicts.csv", "story_rules.csv". Erros acumulam em Errors().
    bool LoadTableCsv(std::string_view tableName, std::string_view csvText);
    // Lê a pasta Story/ (cada tabela é obrigatória). Pasta inexistente = erro.
    bool LoadDirectory(const std::string& storyDir);
    // Confere IDs, referências entre tabelas e, se `content` não for nulo, mapas/inimigos/habilidades. Chamar uma vez.
    bool Finalize(const ContentDB* content = nullptr);
    const std::vector<ContentError>& Errors() const { return errors_; }

    int HungerMax() const { return hungerMax_; }
    // Chaves opcionais de story_rules.csv (0 = não definida): bônus de cura de poção da Relíquia do Descanso e
    // chance extra de elite (em pontos percentuais) nas áreas com Mancha.
    int RelicPotionEffectPct() const { return relicPotionEffectPct_; }
    int StainEliteBonusPct() const { return stainEliteBonusPct_; }
    // Fome que cada uso de habilidade devorada gasta na corrida (0 = não definida) e tabela de loot extra das áreas com Mancha ("" = nenhuma).
    int DevouredHungerCost() const { return devouredHungerCost_; }
    const std::string& StainLootTable() const { return stainLootTable_; }
    const StoryRegion* FindRegion(std::string_view id) const;
    const StoryEcho* FindEcho(std::string_view id) const;
    const StoryQuest* FindQuest(std::string_view id) const;
    const StoryVerdict* FindVerdict(std::string_view id) const;
    const std::vector<StoryRegion>& Regions() const { return regions_; }     // ordem do CSV
    const std::vector<StoryEcho>& Echoes() const { return echoes_; }
    const std::vector<StoryQuest>& Quests() const { return quests_; }
    const std::vector<StoryVerdict>& Verdicts() const { return verdicts_; }

private:
    std::vector<StoryRegion> regions_;
    std::vector<StoryEcho> echoes_;
    std::vector<StoryQuest> quests_;
    std::vector<StoryVerdict> verdicts_;
    int hungerMax_ = 0;
    bool hasHungerMax_ = false;
    int relicPotionEffectPct_ = 0;
    int stainEliteBonusPct_ = 0;
    int devouredHungerCost_ = 0;
    std::string stainLootTable_;
    std::vector<ContentError> errors_;
};

// ---------------------------------------------------------------------------
// Regras sobre o save
// ---------------------------------------------------------------------------
// Registra um Eco achado. true só se for novo; false (sem mudar nada) se o Eco não existe ou já estava registrado.
bool RecordEcho(const StoryDB& story, SaveData& s, std::string_view echoId);
int EchoesFound(const StoryDB& story, const SaveData& s, std::string_view regionId);
// O Eco revela o golpe quando a região já tem `minToReveal` Ecos achados que apontam a mesma habilidade.
bool IsSkillRevealed(const StoryDB& story, const SaveData& s, std::string_view regionId, std::string_view skillId);

enum class VerdictResult : std::uint8_t {
    Ok = 0,
    UnknownVerdict,       // id fora de verdicts.csv
    GeneralNotDefeated,   // nenhum herói do save venceu o General da região
    AlreadyDecided,       // a região já tem veredito (irreversível)
    SaveFull,             // o save já guarda kMaxSavedVerdicts vereditos
};
// Aplica o veredito da região: grava a escolha e soma a Fome (limitada a story_rules hunger_max). Sem efeito se != Ok.
VerdictResult ApplyVerdict(const StoryDB& story, SaveData& s, std::string_view verdictId);
const StoryVerdict* DecidedVerdict(const StoryDB& story, const SaveData& s, std::string_view regionId);
// Soma de statBonusPct dos vereditos tomados (Devorar). O cliente aplica o bônus; o core só informa o total.
int TotalStatBonusPct(const StoryDB& story, const SaveData& s);

// ---------------------------------------------------------------------------
// Missões (quests.csv; progresso em `SaveData::story.quests`)
// ---------------------------------------------------------------------------
// Objetivos `collect_echo` (Ecos achados na região) e `verdict` (veredito tomado) avançam sozinhos: RecordEcho e ApplyVerdict
// sincronizam as missões. Os objetivos `talk` e `reach_map_boss` dependem do cliente, que avisa com ReportQuestEvent.
// Uma missão só avança depois de a que ela `requires` estar concluída; Ecos achados antes contam quando a missão libera.
// O core só guarda progresso e conclusão: a recompensa (`reward`) é uma chave que o cliente lê e aplica.
enum class QuestStatus : std::uint8_t { Locked = 0, Active = 1, Done = 2 };
QuestStatus GetQuestStatus(const StoryDB& story, const SaveData& s, std::string_view questId);   // id desconhecido = Locked
int QuestProgress(const StoryDB& story, const SaveData& s, std::string_view questId);            // 0..objectiveCount
// Avisa um evento do cliente: `type` "talk" ou "reach_map_boss", `target` como em quests.csv (npc.ilsa, map.act1.crypt).
// Soma `amount` (>= 1) a toda missão liberada e não concluída com esse objetivo. Devolve quantas missões concluiu agora
// (inclui as que a conclusão liberou e que já estavam cumpridas). Tipo ou alvo sem missão: 0 e nada muda.
int ReportQuestEvent(const StoryDB& story, SaveData& s, std::string_view type, std::string_view target, int amount = 1);

// Relíquias (veredito tomado com grantsRelic): soma de relic_potion_effect_pct, uma vez por relíquia.
int TotalPotionEffectPct(const StoryDB& story, const SaveData& s);
// Mancha: se o mapa pertence a uma região cujo veredito tomado deixou regionState "stain", devolve stain_elite_bonus_pct; senão 0.
int StainEliteBonusPctForMap(const StoryDB& story, const SaveData& s, std::string_view mapId);
// Mancha: tabela de loot extra (stain_loot_table) das áreas com Mancha; "" se o mapa não tem Mancha ou a chave não existe.
std::string StainLootTableForMap(const StoryDB& story, const SaveData& s, std::string_view mapId);

// ---------------------------------------------------------------------------
// Efeitos da história na expedição idle (docs/tecnico/09, 15.4)
// ---------------------------------------------------------------------------
// Golpes devorados que o save tem (grantsSignature skill.devoured.* dos vereditos tomados, na ordem dos vereditos).
std::vector<ContentId> DevouredSkills(const StoryDB& story, const SaveData& s);
// Usos de golpe devorado numa "corrida" (vida no manual, expedição inteira no idle): (hunger_max - Fome) / devoured_hunger_cost,
// arredondado para baixo. Fome 1 a 4 com custo 1 dá 3, 2, 1 e 0. Custo 0 (ou sem hunger_max) = -1, sem limite.
int IdleDevouredUses(const StoryDB& story, const SaveData& s);
// Preenche os campos story* dos parâmetros de início para o mapa: bônus do veredito, Relíquia, elites e loot da Mancha, golpes
// devorados e usos (Fome cheia = sem golpe). O cliente pode usar isto em vez de montar os campos a partir do JSON do estado.
void ApplyStoryToExpedition(const StoryDB& story, const SaveData& s, std::string_view mapId, ExpeditionStartParams& p);

}  // namespace shatter
