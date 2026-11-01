// Roguelike 2D da Cripta (rogue.h): regras do meta_2d.gd, upgrades_2d.gd e run_2d.gd com os números reais de
// godot/data2d. Se um CSV mudar, os números esperados aqui mudam junto (é de propósito: o teste prova a regra com o dado).
#include <algorithm>
#include <filesystem>
#include <string>
#include <vector>

#include "test_util.h"

using namespace shatter;

namespace {

std::string RogueDir() { return SHATTER_ROGUE_DATA_DIR; }

const RogueData& Data() {
    static RogueData d;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        d.LoadDirectory(RogueDir());
        d.Finalize();
    }
    return d;
}

RogueStats Base() { return {{"hp_max", 100.0}, {"arrow_damage", 10.0}, {"speed", 200.0}, {"shoot_cooldown", 0.5}}; }

double Stat(const RogueStats& s, const std::string& id) {
    for (const auto& p : s)
        if (p.first == id) return p.second;
    return -1.0;
}

std::int64_t GainMat(const RogueState& s, const std::string& id) {
    for (const auto& m : s.GainMaterials())
        if (m.first == id) return m.second;
    return 0;
}

bool Has(const std::vector<ContentId>& v, const std::string& id) { return std::find(v.begin(), v.end(), id) != v.end(); }

// Mata, na ordem do texto de enemies, o próximo inimigo vivo da sala atual.
RogueRunResult KillNext(RogueState& s, RogueKill* k = nullptr) {
    const RogueNode* n = s.CurrentNode();
    int idx = n->enemyTotal - s.Alive();
    for (const RogueEnemyCount& e : n->enemyList) {
        if (idx < e.count) return s.EnemyKilled(e.enemy, k);
        idx -= e.count;
    }
    return s.EnemyKilled("crypt_bat", k);
}

void ClearRoom(RogueState& s) {
    while (s.Phase() == RoguePhase::Fight) KillNext(s);
}

// Leva a corrida até a etapa `stage` (0-based) pelo caminho padrão, escolhendo a 1ª carta.
void AdvanceTo(RogueState& s, int stage) {
    while (s.Stage() < stage) {
        ClearRoom(s);
        if (s.Phase() == RoguePhase::Choice) s.ChooseCard(s.Offer().front(), 50.0);
        const RogueDoor d = s.UseDoor();
        if (d == RogueDoor::Route) s.ChoosePath(0);
    }
}

}  // namespace

TEST(rogue_data_loads_real_csv) {
    const RogueData& d = Data();
    for (const ContentError& e : d.Errors()) FAIL(e.table + ":" + std::to_string(e.line) + " " + e.message);
    ASSERT_TRUE(d.Ok());
    EXPECT_EQ(d.MetaDefs().size(), std::size_t(6));
    EXPECT_EQ(d.Recipes().size(), std::size_t(9));
    EXPECT_EQ(d.Drops().size(), std::size_t(13));
    EXPECT_EQ(d.Stages().size(), std::size_t(4));
    EXPECT_EQ(d.Upgrades().size(), std::size_t(21));
    EXPECT_EQ(d.UpgradeCards(), 3);
    EXPECT_EQ(d.EliteExtraCards(), 1);
    EXPECT_EQ(d.RoomClearFragments(), std::int64_t(5));
    EXPECT_EQ(d.EliteFragments(), std::int64_t(15));
    EXPECT_EQ(d.VictoryFragments(), std::int64_t(25));
    EXPECT_NEAR(d.RestHeal(), 0.5, 0.0);
    EXPECT_EQ(d.BaseSeed(), std::uint64_t(1234));
    double clearDelay = 0.0;
    EXPECT_TRUE(d.Setting("clear_delay", clearDelay));
    EXPECT_NEAR(clearDelay, 0.8, 0.0);
    // Caminhos: etapa 2 tem a elite, etapa 3 o descanso, as outras só o padrão.
    EXPECT_EQ(d.Paths(0).size(), std::size_t(1));
    ASSERT_EQ(d.Paths(1).size(), std::size_t(2));
    EXPECT_EQ(d.Paths(1)[0].id, std::string("combate"));
    EXPECT_EQ(d.Paths(1)[1].id, std::string("elite_ossuario"));
    EXPECT_EQ(d.Paths(1)[1].enemyTotal, 7);
    ASSERT_EQ(d.Paths(2).size(), std::size_t(2));
    EXPECT_EQ(d.Paths(2)[1].kind, std::string("descanso"));
    EXPECT_EQ(d.Paths(2)[1].enemyTotal, 0);
    EXPECT_EQ(d.Paths(3).size(), std::size_t(1));
    EXPECT_TRUE(d.Paths(4).empty());
    EXPECT_EQ(d.Paths(0)[0].enemyTotal, 3);
    // Materiais conhecidos (drops e receitas).
    EXPECT_EQ(d.Materials().size(), std::size_t(5));
    EXPECT_TRUE(d.FindMaterial("nucleo_estilhaco") >= 0);
}

