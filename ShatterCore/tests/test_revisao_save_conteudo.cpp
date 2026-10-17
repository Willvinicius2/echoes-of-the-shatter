// Revisão do core da Etapa 2 (docs/17_revisao_core_etapa2.md): reproduções de achados em save, loot fixo e conteúdo.
//
// Cada teste afirma o comportamento CORRETO e falha no master atual. Ficam DESLIGADOS por padrão (saem cedo e passam)
// e só rodam com SHATTER_REVISAO_BUGS=1, no mesmo padrão de SHATTER_BALANCE_PROBE:
//   SHATTER_REVISAO_BUGS=1 shattercore_tests revisao_
// O nome de cada teste traz o ID do achado no docs/17. Quando o achado for corrigido, apague a guarda do teste.
// Os testes com "UB" no nome dependem de comportamento indefinido (o UBSan acusa e, no Clang, aborta):
// rodam só com SHATTER_REVISAO_UB=1, um de cada vez (shattercore_tests <nome do teste>).
#include <climits>
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

using Overrides = std::vector<std::pair<std::string, std::string>>;

bool BugsOn() { return !tu::GetEnv("SHATTER_REVISAO_BUGS").empty(); }
// Variável própria para os testes de UB: SHATTER_REVISAO_BUGS=1 roda os demais até o fim sem abortar.
bool UbOn() { return !tu::GetEnv("SHATTER_REVISAO_UB").empty(); }

std::string RichTable(const std::string& name) { return tu::ReadFile(tu::RichDir() + "/" + name); }

// Fixture rica com tabelas trocadas; `finalized` diz se o Finalize aceitou.
std::unique_ptr<ContentDB> RichWith(const Overrides& ov, bool* finalized = nullptr) {
    auto db = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        std::string text = RichTable(t);
        for (const auto& o : ov)
            if (o.first == t) text = o.second;
        db->LoadTableCsv(t, text);
    }
    const bool ok = db->Finalize();
    if (finalized) *finalized = ok;
    return db;
}

bool Drops(const LootDrop& d, const std::string& kind, const std::string& ref) {
    for (const ItemInstance& it : d.items) {
        if (kind == "unique" && it.uniqueId == ref) return true;
    }
    for (const StackEntry& s : d.stacks)
        if (s.id == ref) return true;
    return false;
}

// Save v2 com um personagem e o boss_progress dado (texto JSON), com o checksum recalculado.
std::string SaveWithBossProgress(const std::string& bossProgressJson) {
    SaveData s;
    s.characters.push_back(tu::MakeWarrior(tu::RichDb(), 3));
    const std::string text = SerializeJson(s, false);
    json::Value env;
    json::Parse(text, env);
    json::Value data = env["data"];
    json::Value chars = json::Value::MakeArray();
    for (const json::Value& c : data["characters"].Items()) {
        json::Value cc = json::Value::MakeObject();
        for (const json::Value::Member& m : c.Members()) {
            if (m.first == "boss_progress") {
                json::Value bp;
                json::Parse(bossProgressJson, bp);
                cc.Set("boss_progress", bp);
            } else {
                cc.Set(m.first, m.second);
            }
        }
        chars.Push(std::move(cc));
    }
    data.Set("characters", std::move(chars));
    json::Value out = json::Value::MakeObject();
    out.Set("format", json::Value(kSaveFormatTag));
    out.Set("save_version", json::Value(kCurrentSaveVersion));
    out.Set("sha256", json::Value(Sha256::HexDigest(json::Serialize(data, false))));
    out.Set("data", std::move(data));
    return json::Serialize(out, false);
}

}  // namespace

