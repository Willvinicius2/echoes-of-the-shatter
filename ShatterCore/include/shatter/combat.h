// ShatterCore — regras de combate novas do protótipo (docs/13_design_pendencias.md, itens 1 a 11).
// Usadas pelo combate em tempo real (pela API C) e pelo simulador idle, sem duplicar regra:
//   - Vitals: vida, recurso, barreira (regeneração, decaimento fora de combate, poção de barreira);
//   - PotionBelt: poções com cargas, recarga em série, trava global e +1 carga ao matar elite;
//   - DodgeState: esquiva com cargas e janela de invulnerabilidade;
//   - ActionStatus: stun que interrompe a preparação, imunidades e Guarda Quebrada (stagger);
//   - Elite: sorteio de modificador e multiplicadores;
//   - BossFight: fases, escudo frontal, rugido, invocação e padrões por seed.
// Todos os números vêm do ContentDB (CSV). Só + − × ÷ e sqrt nos caminhos que afetam resultado.
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "shatter/character.h"
#include "shatter/content.h"
#include "shatter/effects.h"
#include "shatter/loot.h"
#include "shatter/progress.h"
#include "shatter/rng.h"
#include "shatter/stats.h"

namespace shatter {

// IDs de efeito que o combate reconhece (identificadores, não números de balanceamento).
inline constexpr const char* kEffectGuardBreak = "effect.guard_break";

// ---------------------------------------------------------------------------
// Recarga em série (um relógio só): usada por poções e esquiva.
// ---------------------------------------------------------------------------
void TickSeriesRecharge(int& charges, int maxCharges, double& remaining, double period, double dt);

// ---------------------------------------------------------------------------
// Vitals (vida, recurso, barreira) — o que o IRulesCore do C# pede ao core.
// ---------------------------------------------------------------------------
struct Vitals {
    double life = 0.0;
    double resource = 0.0;
    double barrier = 0.0;
    double barrierSecondsLeft = 0.0;   // > 0: a barreira (de poção) some ao chegar a 0
    double potionBarrier = 0.0;        // parte de `barrier` que veio da poção (a das outras fontes não expira junto)
};

// Barreira da Poção de Resguardo (docs/13 item 2): UMA regra para o manual (Vitals, pela API C) e para o simulador idle.
// Reaplicar renova (não acumula): troca só a parte da poção; a de outras fontes fica.
void ApplyPotionBarrier(double& barrier, double& potionAmount, double& remaining, double newAmount, double seconds);
// Avança o tempo da barreira da poção: a parte da poção que o dano já gastou sai da conta; ao fim do tempo sai só a parte
// da poção. Barreira temporária sem divisão informada (potionAmount = 0 com tempo correndo) conta inteira como da poção.
void TickPotionBarrier(double& barrier, double& potionAmount, double& remaining, double dt);
// Vida cheia; recurso no repouso da classe (vazio se decai fora de combate, senão cheio).
Vitals CreateVitals(const StatBlock& stats, const ClassData* cls);
// Regeneração de vida e recurso, decaimento do recurso fora de combate e fim da barreira temporária.
void TickVitals(Vitals& v, const StatBlock& stats, const ClassData* cls, double dt, bool inCombat);
void GainResource(Vitals& v, const StatBlock& stats, double amount);
bool TrySpendResource(Vitals& v, double amount);   // false (sem gastar) se faltar recurso

// ---------------------------------------------------------------------------
// Tempos de ação
// ---------------------------------------------------------------------------
struct ActionTimingInfo {
    double windup = 0.0, impact = 0.0, recovery = 0.0;  // s, com a velocidade aplicada
    double cooldown = 0.0;                              // EffectiveCooldown (0 se a habilidade não tem recarga)
    double cost = 0.0;
};
// Velocidade de ataque (ou conjuração, se Spell) sem tags, piso 0,01 (como o simulador).
// `elite` (opcional): o telegraph (windup) NÃO encurta com attackSpeedMult do modificador e a recuperação usa recoveryMult.
struct EliteProfile;
ActionTimingInfo ComputeActionTiming(const ContentDB& db, const SkillData& skill, const StatBlock& stats,
                                     const EliteProfile* elite = nullptr);
// Velocidade final em uu/s. `baseMoveSpeedUu` > 0 (inimigo: EnemyData::moveSpeed): base × atributo MoveSpeed (multiplicador).
// `baseMoveSpeedUu` <= 0 (herói): o próprio atributo, que já vem em uu/s de class_stats.csv (move_speed = 450).
double MoveSpeedUu(const StatBlock& stats, double baseMoveSpeedUu);
// Dano base por tipo de uma habilidade: o da arma se ela escala com arma (SEM arma: unarmed_weapon_damage_physical de
// rules.csv, só físico), senão o da própria habilidade. Usado pelo simulador e pelo golpe manual.
std::array<double, kDamageTypeCount> ComputeSkillBaseDamage(const ContentDB& db, const SkillData& skill,
                                                            const ItemBaseData* weaponOrNull);
bool CanAct(const StatBlock& stats);    // AttackSpeed > 0
bool CanMove(const StatBlock& stats);   // MoveSpeed > 0
// Índice do próximo ataque do inimigo (escolha ponderada; consome exatamente 1 número). -1 se não houver.
int PickEnemyAttack(const EnemyData& enemy, Pcg32& rng);

// ---------------------------------------------------------------------------
// Poções (item 2)
// ---------------------------------------------------------------------------
struct PotionBelt {
    std::vector<PotionSlotState> slots;   // um por potions.csv, na ordem do CSV (normalizado)
    double lockoutRemaining = 0.0;        // trava global; NÃO é salva
};
// Belt cheio (todas as cargas, sem recarga pendente).
PotionBelt MakeFullPotionBelt(const ContentDB& db);
// Belt a partir do estado salvo: um slot por poção do CSV (na ordem do CSV); poção ausente entra cheia; ID que
// não existe mais é descartado; cargas acima do máximo são cortadas.
PotionBelt MakePotionBelt(const ContentDB& db, const std::vector<PotionSlotState>& saved);
void RefillPotions(const ContentDB& db, PotionBelt& belt);          // chegou ao Refúgio, checkpoint, reinício do chefe
void TickPotions(const ContentDB& db, PotionBelt& belt, double dt); // recarga em série + trava
// +1 carga ao matar elite: na poção refillOnEliteKill com MENOS cargas (empate: a primeira do CSV). true se entrou.
bool AddChargeOnEliteKill(const ContentDB& db, PotionBelt& belt);
int PotionCharges(const PotionBelt& belt, std::string_view potionId);
// A "Vida": a primeira poção de cura do CSV (nullptr se não houver). Regra de IA com ref_id vazio usa esta.
const PotionData* DefaultHealPotion(const ContentDB& db);

enum class PotionUseStatus : std::uint8_t { Ok = 0, UnknownPotion, NoCharges, LockedOut };
struct PotionOutcome {
    double healAmount = 0.0;        // vida a somar (já com o atributo PotionEffect; o chamador limita à vida máx.)
    double barrierAmount = 0.0;     // barreira nova (substitui a anterior da poção: não acumula)
    double barrierSeconds = 0.0;    // duração da barreira
    double useTime = 0.0;           // s bebendo
    double moveSpeedWhileUsing = 1.0;
    double lockout = 0.0;           // trava global iniciada
};
// Aplica o resultado de uma poção em `v`: cura limitada à vida máxima (devolve o que de fato curou) e barreira renovada.
double ApplyPotionOutcome(Vitals& v, const PotionOutcome& po, double maxLife);

// Resultado puro da poção (sem cargas nem trava): cura = fração × vida máx. × PotionEffect; barreira idem.
PotionOutcome ResolvePotion(const PotionData& potion, double maxLife, double potionEffect);
// Usa a poção do belt: confere trava e cargas, gasta 1 carga (inicia a recarga em série se estava cheia) e inicia a trava.
PotionUseStatus UsePotion(const ContentDB& db, PotionBelt& belt, std::string_view potionId, double maxLife,
                          double potionEffect, PotionOutcome* out);

// ---------------------------------------------------------------------------
// Esquiva (item 1). Cargas NÃO são salvas (reiniciam cheias ao carregar).
// ---------------------------------------------------------------------------
struct DodgeState {
    int charges = -1;                  // < 0 = cheia (ainda não iniciada)
    double rechargeRemaining = 0.0;
    bool active = false;               // dentro da esquiva (duração total)
    double elapsed = 0.0;              // s desde o início da esquiva
};
void NormalizeDodge(const RulesConstants& rules, DodgeState& d);   // charges < 0 vira cheia; corta no máximo
void TickDodge(const RulesConstants& rules, DodgeState& d, double dt);
enum class DodgeStartStatus : std::uint8_t { Ok = 0, NoCharges, Active, NotEnoughResource };
// Inicia a esquiva: gasta 1 carga e o custo de recurso (dodge_cost_resource, conferido contra `resourceAvailable`).
DodgeStartStatus TryStartDodge(const RulesConstants& rules, DodgeState& d, double resourceAvailable);
// Invulnerável de 0 (inclusive) a dodge_iframes (exclusive) desde o início.
bool DodgeInvulnerable(const RulesConstants& rules, const DodgeState& d);
// Esquiva da IA do idle: gasta 1 carga sem janela de invulnerabilidade. false se não houver carga.
bool DodgeSpendCharge(const RulesConstants& rules, DodgeState& d);
// Recurso da esquiva perfeita: dodge_perfect_resource se um golpe chegou durante os i-frames, senão 0.
double DodgePerfectReward(const RulesConstants& rules, const DodgeState& d);

// ---------------------------------------------------------------------------
// Stun, imunidades e Guarda Quebrada (item 3)
// ---------------------------------------------------------------------------
struct StatusProfile {
    bool stunImmune = false;
    bool isBoss = false;
    double staggerSeconds = 0.0;
    double immunitySeconds = 0.0;
};
// Do EnemyData, com o padrão de rules.csv quando a coluna do inimigo é 0. nullptr = alvo comum (herói).
// Imune ao stun: coluna stunImmune, chefe, elite fixo (isElite) ou `isElite` (elite sorteado) — docs/13, item 3.
StatusProfile MakeStatusProfile(const ContentDB& db, const EnemyData* enemy, bool isElite = false);

struct StatusApply {
    bool applied = false;          // o efeito entrou no contêiner
    bool stunned = false;          // stun começou (ou renovou)
    bool stunBlocked = false;      // alvo imune ao stun: nada foi aplicado
    bool interrupted = false;      // a preparação (telegraph) em andamento deve ser cancelada
    bool staggered = false;        // Guarda Quebrada: os acúmulos foram consumidos e o alvo está atordoado
    bool removeBarrier = false;    // o chamador zera a barreira/escudo do alvo
    int guardBreakStacks = 0;      // acúmulos de Guarda Quebrada depois desta aplicação
    double stunSeconds = 0.0;
    double staggerSeconds = 0.0;
};

class ActionStatus {
public:
    ActionStatus() = default;
    explicit ActionStatus(const StatusProfile& p) : profile_(p) {}
    void Init(const StatusProfile& p) { *this = ActionStatus(p); }