TEST(rogue_data_rejects_bad_tables) {
    {
        RogueData d;
        EXPECT_FALSE(d.LoadDirectory(RogueDir() + "/nao_existe"));
        ASSERT_TRUE(!d.Errors().empty());
        EXPECT_TRUE(d.Errors()[0].message.rfind("E_IO", 0) == 0);
    }
    RogueData d;
    EXPECT_FALSE(d.LoadTableCsv("upgrades.csv", "id,stat,modo,valor\npower,arrow_damage,mult,0.25\n"));  // cabeçalho
    RogueData d2;
    EXPECT_FALSE(d2.LoadTableCsv("upgrades.csv", "id,stat,modo,valor,nivel_max\npower,arrow_damage,times,0.25,3\n"));
    RogueData d3;
    EXPECT_FALSE(d3.LoadTableCsv("run.csv", "sala,room,enemies\n1,r.txt,skeleton_soldier:x\n"));
    RogueData d4;
    EXPECT_FALSE(d4.LoadTableCsv("drops.csv", "inimigo,fragmentos,material,material_qtd\nbat,\"2\",osso,1\n"));
    // Habilidade que aponta para upgrade inexistente e chave obrigatória faltando: erro no Finalize.
    RogueData d5;
    EXPECT_TRUE(d5.LoadTableCsv("meta.csv", "id,tipo,alvo,stat,modo,valor,custo,nivel_max\nunlock_x,habilidade,nada,,,,10,1\n"));
    EXPECT_TRUE(d5.LoadTableCsv("upgrades.csv", "id,stat,modo,valor,nivel_max\npower,arrow_damage,mult,0.25,3\n"));
    EXPECT_TRUE(d5.LoadTableCsv("run.csv", "sala,room,enemies\n1,r.txt,crypt_bat:2\n"));
    EXPECT_TRUE(d5.LoadTableCsv("run_settings.csv", "chave,valor,unidade,nota\nupgrade_cards,2.5,,\n"));
    EXPECT_FALSE(d5.Finalize());
    bool alvo = false, missing = false, notInt = false;
    for (const ContentError& e : d5.Errors()) {
        alvo = alvo || e.message.find("alvo") != std::string::npos;
        missing = missing || e.message.find("missing chave rest_heal") != std::string::npos;
        notInt = notInt || e.message.find("upgrade_cards") != std::string::npos;
    }
    EXPECT_TRUE(alvo && missing && notInt);
}

TEST(rogue_meta_buy_dano_raises_10_percent_per_level) {
    RogueState s(Data());
    EXPECT_ENUM_EQ(s.CheckBuy("meta_dano"), RogueMetaResult::NoFragments);
    EXPECT_ENUM_EQ(s.Buy("nao_existe"), RogueMetaResult::Unknown);
    EXPECT_TRUE(s.Credit(42, {}));
    EXPECT_ENUM_EQ(s.Buy("meta_dano"), RogueMetaResult::Ok);  // custo 42
    EXPECT_EQ(s.Fragments(), std::int64_t(0));
    EXPECT_EQ(s.Level("meta_dano"), 1);
    EXPECT_NEAR(Stat(s.ApplyMeta(Base()), "arrow_damage"), 11.0, 1e-12);
    EXPECT_ENUM_EQ(s.Buy("meta_dano"), RogueMetaResult::NoFragments);
    EXPECT_TRUE(s.Credit(42 * 3, {}));
    EXPECT_ENUM_EQ(s.Buy("meta_dano"), RogueMetaResult::Ok);
    EXPECT_ENUM_EQ(s.Buy("meta_dano"), RogueMetaResult::Ok);
    EXPECT_ENUM_EQ(s.Buy("meta_dano"), RogueMetaResult::Maxed);  // nivel_max 3
    EXPECT_EQ(s.Fragments(), std::int64_t(42));
    EXPECT_NEAR(Stat(s.ApplyMeta(Base()), "arrow_damage"), 10.0 * 1.1 * 1.1 * 1.1, 1e-12);
    // meta_vida: +15 de hp_max por nível (add), custo 28.
    RogueState v(Data());
    v.Credit(28, {});
    EXPECT_ENUM_EQ(v.Buy("meta_vida"), RogueMetaResult::Ok);
    EXPECT_NEAR(Stat(v.ApplyMeta(Base()), "hp_max"), 115.0, 0.0);
    // Stat que não está na base é ignorado; a ordem da saída é a da entrada.
    const RogueStats only = v.ApplyMeta({{"speed", 200.0}});
    ASSERT_EQ(only.size(), std::size_t(1));
    EXPECT_NEAR(only[0].second, 200.0, 0.0);
}