// ---------------------------------------------------------------------------------------------
// M1 — boss_progress do save sem validação (save.cpp:253-259): negativo adia a garantia do Único; INT_MAX estoura int.
// (O caso de entradas duplicadas está em test_revisao_api_c.cpp, porque a leitura e a gravação divergem na API C.)
// ---------------------------------------------------------------------------------------------
TEST(revisao_M1_save_aceita_boss_progress_negativo_ou_int_max) {
    if (!BugsOn()) return;  // DESLIGADO: M1
    const std::string text = SaveWithBossProgress(
        "[{\"enemy_id\":\"enemy.crypt_guardian\",\"kills\":2147483647,\"kills_since_unique\":-1000}]");
    SaveData s;
    std::string err;
    ASSERT_TRUE(ParseJson(text, s, &err) == LoadStatus::Ok);
    ASSERT_TRUE(s.characters.size() == 1 && s.characters[0].bossProgress.size() == 1);
    const BossProgressEntry& b = s.characters[0].bossProgress[0];
    // Esperado: a leitura recusa (BadData) ou corta para 0 <= killsSinceUnique <= kills < INT_MAX.
    EXPECT_TRUE(b.killsSinceUnique >= 0);
    EXPECT_TRUE(b.kills < INT_MAX);
}

TEST(revisao_M1_pity_negativo_vindo_do_save_atrasa_o_unico) {
    if (!BugsOn()) return;  // DESLIGADO: M1
    // Só a proteção (pityKills = 5) faz o Único cair; o save traz killsSinceUnique = -1000.
    bool ok = false;
    const std::unique_ptr<ContentDB> db = RichWith(
        {{"loot_entries.csv",
          tu::Replace(RichTable("loot_entries.csv"),
                      "loot.crypt.guardian,unique,unique.bell_warden_blade,,1,1,1,999,true,0.2,true,5",
                      "loot.crypt.guardian,unique,unique.bell_warden_blade,,1,1,1,999,true,0,false,5")}},
        &ok);
    ASSERT_TRUE(ok);
    const EnemyData* boss = db->FindEnemy("enemy.crypt_guardian");
    BossProgressEntry prog{boss->id, 3, -1000};
    std::uint64_t uid = 1;
    Pcg32 rng(11);
    int drops = 0;
    for (int i = 0; i < 5; ++i)
        drops += Drops(RollBossLoot(*db, *boss, 3, prog, &uid, rng), "unique", "unique.bell_warden_blade") ? 1 : 0;
    EXPECT_EQ(drops, 1);  // hoje: 0 (a garantia só viria na vitória 1005)
}

TEST(revisao_M1_kills_int_max_estoura_no_roll_UB) {
    if (!UbOn()) return;  // DESLIGADO: M1 (UB: o UBSan acusa loot.cpp:124, 131 e 133)
    const ContentDB& db = tu::RichDb();
    const EnemyData* boss = db.FindEnemy("enemy.crypt_guardian");
    BossProgressEntry prog{boss->id, INT_MAX, INT_MAX};
    std::uint64_t uid = 1;
    Pcg32 rng(3);
    RollBossLoot(db, *boss, 3, prog, &uid, rng);  // ++kills e killsSinceUnique + 1 com INT_MAX: estouro de int
    EXPECT_TRUE(prog.kills >= 0);
    EXPECT_TRUE(prog.killsSinceUnique >= 0);
}

// ---------------------------------------------------------------------------------------------
// M3 — as 21 chaves novas de rules.csv são opcionais (content.cpp:118-144) e, sem a linha, vale o número de
// balanceamento escrito em constants.h:42-68 (CLAUDE.md: nenhum número de balanceamento no código).
// ---------------------------------------------------------------------------------------------
TEST(revisao_M3_rules_sem_chave_de_balanceamento_usa_numero_do_codigo) {
    if (!BugsOn()) return;  // DESLIGADO: M3
    std::string rules = RichTable("rules.csv");
    const std::size_t at = rules.find("elite_life_mult,");
    ASSERT_TRUE(at != std::string::npos);
    rules.erase(at, rules.find('\n', at) - at + 1);
    bool ok = true;
    const std::unique_ptr<ContentDB> db = RichWith({{"rules.csv", rules}}, &ok);
    EXPECT_FALSE(ok);  // hoje: Finalize aceita e eliteLifeMult = o padrão do constants.h
    if (ok) FAIL("elite_life_mult ausente aceito; valor usado = " + std::to_string(db->Rules().eliteLifeMult));
}

