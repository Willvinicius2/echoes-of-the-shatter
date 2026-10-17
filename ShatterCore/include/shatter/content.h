// ShatterCore — dados de conteúdo (somente leitura em tempo de jogo).
// Fonte da verdade: CSV em EchoesOfTheShatter/Content/Data/*.csv (UTF-8, vírgula,
// 1ª linha = cabeçalho, listas internas separadas por '|'). O mesmo CSV alimenta:
//   - o ShatterCore (ContentDB::LoadTableCsv) — no jogo, nos testes e no bench;
//   - opcionalmente DataTables no editor UE, só para visualização.
// Esquemas das colunas: docs/06_dados.md (Data Engineer). Nomes de campo abaixo = nomes de coluna.
#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "shatter/constants.h"
#include "shatter/effects.h"
#include "shatter/item.h"
#include "shatter/stats.h"
#include "shatter/types.h"

namespace shatter {

// Valor de atributo por nível: base + perLevel × (nível − 1).
struct StatGrowth {
    StatId stat = StatId::Life;
    double base = 0.0;
    double perLevel = 0.0;
};

// ---------------------------------------------------------------------------
struct ClassData {                         // classes.csv + class_stats.csv
    ContentId id;                          // "class.warrior"
    ContentId resourceId;                  // "resource.momentum" | "resource.focus" | "resource.mana"
    std::vector<StatGrowth> stats;         // vida, recurso, regen, armadura base...
    ContentId startingSkill;               // "skill.warrior.iron_cut"
    std::vector<ContentId> specializations;// "spec.warrior.bastion", "spec.warrior.breaker"
    // Regras de recurso (por classe, sem código específico):
    double resourceOnHit = 0.0;            // Ímpeto ao acertar
    double resourceOnBlock = 0.0;          // Ímpeto ao bloquear
    double resourceDecayOutOfCombat = 0.0; // Ímpeto/s fora de combate
    double regenMultWhileMoving = 1.0;     // Foco: 0.3 andando, 1.0 parado
};

// Forma espacial da habilidade no tempo real (o UE escolhe o "behavior" por este enum).
enum class SkillShape : std::uint8_t { Melee, Cone, Projectile, Area, Dash, Self, Channel, Trap };
bool ParseSkillShape(std::string_view text, SkillShape& out);

// Selo de calibração do perfil idle (docs/13, item 8). `ManualEstimate` = estimativa manual (amostra jogada e medida
// pelo dono): a previsão e o relatório mostram "estimativa". `BotParity` = calibrado pelo teste de paridade.
// `None` = não calibrado (nunca pode ser idleSupported).
enum class IdleCalibration : std::uint8_t { None = 0, ManualEstimate = 1, BotParity = 2 };
bool ParseIdleCalibration(std::string_view text, IdleCalibration& out);  // "none" | "manual_estimate" | "bot_parity"
const char* ToString(IdleCalibration c);
// O pior selo entre dois (None < ManualEstimate < BotParity): a previsão mostra o mais fraco da build.
inline IdleCalibration WeakestCalibration(IdleCalibration a, IdleCalibration b) {
    return static_cast<std::uint8_t>(a) <= static_cast<std::uint8_t>(b) ? a : b;
}

// Tradução do espacial para números, usada só pelo simulador idle.
// Calibrado pelo teste de paridade, nunca chutado. Sem IdleProfile validado → expedição bloqueada.
struct IdleProfile {
    bool supported = false;                // false = "ainda não funciona em patrulha" (bloqueia)
    double avgTargetsHit = 1.0;            // alvos médios atingidos (por inimigo vivo, limitado ao grupo)
    double fractionOfGroupHit = 0.0;       // alternativa: fração do grupo (0 = usar avgTargetsHit)
    double approachTime = 0.0;             // s gastos para alcançar alvos (melee vs atiradores)
    double uptime = 1.0;                   // fração do tempo em que a habilidade é usável de fato
    double dodgeTelegraphedBonus = 0.0;    // soma à esquiva base da IA (Recuo Ágil, Passagem Arcana)
    double damageTakenMult = 1.0;          // distância/posicionamento (arqueiro leva menos)
    std::uint32_t paritySampleSize = 0;    // nº de encontros usados na calibração (0 = não calibrado)
    IdleCalibration calibration = IdleCalibration::None;  // selo: manual_estimate | bot_parity (supported exige != none)
};

struct SkillData {                         // skills.csv
    ContentId id;                          // "skill.warrior.cleave"
    ContentId classId;                     // dona (vazio = qualquer classe pode aprender)
    ContentId specId;                      // vazio = básica
    TagMask tags = 0;
    SkillShape shape = SkillShape::Melee;
    bool scalesWithWeapon = false;         // true: baseDamage vem da arma
    std::array<double, kDamageTypeCount> baseDamage{};
    std::array<double, 3> coefficientByRank = {1.0, 1.0, 1.0}; // rank 1..3
    double cost = 0.0;                     // recurso; mínimo 0
    double cooldown = 0.0;                 // s; mínimo RulesConstants::minCooldown se > 0
    double windup = 0.0;                   // s de preparação
    double impact = 0.0;                   // s até o golpe acertar após windup
    double recovery = 0.0;                 // s de recuperação
    double range = 0.0;                    // unidades de mundo (px da arte); só tempo real
    double radius = 0.0;
    int projectiles = 1;
    double coneAngle = 0.0;                // graus; forma de cone no tempo real (0 = sem cone)
    double knockback = 0.0;                // uu empurrados no alvo; só tempo real
    double wallStaggerSeconds = 0.0;       // > 0: stagger do atacante ao bater em pilar/parede na investida (BossFight::OnWallHit)
    double projectileSpeed = 0.0;          // uu/s; só tempo real
    // Coluna OPCIONAL `pierce` (docs/18 8.2), só tempo real e só shape projectile: 0 = nenhuma; N = atravessa N alvos além
    // do primeiro; kPierceAll (99) = atravessa todos. Cada projétil acerta o mesmo alvo uma vez (RF-16).
    int pierce = 0;
    // Coluna OPCIONAL `explosionRadius` (uu): raio da explosão no impacto de um projétil (caso (a) de docs/18 8.3). 0 = sem
    // explosão. `radius` num projétil é só a largura de colisão do corredor; as duas não se misturam. Só shape projectile.
    double explosionRadius = 0.0;
    std::vector<ContentId> onHitEffects;   // "effect.burn", "effect.guard_break"
    std::vector<ContentId> selfEffects;    // aplicados em quem usa (Postura Firme, Barreira de Vidro)
    IdleProfile idle;
    int unlockLevel = 1;
};

inline constexpr int kPierceAll = 99;

// Comportamento em tempo real que os dados de uma habilidade determinam (docs/18 §8 item 3). UMA interpretação, no core:
// o cliente escolhe a geometria por estes campos em vez de reler shape/range/radius.
//  (a) projétil com explosionRadius > 0 explode no impacto e acerta todos os alvos da área uma vez (explodes); `radius` do
//      projétil é só a largura de colisão;
//  (b) projétil com projectiles > 1 e coneAngle > 0 sai em leque de coneAngle graus (fan);
//  (c) área com range 0 é centrada em quem usa (selfCentered);
//  (d) área com range > 0 cai no cursor, limitada a `range` uu do herói; `impact` é o atraso até acertar (groundTargeted);
//  (e) dash com tag projectile pula `range` uu para trás e atira em dash_shot_range no pico (dashBackShot).
struct SkillBehavior {
    bool explodes = false;
    bool fan = false;
    bool selfCentered = false;
    bool groundTargeted = false;
    bool dashBackShot = false;
    int pierce = 0;                        // = SkillData::pierce (0 nenhuma; kPierceAll todos)
};
SkillBehavior ClassifySkill(const SkillData& skill);

// Comportamento base de IA do inimigo (máquina parado→perseguir→telegraph→atacar→recuperar).
struct EnemyAttack {
    ContentId skillId;                     // reusa SkillData (inimigos também usam skills.csv)
    double weight = 1.0;                   // escolha ponderada
    bool telegraphed = false;              // IA do jogador pode esquivar (idle: aiBaseDodgeTelegraphed)
};

struct EnemyData {                         // enemies.csv + enemy_attacks.csv
    ContentId id;                          // "enemy.hollow_sentinel"
    ContentId familyId;                    // "family.soldier_echo"
    std::vector<StatGrowth> stats;         // escalam pelo nível do monstro
    std::vector<EnemyAttack> attacks;
    double xpBase = 0.0;                   // XP no nível 1; escala por xpPerLevel
    double xpPerLevel = 0.0;
    ContentId lootTableId;
    bool isBoss = false;
    bool isElite = false;
    double moveSpeed = 0.0;                // tempo real
    double aggroRange = 0.0;               // tempo real
    // ADIÇÃO (docs/09, docs/13 itens 3 a 5): stun, Guarda Quebrada, escudo frontal e elite fixo.
    bool stunImmune = false;               // imune a effect.stun (elite, Arauto, chefe); sofre Guarda Quebrada
    double shieldArcDegrees = 0.0;         // escudo frontal: arco TOTAL em graus (120 = ±60° em torno da frente); 0 = sem escudo
    double turnRateDegPerSec = 0.0;        // giro (fase 1)
    double turnRateDegPerSecPhase2 = 0.0;  // giro (fase 2); 0 = igual ao da fase 1
    double guardBreakStaggerSeconds = 0.0; // 0 = usa guard_break_stagger_seconds de rules.csv
    double guardBreakImmunitySeconds = 0.0;// 0 = usa guard_break_immunity_boss (chefe) ou _other (demais) de rules.csv
    ContentId modifierId;                  // elite fixo: modificador já aplicado (modifier.elite.*); vazio = nenhum
    ContentId eliteLootTableId;            // coluna OPCIONAL: tabela do elite sorteado (vazio = a do próprio inimigo)
    double patrolSpeedMult = 0.0;          // 0 = não patrulha; (0,1] = fração da velocidade de perseguição ao patrulhar
};

enum class AffixKind : std::uint8_t { Prefix, Suffix };

struct AffixData {                         // affixes.csv
    ContentId id;                          // "affix.life_flat"
    AffixKind kind = AffixKind::Prefix;
    StatId stat = StatId::Life;
    ModKind modKind = ModKind::Flat;
    TagMask requiredTags = 0;              // tags do mod gerado
    double minValue = 0.0;                 // faixa do valor (min <= max, validado)
    double maxValue = 0.0;
    int minItemLevel = 1;
    double weight = 1.0;                   // peso de sorteio (> 0)
    std::vector<ItemSlot> allowedSlots;    // vazio = qualquer
    std::string group;                     // afixos do mesmo grupo não coexistem no item
    bool craftInscription = false;         // aparece na lista de Fixar Inscrição
};

struct ItemBaseData {                      // item_bases.csv
    ContentId id;                          // "item_base.iron_sword"
    ItemSlot slot = ItemSlot::MainHand;
    int itemLevel = 1;
    std::vector<Modifier> implicitMods;    // propriedade da base
    std::array<double, kDamageTypeCount> weaponDamage{};  // só armas
    double attackTime = 0.0;               // s por ataque (só armas)
    TagMask weaponTags = 0;                // Melee ou Projectile
    char grammaticalGender = 'm';          // 'm' | 'f' — nomes gerados em pt-BR/es
    ContentId visualSetId;                 // ADIÇÃO (C-10d): vset.* para a Unity escolher o visual; vazio = vset.starter. Fora do resultHash
};

struct UniqueData {                        // uniques.csv
    ContentId id;                          // "unique.bell_warden_helm"
    ContentId baseId;
    std::vector<Modifier> fixedMods;
    ContentId ruleEffectId;                // efeito que muda a build
    bool idleSupported = false;            // sem perfil testado → bloqueia expedição
    std::uint32_t idleParitySampleSize = 0;               // amostra da calibração (supported exige > 0)
    IdleCalibration idleCalibration = IdleCalibration::None;  // selo (supported exige != none)
    ContentId visualSetId;                 // ADIÇÃO (C-10d): prevalece sobre a da base; vazio = usa a da base. Fora do resultHash
};

// Entrada de tabela de loot. Uma entrada sorteia UMA coisa.
enum class LootEntryKind : std::uint8_t {
    ItemBase,      // refId = item_base.*; raridade rolada por rarityWeights
    Unique,        // refId = unique.*
    Stack,         // refId = currency.gold / material.* / page.* / sigil.common.*
    SpecBook,      // refId = book.spec.*
    MapStone,      // refId = map_stone.*
    EchoFragment,  // refId = material.echo_fragment
    Table,         // refId = loot.* (subtabela)
    Nothing,
};

struct LootEntry {
    LootEntryKind kind = LootEntryKind::Nothing;
    ContentId refId;
    double weight = 1.0;                   // > 0
    std::int64_t minAmount = 1;            // Stack
    std::int64_t maxAmount = 1;
    int minAreaLevel = 1;                  // fora do tier não cai
    int maxAreaLevel = 999;
    bool manualOnly = false;               // nunca cai no idle (Únicos, livros de spec, pedras, fragmentos)
    // ADIÇÃO (docs/13, item 9): entrada "fixa", fora do sorteio ponderado (o peso não dilui as outras).
    double fixedChance = 0.0;              // 0..1: chance própria a cada vitória
    bool guaranteeFirstKill = false;       // cai na 1ª vitória sobre o chefe
    int pityKills = 0;                     // > 0: garantida na N-ésima vitória seguida sem cair (0 = sem proteção)
    bool IsFixed() const { return fixedChance > 0.0 || guaranteeFirstKill || pityKills > 0; }
};

struct LootTableData {                     // loot_tables.csv
    ContentId id;                          // "loot.crypt.common"
    int rolls = 1;                         // nº de sorteios por chamada
    double dropChance = 1.0;               // chance de cada sorteio cair
    std::vector<LootEntry> entries;
    // Pesos base de raridade para ItemBase: Normal, Magic, Rare (Unique só por entrada Unique).
    std::array<double, 3> rarityWeights = {80.0, 18.0, 2.0};
};

// Um grupo de inimigos dentro de um encontro.
struct EncounterGroup {
    ContentId enemyId;
    int countMin = 1;
    int countMax = 1;
    double eliteChance = 0.0;              // fluxo Events
};

struct EncounterTemplate {                 // encounters.csv
    ContentId id;                          // "enc.crypt.patrol_a"
    std::vector<EncounterGroup> groups;
    double weight = 1.0;                   // escolha do próximo encontro (fluxo Events)
    double travelTime = 0.0;               // s de travessia até o próximo grupo
    bool isBoss = false;
};

struct MapData {                           // maps.csv
    ContentId id;                          // "map.act1.crypt" | "map.endgame.ossuary"
    int monsterLevel = 1;
    int tier = 0;                          // 0 = campanha; 1..5 endgame
    std::vector<ContentId> encounters;     // EncounterTemplate ids
    ContentId bossEncounter;               // vazio se não houver
    ContentId areaLootTable;               // loot extra por encontro concluído (ouro/materiais)
    bool idleAllowed = true;               // o mapa pode ser rota de expedição (se dominado)
};


// Kit básico de uma classe (basic_kits.csv, docs/18 4.6): combo de golpes leves, golpe forte carregado e defesa. TABELA
// OPCIONAL: classe sem linha não tem kit. A máquina (índice do combo, janelas, carga) roda no C#; o core guarda e valida.
inline constexpr std::size_t kMaxLightChain = 3;
inline constexpr std::size_t kMaxGuardPerfectEffects = 4;
struct BasicKitData {
    ContentId classId;                     // chave primária
    std::vector<ContentId> lightChain;     // 1 a 3 golpes leves em ordem; o mesmo ID pode repetir
    ContentId heavySkill;                  // golpe forte
    double heavyChargeTime = 0.0;          // s de carga depois de heavy_hold_threshold (> 0)
    double heavyMaxMult = 1.0;             // multiplicador de dano na carga máxima (>= 1; linear)
    ContentId chargeEffect;                // reaplicado a cada tick enquanto carrega
    ContentId guardEffect;                 // reaplicado a cada tick enquanto defende (tag guard)
    double guardArc = 0.0;                 // graus, arco TOTAL da defesa (0 a 360)
    double guardMaxHold = 0.0;             // s; 0 = ilimitado
    double guardCooldown = 0.0;            // s de espera depois de soltar (ou de cair sozinha)
    double guardPerfectWindow = 0.0;       // s depois do aperto; 0 = sem defesa perfeita
    double guardPerfectCooldown = 0.0;     // s mínimos desde o último aperto para a janela abrir de novo
    std::vector<ContentId> guardPerfectEffects;  // aplicados no atacante corpo a corpo (no máximo kMaxGuardPerfectEffects)
    double guardPerfectResource = 0.0;     // recurso ganho pela perfeita (substitui resourceOnBlock)
    double guardDrainPerDamage = 0.0;      // recurso gasto por ponto de dano evitado; 0 = não gasta
};

// ---------------------------------------------------------------------------
// ADIÇÃO (docs/09, docs/13): poções, modificadores de elite, fases e padrões do chefe, IA dos comuns.
// ---------------------------------------------------------------------------
enum class PotionKind : std::uint8_t { Heal = 0, Barrier = 1 };
bool ParsePotionKind(std::string_view text, PotionKind& out);  // "heal" | "barrier"

struct PotionData {                        // potions.csv
    ContentId id;                          // "potion.life" | "potion.ward"
    PotionKind kind = PotionKind::Heal;
    double fractionOfMaxLife = 0.0;        // cura (heal) ou barreira (barrier), como fração da vida máxima
    double duration = 0.0;                 // s; só barrier (a barreira some ao fim)
    int maxCharges = 1;
    double rechargeSeconds = 0.0;          // por carga, em série (um relógio só)
    double useTime = 0.0;                  // s bebendo
    double moveSpeedWhileUsing = 1.0;      // fração da velocidade durante o uso (tempo real)
    double globalLockout = 0.0;            // s; 0 = usa potion_lockout de rules.csv
    bool refillOnEliteKill = false;        // entra na regra "+1 carga ao matar elite"
    int hotkeySlot = 1;                    // 1..9 (tecla)
};

struct EliteModifierData {                 // elite_modifiers.csv
    ContentId id;                          // "modifier.elite.shield"
    double weightPrototype = 0.0;          // peso de sorteio no protótipo (0 = desligado)
    double lifeMult = 1.0;                 // multiplica elite_life_mult (elite sorteado) ou a vida do elite fixo
    double damageMult = 1.0;
    double xpMult = 1.0;
    double barrierFractionOfLife = 0.0;    // barreira inicial = fração × vida máxima
    double moveSpeedMult = 1.0;
    double attackSpeedMult = 1.0;          // não encurta o telegraph (só impacto + recuperação)
    double recoveryMult = 1.0;
    double deathExplosionRadius = 0.0;     // > 0: explode ao morrer
    double deathExplosionDamage = 0.0;
    double deathExplosionFuse = 0.0;       // s entre a marca e a explosão
};

struct BossPhaseData {                     // boss_phases.csv (uma linha por bossId + phase)
    ContentId bossId;
    int phase = 1;                         // 1, 2, ...
    double lifeThreshold = 1.0;            // a fase começa quando vida/vida máx <= limiar (fase 1: 1.0)
    double transitionSeconds = 0.0;        // ao ENTRAR na fase: espera (fase 1: abertura) ou rugido invulnerável (fase >= 2)
    ContentId summonEnemyId;               // invocado no meio da transição (vazio = nada)
    int summonCount = 0;
    double shieldSeconds = 0.0;            // tempo do escudo caído após Guarda Quebrada nesta fase (0 = boss_shield_down_seconds)
    double summonAtFraction = 0.0;         // (0,1): fração da transição em que surgem os invocados; obrigatória se summonCount > 0
    double turnRate = 0.0;                 // graus/s nesta fase (0 = turnRateDegPerSec[Phase2] do inimigo)
    double decisionDelayMin = 0.0;         // atraso sorteado entre ações
    double decisionDelayMax = 0.0;
};

struct BossPatternData {                   // boss_patterns.csv
    ContentId id;                          // "pattern.guardian.hammer" (repete por fase: chave = id + phase)
    ContentId bossId;
    int phase = 1;                         // fase em que o padrão vale
    ContentId skillId;                     // skill.enemy.* (dano, impacto, alcance, cone)
    double weight = 1.0;
    double telegraphSeconds = 0.0;         // substitui windup da skill neste padrão
    double recoverySeconds = 0.0;          // substitui recovery da skill neste padrão
    double cooldown = 0.0;                 // recarga própria do padrão (s)
    int maxRepeat = 0;                     // máx. de vezes SEGUIDAS (0 = sem limite)
    double playerNearWeightMult = 1.0;     // multiplica o peso se o jogador está perto E na frente (alcance da skill)
    bool ignoreIfBehind = false;           // peso 0 se o jogador está atrás do chefe
};

struct EnemyAiData {                       // enemy_ai.csv (IA em tempo real dos comuns; o core guarda e valida)
    ContentId enemyId;
    double aggroRange = 0.0, alertRadius = 0.0, leashRange = 0.0, leashSeconds = 0.0;
    double preferredMin = 0.0, preferredMax = 0.0, retreatBelow = 0.0, retreatMaxSeconds = 0.0;
    double circleMin = 0.0, circleMax = 0.0, circleSpeed = 0.0;
    int attackTokens = 0;
    double tokenIntervalMin = 0.0, tokenIntervalMax = 0.0;
    double fleeLifeFraction = 0.0;         // > 0: foge abaixo desta fração de vida
    double fleeSeconds = 0.0;
    bool fleeOncePerLife = false;
    double attackCooldown = 0.0;
    int maxSimultaneousShooters = 0;
    bool requireOnScreen = false;          // R-VIS-1: atirador só mira com o alvo dentro da tela (margem require_on_screen_margin)
};

// ---------------------------------------------------------------------------
// Banco de conteúdo. Carregado uma vez; depois é imutável e pode ser lido de
// várias threads (o simulador roda fora da game thread).
// ---------------------------------------------------------------------------
struct ContentError {
    std::string table;   // "skills.csv"
    int line = 0;        // linha 1-based (0 = global)
    std::string message; // em inglês (log técnico)
};

class ContentDB {
public:
    ContentDB();
    ~ContentDB();
    ContentDB(const ContentDB&) = delete;
    ContentDB& operator=(const ContentDB&) = delete;
    ContentDB(ContentDB&&) noexcept;
    ContentDB& operator=(ContentDB&&) noexcept;

