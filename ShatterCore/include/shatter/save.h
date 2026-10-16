// ShatterCore — save em JSON próprio, gravação segura, backups, checksum e migração.
//
// Formato do arquivo (slot_N.json), UTF-8:
//   {
//     "format": "echoes-of-the-shatter-save",
//     "save_version": 1,
//     "sha256": "<hex de 64 chars>",   // SHA-256 de json::Serialize(data, pretty=false)
//     "data": { ... SaveData ... }
//   }
// O arquivo em disco é "pretty" (legível); o hash é sempre sobre a forma compacta
// canônica de "data" (re-serializar após Parse dá os mesmos bytes — ver json.h).
//
// Gravação segura (WriteSaveFile):
//   1. serializa e grava slot_N.tmp; fsync/flush; relê e confere o hash;
//   2. rotaciona backups: slot_N.bak2→bak3, bak1→bak2, slot_N.json→bak1 (cópia);
//   3. rename(slot_N.tmp → slot_N.json) (substitui; atômico no mesmo volume).
// Leitura (ReadSaveFile): tenta json, depois bak1, bak2, bak3; o primeiro válido vence
// e LoadReport diz se veio de backup (a UI avisa o jogador).
#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "shatter/character.h"
#include "shatter/expedition.h"
#include "shatter/item.h"
#include "shatter/json.h"
#include "shatter/types.h"