TEST(rogue_forge_amuleto_osso_costs_bone_stone_and_30_fragments) {
    RogueState s(Data());
    EXPECT_TRUE(s.Credit(30, {{"osso_antigo", 2}, {"pedra_cinza", 1}}));
    EXPECT_ENUM_EQ(s.CheckCraft("amuleto_osso"), RogueMetaResult::NoMaterials);  // osso 3
    EXPECT_TRUE(s.Credit(0, {{"osso_antigo", 1}}));
    RogueState poor(Data());
    poor.Credit(29, {{"osso_antigo", 3}, {"pedra_cinza", 1}});
    EXPECT_ENUM_EQ(poor.Craft("amuleto_osso"), RogueMetaResult::NoFragments);
    EXPECT_ENUM_EQ(s.Craft("amuleto_osso"), RogueMetaResult::Ok);
    EXPECT_EQ(s.Fragments(), std::int64_t(0));
    EXPECT_EQ(s.Material("osso_antigo"), std::int64_t(0));
    EXPECT_EQ(s.Material("pedra_cinza"), std::int64_t(0));
    EXPECT_TRUE(s.Owns("amuleto_osso"));
    EXPECT_EQ(s.Equipped(), std::string("amuleto_osso"));  // o 1º criado se equipa sozinho
    EXPECT_NEAR(Stat(s.ApplyMeta(Base()), "arrow_damage"), 10.5, 1e-12);  // mult 0.05
    s.Credit(100, {{"osso_antigo", 9}, {"pedra_cinza", 9}});
    EXPECT_ENUM_EQ(s.Craft("amuleto_osso"), RogueMetaResult::AlreadyOwned);
    // Segundo amuleto não troca o equipado; equipar troca; equipar o mesmo desequipa.
    EXPECT_ENUM_EQ(s.Craft("amuleto_pedra"), RogueMetaResult::Ok);  // pedra 2 + osso 4 + 40
    EXPECT_EQ(s.Equipped(), std::string("amuleto_osso"));
    EXPECT_ENUM_EQ(s.Equip("amuleto_pedra"), RogueMetaResult::Ok);
    EXPECT_EQ(s.Equipped(), std::string("amuleto_pedra"));
    EXPECT_NEAR(Stat(s.ApplyMeta(Base()), "hp_max"), 110.0, 0.0);
    EXPECT_NEAR(Stat(s.ApplyMeta(Base()), "arrow_damage"), 10.0, 0.0);
    EXPECT_ENUM_EQ(s.Equip("amuleto_pedra"), RogueMetaResult::Ok);
    EXPECT_EQ(s.Equipped(), std::string());
    EXPECT_ENUM_EQ(s.Equip("amuleto_nucleo"), RogueMetaResult::NotOwned);
    EXPECT_ENUM_EQ(s.Equip("tonico_vida"), RogueMetaResult::NotOwned);
    EXPECT_ENUM_EQ(s.Craft("nao_existe"), RogueMetaResult::Unknown);
    // Material desconhecido ou negativo: Credit recusa sem mudar nada.
    const std::int64_t before = s.Fragments();
    EXPECT_FALSE(s.Credit(5, {{"ouro", 1}}));
    EXPECT_FALSE(s.Credit(-1, {}));
    EXPECT_EQ(s.Fragments(), before);
}

TEST(rogue_consumables_stock_prepare_and_apply_for_one_run) {
    RogueState s(Data());
    s.Credit(100, {{"essencia_etera", 10}, {"osso_antigo", 10}});
    EXPECT_ENUM_EQ(s.Craft("tonico_vida"), RogueMetaResult::Ok);  // essencia 1 + osso 1 + 8
    EXPECT_EQ(s.Fragments(), std::int64_t(92));
    EXPECT_ENUM_EQ(s.Craft("tonico_vida"), RogueMetaResult::Ok);
    EXPECT_ENUM_EQ(s.Craft("tonico_vida"), RogueMetaResult::Ok);
    EXPECT_ENUM_EQ(s.Craft("tonico_vida"), RogueMetaResult::StockFull);  // estoque_max 3
    EXPECT_EQ(s.Stock("tonico_vida"), 3);
    EXPECT_NEAR(Stat(s.ApplyMeta(Base()), "hp_max"), 100.0, 0.0);  // guardado não vale
    s.PrepareRun();
    EXPECT_EQ(s.Stock("tonico_vida"), 2);
    EXPECT_TRUE(s.Active("tonico_vida"));
    EXPECT_NEAR(Stat(s.ApplyMeta(Base()), "hp_max"), 125.0, 0.0);
    // Não vai ao save: ao ler, ativos zerados.
    RogueState t(Data());
    EXPECT_ENUM_EQ(t.MetaFromJson(s.MetaToJson()), RogueLoadResult::Ok);
    EXPECT_FALSE(t.Active("tonico_vida"));
    EXPECT_EQ(t.Stock("tonico_vida"), 2);
    // Gasta tudo: na 3ª preparação o tônico acaba e o seguinte não tem ativo.
    s.PrepareRun();
    s.PrepareRun();
    EXPECT_EQ(s.Stock("tonico_vida"), 0);
    EXPECT_TRUE(s.Active("tonico_vida"));
    s.PrepareRun();
    EXPECT_FALSE(s.Active("tonico_vida"));
}

TEST(rogue_run_drops_and_room_clear_bonus) {
    RogueState s(Data());
    s.StartRun(7, Base());
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Fight);
    EXPECT_EQ(s.Alive(), 3);  // hollow_sentinel:1|skeleton_soldier:2
    RogueKill k;
    EXPECT_ENUM_EQ(s.EnemyKilled("hollow_sentinel", &k), RogueRunResult::Ok);
    EXPECT_TRUE(k.hasDrop);
    EXPECT_EQ(k.fragments, std::int64_t(3));
    EXPECT_EQ(k.material, std::string("pedra_cinza"));
    EXPECT_FALSE(k.roomCleared);
    s.EnemyKilled("skeleton_soldier", &k);
    s.EnemyKilled("skeleton_soldier", &k);
    EXPECT_TRUE(k.roomCleared);
    EXPECT_EQ(k.clearFragments, std::int64_t(5));
    EXPECT_EQ(s.GainFragments(), std::int64_t(3 + 3 + 3 + 5));
    EXPECT_EQ(GainMat(s, "pedra_cinza"), std::int64_t(1));
    EXPECT_EQ(GainMat(s, "osso_antigo"), std::int64_t(2));
    EXPECT_EQ(s.GainMaterials()[0].first, std::string("pedra_cinza"));  // ordem do 1º ganho
    // Sala comum: 3 cartas distintas.
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Choice);
    ASSERT_EQ(s.Offer().size(), std::size_t(3));
    EXPECT_TRUE(s.Offer()[0] != s.Offer()[1] && s.Offer()[1] != s.Offer()[2] && s.Offer()[0] != s.Offer()[2]);
    // Inimigo sem drop: nada de ganho; morte depois da sala limpa ainda soma drop mas não limpa de novo.
    const std::int64_t g = s.GainFragments();
    s.EnemyKilled("nao_existe", &k);
    EXPECT_FALSE(k.hasDrop);
    EXPECT_EQ(s.GainFragments(), g);
    s.EnemyKilled("crypt_bat", &k);
    EXPECT_FALSE(k.roomCleared);
    EXPECT_EQ(s.GainFragments(), g + 2);
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Choice);
    // Porta fechada enquanto há cartas.
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::NotReady);
}

