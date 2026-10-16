// ShatterCore — dados de conteúdo (somente leitura em tempo de jogo).
// Fonte da verdade: CSV em EchoesOfTheShatter/Content/Data/*.csv (UTF-8, vírgula,
// 1ª linha = cabeçalho, listas internas separadas por '|'). O mesmo CSV alimenta:
//   - o ShatterCore (ContentDB::LoadTableCsv) — no jogo, nos testes e no bench;
//   - opcionalmente DataTables no editor UE, só para visualização.
// Esquemas das colunas: docs/06_dados.md (Data Engineer). Nomes de campo abaixo = nomes de coluna.
#pragma once

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
    std::vector<ContentId> onHitEffects;   // "effect.burn", "effect.guard_break"
    std::vector<ContentId> selfEffects;    // aplicados em quem usa (Postura Firme, Barreira de Vidro)
    IdleProfile idle;
    int unlockLevel = 1;
};

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
};

struct UniqueData {                        // uniques.csv
    ContentId id;                          // "unique.bell_warden_helm"
    ContentId baseId;
    std::vector<Modifier> fixedMods;
    ContentId ruleEffectId;                // efeito que muda a build
    bool idleSupported = false;            // sem perfil testado → bloqueia expedição
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
    //  "loot_tables.csv", "loot_entries.csv", "encounters.csv", "maps.csv", "meta.csv").
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

    // Listas em ordem estável (ordem do CSV) — iteração determinística.
    const std::vector<AffixData>& Affixes() const;
    const std::vector<ItemBaseData>& ItemBases() const;
    const std::vector<MapData>& Maps() const;
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

private:
    struct Impl;                       // tabelas e índices; definido em src/content.cpp
    std::unique_ptr<Impl> impl_;
    std::vector<ContentError> errors_;
    RulesConstants rules_;
    std::uint32_t contentVersion_ = 0;
};

}  // namespace shatter
