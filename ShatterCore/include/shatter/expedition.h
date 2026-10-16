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
    UsePotion = 0,      // cura de poção; falha (e conta healFailures) se potions == 0
    UseSkill,           // refId = skill id; precisa estar na barra, fora de recarga e com recurso
};

struct AiRule {
    AiCondition condition = AiCondition::Always;
    double param = 0.0;
    AiAction action = AiAction::UseSkill;
    ContentId refId;    // skill ou efeito, conforme acima
};

// ---------------------------------------------------------------------------
// Pedido: tudo que a simulação precisa. Congelado no início; gravado no save.
// ---------------------------------------------------------------------------
struct ExpeditionRequest {
    CharacterSnapshot snapshot;          // build congelada
    ContentId mapId;                     // área dominada (validada por CanStartExpedition)
    ExpeditionObjective objective = ExpeditionObjective::Xp;
    std::vector<AiRule> rules;           // máx. RulesConstants::maxAiRules (6)
    double potionHealFraction = 0.35;    // cura da poção como fração da vida máx. (vem de dados; copiado aqui)
    std::uint64_t seed = 0;              // seed da expedição (gerada no início; fluxo independente do jogo)
    UnixSeconds startUtc = 0;
    int durationHours = 1;               // 1..12, limitado pelas Cargas do Marco
    // Segundos de jogo a simular de fato (calculado por clock.h a partir de agora/last_seen).
    // Nunca maior que durationHours×3600 nem que maxOfflineHours×3600.
    double effectiveSeconds = 0.0;
    std::uint32_t contentVersion = 0;    // ContentDB::ContentVersion() no início
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
    std::int64_t potionsLeft = -1;       // < 0 = pegar do snapshot
    int raresDropped = 0;
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
    std::uint64_t resultHash = 0;        // hash canônico do resultado (detecção de divergência/duplicação)
};

// ADIÇÃO (docs/09_mudancas_contrato.md): chaves de localização das dicas do relatório do Tico.
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
};
StartCheck CanStartExpedition(const ContentDB& db, const CharacterState& c, const ContentId& mapId,
                              int durationHours, int chargesAvailable, bool anotherRunning,
                              std::size_t ruleCount, std::vector<ContentId>* blockingIds);

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

// ADIÇÃO (docs/09_mudancas_contrato.md), RF-48: se a janela offline (clock.h) terminou porque o
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
    DamageType worstResistGap = DamageType::Physical;  // maior fonte de dano recebido (dica de risco)
};
ExpeditionForecast ForecastExpedition(const ContentDB& db, const ExpeditionRequest& req,
                                      std::uint64_t baseSeed, int samples);

}  // namespace shatter