TEST(rogue_locked_skills_never_offered_until_unlocked) {
    RogueState s(Data());
    EXPECT_FALSE(s.Unlocked("multishot"));
    EXPECT_FALSE(s.Unlocked("pierce"));
    EXPECT_FALSE(s.Unlocked("evasion"));
    EXPECT_TRUE(s.Unlocked("power"));  // sem entrada habilidade: nasce liberado
    for (std::uint64_t seed = 1; seed <= 200; ++seed) {
        s.StartRun(seed, Base());
        ClearRoom(s);
        for (const ContentId& id : s.Offer())
            if (id == "multishot" || id == "pierce" || id == "evasion") FAIL("bloqueada oferecida: " + id);
    }
    s.FinishRun();
    s.Credit(56, {});
    EXPECT_ENUM_EQ(s.Buy("unlock_multishot"), RogueMetaResult::Ok);
    EXPECT_TRUE(s.Unlocked("multishot"));
    EXPECT_TRUE(Has(s.AvailableUpgrades(), "multishot"));
    bool seen = false;
    for (std::uint64_t seed = 1; seed <= 200 && !seen; ++seed) {
        s.StartRun(seed, Base());
        ClearRoom(s);
        seen = Has(s.Offer(), "multishot");
    }
    EXPECT_TRUE(seen);
}

TEST(rogue_elite_room_gives_15_fragments_and_one_extra_card) {
    RogueState s(Data());
    s.StartRun(11, Base());
    ClearRoom(s);
    s.ChooseCard(s.Offer().front(), 100.0);
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::Route);  // etapa 2: combate ou elite
    EXPECT_EQ(s.Stage(), 1);
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Route);
    EXPECT_ENUM_EQ(s.ChoosePath(5), RogueRunResult::Unknown);
    EXPECT_ENUM_EQ(s.ChoosePath(1), RogueRunResult::Ok);
    EXPECT_EQ(s.CurrentNode()->id, std::string("elite_ossuario"));
    EXPECT_EQ(s.Alive(), 7);
    const std::int64_t before = s.GainFragments();
    RogueKill k;
    std::int64_t drops = 0;
    while (s.Phase() == RoguePhase::Fight) {
        KillNext(s, &k);
        drops += k.fragments;
    }
    EXPECT_EQ(drops, std::int64_t(10 + 12 + 3 * 2 + 5 + 2 * 2));
    EXPECT_EQ(k.clearFragments, std::int64_t(5 + 15));
    EXPECT_EQ(s.GainFragments() - before, drops + 20);
    ASSERT_EQ(s.Offer().size(), std::size_t(4));  // 3 + 1 da elite
}

TEST(rogue_rest_heals_half_of_max_hp_without_cards) {
    RogueState s(Data());
    s.StartRun(3, Base());
    AdvanceTo(s, 1);
    ClearRoom(s);
    if (s.Phase() == RoguePhase::Choice) s.ChooseCard(s.Offer().front(), 50.0);
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::Route);  // etapa 3: combate ou descanso
    double hp = 0.0;
    EXPECT_ENUM_EQ(s.Rest(10.0, &hp), RogueRunResult::WrongPhase);
    EXPECT_ENUM_EQ(s.ChoosePath(1), RogueRunResult::Ok);
    EXPECT_EQ(s.CurrentNode()->kind, std::string("descanso"));
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Cleared);  // porta aberta, sem cartas
    EXPECT_TRUE(s.Offer().empty());
    EXPECT_EQ(s.Alive(), 0);
    const std::int64_t gains = s.GainFragments();
    double maxHp = 0.0;
    for (const auto& p : s.RunStats())
        if (p.first == "hp_max") maxHp = p.second;
    EXPECT_ENUM_EQ(s.Rest(10.0, &hp), RogueRunResult::Ok);
    EXPECT_NEAR(hp, 10.0 + maxHp * 0.5, 1e-12);
    EXPECT_ENUM_EQ(s.Rest(10.0, &hp), RogueRunResult::WrongPhase);  // uma vez por sala
    EXPECT_EQ(s.GainFragments(), gains);  // descanso não dá bônus de sala limpa
    // Cura limitada à vida máxima.
    RogueState u(Data());
    u.StartRun(3, Base());
    AdvanceTo(u, 1);
    ClearRoom(u);
    if (u.Phase() == RoguePhase::Choice) u.ChooseCard(u.Offer().front(), 50.0);
    u.UseDoor();
    u.ChoosePath(1);
    EXPECT_ENUM_EQ(u.Rest(maxHp - 1.0, &hp), RogueRunResult::Ok);
    EXPECT_NEAR(hp, maxHp, 0.0);
    // Sem hp_max nos stats: não tem como curar.
    RogueState w(Data());
    w.StartRun(3, {{"speed", 1.0}});
    AdvanceTo(w, 1);
    ClearRoom(w);
    if (w.Phase() == RoguePhase::Choice) w.ChooseCard(w.Offer().front(), 50.0);
    w.UseDoor();
    w.ChoosePath(1);
    EXPECT_ENUM_EQ(w.Rest(5.0, &hp), RogueRunResult::NoHpStat);
    EXPECT_NEAR(hp, 5.0, 0.0);
}