namespace shatter {

inline constexpr int kCurrentSaveVersion = 1;
inline constexpr int kSaveBackupCount = 3;
inline constexpr const char* kSaveFormatTag = "echoes-of-the-shatter-save";

enum class ExpeditionStatus : std::uint8_t {
    None = 0,       // nenhuma expedição
    Running = 1,    // em andamento (ou terminada e ainda não coletada)
    Collected = 2,  // coletada; loot já está no baú NESTE MESMO save
};

// Expedição gravada: o pedido completo basta para recalcular o resultado (determinismo).
struct SavedExpedition {
    ExpeditionStatus status = ExpeditionStatus::None;
    int characterIndex = -1;            // índice em SaveData::characters
    ExpeditionRequest request;          // snapshot, seed, start, duração, regras, content_version
    std::uint64_t collectedResultHash = 0;  // ExpeditionResult::resultHash da coleta (anti-duplicação)
};

struct SaveData {
    int saveVersion = kCurrentSaveVersion;
    std::uint32_t contentVersion = 0;
    std::vector<CharacterState> characters;
    std::vector<ItemInstance> stash;          // baú compartilhado
    std::vector<StackEntry> currencies;       // ouro e materiais (compartilhados)
    int markerCharges = 0;                    // Cargas do Marco
    std::int64_t lastRestDay = 0;             // UtcDay do último descanso
    UnixSeconds lastSeenUtc = 0;
    std::uint64_t nextItemUid = 1;
    int expeditionSlots = 1;                  // 1 no AA; 2º slot é recompensa de endgame
    std::vector<SavedExpedition> expeditions; // 0..expeditionSlots
    std::vector<ContentId> codexSeenUniques;  // Codex (Fragmentos de Eco)
    std::vector<ContentId> booksSeen;         // proteção contra azar (Irmã Odete)
};

// ---------------------------------------------------------------------------
// JSON <-> SaveData
// ---------------------------------------------------------------------------
// Serializa SÓ o objeto "data". Nomes de campo em snake_case (estáveis, como IDs).
json::Value SaveToJson(const SaveData& s);
// Lê o objeto "data" já migrado para kCurrentSaveVersion. Campos ausentes → padrão.
bool SaveFromJson(const json::Value& data, SaveData& out, std::string* error);

// ADIÇÃO (docs/09_mudancas_contrato.md): as partes do save em JSON, no MESMO formato de "data"
// (snake_case, uint64 como texto decimal). Usadas pela API C para o snapshot e o pedido de expedição.
json::Value ItemToJson(const ItemInstance& item);
bool ItemFromJson(const json::Value& v, ItemInstance& out, std::string* error = nullptr);
json::Value CharacterToJson(const CharacterState& c);
bool CharacterFromJson(const json::Value& v, CharacterState& out, std::string* error = nullptr);
json::Value ExpeditionRequestToJson(const ExpeditionRequest& r);
bool ExpeditionRequestFromJson(const json::Value& v, ExpeditionRequest& out, std::string* error = nullptr);
// Nomes estáveis dos enums no JSON ("xp", "life_below", "use_potion", "running", "duration_reached"...).
const char* ToString(ExpeditionObjective o);
const char* ToString(AiCondition c);
const char* ToString(AiAction a);
const char* ToString(ExpeditionStatus s);
const char* ToString(StopReason r);
bool ParseExpeditionObjective(std::string_view text, ExpeditionObjective& out);
bool ParseAiCondition(std::string_view text, AiCondition& out);
bool ParseAiAction(std::string_view text, AiAction& out);
bool ParseStopReason(std::string_view text, StopReason& out);

// Envelope completo do arquivo (format, save_version, sha256, data). pretty=true no disco.
std::string SerializeJson(const SaveData& s, bool pretty = true);

enum class LoadStatus : std::uint8_t {
    Ok = 0,
    Missing,            // arquivo não existe
    BadJson,
    BadFormatTag,
    ChecksumMismatch,
    TooNew,             // save_version > kCurrentSaveVersion (save de versão futura do jogo)
    MigrationFailed,
    BadData,
};
// Parse do envelope + checagem de hash + migração até kCurrentSaveVersion + SaveFromJson.
LoadStatus ParseJson(std::string_view fileText, SaveData& out, std::string* error = nullptr);

// ADIÇÃO (docs/09_mudancas_contrato.md): RNF-10. false se o save foi gravado com um content_version
// maior que o do jogo (o chamador recusa com aviso e NÃO altera o arquivo).
bool SaveContentVersionSupported(const SaveData& s, const ContentDB& db);

// ---------------------------------------------------------------------------
// Migração (opera na árvore JSON de "data")
// ---------------------------------------------------------------------------
// Cada mudança de formato ganha UMA função v→v+1 registrada em src/save_migrations.cpp.
// Migrate aplica em sequência from→from+1→…→to. Retorna false se faltar um passo.
// O CI guarda tests/data/saves/save_vN.json de cada versão publicada e testa todos.
using MigrationFn = bool (*)(json::Value& data, std::string* error);
bool Migrate(json::Value& data, int from, int to, std::string* error = nullptr);
// Tabela de migrações: índice i = função de (i+1) → (i+2). Exposta para teste.
const std::vector<MigrationFn>& Migrations();

// ---------------------------------------------------------------------------
// E/S de arquivo — abstraída para o UE poder usar IPlatformFile se quiser.
// ---------------------------------------------------------------------------
class IFileIO {
public:
    virtual ~IFileIO() = default;
    virtual bool Exists(const std::string& path) = 0;
    virtual bool ReadAll(const std::string& path, std::string& out) = 0;
    virtual bool WriteAll(const std::string& path, std::string_view data) = 0;  // cria/substitui e faz flush
    virtual bool Copy(const std::string& from, const std::string& to) = 0;      // substitui destino
    virtual bool Rename(const std::string& from, const std::string& to) = 0;    // substitui destino
    virtual bool Remove(const std::string& path) = 0;
};
// Implementação padrão com <cstdio>/<filesystem> (testes, bench e também o jogo).
// Caminhos UTF-8; no Windows a implementação converte para wide (std::filesystem::u8path).
std::unique_ptr<IFileIO> MakeStdFileIO();

struct LoadReport {
    LoadStatus status = LoadStatus::Missing;
    int usedBackup = 0;          // 0 = principal; 1..3 = backup usado
    std::string error;
};

// Grava slot (ex.: base = ".../Saved/SaveGames/slot_1") com tmp→rename e 3 backups.
bool WriteSaveFile(IFileIO& io, const std::string& basePath, const SaveData& s, std::string* error = nullptr);
// Lê o principal; se inválido, o backup mais recente válido.
LoadReport ReadSaveFile(IFileIO& io, const std::string& basePath, SaveData& out);

// Nomes derivados (base + sufixo): ".json", ".tmp", ".bak1".. ".bak3".
inline std::string SavePath(const std::string& base) { return base + ".json"; }
inline std::string SaveTmpPath(const std::string& base) { return base + ".tmp"; }
inline std::string SaveBackupPath(const std::string& base, int n) { return base + ".bak" + std::to_string(n); }

// ---------------------------------------------------------------------------
// ADIÇÃO (docs/09_mudancas_contrato.md): progresso manual e início de expedição.
// O jogo informa o que aconteceu; as regras de cargas e domínio ficam aqui, não no C#.
// ---------------------------------------------------------------------------
struct AreaRunOutcome {
    bool reachedEnd = false;    // percorreu a área até o fim nesta corrida
    bool bossDefeated = false;  // venceu o chefe da área nesta MESMA corrida
};
struct AreaRunReward {
    int chargesGained = 0;      // cargas que entraram de fato (depois do teto charges_max)
    bool newConquest = false;   // o domínio foi gravado agora (libera a expedição na Ilsa)
};
// Fim de uma corrida manual numa área (RF-35, RF-50):
//  - domínio = chegar ao fim E vencer o chefe na mesma corrida (mapa sem bossEncounter: só chegar ao fim);
//    a primeira vez grava o mapa em conquered_maps (e highest_tier_cleared, se o tier for maior);
//  - cargas: o maior entre limpar a área (+charges_clear_area) e vencer o chefe (+charges_boss), mais
//    +charges_new_area na primeira conquista (Cripta: 2 + 3 = +5); o total respeita charges_max.
// Devolve false (sem alterar nada) se o personagem ou o mapa não existirem.
bool RecordAreaRun(const ContentDB& db, SaveData& s, std::size_t characterIndex, const ContentId& mapId,
                   const AreaRunOutcome& run, AreaRunReward* reward = nullptr);

struct ExpeditionStartParams {
    std::size_t characterIndex = 0;
    ContentId mapId;
    ExpeditionObjective objective = ExpeditionObjective::Xp;
    std::vector<AiRule> rules;
    int durationHours = 1;
    std::uint64_t seed = 0;     // gerado pelo jogo (o core não tem fonte de entropia)
    UnixSeconds startUtc = 0;   // ResolveNow(...).now no momento da partida
};
// Inicia a expedição no save (RF-31, RF-35, RF-37, RF-39, RF-43): confere CanStartExpedition com as
// cargas do save e "outra em andamento" entre TODOS os personagens; se Ok, congela o snapshot do
// personagem (RF-38), grava a expedição Running (reaproveita uma vaga None/Collected ou acrescenta até
// expeditionSlots) e desconta durationHours × charges_per_hour cargas. Não grava em disco.
// Personagem inexistente: UnknownContent. Sem vaga livre: AnotherExpeditionRunning.
StartCheck StartExpedition(const ContentDB& db, SaveData& s, const ExpeditionStartParams& p,
                           std::vector<ContentId>* blockingIds = nullptr);

// ---------------------------------------------------------------------------
// Coleta de expedição sem duplicar (plano, seção 10 "Coleta sem duplicar").
// ---------------------------------------------------------------------------
// Adiciona itens (com uid novos) e stacks do resultado ao baú, aplica XP ao personagem
// (via XpToNextLevel), marca status = Collected e grava collectedResultHash — tudo em `s`.
// O chamador grava o save UMA vez em seguida. Se status já for Collected com o mesmo hash,
// não faz nada e devolve false (idempotente).
bool CollectExpedition(const ContentDB& db, SaveData& s, std::size_t expeditionIndex, const ExpeditionResult& r);

}  // namespace shatter