    // Carrega uma tabela a partir do texto CSV. tableName = nome do arquivo
    // ("rules.csv", "classes.csv", "class_stats.csv", "skills.csv", "effects.csv",
    //  "enemies.csv", "enemy_attacks.csv", "affixes.csv", "item_bases.csv", "uniques.csv",
    //  "loot_tables.csv", "loot_entries.csv", "encounters.csv", "maps.csv", "meta.csv";
    //  ADIÇÃO, opcionais: "potions.csv", "elite_modifiers.csv", "boss_phases.csv", "boss_patterns.csv", "enemy_ai.csv";
    //  docs/18, opcional de verdade: "basic_kits.csv").
    // Erros são acumulados; retorna false se houve algum nesta tabela.
    bool LoadTableCsv(std::string_view tableName, std::string_view csvText);
    // Conveniência fora do UE (testes, bench, ferramentas): lê todos os *.csv de uma pasta.
    bool LoadDirectory(const std::string& path);

    // Valida tudo após carregar: IDs únicos e válidos, referências existentes,
    // min <= max, pesos > 0, toda skill/único com idle.supported tem paritySampleSize > 0, etc.
    // Deve ser chamada uma vez; o jogo NÃO inicia com erros (no CI, o build falha).
    bool Finalize();
    const std::vector<ContentError>& Errors() const { return errors_; }

