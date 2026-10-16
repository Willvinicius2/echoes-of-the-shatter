// Save — RF-51..RF-56, RNF-05, RNF-10: ida e volta, checksum, tmp->rename, 3 backups, migração, coleta sem duplicar.
#include <map>
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

// IFileIO em memória (rápido; permite injetar falhas).
class MemIO : public IFileIO {
public:
    std::map<std::string, std::string> files;
    int failWriteAt = -1;   // n-ésimo WriteAll (0-based) grava só metade e falha
    int failRenameAt = -1;  // n-ésimo Rename falha
    int failCopyAt = -1;
    int writes = 0, renames = 0, copies = 0;

    bool Exists(const std::string& p) override { return files.count(p) != 0; }
    bool ReadAll(const std::string& p, std::string& out) override {
        const auto it = files.find(p);
        if (it == files.end()) return false;
        out = it->second;
        return true;
    }
    bool WriteAll(const std::string& p, std::string_view d) override {
        if (writes++ == failWriteAt) {
            files[p] = std::string(d.substr(0, d.size() / 2));  // queda no meio da gravação
            return false;
        }
        files[p] = std::string(d);
        return true;
    }
    bool Copy(const std::string& f, const std::string& t) override {
        if (copies++ == failCopyAt) return false;
        const auto it = files.find(f);
        if (it == files.end()) return false;
        files[t] = it->second;
        return true;
    }
    bool Rename(const std::string& f, const std::string& t) override {
        if (renames++ == failRenameAt) return false;
        const auto it = files.find(f);
        if (it == files.end()) return false;
        files[t] = it->second;
        files.erase(f);
        return true;
    }
    bool Remove(const std::string& p) override { return files.erase(p) != 0; }
};

SaveData SampleSave(double playTime = 1.0) {
    const ContentDB& db = tu::RichDb();
    SaveData s;
    s.contentVersion = db.ContentVersion();
    s.characters.push_back(tu::MakeWarrior(db, 3));
    s.characters[0].name = "Guerreiro \xC3\x9Cn\xC3\xAF\xC3\xA7\xC3\xB3" "de \xF0\x9F\x94\xA5 \"aspas\" \\ \t";
    s.characters[0].playTimeSeconds = playTime;
    s.characters[0].xp = 12.5;
    s.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)] =
        ItemInstance{18446744073709551000ull, "item_base.bone_helm", Rarity::Rare, 7, "", {{"affix.life_flat", 13.25}, {"affix.fire_res", 0.1}}, true};
    ItemInstance in;
    in.uid = 2;
    in.baseId = "item_base.leather_vest";
    in.rarity = Rarity::Magic;
    in.affixes = {{"affix.life_flat", 11.0}};
    s.stash.push_back(in);
    s.currencies = {{"currency.gold", 120}, {"material.shard", 9000000000LL}};
    s.markerCharges = 7;
    s.lastRestDay = 20000;
    s.lastSeenUtc = 1'700'000'000;
    s.nextItemUid = 18446744073709551615ull;
    s.codexSeenUniques = {"unique.bell_warden_blade"};
    s.booksSeen = {"book.spec.warrior_bastion"};
    SavedExpedition e;
    e.status = ExpeditionStatus::Running;
    e.characterIndex = 0;
    e.request = tu::MakeRequest(db, 2, 18446744073709551615ull, 3);
    e.request.startUtc = 1'700'000'000;
    s.expeditions.push_back(e);
    return s;
}

std::string Canon(const SaveData& s) { return json::Serialize(SaveToJson(s), false); }

const std::string kBase = "slot_1";

}  // namespace

