// ShatterCore — roguelike 2D da Cripta: economia, meta-progressão e fluxo da corrida (marco M10, pacote 1).
//
// Assume as regras que moravam em godot/scripts2d/meta_2d.gd, upgrades_2d.gd e run_2d.gd, com paridade de
// comportamento. Combate, movimento, física, spawns e tempo real ficam no Godot: o core só decide economia
// (fragmentos, materiais, compras, Forja), progressão (melhorias permanentes, habilidades liberadas, cartas da
// corrida) e fluxo da corrida (etapas, rotas, salas limpas, descanso, vitória e derrota).
//
// - Dados: godot/data2d/{meta,receitas,drops,rota,run,run_settings,upgrades}.csv, no formato que o GDScript já lê.
//   Os CSV são a única fonte de números. Os ids de stat (hp_max, arrow_damage...) são o contrato com o cliente.
// - Sorteio das cartas: Pcg32 do core, um gerador por sorteio (Pcg32::ForStream(seed, RngStream::Rogue, nº do
//   sorteio)). NÃO reproduz o RandomNumberGenerator do Godot: a paridade é nas regras (quais cartas podem sair,
//   quantas, sem repetir), não na sequência aleatória. Mesmo seed + dados + ações = mesmo estado e mesmo hash.
// - Save do meta: o MESMO JSON do meta_2d.gd (`versao` 1, chaves em português), então o save que o GDScript já
//   gravou continua valendo. Leitura tolerante como o carregar() do GDScript. Não usa o save.h do ARPG (só o IFileIO).
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "shatter/content.h"
#include "shatter/save.h"
#include "shatter/types.h"