    // Versão do conteúdo (meta.csv: content_version). Gravada em todo save e expedição.
    std::uint32_t ContentVersion() const { return contentVersion_; }
    const RulesConstants& Rules() const { return rules_; }

    // Lookups: nullptr se não existir.
    const ClassData* FindClass(std::string_view id) const;
    const SkillData* FindSkill(std::string_view id) const;
    const EffectData* FindEffect(std::string_view id) const;
    const EnemyData* FindEnemy(std::string_view id) const;
    const AffixData* FindAffix(std::string_view id) const;
    const ItemBaseData* FindItemBase(std::string_view id) const;
    const UniqueData* FindUnique(std::string_view id) const;
    const LootTableData* FindLootTable(std::string_view id) const;
    const EncounterTemplate* FindEncounter(std::string_view id) const;
    const MapData* FindMap(std::string_view id) const;
    const PotionData* FindPotion(std::string_view id) const;
    const EliteModifierData* FindEliteModifier(std::string_view id) const;
    const BossPatternData* FindBossPattern(std::string_view id, int phase) const;  // chave = id + phase
    const EnemyAiData* FindEnemyAi(std::string_view enemyId) const;
    // Kit básico da classe (basic_kits.csv); nullptr se a classe não tem linha ou a tabela não foi carregada.
    const BasicKitData* FindBasicKit(std::string_view classId) const;
    // Fase `phase` do chefe (nullptr se não existir).
    const BossPhaseData* FindBossPhase(std::string_view bossId, int phase) const;