TEST(save_roundtrip_is_lossless_and_canonical) {
    const SaveData s = SampleSave();
    const std::string text = SerializeJson(s, true);
    SaveData back;
    std::string err;
    ASSERT_TRUE(ParseJson(text, back, &err) == LoadStatus::Ok);
    EXPECT_EQ(Canon(back), Canon(s));
    EXPECT_EQ(back.nextItemUid, 18446744073709551615ull);
    EXPECT_EQ(back.expeditions[0].request.seed, 18446744073709551615ull);
    EXPECT_EQ(back.characters[0].name, s.characters[0].name);
    EXPECT_EQ(back.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)]->uid, 18446744073709551000ull);
    EXPECT_NEAR(back.characters[0].equipment[static_cast<std::size_t>(ItemSlot::Head)]->affixes[0].value, 13.25, 0.0);
    EXPECT_EQ(back.currencies[1].amount, static_cast<std::int64_t>(9000000000LL));
    // Compacto e pretty têm o mesmo hash (o hash é sempre da forma compacta de "data").
    json::Value a, b;
    ASSERT_TRUE(json::Parse(SerializeJson(s, true), a));
    ASSERT_TRUE(json::Parse(SerializeJson(s, false), b));
    EXPECT_EQ(a["sha256"].AsString(), b["sha256"].AsString());
    EXPECT_EQ(a["sha256"].AsString().size(), static_cast<std::size_t>(64));
    EXPECT_TRUE(text.find('\n') != std::string::npos);  // legível em editor de texto
    EXPECT_TRUE(text.find("/Game/") == std::string::npos);
}

TEST(save_rf51_rf56_v1_sample_loads_with_matching_checksum) {
    const std::string path = tu::DataDir() + "/saves/save_v1.json";
    const std::string text = tu::ReadFile(path);
    ASSERT_TRUE(!text.empty());
    SaveData s;
    std::string err;
    ASSERT_TRUE(ParseJson(text, s, &err) == LoadStatus::Ok);  // checksum do Python bate com o do core
    EXPECT_EQ(s.saveVersion, kCurrentSaveVersion);
    ASSERT_TRUE(s.characters.size() == 1);
    EXPECT_EQ(s.characters[0].name, std::string("Teste"));
    EXPECT_EQ(s.characters[0].classId, std::string("class.warrior"));
    EXPECT_EQ(s.characters[0].skillBar[0], std::string("skill.warrior.iron_cut"));
    EXPECT_EQ(s.characters[0].equipment[0]->baseId, std::string("item_base.iron_sword"));
    EXPECT_FALSE(s.characters[0].equipment[1].has_value());
    EXPECT_EQ(s.characters[0].potions, static_cast<std::int64_t>(2));
    EXPECT_EQ(s.currencies[0].amount, static_cast<std::int64_t>(120));
    EXPECT_EQ(s.markerCharges, 3);
    EXPECT_EQ(s.nextItemUid, static_cast<std::uint64_t>(2));
    ASSERT_TRUE(s.expeditions.size() == 1);
    EXPECT_ENUM_EQ(s.expeditions[0].status, ExpeditionStatus::Running);
    EXPECT_EQ(s.expeditions[0].request.seed, 9007199254740993ull);  // > 2^53: exato
    EXPECT_EQ(s.expeditions[0].request.rules.size(), static_cast<std::size_t>(2));
    EXPECT_ENUM_EQ(s.expeditions[0].request.rules[0].action, AiAction::UsePotion);
    EXPECT_NEAR(s.expeditions[0].request.rules[0].param, 0.35, 0.0);
    // Sem perda: re-serializar dá o MESMO hash do arquivo (mesma forma canônica do validador Python).
    json::Value orig, again;
    ASSERT_TRUE(json::Parse(text, orig));
    ASSERT_TRUE(json::Parse(SerializeJson(s, false), again));
    EXPECT_EQ(again["sha256"].AsString(), orig["sha256"].AsString());
    EXPECT_EQ(json::Serialize(again["data"], false), json::Serialize(orig["data"], false));
    EXPECT_TRUE(text.find("/Game/") == std::string::npos);  // só IDs
    // A expedição gravada roda no simulador (pedido completo basta).
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest req = s.expeditions[0].request;
    req.effectiveSeconds = 300;
    EXPECT_TRUE(SimulateExpedition(db, req).resultHash != 0);
}

