// ShatterCore — simulador de expedição idle (plano, seções 7 e 10).
// Resolve encontro por encontro, sem posições nem física, com o MESMO ResolveHit,
// EffectContainer, BuildStatBlock e RollLootTable do jogo em tempo real.
//
// Determinismo (contrato testado a cada commit):
//   SimulateExpedition(db, req) == FinalizeExpedition(db, req, recibos de N chamadas
//   encadeadas de SimulateRange), para qualquer divisão em partes.
// Isso funciona porque:
//   - cada encontro i usa Pcg32::ForStream(req.seed, Combat|Loot|Events, i), nunca um RNG "corrido";
//   - o estado que atravessa encontros (vida, poções, raros, tempo) fica em ExpeditionProgress,
//     que é explícito, copiável e serializável;
//   - as taxas da seção 7 (Vigor, teto de nível) são aplicadas UMA vez, em FinalizeExpedition.
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

#include "shatter/character.h"
#include "shatter/clock.h"
#include "shatter/content.h"
#include "shatter/loot.h"
#include "shatter/progress.h"
#include "shatter/types.h"

namespace shatter {

// Objetivo escolhido com a Ilsa: muda só o peso da tabela de área (mais ouro, mais materiais) e o relatório.
enum class ExpeditionObjective : std::uint8_t { Xp = 0, Gold = 1, Materials = 2 };

// ---------------------------------------------------------------------------
// Política de IA: até 6 regras, avaliadas em ordem a cada passo; vale a primeira válida.
// Sem regra válida → ataque básico (skillBar[0]).
// ---------------------------------------------------------------------------
enum class AiCondition : std::uint8_t {
    Always = 0,
    LifeBelow,          // param = fração (0.35 = "abaixo de 35% de vida")
    ResourceAbove,      // param = fração do recurso
    ResourceBelow,
    EnemiesAtLeast,     // param = nº de inimigos vivos no encontro (Fenda de Pedra se ≥ 3)
    TargetIsElite,      // param ignorado
    TargetIsBoss,
    EffectMissing,      // refId = efeito que NÃO está ativo em si (renovar Postura Firme)
};

enum class AiAction : std::uint8_t {
    UsePotion = 0,      // usa a poção `refId` (potions.csv; vazio = a primeira de cura, a "Vida"); falha (e conta healFailures) sem cargas
    UseSkill,           // refId = skill id; precisa estar na barra, fora de recarga e com recurso
};

struct AiRule {
    AiCondition condition = AiCondition::Always;
    double param = 0.0;
    AiAction action = AiAction::UseSkill;
    ContentId refId;    // skill, efeito ou poção (potion.life, potion.ward), conforme acima
};

// ---------------------------------------------------------------------------
// Pedido: tudo que a simulação precisa. Congelado no início; gravado no save.
// ---------------------------------------------------------------------------
struct ExpeditionRequest {
    CharacterSnapshot snapshot;          // build congelada
    ContentId mapId;                     // área dominada (validada por CanStartExpedition)
    ExpeditionObjective objective = ExpeditionObjective::Xp;
    std::vector<AiRule> rules;           // máx. RulesConstants::maxAiRules (6)
    std::uint64_t seed = 0;              // seed da expedição (gerada no início; fluxo independente do jogo)
    UnixSeconds startUtc = 0;
    int durationHours = 1;               // 1..12, limitado pelas Cargas do Marco
    // Segundos de jogo a simular de fato (calculado por clock.h a partir de agora/last_seen).
    // Nunca maior que durationHours×3600 nem que maxOfflineHours×3600.
    double effectiveSeconds = 0.0;
    std::uint32_t contentVersion = 0;    // ContentDB::ContentVersion() no início
    // Efeitos da história congelados no início (campos opcionais no save; 0 = sem veredito/relíquia/Mancha).
    int storyStatBonusPct = 0;           // Devorar: "aumentado" em Vida, Dano e Armadura (story.h TotalStatBonusPct)
    int storyPotionEffectPct = 0;        // Relíquia do Descanso: cura de poção "aumentada" (TotalPotionEffectPct)
    int storyEliteBonusPct = 0;          // Mancha no mapa: pontos percentuais somados a eliteChance (StainEliteBonusPctForMap)
    // ADIÇÃO (docs/tecnico/09, 15.4): Fome e loot da Mancha no idle.
    // Golpes devorados (story.h DevouredSkills): entram nos espaços vazios 3..6 da barra, do último para trás, como no
    // manual (DevouredKit.FillBar), com posto 1. Cada uso gasta 1 de storyDevouredUses na expedição inteira (a "corrida"
    // do idle); 0 = a Fome não deixa usar (o golpe nem entra), < 0 = sem limite (custo 0). Ver IdleDevouredUses.
    std::vector<ContentId> storyDevouredSkills;
    int storyDevouredUses = 0;
    // Tabela de loot extra das áreas com Mancha (StainLootTableForMap): rolada ao fim de cada encontro limpo, depois da
    // tabela de área. Vazio = nenhuma.
    ContentId storyStainLootTable;
};

// Por que a expedição parou.
enum class StopReason : std::uint8_t {
    None = 0,            // ainda rodando (em ExpeditionProgress)
    DurationReached,     // tempo efetivo acabou (inclui teto de 12 h)
    Retreat,             // vida baixa e sem poção (risco real) — o loot já obtido fica
    ClockRollback,       // relógio voltou: encerrada no último ponto conhecido
    IncompatibleBuild,   // habilidade/Único sem IdleProfile (não deveria acontecer: validado antes)
    ContentMismatch,     // content_version mudou e o snapshot referencia ID que não existe mais
};

enum class EncounterOutcome : std::uint8_t {
    Cleared = 0,
    Retreated = 1,
};

// Recibo de UM encontro (valores BRUTOS, sem Vigor nem teto de nível).
struct EncounterReceipt {
    std::uint32_t index = 0;             // índice global do encontro na expedição
    ContentId templateId;
    EncounterOutcome outcome = EncounterOutcome::Cleared;
    double startTime = 0.0;              // s desde o início da expedição
    double duration = 0.0;               // s de combate + travessia
    int kills = 0;
    int elitesKilled = 0;
    int potionsUsed = 0;
    int healFailures = 0;                // quis curar e não tinha poção (dica do relatório)
    int dodgesUsed = 0;                  // esquivas da IA que gastaram carga (ADIÇÃO, docs/13 item 1)
    int devouredUses = 0;                // ADIÇÃO (docs/09, 15.4): usos de golpe devorado neste encontro (gasto de Fome)
    double damageTaken = 0.0;
    double damageDealt = 0.0;
    double xpRaw = 0.0;
    LootDrop loot;                       // já respeita o teto de Raros e a ausência de itens de topo
    double lifeFractionAtEnd = 1.0;
    std::uint8_t vigorBand = 0;          // 0: horas 1–4, 1: 5–8, 2: 9–12 (pelo startTime)
};

// Estado que atravessa encontros. Serializável (save) para retomar a simulação em partes.
struct ExpeditionProgress {
    std::uint32_t nextEncounter = 0;     // primeiro encontro ainda não simulado
    double elapsed = 0.0;                // s simulados até o fim do último encontro
    double life = -1.0;                  // < 0 = cheia (ainda não iniciada)
    double resource = -1.0;
    double barrier = 0.0;
    // ADIÇÃO (docs/13, itens 1 e 2): poções (cargas e recarga em série por slot; vazio = pegar do snapshot), cargas da
    // esquiva (< 0 = cheia) e a barreira da Poção de Resguardo (valor restante e tempo restante).
    std::vector<PotionSlotState> potionSlots;
    int dodgeCharges = -1;
    double dodgeRecharge = 0.0;
    double wardAmount = 0.0;
    double wardRemaining = 0.0;
    int raresDropped = 0;
    int devouredUsesSpent = 0;           // ADIÇÃO (docs/09, 15.4): usos de golpe devorado na expedição até aqui
    StopReason stop = StopReason::None;
    std::vector<EncounterReceipt> receipts;  // acumulados, em ordem de índice
};

// Resultado final (o que o Tico entrega).
struct ExpeditionResult {
    StopReason stop = StopReason::None;
    double effectiveSeconds = 0.0;       // até o fim do último encontro concluído
    int encountersCleared = 0;
    int kills = 0;
    int potionsUsed = 0;
    int healFailures = 0;
    double xpGained = 0.0;               // após Vigor e teto de nível
    bool xpCapped = false;               // teto de nível (área + 2) atingido
    std::vector<ItemInstance> items;
    std::vector<StackEntry> stacks;      // ouro, materiais, páginas — após Vigor
    int raresDropped = 0;
    std::vector<EncounterReceipt> receipts;
    std::vector<std::string> tipKeys;    // UMA chave de dica do relatório (kTip* abaixo; RF-44)
    // ADIÇÃO (docs/13, item 8): o selo mais fraco entre as habilidades da barra e os Únicos equipados. ManualEstimate
    // = o relatório mostra "estimativa". Entra no resultHash.
    IdleCalibration calibration = IdleCalibration::BotParity;
    std::uint64_t resultHash = 0;        // hash canônico do resultado (detecção de divergência/duplicação)
};

// ADIÇÃO (docs/tecnico/09_mudancas_contrato.md): chaves de localização das dicas do relatório do Tico.
// Existem em Content/Data/Loc/expedition.csv (pt_BR e en); o core só devolve a chave (RF-61).
// FinalizeExpedition escolhe exatamente uma, nesta prioridade:
//   recuo com poções sobrando (morreu antes de beber) → kTipLowLife;
//   recuo sem poções, ou quis curar sem ter poção     → kTipMorePotions;
//   nada a corrigir                                    → kTipAllGood.
// kTipRaisePotion ("tente subir o limiar para {pct}%") fica para quando o core souber sugerir o {pct}.
inline constexpr const char* kTipRaisePotion = "report.tip.raise_potion";
inline constexpr const char* kTipMorePotions = "report.tip.more_potions";
inline constexpr const char* kTipLowLife = "report.tip.low_life";
inline constexpr const char* kTipAllGood = "report.tip.all_good";

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

// Pré-condições para iniciar (regras 1, 5, 7 da seção 7 e incompatibilidade explícita).
enum class StartCheck : std::uint8_t {
    Ok = 0,
    MapNotConquered,      // área não vencida na mão / tier acima de (maior tier − 1)
    NotEnoughCharges,
    AnotherExpeditionRunning,
    InvalidDuration,      // fora de 1..12
    TooManyRules,         // > 6
    IdleIncompatible,     // ver blockingIds
    UnknownContent,
    ClockRollback,        // ADIÇÃO (docs/17, A2): o relógio voltou (RF-48); só a API de início confiável devolve (nada muda)
};
StartCheck CanStartExpedition(const ContentDB& db, const CharacterState& c, const ContentId& mapId,
                              int durationHours, int chargesAvailable, bool anotherRunning,
                              std::size_t ruleCount, std::vector<ContentId>* blockingIds);

// ADIÇÃO (docs/13, item 8): o selo de calibração mais fraco entre as habilidades da barra e os Únicos equipados.
// Só olha o que o simulador usa de fato (barra e equipamento); sem nenhum, BotParity.
IdleCalibration BuildIdleCalibration(const ContentDB& db, const CharacterState& c);

// Simula tudo de uma vez = SimulateRange(0, ∞) + FinalizeExpedition.
ExpeditionResult SimulateExpedition(const ContentDB& db, const ExpeditionRequest& req);

// Simula `count` encontros a partir de `start`. Exige firstEncounter == start.nextEncounter
// (senão devolve start inalterado com stop = ContentMismatch e loga). Para ao atingir
// effectiveSeconds ou outra StopReason. Um encontro que terminaria depois de effectiveSeconds
// NÃO entra (o tempo efetivo é o fim do último encontro concluído).
// Passo de simulação: RulesConstants::simStep (0,1 s).
ExpeditionProgress SimulateRange(const ContentDB& db, const ExpeditionRequest& req,
                                 const ExpeditionProgress& start,
                                 std::uint32_t firstEncounter, std::uint32_t count);

// ADIÇÃO (docs/tecnico/09_mudancas_contrato.md), RF-48: se a janela offline (clock.h) terminou porque o
// relógio do PC voltou, a parada por tempo vira StopReason::ClockRollback ("o relógio voltou"; a
// expedição encerra no último ponto conhecido). Chamar sobre o progresso final, ANTES de
// FinalizeExpedition (o resultHash inclui o motivo). Recuo e outras paradas reais não mudam.
void ApplyWindowStop(ExpeditionProgress& progress, const OfflineWindow& window);

// Aplica as regras da seção 7 UMA vez sobre os recibos, em ordem:
//   Vigor por faixa (XP e Stacks; itens não) → teto de nível (XP para quando o personagem
//   passaria 2 níveis acima do nível de monstro da área; level-up é calculado a partir do snapshot
//   mas a build NÃO muda durante a expedição) → agregação → dicas → resultHash.
ExpeditionResult FinalizeExpedition(const ContentDB& db, const ExpeditionRequest& req,
                                    const ExpeditionProgress& progress);

// Previsão em faixa para a tela da Ilsa: roda `samples` expedições com seeds derivadas
// de baseSeed (DeriveSeed(baseSeed, Events, k)) e devolve percentis 10/50/90.
struct ExpeditionForecast {
    double xpP10 = 0, xpP50 = 0, xpP90 = 0;
    double goldP10 = 0, goldP50 = 0, goldP90 = 0;
    double retreatProbability = 0;      // fração das amostras com StopReason::Retreat
    IdleCalibration calibration = IdleCalibration::BotParity;  // ADIÇÃO: selo da previsão ("estimativa" se ManualEstimate)
    DamageType worstResistGap = DamageType::Physical;  // maior fonte de dano recebido (dica de risco)
};
ExpeditionForecast ForecastExpedition(const ContentDB& db, const ExpeditionRequest& req,
                                      std::uint64_t baseSeed, int samples);

}  // namespace shatter