namespace shatter {

namespace json {
class Value;
}  // namespace json


// Versão do save do meta do rogue (campo `versao`; igual a VERSAO do meta_2d.gd).
inline constexpr std::int64_t kRogueSaveVersion = 1;
// Versão do JSON de estado completo (RogueState::StateJson / RestoreState).
inline constexpr std::int64_t kRogueStateFormat = 1;

enum class RogueMode : std::uint8_t { Add = 0, Mult = 1 };
const char* RogueModeName(RogueMode m);  // "add" | "mult" (como no CSV)

struct RogueMetaDef {          // meta.csv
    ContentId id;
    bool ability = false;      // tipo "habilidade" (libera um upgrade da corrida); senão "stat"
    ContentId target;          // alvo: id do upgrade liberado (habilidade)
    std::string stat;          // stat afetado (tipo stat)
    RogueMode mode = RogueMode::Add;
    double value = 0.0;
    std::int64_t cost = 0;
    int maxLevel = 1;
};

struct RogueRecipe {           // receitas.csv
    ContentId id;
    bool amulet = false;       // "amuleto"; senão "consumivel"
    std::string stat;
    RogueMode mode = RogueMode::Add;
    double value = 0.0;
    std::vector<std::pair<ContentId, std::int64_t>> materials;  // mat1/qtd1, mat2/qtd2 (vazios ficam fora)
    std::int64_t fragments = 0;
    int maxStock = 1;
};

struct RogueDrop {             // drops.csv
    ContentId enemy;
    std::int64_t fragments = 0;
    ContentId material;
    std::int64_t materialQty = 0;
    std::int64_t xp = 0;       // coluna opcional `xp` (API 1.12): XP da gema que o inimigo solta
};

struct RogueEnemyCount {
    ContentId enemy;
    int count = 0;
};

struct RogueNode {             // linha de run.csv (caminho padrão "combate") ou de rota.csv
    ContentId id;
    std::string kind;          // combate | elite | descanso
    std::string room;
    std::string enemies;       // texto original ("skeleton_soldier:3|crypt_bat:2")
    std::vector<RogueEnemyCount> enemyList;
    int enemyTotal = 0;
};

struct RogueUpgrade {          // upgrades.csv
    ContentId id;
    std::string stat;
    RogueMode mode = RogueMode::Add;
    double value = 0.0;
    int maxLevel = 1;
    // Colunas opcionais `tipo` e `raridade` (API 1.12). A oferta de nível tem ao menos uma carta de ataque; o baú de
    // elite só oferece cartas raras (se não sobrar nenhuma, qualquer uma).
    std::string kind = "utilidade";  // ataque | defesa | utilidade
    bool attack = false;             // kind == "ataque"
    bool rare = false;               // raridade == "rara" (senão "comum")
};

// curva_horda.csv (opcional, API 1.12): multiplicadores por onda de uma fase. Onda = ondas da fase + 1 é o enxame final.
struct RogueCurveRow {
    std::string phase;
    int wave = 0;
    double hp = 1.0;           // vida dos inimigos comuns da onda
    double damage = 1.0;       // dano
    double speed = 1.0;        // velocidade de movimento
    double xp = 1.0;           // XP da gema
};

// Pares stat -> valor, na ordem em que o chamador mandou (a saída mantém a ordem).
using RogueStats = std::vector<std::pair<std::string, double>>;

// --- Habilidades por classe (API 1.10; runtime de godot/scripts2d/habilidades_2d.gd; docs/09 seção 17) ---------
// Quantos slots ativos a árvore tem (Q, E, F, R). Contrato com a HUD, não balanceamento.
inline constexpr int kRogueSkillSlots = 4;

struct RogueSkillDef {         // linha de habilidades_<classe>.csv (formato do doc 29)
    ContentId id;
    bool active = false;       // tipo "ativa"; senão "passiva"
    ContentId parent;          // pai ("" = raiz do ramo)
    int parentIndex = -1;      // índice do pai na mesma classe
    int points = 1;            // custo por nível (mínimo 1)
    int maxLevel = 1;          // mínimo 1
    double cooldown = 0.0;     // cd (s), não escala
    double cost = 0.0;         // custo de mana, não escala
    double scale = 0.0;        // escala por nível acima do 1
    std::string stat;          // passiva: stat afetado ("" = passiva sem stat)
    RogueMode mode = RogueMode::Add;
    double value = 0.0;        // passiva: valor por nível
    // Todas as colunas na ordem do CSV: as de texto (id, ramo, tipo, pai, efeito, stat, modo, icone) em `texts`, as
    // demais em `numbers` (vazio = 0). A definição escalonada (SkillDefAt) repassa todas ao cliente.
    std::vector<std::pair<std::string, std::string>> texts;
    std::vector<std::pair<std::string, double>> numbers;
};

struct RogueClass {            // linha de classes_2d.csv + a árvore dela
    ContentId id;
    std::string skillFile;     // nome do arquivo da árvore (só o nome, sem pasta); "" = sem árvore
    std::vector<RogueSkillDef> skills;
};

// Estado da árvore de uma classe (meta; vai ao save em "habilidades": {classe: {niveis, slots, pontos}}).
struct RogueSkillMeta {
    std::int64_t points = 0;
    std::vector<int> levels;                                   // por habilidade da classe
    std::array<int, kRogueSkillSlots> slots{{-1, -1, -1, -1}};  // índice da habilidade ou -1
};

// Uma habilidade num nível: as colunas do CSV com dano, qtd, raio, duracao, alcance e valor multiplicados por
// 1 + escala * max(0, n - 1); qtd > 0 é arredondada e fica no mínimo 1 (def_nivel do habilidades_2d.gd).
struct RogueSkillLevelDef {
    std::vector<std::pair<std::string, std::string>> texts;
    std::vector<std::pair<std::string, double>> numbers;
    int level = 0;
};

// --- Ondas de horda (API 1.11; ondas.csv; docs/09 seção 18; runtime em rogue_waves.h) --------------------------
struct RogueWaveMix {          // uma entrada da coluna `inimigos` ("id:peso" ou "id:peso:custo")
    ContentId enemy;
    int weight = 1;            // peso no sorteio do tipo
    int cost = 1;              // pontos do orçamento que cada um gasta (padrão 1)
};

struct RogueWaveDef {          // linha de ondas.csv
    std::string phase;         // fase (mapa aberto) a que a onda pertence
    int wave = 0;              // 1, 2, 3... dentro da fase
    double duration = 0.0;     // s: tempo mínimo da onda antes de passar à próxima (ou antes, se ela for limpa)
    double interval = 0.0;     // s entre lotes de spawn
    std::int64_t durationUs = 0, intervalUs = 0;  // os mesmos tempos em microssegundos (relógio inteiro do spawner)
    int batch = 1;             // até quantos nascem por lote
    std::int64_t budget = 0;   // orçamento de spawn da onda (soma dos custos)
    int cap = 1;               // teto de inimigos vivos (o chefe não respeita o teto)
    std::string mixText;       // texto original da coluna inimigos
    std::vector<RogueWaveMix> mix;
    int minCost = 0;           // menor custo da mistura (0 = mistura vazia)
    int elites = 0;            // quantos nascem marcados como elite, espalhados pelo orçamento
    double eliteHp = 1.0;      // multiplicador de vida do elite
    double eliteDamage = 1.0;  // multiplicador de dano do elite
};

struct RogueWavePhaseDef {     // linha de ondas_fases.csv: regras da fase inteira
    std::string id;
    double deadline = 0.0;     // s: prazo da fase; ao chegar, vem o enxame final (e o chefe acorda, se ainda dorme)
    std::int64_t deadlineUs = 0;
    double ringMin = 0.0;      // px: raio mínimo do anel de spawn ao redor do jogador (fora da tela)
    double ringMax = 0.0;      // px: raio máximo (>= mínimo)
    ContentId boss;            // chefe que o jogador acorda ("" = fase sem chefe)
    int wakeWave = 1;          // a partir de qual onda o jogador pode acordar o chefe
    RogueWaveDef swarm;        // enxame final (onda = ondas da fase + 1; duração sem efeito)
};

class RogueData {
public:
    // Tabelas: "meta.csv", "receitas.csv", "drops.csv", "rota.csv", "run.csv", "run_settings.csv", "upgrades.csv",
    // "classes_2d.csv" (opcional), "ondas.csv" e "ondas_fases.csv" (opcionais, API 1.11).
    bool LoadTableCsv(std::string_view tableName, std::string_view csvText);
    // Árvore de habilidades de uma classe já lida de classes_2d.csv (texto de habilidades_<classe>.csv).
    bool LoadSkillTableCsv(std::string_view classId, std::string_view csvText);
    // Lê as 7 tabelas da pasta (todas obrigatórias). Erro de IO vem com mensagem "E_IO ...". Se houver classes_2d.csv,
    // lê também a árvore de cada classe (arquivo da coluna `habilidades`, só o nome); árvore ausente = classe sem árvore.
    // Se houver ondas.csv e ondas_fases.csv, lê as ondas de horda e as regras de cada fase.
    bool LoadDirectory(const std::string& dir);
    // Confere referências (habilidade -> upgrade, rota -> etapa) e as chaves obrigatórias de run_settings. Uma vez.
    bool Finalize();
    bool Ok() const { return finalized_ && errors_.empty(); }
    const std::vector<ContentError>& Errors() const { return errors_; }