TEST(save_rf52_altered_byte_fails_checksum_and_invalid_inputs) {
    SaveData out;
    std::string err;
    const std::string altered = tu::ReadFile(tu::DataDir() + "/saves/invalid/checksum_altered.json");
    EXPECT_ENUM_EQ(ParseJson(altered, out, &err), LoadStatus::ChecksumMismatch);
    const std::string good = SerializeJson(SampleSave(), true);
    for (std::size_t pos : {good.size() / 2, good.size() / 3, good.size() - 20}) {
        std::string bad = good;
        bad[pos] = static_cast<char>(bad[pos] == '7' ? '8' : '7');
        const LoadStatus st = ParseJson(bad, out);
        EXPECT_TRUE(st != LoadStatus::Ok);
    }
    EXPECT_ENUM_EQ(ParseJson("{ nope", out), LoadStatus::BadJson);
    EXPECT_ENUM_EQ(ParseJson("[]", out), LoadStatus::BadFormatTag);
    EXPECT_ENUM_EQ(ParseJson(R"({"format":"other","save_version":1})", out), LoadStatus::BadFormatTag);
    EXPECT_ENUM_EQ(ParseJson(R"({"format":"echoes-of-the-shatter-save","data":{}})", out), LoadStatus::BadData);
    // Dados com checksum válido, mas conteúdo ilegível (raridade desconhecida): BadData.
    json::Value data = SaveToJson(SampleSave());
    std::string text = json::Serialize(data, false);
    text = tu::Replace(text, "\"rarity\":\"rare\"", "\"rarity\":\"mythic\"");
    json::Value badData;
    ASSERT_TRUE(json::Parse(text, badData));
    json::Value env = json::Value::MakeObject();
    env.Set("format", json::Value(kSaveFormatTag));
    env.Set("save_version", json::Value(1));
    env.Set("sha256", json::Value(Sha256::HexDigest(json::Serialize(badData, false))));
    env.Set("data", badData);
    EXPECT_ENUM_EQ(ParseJson(json::Serialize(env, false), out, &err), LoadStatus::BadData);
}

TEST(save_future_version_is_refused_without_touching_the_file) {
    std::string text = SerializeJson(SampleSave(), true);
    text = tu::Replace(text, "\"save_version\": 1,", "\"save_version\": 2,");
    SaveData out;
    EXPECT_ENUM_EQ(ParseJson(text, out), LoadStatus::TooNew);
    MemIO io;
    io.files[SavePath(kBase)] = text;
    io.files[SaveBackupPath(kBase, 1)] = SerializeJson(SampleSave(), true);  // backup antigo e válido
    const LoadReport rep = ReadSaveFile(io, kBase, out);
    EXPECT_ENUM_EQ(rep.status, LoadStatus::TooNew);  // não cai silenciosamente para o backup antigo
    EXPECT_EQ(rep.usedBackup, 0);
    EXPECT_EQ(io.files[SavePath(kBase)], text);      // arquivo intacto
}

TEST(save_rnf10_content_version_newer_than_game_is_refused) {
    const ContentDB& db = tu::RichDb();
    SaveData s = SampleSave();
    EXPECT_TRUE(SaveContentVersionSupported(s, db));
    s.contentVersion = db.ContentVersion() + 1;
    EXPECT_FALSE(SaveContentVersionSupported(s, db));
    // content_version vai gravado no save e no pedido de expedição.
    json::Value v = SaveToJson(s);
    EXPECT_EQ(v["content_version"].AsInt(), static_cast<std::int64_t>(db.ContentVersion() + 1));
    EXPECT_EQ(v["expeditions"].At(0)["request"]["content_version"].AsInt(), static_cast<std::int64_t>(db.ContentVersion()));
    EXPECT_EQ(v["expeditions"].At(0)["request"]["snapshot"]["content_version"].AsInt(), static_cast<std::int64_t>(db.ContentVersion()));
}