    // Aplica um efeito no alvo (statblock + contêiner dele). Efeito com interruptsAction vira stun real (alvo imune
    // ignora). A Guarda Quebrada usa timer único; no N-ésimo acúmulo (N = maxStacks do efeito), alvo stunImmune sem
    // imunidade ativa entra em stagger. allowStagger = false (ex.: chefe no rugido) acumula sem atordoar.
    StatusApply ApplyEffect(const ContentDB& db, const EffectData& effect, std::string_view source, double magnitude,
                            TriggerKind triggeredBy, EffectContainer& fx, StatBlock& target, bool allowStagger = true);
    // Atordoa o alvo por `seconds` (bônus de dano recebido durante o stagger). false se já estiver em stagger.
    // Não mexe na imunidade a nova Guarda Quebrada.
    bool BeginStagger(const ContentDB& db, double seconds, StatBlock& target);
    // Avança os relógios; ao fim do stagger remove o bônus de dano recebido. Devolve true se o stagger acabou agora.
    bool Tick(double dt, StatBlock& target);

    bool Stunned() const { return stunRemaining_ > 1e-9; }
    bool Staggered() const { return staggerRemaining_ > 1e-9; }
    bool CanAct() const { return !Stunned() && !Staggered(); }
    double StunRemaining() const { return stunRemaining_; }
    double StaggerRemaining() const { return staggerRemaining_; }
    double ImmunityRemaining() const { return immunityRemaining_; }
    const StatusProfile& Profile() const { return profile_; }

private:
    StatusProfile profile_;
    double stunRemaining_ = 0.0;
    double staggerRemaining_ = 0.0;
    double immunityRemaining_ = 0.0;
};

// ---------------------------------------------------------------------------
// Elite (item 5)
// ---------------------------------------------------------------------------
struct EliteProfile {
    ContentId modifierId;              // vazio = só os multiplicadores base
    bool rolled = false;               // sorteado por chanceElite (os multiplicadores base de rules.csv valem)
    double lifeMult = 1.0, damageMult = 1.0, xpMult = 1.0;
    double barrierFractionOfLife = 0.0;
    double moveSpeedMult = 1.0, attackSpeedMult = 1.0, recoveryMult = 1.0;
    double deathExplosionRadius = 0.0, deathExplosionDamage = 0.0, deathExplosionFuse = 0.0;
};
// Sorteia o modificador pelos pesos weightPrototype (peso 0 = desligado). Consome SEMPRE exatamente 1 número.
// nullptr se nenhum tem peso.
const EliteModifierData* RollEliteModifier(const ContentDB& db, Pcg32& eventsRng);
// Elite sorteado (rolled = true): lifeMult/damageMult/xpMult = elite_*_mult × os do modificador.
// Elite fixo (rolled = false, `mod` = EnemyData::modifierId): só os do modificador (os números do inimigo já são de elite).
EliteProfile MakeEliteProfile(const ContentDB& db, const EliteModifierData* mod, bool rolled);
// Escreve no StatBlock (source "elite"): Life/Damage More (mult − 1), MoveSpeed e AttackSpeed More. O chamador chama
// depois de BuildEnemyStatBlock. Barreira inicial = EliteBarrier(...).
void ApplyEliteToStats(const EliteProfile& p, StatBlock& stats);
double EliteBarrier(const EliteProfile& p, double maxLife);
// Tabela de loot do inimigo: eliteLootTableId do EnemyData se for elite sorteado e a coluna existir, senão a do inimigo.
const ContentId& EliteLootTable(const EnemyData& enemy, bool rolled);

// ---------------------------------------------------------------------------
// Chefe (item 4 e 6)
// ---------------------------------------------------------------------------
struct Vec2 {
    double x = 0.0, z = 0.0;
};

// Trigonometria determinística (série de Taylor; só + − × ÷). Ângulo em radianos, |x| <= pi.
double DetCos(double x);
double DetSin(double x);

enum class BossState : std::uint8_t { Idle = 0, Waiting, Telegraph, Impact, Recovery, Stagger, Transition, Dead };

struct BossEvent {
    enum class Kind : std::uint8_t {
        PatternStart = 0,      // telegraph começou: patternId, skillId, seconds = duração do telegraph
        PatternImpact,         // o golpe acerta agora (forma pela skill); seconds = duração do impacto
        PatternEnd,            // recuperação terminou
        PatternInterrupted,    // stagger cancelou o padrão em andamento
        PhaseTransitionStart,  // rugido invulnerável: phase = nova fase, seconds = duração
        SummonMarker,          // marca no chão: enemyId, count; seconds = tempo até surgirem
        SummonSpawn,           // surgem enemyId × count (sem XP e sem loot; morrem com o chefe)
        PhaseTransitionEnd,
        StaggerStart,          // seconds = duração
        StaggerEnd,
        ShieldDown,            // escudo frontal caiu; seconds = duração
        ShieldUp,
        Died,
    };
    Kind kind = Kind::PatternStart;
    int phase = 1;
    ContentId patternId;
    ContentId skillId;
    ContentId enemyId;
    int count = 0;
    double seconds = 0.0;
};

class BossFight {
public:
    // `seed`: seed do fluxo de eventos (Pcg32::ForStream(seed, Events, 0)); mesma seed + dados = mesma sequência.
    BossFight(const ContentDB& db, const EnemyData& boss, int level, std::uint64_t seed);