    const std::vector<RogueMetaDef>& MetaDefs() const { return meta_; }
    const std::vector<RogueRecipe>& Recipes() const { return recipes_; }
    const std::vector<RogueDrop>& Drops() const { return drops_; }
    const std::vector<RogueUpgrade>& Upgrades() const { return upgrades_; }
    const std::vector<RogueClass>& Classes() const { return classes_; }       // classes_2d.csv, na ordem
    int FindClass(std::string_view id) const;                                // índice ou -1
    int FindSkill(int classIndex, std::string_view skillId) const;           // índice ou -1
    const std::vector<RogueNode>& Stages() const { return stages_; }          // run.csv, na ordem
    // ondas.csv (opcional): ondas na ordem do CSV, cada fase num bloco contíguo (onda 1, 2, 3...).
    const std::vector<RogueWaveDef>& Waves() const { return waves_; }
    std::vector<std::string> WavePhases() const;                             // fases na ordem do CSV
    // Primeira onda da fase em Waves() e quantas são; false se a fase não existe.
    bool FindWavePhase(std::string_view phase, int& first, int& count) const;
    // ondas_fases.csv (opcional, obrigatório se houver ondas.csv): regras de cada fase. nullptr se não existe.
    const std::vector<RogueWavePhaseDef>& WavePhaseDefs() const { return wavePhases_; }
    const RogueWavePhaseDef* FindWavePhaseDef(std::string_view phase) const;
    // curva_horda.csv (opcional): linha da fase e onda, ou nullptr (multiplicadores 1).
    const std::vector<RogueCurveRow>& Curve() const { return curve_; }
    const RogueCurveRow* FindCurve(std::string_view phase, int wave) const;
    // Vida do chefe adaptativa (API 1.12): DPS medido do jogador x boss_fight_time de run_settings, presa entre
    // boss_hp_min e boss_hp_max vezes a vida base. Sem boss_fight_time (ou DPS <= 0 ou inválido), devolve a vida base.
    double BossHp(double baseHp, double dps) const;
    // XP para passar do nível `level` ao seguinte: xp_level_base + xp_level_step x (level - 1). 0 = sem níveis.
    std::int64_t XpForLevel(int level) const;
    int LevelCards() const { return levelCards_; }
    int ChestCards() const { return chestCards_; }
    int LevelRerolls() const { return levelRerolls_; }
    int LevelSkips() const { return levelSkips_; }
    int LevelBans() const { return levelBans_; }
    // Materiais conhecidos (drops.csv e depois receitas.csv, na ordem em que aparecem).
    const std::vector<ContentId>& Materials() const { return materials_; }