TEST(save_migration_machinery_and_registry) {
    // Só existe a v1: nenhuma migração registrada (o exemplo potion_slots do 06_dados.md e ilustrativo, P10).
    EXPECT_EQ(Migrations().size(), static_cast<std::size_t>(kCurrentSaveVersion - 1));
    json::Value d = json::Value::MakeObject();
    d.Set("x", json::Value(1));
    std::string err;
    EXPECT_TRUE(Migrate(d, 1, 1, &err));
    EXPECT_FALSE(Migrate(d, 1, 2, &err));  // falta o passo 1->2
    EXPECT_TRUE(err.find("missing migration") != std::string::npos);
    EXPECT_FALSE(Migrate(d, 2, 1, &err));
    EXPECT_FALSE(Migrate(d, 0, 2, &err));
    // O save de exemplo de CADA versão publicada carrega na versão atual (RF-56).
    for (int v = 1; v <= kCurrentSaveVersion; ++v) {
        SaveData s;
        const std::string path = tu::DataDir() + "/saves/save_v" + std::to_string(v) + ".json";
        EXPECT_ENUM_EQ(ParseJson(tu::ReadFile(path), s, &err), LoadStatus::Ok);
    }
    // Ferramenta de migração entre versões: o JSON do exemplo v1->v2 existe e é JSON válido (referência do Data Engineer).
    json::Value expected;
    EXPECT_TRUE(json::Parse(tu::ReadFile(tu::DataDir() + "/saves/migration/v1_to_v2_expected.json"), expected));
}

TEST(save_rf52_safe_write_keeps_exactly_three_backups) {
    MemIO io;
    SaveData out;
    for (int i = 1; i <= 5; ++i) {
        ASSERT_TRUE(WriteSaveFile(io, kBase, SampleSave(i)));
        EXPECT_FALSE(io.Exists(SaveTmpPath(kBase)));  // tmp consumido pelo rename
    }
    EXPECT_TRUE(io.Exists(SavePath(kBase)));
    EXPECT_TRUE(io.Exists(SaveBackupPath(kBase, 1)));
    EXPECT_TRUE(io.Exists(SaveBackupPath(kBase, 2)));
    EXPECT_TRUE(io.Exists(SaveBackupPath(kBase, 3)));
    EXPECT_FALSE(io.Exists(SaveBackupPath(kBase, 4)));
    // main = 5ª gravação; bak1 = 4ª; bak2 = 3ª; bak3 = 2ª.
    const double expected[] = {5, 4, 3, 2};
    for (int n = 0; n <= 3; ++n) {
        SaveData s;
        const std::string p = n == 0 ? SavePath(kBase) : SaveBackupPath(kBase, n);
        ASSERT_TRUE(ParseJson(io.files[p], s) == LoadStatus::Ok);
        EXPECT_NEAR(s.characters[0].playTimeSeconds, expected[n], 0.0);
    }
    const LoadReport rep = ReadSaveFile(io, kBase, out);
    EXPECT_ENUM_EQ(rep.status, LoadStatus::Ok);
    EXPECT_EQ(rep.usedBackup, 0);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 5.0, 0.0);
}

TEST(save_rf52_failure_injection_keeps_previous_save_intact) {
    MemIO io;
    ASSERT_TRUE(WriteSaveFile(io, kBase, SampleSave(1)));
    ASSERT_TRUE(WriteSaveFile(io, kBase, SampleSave(2)));
    const std::string mainBefore = io.files[SavePath(kBase)];
    const std::string bak1Before = io.files[SaveBackupPath(kBase, 1)];
    SaveData out;
    // (a) queda no meio da escrita do .tmp.
    io.failWriteAt = io.writes;
    std::string err;
    EXPECT_FALSE(WriteSaveFile(io, kBase, SampleSave(3), &err));
    io.failWriteAt = -1;
    EXPECT_EQ(io.files[SavePath(kBase)], mainBefore);
    EXPECT_EQ(io.files[SaveBackupPath(kBase, 1)], bak1Before);
    EXPECT_NEAR(ReadSaveFile(io, kBase, out).usedBackup, 0, 0);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 2.0, 0.0);
    // (b) tmp escrito, mas o rename falha.
    io.failRenameAt = io.renames;
    EXPECT_FALSE(WriteSaveFile(io, kBase, SampleSave(3), &err));
    io.failRenameAt = -1;
    EXPECT_EQ(io.files[SavePath(kBase)], mainBefore);
    EXPECT_FALSE(io.Exists(SaveTmpPath(kBase)));
    // (c) falha na rotação dos backups: o principal continua íntegro.
    io.failCopyAt = io.copies;
    EXPECT_FALSE(WriteSaveFile(io, kBase, SampleSave(3), &err));
    io.failCopyAt = -1;
    EXPECT_EQ(io.files[SavePath(kBase)], mainBefore);
    // (d) o processo "morre" depois de gravar o .tmp: um .tmp corrompido sobrando não atrapalha a leitura.
    io.files[SaveTmpPath(kBase)] = mainBefore.substr(0, mainBefore.size() / 2);
    const LoadReport rep = ReadSaveFile(io, kBase, out);
    EXPECT_ENUM_EQ(rep.status, LoadStatus::Ok);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 2.0, 0.0);
    // Depois da falha, gravar de novo funciona.
    EXPECT_TRUE(WriteSaveFile(io, kBase, SampleSave(3)));
    ASSERT_TRUE(ReadSaveFile(io, kBase, out).status == LoadStatus::Ok);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 3.0, 0.0);
}