TEST(rogue_last_room_has_no_cards_and_door_is_victory) {
    RogueState s(Data());
    s.StartRun(5, Base());
    AdvanceTo(s, 3);
    EXPECT_EQ(s.CurrentNode()->enemyTotal, 1);  // crypt_guardian
    RogueKill k;
    s.EnemyKilled("crypt_guardian", &k);
    EXPECT_TRUE(k.roomCleared);
    EXPECT_EQ(k.fragments, std::int64_t(40));
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Cleared);
    EXPECT_TRUE(s.Offer().empty());
    const std::int64_t before = s.GainFragments();
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::Victory);
    EXPECT_EQ(s.GainFragments(), before + 25);
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Won);
    EXPECT_ENUM_EQ(s.PlayerDied(), RogueRunResult::WrongPhase);
    const RogueSummary sum = s.Summary();
    EXPECT_TRUE(sum.victory);
    EXPECT_EQ(sum.stageReached, 4);
    EXPECT_EQ(sum.stagesTotal, 4);
    EXPECT_EQ(sum.upgradesTotal, 3);
    EXPECT_EQ(sum.fragments, before + 25);
    EXPECT_TRUE(s.FinishRun());
    EXPECT_EQ(s.Fragments(), before + 25);
    EXPECT_EQ(s.GainFragments(), std::int64_t(0));
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::None);
    EXPECT_FALSE(s.FinishRun());
}

TEST(rogue_choose_card_levels_up_and_vitality_raises_current_hp) {
    RogueState s(Data());
    bool found = false;
    for (std::uint64_t seed = 1; seed <= 100 && !found; ++seed) {
        s.StartRun(seed, Base());
        ClearRoom(s);
        found = Has(s.Offer(), "vitality");
    }
    ASSERT_TRUE(found);
    double hp = 0.0;
    std::string other = "pierce";
    EXPECT_ENUM_EQ(s.ChooseCard(other, 50.0, &hp), RogueRunResult::NotOffered);
    EXPECT_ENUM_EQ(s.ChooseCard("vitality", 50.0, &hp), RogueRunResult::Ok);
    EXPECT_NEAR(hp, 80.0, 0.0);  // vitality: hp_max add 30
    EXPECT_EQ(s.RunLevel("vitality"), 1);
    EXPECT_NEAR(Stat(s.RunStats(), "hp_max"), 130.0, 0.0);
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Cleared);
    EXPECT_ENUM_EQ(s.ChooseCard("vitality", 50.0, &hp), RogueRunResult::WrongPhase);
    // power (mult 0.25) sobre a base com o meta: o upgrade vem depois do meta.
    RogueState m(Data());
    m.Credit(42, {});
    m.Buy("meta_dano");
    m.StartRun(1, Base());
    EXPECT_NEAR(Stat(m.RunStats(), "arrow_damage"), 11.0, 1e-12);
}

TEST(rogue_death_and_abandoned_run_still_credit_gains) {
    RogueState s(Data());
    s.StartRun(9, Base());
    s.EnemyKilled("hollow_sentinel");
    EXPECT_ENUM_EQ(s.PlayerDied(), RogueRunResult::Ok);
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Dead);
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::NotReady);
    EXPECT_FALSE(s.Summary().victory);
    EXPECT_EQ(s.Summary().stageReached, 1);
    EXPECT_TRUE(s.FinishRun());
    EXPECT_EQ(s.Fragments(), std::int64_t(3));
    EXPECT_EQ(s.Material("pedra_cinza"), std::int64_t(1));
    // Abandono: começar outra corrida credita o que a anterior rendeu.
    s.StartRun(10, Base());
    s.EnemyKilled("skeleton_soldier");
    EXPECT_TRUE(s.StartRun(11, Base()));
    EXPECT_EQ(s.Fragments(), std::int64_t(6));
    EXPECT_EQ(s.Material("osso_antigo"), std::int64_t(1));
    EXPECT_FALSE(s.StartRun(12, Base()));  // nada pendente
    RogueState none(Data());
    EXPECT_ENUM_EQ(none.EnemyKilled("crypt_bat"), RogueRunResult::WrongPhase);
    EXPECT_ENUM_EQ(none.PlayerDied(), RogueRunResult::WrongPhase);
}