    bool Valid() const { return boss_ != nullptr && !phases_.empty(); }
    // Reinício total (morte do jogador): vida cheia, fase 1, escudo de pé, relógios zerados, padrões liberados.
    // O RNG NÃO volta ao início (a luta seguinte sorteia de novo). As invocadas são removidas pelo chamador.
    void Reset(StatBlock* stats = nullptr);   // `stats`: se informado, remove o bônus de dano do stagger
    // O jogador entrou na arena: a primeira ação só vem depois de transitionSeconds da fase 1 (ou de um atraso sorteado).
    void Start();

    struct Context {
        Vec2 boss;      // posição do chefe
        Vec2 player;    // posição do jogador
    };
    // Passo fixo. Gira (fora de telegraph/impacto), conta relógios e dirige a máquina de estados. Eventos em `out` (anexa).
    void Step(double dt, const Context& ctx, StatBlock& stats, std::vector<BossEvent>& out);

    struct DamageResult {
        double applied = 0.0;        // dano que de fato tirou vida
        double lifeAfter = 0.0;
        bool shieldBlocked = false;  // escudo frontal: 0 de dano, sem Ímpeto, sem knockback
        bool invulnerable = false;   // rugido da transição
        bool clampedByPhase = false; // dano excedente cortado no limiar da próxima fase
        bool killed = false;
    };
    // Dano JÁ calculado por ResolveHit (o escudo/limiar são regras do chefe, aplicadas depois). `origin` = posição do
    // atacante (para área, o centro do alvo atingido).
    DamageResult ApplyDamage(double amount, Vec2 bossPos, Vec2 origin, std::vector<BossEvent>& out);
    // Efeito no chefe (stun é ignorado: o chefe é imune; Guarda Quebrada acumula e no limite entra em stagger,
    // interrompe o padrão e derruba o escudo). `fx` e `stats` são os do chefe (do chamador).
    StatusApply ApplyEffect(const ContentDB& db, const EffectData& effect, std::string_view source, double magnitude,
                            EffectContainer& fx, StatBlock& stats, std::vector<BossEvent>& out);
    // A investida bateu em pilar ou parede: se o padrão em curso (impacto) tem wallStaggerSeconds > 0, o chefe entra em
    // stagger por esse tempo, interrompe o padrão e o escudo cai (fase `shieldSeconds` ou boss_shield_down_seconds).
    // false (nada muda) fora do impacto, sem padrão em curso ou se já estiver em stagger.
    bool OnWallHit(StatBlock& stats, std::vector<BossEvent>& out);
    // O ponto de origem está dentro do escudo frontal (e o escudo está de pé)?
    bool ShieldCovers(Vec2 bossPos, Vec2 origin) const;