TEST(save_rf53_corrupted_main_loads_latest_valid_backup) {
    MemIO io;
    for (int i = 1; i <= 4; ++i) ASSERT_TRUE(WriteSaveFile(io, kBase, SampleSave(i)));
    SaveData out;
    // Altera 1 byte do principal: checksum falha e o bak1 (4... o anterior) assume.
    std::string& m = io.files[SavePath(kBase)];
    m[m.size() / 2] = static_cast<char>(m[m.size() / 2] == '5' ? '6' : '5');
    LoadReport rep = ReadSaveFile(io, kBase, out);
    EXPECT_ENUM_EQ(rep.status, LoadStatus::Ok);
    EXPECT_EQ(rep.usedBackup, 1);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 3.0, 0.0);
    // Principal e bak1 corrompidos: bak2.
    io.files[SaveBackupPath(kBase, 1)] = "{}";
    rep = ReadSaveFile(io, kBase, out);
    EXPECT_EQ(rep.usedBackup, 2);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 2.0, 0.0);
    // Salvar com o principal corrompido não empurra o lixo para dentro dos backups.
    const std::string bak2 = io.files[SaveBackupPath(kBase, 2)];
    ASSERT_TRUE(WriteSaveFile(io, kBase, SampleSave(9)));
    EXPECT_EQ(io.files[SaveBackupPath(kBase, 2)], bak2);
    // Tudo corrompido: status de erro, `out` intocado e nenhum arquivo é alterado pela leitura.
    for (const std::string& p : {SavePath(kBase), SaveBackupPath(kBase, 1), SaveBackupPath(kBase, 2), SaveBackupPath(kBase, 3)})
        io.files[p] = "garbage";
    SaveData untouched = SampleSave(77);
    rep = ReadSaveFile(io, kBase, untouched);
    EXPECT_TRUE(rep.status != LoadStatus::Ok);
    EXPECT_NEAR(untouched.characters[0].playTimeSeconds, 77.0, 0.0);
    EXPECT_EQ(io.files[SavePath(kBase)], std::string("garbage"));
    // Nada existe: Missing.
    MemIO empty;
    EXPECT_ENUM_EQ(ReadSaveFile(empty, kBase, out).status, LoadStatus::Missing);
    // Só existe um backup: ele é usado.
    MemIO onlyBak;
    onlyBak.files[SaveBackupPath(kBase, 2)] = SerializeJson(SampleSave(5), true);
    rep = ReadSaveFile(onlyBak, kBase, out);
    EXPECT_ENUM_EQ(rep.status, LoadStatus::Ok);
    EXPECT_EQ(rep.usedBackup, 2);
}