TEST(rogue_save_round_trip_in_gdscript_format_and_atomic_file) {
    RogueState s(Data());
    s.Credit(500, {{"osso_antigo", 20}, {"pedra_cinza", 20}, {"essencia_etera", 5}});
    s.Buy("meta_dano");
    s.Buy("unlock_pierce");
    s.Craft("amuleto_osso");
    s.Craft("po_afiado");
    const std::string text = s.MetaToJson();
    EXPECT_TRUE(text.rfind("{\"versao\":1,\"fragmentos\":", 0) == 0);
    EXPECT_TRUE(text.find("\"equipado\":\"amuleto_osso\"") != std::string::npos);
    RogueState t(Data());
    EXPECT_ENUM_EQ(t.MetaFromJson(text), RogueLoadResult::Ok);
    EXPECT_EQ(t.MetaToJson(), text);
    EXPECT_EQ(t.StateHash(), s.StateHash());

    const std::string dir = tu::TmpDir("rogue_save");
    const std::string path = dir + "/save_2d.json";
    auto io = MakeStdFileIO();
    std::string err;
    ASSERT_TRUE(WriteRogueMetaFile(*io, path, s, &err));
    EXPECT_FALSE(std::filesystem::exists(std::filesystem::u8path(path + ".tmp")));
    EXPECT_EQ(tu::ReadFile(path), text);
    s.Buy("meta_vida");
    ASSERT_TRUE(WriteRogueMetaFile(*io, path, s, &err));  // substitui o principal
    RogueState u(Data());
    EXPECT_ENUM_EQ(ReadRogueMetaFile(*io, path, u), RogueLoadResult::Ok);
    EXPECT_EQ(u.Level("meta_vida"), 1);
    EXPECT_EQ(u.MetaToJson(), s.MetaToJson());
    EXPECT_ENUM_EQ(ReadRogueMetaFile(*io, dir + "/nao_existe.json", u), RogueLoadResult::Missing);
    EXPECT_EQ(u.Fragments(), std::int64_t(0));
}

TEST(rogue_save_corrupt_or_wrong_version_zeroes_state_and_reading_is_tolerant) {
    RogueState s(Data());
    s.Credit(77, {});
    EXPECT_ENUM_EQ(s.MetaFromJson("{\"versao\":1,\"fragmentos\":"), RogueLoadResult::BadJson);
    EXPECT_EQ(s.Fragments(), std::int64_t(0));
    s.Credit(77, {});
    EXPECT_ENUM_EQ(s.MetaFromJson("[1,2]"), RogueLoadResult::BadJson);
    EXPECT_EQ(s.Fragments(), std::int64_t(0));
    s.Credit(77, {});
    EXPECT_ENUM_EQ(s.MetaFromJson("{\"versao\":2,\"fragmentos\":10}"), RogueLoadResult::BadVersion);
    EXPECT_EQ(s.Fragments(), std::int64_t(0));
    EXPECT_ENUM_EQ(s.MetaFromJson("{\"fragmentos\":10}"), RogueLoadResult::BadVersion);
    // Leitura tolerante (números como float, como o JSON do Godot grava/lê).
    const char* loose =
        "{\"versao\":1.0,\"fragmentos\":-5,\"materiais\":{\"osso_antigo\":4.0,\"ouro\":9,\"pedra_cinza\":-2},"
        "\"niveis\":{\"meta_dano\":99,\"meta_vida\":2.0,\"sumiu\":1,\"meta_passo\":-1},"
        "\"amuletos\":[\"amuleto_osso\",\"tonico_vida\",\"nao_existe\",7],\"equipado\":\"amuleto_pedra\","
        "\"estoque\":{\"tonico_vida\":99,\"amuleto_osso\":1,\"po_afiado\":2}}";
    EXPECT_ENUM_EQ(s.MetaFromJson(loose), RogueLoadResult::Ok);
    EXPECT_EQ(s.Fragments(), std::int64_t(0));
    EXPECT_EQ(s.Material("osso_antigo"), std::int64_t(4));
    EXPECT_EQ(s.Material("pedra_cinza"), std::int64_t(0));
    EXPECT_EQ(s.Level("meta_dano"), 3);
    EXPECT_EQ(s.Level("meta_vida"), 2);
    EXPECT_EQ(s.Level("meta_passo"), 0);
    EXPECT_TRUE(s.Owns("amuleto_osso"));
    EXPECT_EQ(s.Equipped(), std::string());  // amuleto_pedra não foi criado
    EXPECT_EQ(s.Stock("tonico_vida"), 3);
    EXPECT_EQ(s.Stock("po_afiado"), 2);
    EXPECT_EQ(s.Stock("amuleto_osso"), 0);
    EXPECT_TRUE(s.MetaToJson().find("ouro") == std::string::npos);
}

namespace {

// Uma ação por chamada, decidida só pelo estado (assim simular em partes = de uma vez).
void Step(RogueState& s) {
    switch (s.Phase()) {
        case RoguePhase::None: {
            for (const RogueMetaDef& d : Data().MetaDefs()) s.Buy(d.id);
            for (const RogueRecipe& r : Data().Recipes()) s.Craft(r.id);
            s.PrepareRun();
            s.StartRun(s.Seed() * 31 + 17, Base());
            return;
        }
        case RoguePhase::Fight:
            if (s.Stage() == 2 && s.Alive() == 1 && (s.Seed() & 1u) == 0u) s.PlayerDied();
            else KillNext(s);
            return;
        case RoguePhase::Choice: s.ChooseCard(s.Offer()[static_cast<std::size_t>(s.Draws() % s.Offer().size())], 40.0); return;
        case RoguePhase::Cleared:
            if (s.RestPending()) s.Rest(40.0);
            else s.UseDoor();
            return;
        case RoguePhase::Route: s.ChoosePath(static_cast<int>(s.Seed() % 2)); return;
        case RoguePhase::Won:
        case RoguePhase::Dead: s.FinishRun(); return;
    }
}

}  // namespace

