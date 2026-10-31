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

#include <cstdint>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "shatter/content.h"
#include "shatter/save.h"
#include "shatter/types.h"

namespace shatter {

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
};

// Pares stat -> valor, na ordem em que o chamador mandou (a saída mantém a ordem).
using RogueStats = std::vector<std::pair<std::string, double>>;

class RogueData {
public:
    // Tabelas: "meta.csv", "receitas.csv", "drops.csv", "rota.csv", "run.csv", "run_settings.csv", "upgrades.csv".
    bool LoadTableCsv(std::string_view tableName, std::string_view csvText);
    // Lê as 7 tabelas da pasta (todas obrigatórias). Erro de IO vem com mensagem "E_IO ...".
    bool LoadDirectory(const std::string& dir);
    // Confere referências (habilidade -> upgrade, rota -> etapa) e as chaves obrigatórias de run_settings. Uma vez.
    bool Finalize();
    bool Ok() const { return finalized_ && errors_.empty(); }
    const std::vector<ContentError>& Errors() const { return errors_; }

    const std::vector<RogueMetaDef>& MetaDefs() const { return meta_; }
    const std::vector<RogueRecipe>& Recipes() const { return recipes_; }
    const std::vector<RogueDrop>& Drops() const { return drops_; }
    const std::vector<RogueUpgrade>& Upgrades() const { return upgrades_; }
    const std::vector<RogueNode>& Stages() const { return stages_; }          // run.csv, na ordem
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

private:
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
    std::vector<ContentId> materials_;
    std::vector<std::pair<std::string, double>> settings_;
    std::vector<ContentError> errors_;
    std::uint64_t baseSeed_ = 0;
    int upgradeCards_ = 0, eliteExtraCards_ = 0;
    std::int64_t roomClearFragments_ = 0, eliteFragments_ = 0, victoryFragments_ = 0;
    double restHeal_ = 0.0;
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
    // Stats finais da corrida: base com meta (guardada no início) + upgrades escolhidos.
    RogueStats RunStats() const;

    // Inimigo morto: soma o drop aos ganhos; se a sala estava em luta e os vivos chegaram a 0, limpa a sala
    // (+ room_clear_fragments, + elite_fragments na elite) e sorteia as cartas. Vale em qualquer fase com corrida.
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
    void AddGainMaterial(const ContentId& id, std::int64_t qty);

    const RogueData* data_ = nullptr;
    // meta
    std::int64_t fragments_ = 0;
    std::vector<std::int64_t> materials_;   // por índice de RogueData::Materials()
    std::vector<int> levels_;               // por índice de MetaDefs()
    std::vector<std::uint8_t> owned_;       // por receita (amuleto criado)
    std::vector<int> stock_;                // por receita (consumível)
    std::vector<std::uint8_t> active_;      // por receita (consumível ativo nesta corrida)
    int equipped_ = -1;
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
};

// Gravação atômica do save do meta: grava `path + ".tmp"`, confere relendo e troca pelo principal.
bool WriteRogueMetaFile(IFileIO& io, const std::string& path, const RogueState& s, std::string* error = nullptr);
// Lê o save do meta. Ausente ou inválido deixa o meta zerado (como o carregar() do GDScript).
RogueLoadResult ReadRogueMetaFile(IFileIO& io, const std::string& path, RogueState& s);

}  // namespace shatter