TEST(save_rf55_collect_is_idempotent_and_survives_crash_before_write) {
    const ContentDB& db = tu::RichDb();
    MemIO io;
    SaveData s = SampleSave();
    s.characters[0].level = 1;
    s.characters[0].xp = 0;
    s.expeditions[0].request = tu::MakeRequest(db, 1, 4711, 1);
    s.expeditions[0].request.effectiveSeconds = 900;
    ASSERT_TRUE(WriteSaveFile(io, kBase, s));

    // Reabre, simula e coleta em memória... e "cai" antes de gravar.
    SaveData loaded;
    ASSERT_TRUE(ReadSaveFile(io, kBase, loaded).status == LoadStatus::Ok);
    const ExpeditionResult r1 = SimulateExpedition(db, loaded.expeditions[0].request);
    ASSERT_TRUE(CollectExpedition(db, loaded, 0, r1));
    const std::size_t stashAfter = loaded.stash.size();
    // (queda: o arquivo no disco continua com status Running)

    // Reabre de novo: o resultado recalculado é idêntico e o loot entra uma única vez.
    SaveData again;
    ASSERT_TRUE(ReadSaveFile(io, kBase, again).status == LoadStatus::Ok);
    EXPECT_ENUM_EQ(again.expeditions[0].status, ExpeditionStatus::Running);
    const ExpeditionResult r2 = SimulateExpedition(db, again.expeditions[0].request);
    EXPECT_EQ(r2.resultHash, r1.resultHash);
    const std::int64_t goldBefore = again.currencies[0].amount;
    ASSERT_TRUE(CollectExpedition(db, again, 0, r2));
    EXPECT_EQ(again.stash.size(), stashAfter);
    EXPECT_ENUM_EQ(again.expeditions[0].status, ExpeditionStatus::Collected);
    EXPECT_EQ(again.expeditions[0].collectedResultHash, r2.resultHash);
    std::int64_t gold = 0;
    for (const StackEntry& st : r2.stacks) if (st.id == "currency.gold") gold = st.amount;
    EXPECT_EQ(again.currencies[0].amount, goldBefore + gold);
    EXPECT_TRUE(again.characters[0].xp > 0.0 || again.characters[0].level > 1);
    // Salva uma vez; coletar a MESMA expedição de novo não entrega nada.
    ASSERT_TRUE(WriteSaveFile(io, kBase, again));
    SaveData third;
    ASSERT_TRUE(ReadSaveFile(io, kBase, third).status == LoadStatus::Ok);
    const std::string snapshot = Canon(third);
    EXPECT_FALSE(CollectExpedition(db, third, 0, r2));
    EXPECT_EQ(Canon(third), snapshot);
    // Resultado diferente para a mesma expedição já coletada também é recusado.
    ExpeditionResult other = r2;
    other.resultHash ^= 1;
    EXPECT_FALSE(CollectExpedition(db, third, 0, other));
    EXPECT_EQ(Canon(third), snapshot);
}

TEST(save_collect_applies_items_uids_xp_cap_and_validates_input) {
    const ContentDB& db = tu::RichDb();
    SaveData s = SampleSave();
    s.nextItemUid = 50;
    s.characters[0].level = 5;
    s.characters[0].xp = 0.0;
    ExpeditionResult r;
    r.resultHash = 99;
    ItemInstance it;
    it.baseId = "item_base.bone_helm";
    r.items = {it, it};
    r.stacks = {{"currency.gold", 10}, {"material.shard", 4}};
    r.xpGained = db.XpToNextLevel(5) + 10000.0;  // acima do teto: Cripta nível 4 => teto no nível 6
    // Índice inválido, status None e personagem inexistente: recusado sem alterar nada.
    const std::string before = Canon(s);
    EXPECT_FALSE(CollectExpedition(db, s, 5, r));
    SaveData none = s;
    none.expeditions[0].status = ExpeditionStatus::None;
    EXPECT_FALSE(CollectExpedition(db, none, 0, r));
    SaveData noChar = s;
    noChar.expeditions[0].characterIndex = 3;
    EXPECT_FALSE(CollectExpedition(db, noChar, 0, r));
    ExpeditionResult zeroHash = r;
    zeroHash.resultHash = 0;
    EXPECT_FALSE(CollectExpedition(db, s, 0, zeroHash));
    EXPECT_EQ(Canon(s), before);
    ASSERT_TRUE(CollectExpedition(db, s, 0, r));
    EXPECT_EQ(s.stash.size(), static_cast<std::size_t>(3));
    EXPECT_EQ(s.stash[1].uid, static_cast<std::uint64_t>(50));
    EXPECT_EQ(s.stash[2].uid, static_cast<std::uint64_t>(51));
    EXPECT_EQ(s.nextItemUid, static_cast<std::uint64_t>(52));
    EXPECT_EQ(s.currencies[0].amount, static_cast<std::int64_t>(130));
    EXPECT_EQ(s.currencies[1].amount, static_cast<std::int64_t>(9000000004LL));
    EXPECT_EQ(s.characters[0].level, 6);  // parou no teto
    EXPECT_NEAR(s.characters[0].xp, 0.0, 0.0);
    // Pilha nova entra no fim.
    SaveData t = SampleSave();
    ExpeditionResult r2;
    r2.resultHash = 5;
    r2.stacks = {{"page.skill.warrior.cleave", 2}};
    ASSERT_TRUE(CollectExpedition(db, t, 0, r2));
    EXPECT_EQ(t.currencies.back().id, std::string("page.skill.warrior.cleave"));
}