TEST(rogue_determinism_same_seed_same_hash_and_parts_equal_whole) {
    RogueState a(Data()), b(Data());
    a.StartRun(1234, Base());
    b.StartRun(1234, Base());
    for (int i = 0; i < 400; ++i) Step(a);
    for (int i = 0; i < 400; ++i) Step(b);
    EXPECT_EQ(a.StateHash(), b.StateHash());
    EXPECT_EQ(a.StateJson(), b.StateJson());
    EXPECT_TRUE(a.Fragments() > 0);
    // Em partes: 150 passos, estado para JSON, outro objeto retoma e faz os 250 restantes.
    RogueState c(Data());
    c.StartRun(1234, Base());
    for (int i = 0; i < 150; ++i) Step(c);
    RogueState d(Data());
    std::string err;
    ASSERT_TRUE(d.RestoreState(c.StateJson(), &err));
    EXPECT_EQ(d.StateHash(), c.StateHash());
    for (int i = 0; i < 250; ++i) Step(d);
    EXPECT_EQ(d.StateHash(), a.StateHash());
    // Outra seed muda o sorteio.
    RogueState e(Data());
    e.StartRun(99, Base());
    for (int i = 0; i < 400; ++i) Step(e);
    EXPECT_NE(e.StateHash(), a.StateHash());
    // Hash é SHA-256 em hex.
    EXPECT_EQ(a.StateHash().size(), std::size_t(64));
}

TEST(rogue_restore_rejects_invalid_state_and_keeps_current) {
    RogueState s(Data());
    s.StartRun(5, Base());
    s.EnemyKilled("hollow_sentinel");
    const std::string good = s.StateJson();
    const std::string hash = s.StateHash();
    std::string err;
    EXPECT_FALSE(s.RestoreState("{}", &err));
    EXPECT_FALSE(s.RestoreState("nada", &err));
    std::string bad = good;
    bad.replace(bad.find("\"stage\":0"), 9, "\"stage\":9");
    EXPECT_FALSE(s.RestoreState(bad, &err));
    std::string bad2 = good;
    bad2.replace(bad2.find("\"phase\":\"fight\""), 15, "\"phase\":\"dance\"");
    EXPECT_FALSE(s.RestoreState(bad2, &err));
    std::string bad3 = good;
    bad3.replace(bad3.find("\"alive\":2"), 9, "\"alive\":8");
    EXPECT_FALSE(s.RestoreState(bad3, &err));
    EXPECT_EQ(s.StateHash(), hash);
    EXPECT_TRUE(s.RestoreState(good, &err));
    EXPECT_EQ(s.StateHash(), hash);
}

// --- Modo cartas externas (API 1.9): o Guerreiro tem árvore própria no cliente; o core não sorteia nem oferece cartas. ---
namespace {

// Corrida inteira pelo mesmo caminho (etapa 2 = elite, etapa 3 = descanso), escolhendo a 1ª carta quando houver.
void PlayFullRoute(RogueState& s) {
    while (s.Phase() != RoguePhase::Won && s.Phase() != RoguePhase::Dead) {
        switch (s.Phase()) {
            case RoguePhase::Fight: KillNext(s); break;
            case RoguePhase::Choice: s.ChooseCard(s.Offer().front(), 50.0); break;
            case RoguePhase::Cleared:
                if (s.RestPending()) s.Rest(50.0);
                else s.UseDoor();
                break;
            case RoguePhase::Route: s.ChoosePath(1); break;
            default: return;
        }
    }
}

}  // namespace

TEST(rogue_external_cards_room_clear_goes_to_cleared_without_offer_or_draw) {
    RogueState s(Data());
    EXPECT_FALSE(s.ExternalCards());
    EXPECT_ENUM_EQ(s.SetExternalCards(true), RogueRunResult::Ok);  // fase None
    EXPECT_TRUE(s.ExternalCards());
    s.StartRun(7, Base());
    EXPECT_TRUE(s.ExternalCards());  // StartRun não zera o modo
    // Não muda com a corrida viva.
    EXPECT_ENUM_EQ(s.SetExternalCards(false), RogueRunResult::WrongPhase);
    EXPECT_TRUE(s.ExternalCards());
    RogueKill k;
    while (s.Phase() == RoguePhase::Fight) KillNext(s, &k);
    EXPECT_TRUE(k.roomCleared);
    EXPECT_EQ(k.clearFragments, std::int64_t(5));
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Cleared);
    EXPECT_TRUE(s.Offer().empty());
    EXPECT_EQ(s.Draws(), std::uint64_t(0));
    double hp = 0.0;
    EXPECT_ENUM_EQ(s.ChooseCard(Data().Upgrades().front().id, 50.0, &hp), RogueRunResult::WrongPhase);
    EXPECT_NEAR(hp, 50.0, 1e-12);
    EXPECT_ENUM_EQ(s.SetExternalCards(false), RogueRunResult::WrongPhase);
    // Elite: +5 da sala + 15 da elite, mas nenhuma carta.
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::Route);
    EXPECT_ENUM_EQ(s.ChoosePath(1), RogueRunResult::Ok);
    EXPECT_EQ(s.CurrentNode()->kind, std::string("elite"));
    while (s.Phase() == RoguePhase::Fight) KillNext(s, &k);
    EXPECT_EQ(k.clearFragments, std::int64_t(5 + 15));
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Cleared);
    EXPECT_TRUE(s.Offer().empty());
    // Descanso continua curando; chefe e vitória iguais.
    s.UseDoor();
    s.ChoosePath(1);
    EXPECT_TRUE(s.RestPending());
    EXPECT_ENUM_EQ(s.Rest(20.0, &hp), RogueRunResult::Ok);
    EXPECT_NEAR(hp, 70.0, 1e-12);
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::Entered);
    ClearRoom(s);
    EXPECT_ENUM_EQ(s.UseDoor(), RogueDoor::Victory);
    EXPECT_EQ(s.Draws(), std::uint64_t(0));
    // Stats da corrida = base + meta; nenhum upgrade no resumo.
    const RogueStats rs = s.RunStats(), meta = s.ApplyMeta(Base());
    ASSERT_EQ(rs.size(), meta.size());
    for (std::size_t i = 0; i < rs.size(); ++i) EXPECT_EQ(rs[i].second, meta[i].second);
    EXPECT_EQ(s.Summary().upgradesTotal, 0);
    // Depois da vitória pode mudar; FinishRun não zera.
    EXPECT_ENUM_EQ(s.SetExternalCards(true), RogueRunResult::Ok);
    s.FinishRun();
    EXPECT_TRUE(s.ExternalCards());
    EXPECT_ENUM_EQ(s.SetExternalCards(false), RogueRunResult::Ok);
    s.StartRun(7, Base());
    ClearRoom(s);
    EXPECT_ENUM_EQ(s.Phase(), RoguePhase::Choice);  // desligado: volta a sortear
    EXPECT_EQ(s.Draws(), std::uint64_t(1));
}