    int FindMetaDef(std::string_view id) const;      // índice ou -1
    int FindRecipe(std::string_view id) const;
    int FindUpgrade(std::string_view id) const;
    int FindMaterial(std::string_view id) const;
    const RogueDrop* FindDrop(std::string_view enemy) const;

    // run_settings.csv (chave -> valor). false se a chave não existe.
    bool Setting(std::string_view key, double& out) const;
    const std::vector<std::pair<std::string, double>>& Settings() const { return settings_; }

    // Caminhos oferecidos ao entrar na etapa `stage` (0 = primeira): o padrão de run.csv (id e tipo "combate")
    // e depois as alternativas de rota.csv com etapa == stage + 1, na ordem do CSV. Fora da faixa: lista vazia.
    std::vector<RogueNode> Paths(int stage) const;

    // Regras de run_settings.csv já convertidas (int(config[...]) do GDScript: inteiros conferidos no Finalize).
    std::uint64_t BaseSeed() const { return baseSeed_; }
    int UpgradeCards() const { return upgradeCards_; }
    int EliteExtraCards() const { return eliteExtraCards_; }
    std::int64_t RoomClearFragments() const { return roomClearFragments_; }
    std::int64_t EliteFragments() const { return eliteFragments_; }
    std::int64_t VictoryFragments() const { return victoryFragments_; }
    double RestHeal() const { return restHeal_; }
    // Pontos de habilidade por sala limpa e extras na última sala (chefe). Chaves opcionais (ausente = 0).
    std::int64_t SkillPointsRoom() const { return skillPointsRoom_; }
    std::int64_t SkillPointsBoss() const { return skillPointsBoss_; }

private:
    bool LoadCurveCsv(std::string_view csvText);       // rogue_levels.cpp
    void FinalizeLevels();                             // rogue_levels.cpp (no Finalize)
    bool LoadWavesCsv(std::string_view csvText);       // rogue_waves.cpp
    bool LoadWavePhasesCsv(std::string_view csvText);  // rogue_waves.cpp
    void CheckWaves();                                 // rogue_waves.cpp (no Finalize)
    struct RouteRow {
        int stage = 0;  // etapa (1-based, como no CSV)
        RogueNode node;
    };
    std::vector<RogueMetaDef> meta_;
    std::vector<RogueRecipe> recipes_;
    std::vector<RogueDrop> drops_;
    std::vector<RogueUpgrade> upgrades_;
    std::vector<RogueNode> stages_;
    std::vector<RouteRow> routes_;
    std::vector<RogueClass> classes_;
    std::vector<RogueWaveDef> waves_;
    std::vector<RogueWavePhaseDef> wavePhases_;
    std::vector<RogueCurveRow> curve_;
    std::vector<ContentId> materials_;
    std::vector<std::pair<std::string, double>> settings_;
    std::vector<ContentError> errors_;
    std::uint64_t baseSeed_ = 0;
    int upgradeCards_ = 0, eliteExtraCards_ = 0;
    std::int64_t roomClearFragments_ = 0, eliteFragments_ = 0, victoryFragments_ = 0;
    double restHeal_ = 0.0;
    std::int64_t skillPointsRoom_ = 0, skillPointsBoss_ = 0;
    std::int64_t xpLevelBase_ = 0, xpLevelStep_ = 0;
    int levelCards_ = 0, chestCards_ = 0, levelRerolls_ = 0, levelSkips_ = 0, levelBans_ = 0;
    double bossFightTime_ = 0.0, bossHpMin_ = 0.0, bossHpMax_ = 0.0;
    bool finalized_ = false;
};

// Resultado das ações do meta (comprar, criar, equipar). Só Ok muda o estado.
enum class RogueMetaResult : std::uint8_t {
    Ok = 0,
    Unknown = 1,        // id não existe na tabela
    Maxed = 2,          // melhoria já no nível máximo
    NoFragments = 3,
    NoMaterials = 4,
    AlreadyOwned = 5,   // amuleto já criado
    StockFull = 6,      // consumível no estoque máximo
    NotOwned = 7,       // equipar amuleto que não foi criado
};

// Resultado das ações de habilidade. Só Ok muda o estado.
enum class RogueSkillResult : std::uint8_t {
    Ok = 0,
    Unknown = 1,        // classe ou habilidade que não existe
    Maxed = 2,          // já no nível máximo
    NoPoints = 3,       // saldo menor que o custo
    Locked = 4,         // pai ainda não aprendido
    NotActive = 5,      // equipar uma passiva
    NotLearned = 6,     // equipar uma ativa com nível 0
    BadSlot = 7,        // slot fora de 0..3
    EmptySlot = 8,      // usar um slot vazio
    Cooldown = 9,       // em recarga
    NoMana = 10,        // mana menor que o custo
    WrongPhase = 11,    // trocar de classe com corrida viva
    NoClass = 12,       // nenhuma classe escolhida (sem classes_2d.csv)
};

enum class RogueLoadResult : std::uint8_t { Ok = 0, Missing = 1, BadJson = 2, BadVersion = 3 };

enum class RoguePhase : std::uint8_t {
    None = 0,     // sem corrida (antes da 1ª ou depois de FinishRun)
    Fight = 1,    // luta (LUTA)
    Cleared = 2,  // sala limpa, porta liberada (LIMPA)
    Choice = 3,   // cartas oferecidas, esperando a escolha (ESCOLHA)
    Route = 4,    // bifurcação: esperando o caminho (ROTA)
    Won = 5,      // venceu a cripta (VENCEU)
    Dead = 6,     // morreu (MORTO)
};
const char* RoguePhaseName(RoguePhase p);

// Resultado das ações da corrida.
enum class RogueRunResult : std::uint8_t {
    Ok = 0,
    WrongPhase = 1,     // ação não vale na fase atual (nada muda)
    NotOffered = 2,     // carta fora das oferecidas
    Unknown = 3,        // id ou índice que não existe
    NoHpStat = 4,       // stats da corrida sem "hp_max" (descanso não tem como curar)
};

// Porta usada (_on_porta): o que aconteceu.
enum class RogueDoor : std::uint8_t {
    NotReady = 0,  // porta fechada (fase != Cleared): nada muda
    Entered = 1,   // entrou direto na próxima sala (um caminho só)
    Route = 2,     // bifurcação: escolher com ChoosePath
    Victory = 3,   // era a última sala: venceu (+ victory_fragments)
};

struct RogueKill {
    bool hasDrop = false;
    std::int64_t fragments = 0;     // do drop
    ContentId material;
    std::int64_t materialQty = 0;
    bool roomCleared = false;       // esta morte limpou a sala (vivos chegou a 0 durante a luta)
    std::int64_t clearFragments = 0;  // bônus de sala limpa (+ elite) somado agora
    std::int64_t skillPoints = 0;   // pontos de habilidade dados à classe atual agora (o save do meta mudou)
};

struct RogueSummary {
    bool victory = false;
    int stageReached = 0;           // índice + 1
    int stagesTotal = 0;
    int upgradesTotal = 0;          // soma dos níveis escolhidos na corrida
    std::int64_t fragments = 0;
    std::vector<std::pair<ContentId, std::int64_t>> materials;  // ordem em que foram ganhos
};

// Estado do jogador (meta) e da corrida em curso. Guarda um ponteiro para os dados (que precisam viver mais).
class RogueState {
public:
    RogueState() = default;
    explicit RogueState(const RogueData& data);