TEST(save_rnf05_one_thousand_save_load_cycles_without_drift) {
    MemIO io;
    SaveData s = SampleSave();
    const std::string reference = Canon(s);
    for (int i = 0; i < 1000; ++i) {
        s.characters[0].playTimeSeconds = 1.0 + i;  // muda a cada ciclo
        if (!WriteSaveFile(io, kBase, s)) { FAIL("falha ao gravar"); return; }
        SaveData loaded;
        if (ReadSaveFile(io, kBase, loaded).status != LoadStatus::Ok) { FAIL("falha ao ler"); return; }
        if (Canon(loaded) != Canon(s)) { FAIL("divergencia no ciclo " + std::to_string(i)); return; }
        s = loaded;
    }
    s.characters[0].playTimeSeconds = 1.0;
    EXPECT_EQ(Canon(s), reference);  // 1000 ciclos depois, o conteúdo é o mesmo
}

TEST(save_real_filesystem_roundtrip_with_utf8_path_and_backups) {
    const std::string dir = tu::TmpDir("save_fs") + "/Sa\xC3\xAD" "das";  // acento no caminho (UTF-8)
    const std::unique_ptr<IFileIO> io = MakeStdFileIO();
    const std::string base = dir + "/slot_1";
    EXPECT_FALSE(io->Exists(SavePath(base)));
    for (int i = 1; i <= 5; ++i) ASSERT_TRUE(WriteSaveFile(*io, base, SampleSave(i)));
    EXPECT_TRUE(io->Exists(SavePath(base)));
    EXPECT_TRUE(io->Exists(SaveBackupPath(base, 3)));
    EXPECT_FALSE(io->Exists(SaveBackupPath(base, 4)));
    EXPECT_FALSE(io->Exists(SaveTmpPath(base)));
    SaveData out;
    LoadReport rep = ReadSaveFile(*io, base, out);
    EXPECT_ENUM_EQ(rep.status, LoadStatus::Ok);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 5.0, 0.0);
    // Corrompe o principal no disco: backup assume.
    std::string text;
    ASSERT_TRUE(io->ReadAll(SavePath(base), text));
    text[text.size() / 2] = static_cast<char>(text[text.size() / 2] == 'a' ? 'b' : 'a');
    ASSERT_TRUE(io->WriteAll(SavePath(base), text));
    rep = ReadSaveFile(*io, base, out);
    EXPECT_EQ(rep.usedBackup, 1);
    EXPECT_NEAR(out.characters[0].playTimeSeconds, 4.0, 0.0);
    EXPECT_TRUE(io->Remove(SaveBackupPath(base, 3)));
    EXPECT_FALSE(io->Exists(SaveBackupPath(base, 3)));
    EXPECT_FALSE(io->ReadAll(base + ".nada", text));
}