TEST(rogue_external_cards_same_seed_same_meta_gains_and_different_hash) {
    RogueState cards(Data()), ext(Data());
    ext.SetExternalCards(true);
    cards.StartRun(321, Base());
    ext.StartRun(321, Base());
    PlayFullRoute(cards);
    PlayFullRoute(ext);
    ASSERT_TRUE(cards.Phase() == RoguePhase::Won);
    ASSERT_TRUE(ext.Phase() == RoguePhase::Won);
    EXPECT_EQ(cards.Draws(), std::uint64_t(2));
    EXPECT_EQ(ext.Draws(), std::uint64_t(0));
    EXPECT_EQ(cards.GainFragments(), ext.GainFragments());
    EXPECT_TRUE(cards.GainMaterials() == ext.GainMaterials());
    EXPECT_EQ(cards.Summary().stageReached, ext.Summary().stageReached);
    EXPECT_NE(cards.StateHash(), ext.StateHash());
    cards.FinishRun();
    ext.FinishRun();
    EXPECT_EQ(cards.MetaToJson(), ext.MetaToJson());  // o modo não entra no save do meta
    EXPECT_TRUE(ext.MetaToJson().find("external") == std::string::npos);
    // Mesmo estado em tudo, só o modo muda: hash muda; sem o modo o JSON não ganha chave nova (igual à 1.8).
    RogueState a(Data()), b(Data());
    a.StartRun(5, Base());
    b.SetExternalCards(true);
    b.StartRun(5, Base());
    EXPECT_NE(a.StateHash(), b.StateHash());
    EXPECT_TRUE(a.StateJson().find("external_cards") == std::string::npos);
    EXPECT_TRUE(b.StateJson().find("\"external_cards\":true") != std::string::npos);
}

TEST(rogue_external_cards_state_round_trip_and_parts_equal_whole) {
    RogueState a(Data());
    a.SetExternalCards(true);
    a.StartRun(1234, Base());
    for (int i = 0; i < 400; ++i) Step(a);
    EXPECT_EQ(a.Draws(), std::uint64_t(0));  // nenhum sorteio em 400 passos (várias corridas)
    EXPECT_TRUE(a.Fragments() > 0);
    RogueState c(Data());
    c.SetExternalCards(true);
    c.StartRun(1234, Base());
    for (int i = 0; i < 150; ++i) Step(c);
    RogueState d(Data());
    std::string err;
    ASSERT_TRUE(d.RestoreState(c.StateJson(), &err));
    EXPECT_TRUE(d.ExternalCards());
    EXPECT_EQ(d.StateHash(), c.StateHash());
    for (int i = 0; i < 250; ++i) Step(d);
    EXPECT_EQ(d.StateHash(), a.StateHash());
    // Restaurar um estado sem o modo desliga o modo.
    RogueState off(Data());
    off.StartRun(1234, Base());
    ASSERT_TRUE(d.RestoreState(off.StateJson(), &err));
    EXPECT_FALSE(d.ExternalCards());
    // Inválidos: valor não booleano; modo ligado com cartas na mesa. Nada muda.
    const std::string hash = d.StateHash();
    std::string good = c.StateJson();
    std::string bad = good;
    bad.replace(bad.find("\"external_cards\":true"), 21, "\"external_cards\":1");
    EXPECT_FALSE(d.RestoreState(bad, &err));
    RogueState choice(Data());
    choice.StartRun(7, Base());
    ClearRoom(choice);
    ASSERT_TRUE(choice.Phase() == RoguePhase::Choice);
    std::string bad2 = choice.StateJson();
    bad2.insert(1, "\"external_cards\":true,");
    EXPECT_FALSE(d.RestoreState(bad2, &err));
    EXPECT_EQ(d.StateHash(), hash);
    EXPECT_FALSE(d.ExternalCards());
}