    const RogueData* Data() const { return data_; }

    // --- Meta (meta_2d.gd) -----------------------------------------------------------------------------
    std::int64_t Fragments() const { return fragments_; }
    std::int64_t Material(std::string_view id) const;          // 0 se desconhecido
    int Level(std::string_view metaId) const;                  // 0 se desconhecido
    // Habilidade de corrida liberada? Upgrade sem entrada "habilidade" em meta.csv nasce liberado.
    bool Unlocked(std::string_view upgradeId) const;
    RogueMetaResult CheckBuy(std::string_view metaId) const;
    RogueMetaResult Buy(std::string_view metaId);
    // tem(): amuleto criado ou consumível com estoque > 0.
    bool Owns(std::string_view recipeId) const;
    int Stock(std::string_view recipeId) const;
    bool Active(std::string_view recipeId) const;              // consumível gasto para a corrida atual
    const ContentId& Equipped() const;                         // "" se nenhum
    RogueMetaResult CheckCraft(std::string_view recipeId) const;
    RogueMetaResult Craft(std::string_view recipeId);
    // Equipa o amuleto (troca o do slot) ou desequipa se já era ele.
    RogueMetaResult Equip(std::string_view recipeId);
    // Ao partir: gasta 1 unidade de cada consumível guardado; eles valem só para a corrida (não vão ao save).
    void PrepareRun();
    // Passa ganhos para o saldo permanente. Material desconhecido ou quantidade negativa: false e nada muda.
    bool Credit(std::int64_t fragments, const std::vector<std::pair<ContentId, std::int64_t>>& materials);