    double Life() const { return life_; }
    double MaxLife() const { return maxLife_; }
    int Phase() const { return phase_; }
    BossState State() const { return state_; }
    bool Invulnerable() const { return state_ == BossState::Transition; }
    bool ShieldUp() const { return shieldDown_ <= 1e-9; }
    double ShieldDownRemaining() const { return shieldDown_; }
    Vec2 Facing() const { return facing_; }
    double TurnRateDegPerSec() const { return turnRate_; }
    // Padrão atual (válido de Telegraph a Recovery); nullptr fora disso.
    const BossPatternData* CurrentPattern() const { return state_ >= BossState::Telegraph && state_ <= BossState::Recovery ? current_ : nullptr; }
    const ActionStatus& Status() const { return status_; }

private:
    void EnterPhase(int phase, std::vector<BossEvent>& out);
    void BeginWaiting(bool intro);
    void StartTransition(std::vector<BossEvent>& out);
    void PickAndStart(const Context& ctx, std::vector<BossEvent>& out);
    void Rotate(double dt, const Context& ctx);
    void EnterStagger(double seconds, std::vector<BossEvent>& out);
    double PhaseThresholdLife(int phase) const;
    const BossPhaseData* PhaseData(int phase) const;

    const ContentDB* db_ = nullptr;
    const EnemyData* boss_ = nullptr;
    std::vector<const BossPhaseData*> phases_;      // ordem crescente de fase
    std::vector<const BossPatternData*> patterns_;  // todos os padrões do chefe, na ordem do CSV
    std::vector<double> patternCooldown_;
    Pcg32 rng_;
    ActionStatus status_;
    BossState state_ = BossState::Idle;
    int phase_ = 1;
    double life_ = 0.0, maxLife_ = 0.0;
    double timer_ = 0.0;                 // do estado atual
    double shieldDown_ = 0.0;
    double turnRate_ = 0.0;
    Vec2 facing_{0.0, 1.0};
    bool faceSnap_ = true;
    bool pendingTransition_ = false;
    int lastPattern_ = -1;
    int repeatCount_ = 0;
    const BossPatternData* current_ = nullptr;
    double impactSeconds_ = 0.0;
    double recoverySeconds_ = 0.0;
    // Transição
    double transitionLength_ = 0.0;
    bool summonMarked_ = false, summonDone_ = false;
    double summonAtFraction_ = 0.5;
    int summonCount_ = 0;
    ContentId summonEnemy_;
};

// ---------------------------------------------------------------------------
// Drop do Único (item 9): usa RollLootTable com LootContext::bossProgress. Esta função roda a tabela do chefe no
// modo Manual com o contador do personagem e DEVOLVE o loot; o contador já avançou (persista o save ANTES de
// entregar o item, para a coleta não duplicar — RF-55).
// ---------------------------------------------------------------------------
LootDrop RollBossLoot(const ContentDB& db, const EnemyData& boss, int areaLevel, BossProgressEntry& progress,
                      std::uint64_t* nextItemUid, Pcg32& lootRng);

}  // namespace shatter