    // Listas em ordem estável (ordem do CSV) — iteração determinística.
    const std::vector<AffixData>& Affixes() const;
    const std::vector<ItemBaseData>& ItemBases() const;
    const std::vector<MapData>& Maps() const;
    const std::vector<PotionData>& Potions() const;                 // ordem do CSV (a 1ª de kind heal é a "Vida")
    const std::vector<EliteModifierData>& EliteModifiers() const;
    const std::vector<BossPhaseData>& BossPhases() const;
    const std::vector<BossPatternData>& BossPatterns() const;
    const std::vector<EnemyAiData>& EnemyAis() const;
    const std::vector<BasicKitData>& BasicKits() const;                // ordem do CSV
    // Mapa de efeitos para EffectContainer::Tick.
    const std::unordered_map<ContentId, const EffectData*>& EffectLookup() const;

    // XP necessário para ir de `level` para `level+1` (fórmula de RulesConstants).
    double XpToNextLevel(int level) const;

    // Construção programática (testes unitários sem CSV). Só antes de Finalize().
    void SetContentVersion(std::uint32_t v) { contentVersion_ = v; }
    RulesConstants& MutableRules() { return rules_; }
    void Add(ClassData d);
    void Add(SkillData d);
    void Add(EffectData d);
    void Add(EnemyData d);
    void Add(AffixData d);
    void Add(ItemBaseData d);
    void Add(UniqueData d);
    void Add(LootTableData d);
    void Add(EncounterTemplate d);
    void Add(MapData d);
    void Add(PotionData d);
    void Add(EliteModifierData d);
    void Add(BossPhaseData d);
    void Add(BossPatternData d);
    void Add(EnemyAiData d);
    void Add(BasicKitData d);

private:
    struct Impl;                       // tabelas e índices; definido em src/content.cpp
    std::unique_ptr<Impl> impl_;
    std::vector<ContentError> errors_;
    RulesConstants rules_;
    std::uint32_t contentVersion_ = 0;
};

}  // namespace shatter