// ---------------------------------------------------------------------------------------------
// M4 — as tabelas novas continuam opcionais (content.cpp:359-380 e :1121): uma pasta de dados sem potions.csv
// finaliza sem erro e o herói fica sem poções no manual e no idle.
// ---------------------------------------------------------------------------------------------
TEST(revisao_M4_conteudo_real_sem_potions_csv_finaliza_sem_pocoes) {
    if (!BugsOn()) return;  // DESLIGADO: M4
    ContentDB db;
    for (const char* t : tu::kTableNames) {
        if (std::string(t) == "potions.csv") continue;
        db.LoadTableCsv(t, tu::ReadFile(tu::ContentDir() + "/" + t));
    }
    const bool ok = db.Finalize();
    EXPECT_FALSE(ok);  // hoje: true, com db.Potions() vazio (nenhuma cura no idle; recuo só pela vida)
}

// ---------------------------------------------------------------------------------------------
// B4 — entrada FIXA numa subtabela é aceita pelo Finalize (content.cpp:1494-1495), mas loot.cpp:114 só rola fixas na
// tabela de topo e loot.cpp:144 as tira do sorteio ponderado: a entrada nunca cai.
// ---------------------------------------------------------------------------------------------
TEST(revisao_B4_entrada_fixa_em_subtabela_nunca_cai) {
    if (!BugsOn()) return;  // DESLIGADO: B4
    // O livro de especialização vira entrada fixa garantida (chance 1) numa subtabela sorteada pelo chefe.
    const std::string tables = RichTable("loot_tables.csv") + "loot.crypt.guardian_bonus,1,1,80,18,2\n";
    std::string entries = RichTable("loot_entries.csv");
    entries = tu::Replace(entries, "loot.crypt.guardian,spec_book,book.spec.warrior_bastion,5,1,1,1,999,true,,,",
                          "loot.crypt.guardian,table,loot.crypt.guardian_bonus,1000,1,1,1,999,true,,,\n"
                          "loot.crypt.guardian_bonus,spec_book,book.spec.warrior_bastion,,1,1,1,999,true,1,true,");
    bool ok = false;
    const std::unique_ptr<ContentDB> db = RichWith({{"loot_tables.csv", tables}, {"loot_entries.csv", entries}}, &ok);
    if (!ok) return;  // correção possível: o Finalize recusar a entrada fixa fora da tabela de topo do chefe
    const EnemyData* boss = db->FindEnemy("enemy.crypt_guardian");
    BossProgressEntry prog{boss->id, 0, 0};
    std::uint64_t uid = 1;
    Pcg32 rng(5);
    int books = 0;
    for (int i = 0; i < 50; ++i)
        books += Drops(RollBossLoot(*db, *boss, 3, prog, &uid, rng), "stack", "book.spec.warrior_bastion") ? 1 : 0;
    EXPECT_TRUE(books > 0);  // hoje: 0 em 50 vitórias, com chance fixa 1 e Finalize aceitando
}

// ---------------------------------------------------------------------------------------------
// B6 — recharge_remaining do save sem teto (combat.cpp:196, save.cpp:250): a poção nunca recarrega.
// ---------------------------------------------------------------------------------------------
TEST(revisao_B6_recarga_de_pocao_gigante_no_save_trava_a_carga) {
    if (!BugsOn()) return;  // DESLIGADO: B6
    const ContentDB& db = tu::RichDb();
    const PotionData* life = db.FindPotion("potion.life");
    ASSERT_TRUE(life != nullptr);
    SaveData s;
    s.characters.push_back(tu::MakeWarrior(db, 3, 0));
    s.characters[0].potionSlots[0].rechargeRemaining = 1e12;  // save editado ou corrompido
    std::string err;
    SaveData back;
    ASSERT_TRUE(ParseJson(SerializeJson(s), back, &err) == LoadStatus::Ok);
    NormalizeSavePotions(db, back);
    PotionBelt belt = MakePotionBelt(db, back.characters[0].potionSlots);
    TickPotions(db, belt, life->rechargeSeconds + 1.0);
    EXPECT_EQ(PotionCharges(belt, "potion.life"), 1);  // hoje: 0 (faltam 1e12 s)
}