    // Bônus permanentes sobre os stats base: amuleto equipado, consumíveis ativos (ordem de receitas.csv) e
    // melhorias de stat (ordem de meta.csv, uma vez por nível). Stat que não está em `base` é ignorado.
    RogueStats ApplyMeta(const RogueStats& base) const;
    // Upgrades da corrida (ordem de upgrades.csv, uma vez por nível) sobre `stats`.
    RogueStats ApplyRunUpgrades(const RogueStats& stats) const;
    // Passivas aprendidas da classe atual (ordem do CSV, uma vez por nível). Diferente dos bônus acima, stat que não
    // está em `stats` entra no fim com 0 antes do bônus (aplicar_passivas do habilidades_2d.gd).
    RogueStats ApplySkillPassives(const RogueStats& stats) const;

    // --- Habilidades da classe (habilidades_2d.gd). Pontos, níveis e slots são do meta (vão ao save, por classe);
    // as recargas são da corrida. A mana e os efeitos ficam no cliente.
    int ClassIndex() const { return class_; }                  // -1 sem classes
    const std::vector<RogueSkillMeta>& SkillMetas() const { return skillMeta_; }  // por classe
    const ContentId& ClassId() const;                          // "" sem classes
    // Escolhe a classe da próxima corrida. Só fora de corrida viva (None, Won, Dead); zera as recargas.
    RogueSkillResult SetClass(std::string_view classId);
    std::int64_t SkillPoints() const;                          // saldo da classe atual
    int SkillLevel(std::string_view skillId) const;            // 0 se desconhecida
    const ContentId& SkillSlot(int slot) const;                // "" vazio ou fora da faixa
    RogueSkillResult CheckLearn(std::string_view skillId) const;
    // Gasta os pontos e sobe um nível; ativa recém-aprendida entra no 1º slot livre.
    RogueSkillResult Learn(std::string_view skillId);
    // Soma pontos ao saldo da classe atual (n < 0 conta como 0).
    RogueSkillResult AddSkillPoints(std::int64_t n);
    // Redistribuição gratuita: devolve tudo o que foi gasto, zera níveis e slots.
    RogueSkillResult Respec();
    // Põe a ativa aprendida no slot ("" limpa). Se ela já estava em outro slot, os dois trocam.
    RogueSkillResult EquipSkill(int slot, std::string_view skillId);
    // Definição no nível `level` (< 0 = nível atual; nível 0 mostra o valor base). false se desconhecida.
    bool SkillDefAt(std::string_view skillId, int level, RogueSkillLevelDef& out) const;
    // Recargas: Tick desconta `dt` segundos (dt inválido ou <= 0 não faz nada).
    void TickSkills(double dt);
    double SkillCooldownLeft(std::string_view skillId) const;  // segundos (0 = pronta)
    double SlotCooldownFraction(int slot) const;               // 0..1 para a HUD (0 = pronto)
    // Pode usar o slot com esta mana? (slot, vazio, recarga, mana)
    RogueSkillResult CheckUse(int slot, double mana) const;
    // Depois que o efeito do cliente deu certo: confere de novo, inicia a recarga (cd * skill_cd_mult dos stats da
    // corrida, 1 sem corrida) e devolve o custo de mana em `costOut` (o cliente desconta).
    RogueSkillResult CommitUse(int slot, double mana, double* costOut = nullptr);

    // Save do meta (formato do meta_2d.gd). Leitura: zera o estado e lê o que for válido.
    std::string MetaToJson() const;
    RogueLoadResult MetaFromJson(std::string_view text);
    void ResetMeta();

    // --- Corrida (run_2d.gd + upgrades_2d.gd) ----------------------------------------------------------
    RoguePhase Phase() const { return phase_; }
    // Modo "cartas externas" (API 1.9): a classe tem progressão própria no cliente (ex.: árvore do Guerreiro). Ligado,
    // a sala limpa vai direto a Cleared, sem sortear (Draws() não muda, oferta vazia), e ChooseCard dá WrongPhase; os
    // stats da corrida ficam base + meta. Vale até ser desligado (não é zerado por StartRun, FinishRun nem pelo meta).
    // Só muda fora de uma corrida viva (fase None, Won ou Dead); em outra fase devolve WrongPhase e nada muda.
    RogueRunResult SetExternalCards(bool on);
    bool ExternalCards() const { return externalCards_; }
    // Começa a corrida: credita os ganhos pendentes da anterior (abandono também rende), guarda os stats base
    // com o meta aplicado (restaurar), zera upgrades e ganhos e entra no caminho padrão da etapa 0.
    // Devolve true se creditou ganhos pendentes (o save do meta mudou).
    bool StartRun(std::uint64_t seed, const RogueStats& baseStats);
    int Stage() const { return stage_; }                        // índice 0-based
    int StagesTotal() const;
    const RogueNode* CurrentNode() const;                       // nullptr sem corrida
    int Alive() const { return alive_; }
    bool RestPending() const { return restPending_; }
    const std::vector<ContentId>& Offer() const { return offer_; }
    int RunLevel(std::string_view upgradeId) const;
    std::uint64_t Seed() const { return seed_; }
    std::uint64_t Draws() const { return draws_; }
    std::int64_t GainFragments() const { return gainFragments_; }
    const std::vector<std::pair<ContentId, std::int64_t>>& GainMaterials() const { return gainMaterials_; }
    // Upgrades que podem sair nas cartas: abaixo do nível máximo e liberados no meta (ordem de upgrades.csv).
    std::vector<ContentId> AvailableUpgrades() const;
    // Stats finais da corrida: base com meta (guardada no início) + upgrades escolhidos + passivas da árvore.
    RogueStats RunStats() const;

    // Inimigo morto: soma o drop aos ganhos; se a sala estava em luta e os vivos chegaram a 0, limpa a sala
    // (+ room_clear_fragments, + elite_fragments na elite), dá skill_points_room (+ skill_points_boss na última sala)
    // à classe atual e sorteia as cartas. Vale em qualquer fase com corrida.
    // Com ExternalCards() ligado não sorteia: a sala limpa fica em Cleared.
    RogueRunResult EnemyKilled(std::string_view enemyId, RogueKill* out = nullptr);
    // Escolhe uma das cartas oferecidas: sobe o nível e abre a porta. `hp` volta somado do ganho de hp_max.
    RogueRunResult ChooseCard(std::string_view upgradeId, double hp, double* hpOut = nullptr);
    // Sala de descanso: cura rest_heal da vida máxima (até o máximo). Uma vez por sala de descanso.
    RogueRunResult Rest(double hp, double* hpOut = nullptr);
    // Porta usada na sala limpa.
    RogueDoor UseDoor();
    // Escolhe o caminho da bifurcação (índice em Paths(Stage())).
    RogueRunResult ChoosePath(int pathIndex);
    RogueRunResult PlayerDied();

    // --- Modo horda (API 1.12): a corrida inteira numa fase aberta com o spawner (rogue_waves.h) ---------------
    // Ligado, EnemyKilled só soma o drop (a sala nunca limpa nem sorteia cartas) e a corrida termina com WinRun. Só
    // muda fora de corrida viva, como SetExternalCards; não é zerado por StartRun.
    RogueRunResult SetHorde(bool on);
    bool Horde() const { return horde_; }
    // Venceu a fase (chefe morto e portal usado): + victory_fragments e skill_points_boss. Só no modo horda, em luta.
    RogueRunResult WinRun(RogueKill* out = nullptr);

    // --- XP, nível e cartas de nível (API 1.12; plano 31, pacote H4) ---------------------------------------------
    // XP da gema de um inimigo: xp do drops.csv x xpMult (curva da onda), arredondado; elite também solta um baú.
    // Não muda nada (o cliente cria a gema e o baú no chão e chama GainXp e OpenChest ao pegar).
    RogueRunResult KillXp(std::string_view enemyId, double xpMult, bool elite, std::int64_t* xp, bool* chest) const;
    // Soma XP; cada nível que fecha fica pendente e vira uma oferta de level_cards cartas (ao menos uma de ataque, se
    // houver). Sem xp_level_base, não há níveis. Com cartas externas o nível sobe sem oferta. Vale com corrida viva.
    RogueRunResult GainXp(std::int64_t amount, int* levelsOut = nullptr);
    // Baú de elite: uma oferta de chest_cards cartas raras (depois das ofertas de nível já pendentes).
    RogueRunResult OpenChest();
    // Escolhe uma carta da oferta de nível ou de baú: sobe o nível do upgrade (como ChooseCard) e abre a próxima oferta.
    RogueRunResult ChooseLevelCard(std::string_view upgradeId, double hp, double* hpOut = nullptr);
    // Sorteia a oferta atual de novo (gasta 1 de level_rerolls).
    RogueRunResult RerollLevel();
    // Pula a oferta atual sem carta (gasta 1 de level_skips) e abre a próxima.
    RogueRunResult SkipLevel();
    // Bane uma carta da oferta atual pelo resto da corrida (gasta 1 de level_bans) e sorteia a oferta de novo.
    RogueRunResult BanCard(std::string_view upgradeId);
    std::int64_t RunXp() const { return xp_; }             // XP dentro do nível atual
    int CharLevel() const { return charLevel_; }           // nível na corrida (começa em 1)
    std::int64_t XpNext() const;                           // XP que fecha o nível atual (0 = sem níveis)
    int PendingLevels() const { return pendingLevels_; }   // ofertas de nível na fila (fora a atual)
    int PendingChests() const { return pendingChests_; }
    const std::vector<ContentId>& LevelOffer() const { return levelOffer_; }
    const char* LevelOfferKind() const;                    // "", "level" ou "chest"
    int RerollsLeft() const { return rerolls_; }
    int SkipsLeft() const { return skips_; }
    int BansLeft() const { return bans_; }
    bool Banned(std::string_view upgradeId) const;
    RogueSummary Summary() const;
    // Fim da corrida (tela de resumo): credita os ganhos e volta a None. false se não havia corrida.
    bool FinishRun();

    // --- Estado completo e determinismo ---------------------------------------------------------------
    // meta + consumíveis ativos + corrida (+ "external_cards": true só com o modo ligado; desligado o JSON é o da 1.8).
    std::string StateJson() const;
    bool RestoreState(std::string_view text, std::string* error = nullptr);  // falha: nada muda
    std::string StateHash() const;                              // SHA-256 (hex) do StateJson

private:
    void EnterNode(int stage, int pathIndex);
    void CreditGains();
    void DrawCards(int count);
    void ResetLevels();
    // Sobe o upgrade k um nível e devolve a vida com o ganho de hp_max (ChooseCard e ChooseLevelCard).
    void BumpUpgrade(std::size_t k, double hp, double* hpOut);
    json::Value LevelStateValue() const;
    bool LevelStateFrom(const json::Value& v);
    void DrawLevelOffer();
    void NextLevelOffer();
    RogueRunResult LevelPhaseOk() const;
    void AddGainMaterial(const ContentId& id, std::int64_t qty);
    void ResetSkillState();
    void ClearCooldowns();

    const RogueData* data_ = nullptr;
    // meta
    std::int64_t fragments_ = 0;
    std::vector<std::int64_t> materials_;   // por índice de RogueData::Materials()
    std::vector<int> levels_;               // por índice de MetaDefs()
    std::vector<std::uint8_t> owned_;       // por receita (amuleto criado)
    std::vector<int> stock_;                // por receita (consumível)
    std::vector<std::uint8_t> active_;      // por receita (consumível ativo nesta corrida)
    int equipped_ = -1;
    // habilidades (meta): por classe
    std::vector<RogueSkillMeta> skillMeta_;  // por classe
    int class_ = -1;                      // classe atual (a 1ª de classes_2d.csv por padrão)
    std::vector<double> cooldowns_;       // por habilidade da classe atual (corrida)
    bool externalCards_ = false;            // modo cartas externas (não é meta nem corrida: configuração do cliente)
    // corrida
    RoguePhase phase_ = RoguePhase::None;
    std::uint64_t seed_ = 0;
    std::uint64_t draws_ = 0;
    int stage_ = 0;
    int path_ = 0;                          // caminho da sala atual (na fase Route, da etapa stage_ - 1)
    RogueNode node_;                        // sala atual (no_atual)
    int alive_ = 0;
    bool restPending_ = false;
    std::vector<int> runLevels_;            // por upgrade
    std::vector<ContentId> offer_;
    RogueStats base_;                       // stats base com o meta aplicado (restaurar)
    std::int64_t gainFragments_ = 0;
    std::vector<std::pair<ContentId, std::int64_t>> gainMaterials_;
    // modo horda e níveis (API 1.12). levelUsed_: algo de nível aconteceu nesta corrida (só então o estado leva
    // "progress"; sem isso o JSON é o da 1.11, mesmo hash).
    bool horde_ = false;
    bool levelUsed_ = false;
    std::int64_t xp_ = 0;
    int charLevel_ = 1;
    int pendingLevels_ = 0, pendingChests_ = 0;
    int offerKind_ = 0;                      // 0 nenhuma, 1 nível, 2 baú
    std::vector<ContentId> levelOffer_;
    std::uint64_t levelDraws_ = 0;
    int rerolls_ = 0, skips_ = 0, bans_ = 0;
    std::vector<std::uint8_t> banned_;      // por upgrade
};

// Gravação atômica do save do meta: grava `path + ".tmp"`, confere relendo e troca pelo principal.
bool WriteRogueMetaFile(IFileIO& io, const std::string& path, const RogueState& s, std::string* error = nullptr);
// Lê o save do meta. Ausente ou inválido deixa o meta zerado (como o carregar() do GDScript).
RogueLoadResult ReadRogueMetaFile(IFileIO& io, const std::string& path, RogueState& s);

}  // namespace shatter
