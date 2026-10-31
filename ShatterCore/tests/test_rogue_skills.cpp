// Árvore de habilidades por classe do roguelike 2D (rogue.h, API 1.10): regras do habilidades_2d.gd (doc 29) com a
// fixture do PR 127 (habilidades_teste.csv) e a árvore real do Guerreiro (godot/data2d/habilidades_guerreiro.csv).
// A pasta de dados é uma cópia de godot/data2d com classes_2d.csv e os pontos de habilidade do run_settings.
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "test_util.h"

using namespace shatter;

namespace {

namespace fs = std::filesystem;

std::string RogueDir() { return SHATTER_ROGUE_DATA_DIR; }

// Fixture do PR 127 (godot/data2d/testes/habilidades_teste.csv).
const char* kFixture =
    "id,ramo,tipo,tier,pai,pontos,nivel_max,efeito,cd,custo,dano,qtd,angulo,raio,duracao,alcance,valor,escala,stat,modo,icone\n"
    "t_golpe,fogo,ativa,1,,1,3,golpe,2,10,20,1,0,0,0,300,0,0.5,,,tiro\n"
    "t_nova,fogo,ativa,2,t_golpe,2,2,nova,5,30,40,0,0,120,0,0,0,0.5,,,tiro\n"
    "t_vigor,vida,passiva,1,,1,3,,0,0,0,0,0,0,0,0,0.2,0,hp_max,mult,\n"
    "t_passo,vida,passiva,2,t_vigor,1,2,,0,0,0,0,0,0,0,0,10,0,speed,add,\n";

void WriteText(const std::string& path, const std::string& text) {
    std::ofstream out(fs::u8path(path), std::ios::binary);
    out << text;
}

// Cópia de godot/data2d com classes_2d.csv: "teste" (fixture), "guerreiro" (árvore real) e "mago" (sem arquivo).
std::string SkillDir() {
    static std::string dir;
    if (!dir.empty()) return dir;
    dir = tu::TmpDir("rogue_skills_data");
    for (const char* t : {"meta.csv", "receitas.csv", "drops.csv", "rota.csv", "run.csv", "upgrades.csv",
                          "habilidades_guerreiro.csv"})
        WriteText(dir + "/" + t, tu::ReadFile(RogueDir() + "/" + t));
    std::string settings = tu::ReadFile(RogueDir() + "/run_settings.csv");
    if (settings.find("skill_points_room") == std::string::npos) {
        if (!settings.empty() && settings.back() != '\n') settings += "\n";
        settings += "skill_points_room,1,pontos,teste\nskill_points_boss,3,pontos,teste\n";
    }
    WriteText(dir + "/run_settings.csv", settings);
    WriteText(dir + "/habilidades_teste.csv", kFixture);
    WriteText(dir + "/classes_2d.csv",
              "id,nome,sprite,habilidades,efeitos,hp_max,speed,mana_max\n"
              "teste,class.teste,arqueiro,res://data2d/habilidades_teste.csv,,,,80\n"
              "guerreiro,class.guerreiro,guerreiro,res://data2d/habilidades_guerreiro.csv,,150,235,60\n"
              "mago,class.mago,mago,res://data2d/habilidades_mago_que_nao_existe.csv,,80,250,140\n");
    return dir;
}

const RogueData& Data() {
    static RogueData d;
    static bool loaded = false;
    if (!loaded) {
        loaded = true;
        d.LoadDirectory(SkillDir());
        d.Finalize();
    }
    return d;
}

RogueStats Base() { return {{"hp_max", 100.0}, {"speed", 200.0}, {"skill_cd_mult", 1.0}}; }

double Stat(const RogueStats& s, const std::string& id) {
    for (const auto& p : s)
        if (p.first == id) return p.second;
    return -1.0;
}

double Num(const RogueSkillLevelDef& d, const std::string& col) {
    for (const auto& p : d.numbers)
        if (p.first == col) return p.second;
    return -1.0;
}

void ClearRoom(RogueState& s) {
    while (s.Phase() == RoguePhase::Fight) {
        const RogueNode* n = s.CurrentNode();
        int idx = n->enemyTotal - s.Alive();
        for (const RogueEnemyCount& e : n->enemyList) {
            if (idx < e.count) {
                s.EnemyKilled(e.enemy);
                break;
            }
            idx -= e.count;
        }
    }
}

}  // namespace

TEST(rogue_skills_load_classes_and_trees) {
    const RogueData& d = Data();
    for (const ContentError& e : d.Errors()) FAIL(e.table + ":" + std::to_string(e.line) + " " + e.message);
    ASSERT_TRUE(d.Ok());
    ASSERT_EQ(d.Classes().size(), std::size_t(3));
    EXPECT_EQ(d.Classes()[0].skills.size(), std::size_t(4));
    EXPECT_EQ(d.Classes()[1].skills.size(), std::size_t(20));
    EXPECT_EQ(d.Classes()[2].skills.size(), std::size_t(0));  // árvore ausente = classe sem árvore
    EXPECT_EQ(d.SkillPointsRoom(), std::int64_t(1));
    EXPECT_EQ(d.SkillPointsBoss(), std::int64_t(3));
    const RogueSkillDef& nova = d.Classes()[0].skills[1];
    EXPECT_EQ(nova.parentIndex, 0);
    EXPECT_EQ(nova.points, 2);
    EXPECT_TRUE(nova.active);
    // Colunas extras do Guerreiro (espera, recup) passam como número.
    const int heavy = d.FindSkill(1, "w_heavy_slash");
    ASSERT_TRUE(heavy >= 0);
    bool espera = false;
    for (const auto& p : d.Classes()[1].skills[static_cast<std::size_t>(heavy)].numbers)
        if (p.first == "espera") espera = p.second == 0.35;
    EXPECT_TRUE(espera);

    // Sem classes_2d.csv (godot/data2d de hoje): nenhuma classe e nada muda no save.
    RogueData plain;
    plain.LoadDirectory(RogueDir());
    plain.Finalize();
    RogueState s(plain);
    if (plain.Classes().empty()) {
        EXPECT_ENUM_EQ(s.Learn("t_golpe"), RogueSkillResult::NoClass);
        EXPECT_TRUE(s.MetaToJson().find("habilidades") == std::string::npos);
    }
}

TEST(rogue_skills_reject_bad_trees) {
    auto load = [](const std::string& tree) {
        RogueData d;
        d.LoadTableCsv("classes_2d.csv", "id,habilidades\nc,res://h.csv\n");
        const bool ok = d.LoadSkillTableCsv("c", tree);
        d.Finalize();  // as tabelas do rogue faltam de propósito: só contam os erros da árvore (h.csv)
        for (const ContentError& e : d.Errors())
            if (e.table == "h.csv") return false;
        return ok;
    };
    const std::string h = "id,ramo,tipo,pai,pontos,nivel_max,cd,custo,valor,escala,stat,modo\n";
    EXPECT_FALSE(load(h + "a,r,magia,,1,1,0,0,0,0,,\n"));                  // tipo
    EXPECT_FALSE(load(h + "a,r,ativa,x,1,1,0,0,0,0,,\n"));                 // pai que não existe
    EXPECT_FALSE(load(h + "a,r,ativa,b,1,1,0,0,0,0,,\nb,r,ativa,a,1,1,0,0,0,0,,\n"));  // ciclo
    EXPECT_FALSE(load(h + "a,r,ativa,,1.5,1,0,0,0,0,,\n"));                // pontos não inteiro
    EXPECT_FALSE(load(h + "a,r,ativa,,1,1,-1,0,0,0,,\n"));                 // cd negativo
    EXPECT_FALSE(load(h + "a,r,passiva,,1,1,0,0,0.1,0,hp_max,soma\n"));    // modo
    EXPECT_FALSE(load(h + "a,r,ativa,,1,1,0,0,abc,0,,\n"));                // número inválido
    EXPECT_FALSE(load(h + "a,r,ativa,,1,1,0,0,0,0,,\na,r,ativa,,1,1,0,0,0,0,,\n"));    // id repetido
    EXPECT_FALSE(load("id,tipo\na,ativa\n"));                               // colunas obrigatórias
    EXPECT_TRUE(load(h + "a,r,ativa,,0,0,0,0,0,0,,\nb,r,passiva,a,1,2,0,0,0.1,0,hp_max,mult\n"));
    // pontos e nivel_max 0 contam como 1 (maxi(1, ...) do GDScript).
    RogueData d;
    d.LoadTableCsv("classes_2d.csv", "id,habilidades\nc,h.csv\n");
    d.LoadSkillTableCsv("c", h + "a,r,ativa,,0,0,0,0,0,0,,\n");
    d.Finalize();
    EXPECT_EQ(d.Classes()[0].skills[0].points, 1);
    EXPECT_EQ(d.Classes()[0].skills[0].maxLevel, 1);
}

TEST(rogue_skills_learn_needs_points_and_parent_and_fills_slots) {
    RogueState s(Data());
    EXPECT_EQ(s.ClassId(), std::string("teste"));
    EXPECT_ENUM_EQ(s.Learn("t_golpe"), RogueSkillResult::NoPoints);
    EXPECT_ENUM_EQ(s.Learn("nao_existe"), RogueSkillResult::Unknown);
    EXPECT_ENUM_EQ(s.AddSkillPoints(5), RogueSkillResult::Ok);
    EXPECT_ENUM_EQ(s.AddSkillPoints(-3), RogueSkillResult::Ok);  // negativo conta como 0
    EXPECT_EQ(s.SkillPoints(), std::int64_t(5));
    EXPECT_ENUM_EQ(s.Learn("t_nova"), RogueSkillResult::Locked);
    EXPECT_ENUM_EQ(s.Learn("t_golpe"), RogueSkillResult::Ok);
    EXPECT_EQ(s.SkillLevel("t_golpe"), 1);
    EXPECT_EQ(s.SkillSlot(0), std::string("t_golpe"));
    EXPECT_ENUM_EQ(s.Learn("t_nova"), RogueSkillResult::Ok);  // custa 2
    EXPECT_EQ(s.SkillPoints(), std::int64_t(2));
    EXPECT_EQ(s.SkillSlot(1), std::string("t_nova"));
    EXPECT_ENUM_EQ(s.Learn("t_nova"), RogueSkillResult::Ok);
    EXPECT_ENUM_EQ(s.Learn("t_nova"), RogueSkillResult::Maxed);
    EXPECT_EQ(s.SkillPoints(), std::int64_t(0));
    EXPECT_EQ(s.SkillSlot(2), std::string());  // subir de nível não ocupa outro slot
    EXPECT_ENUM_EQ(s.CheckLearn("t_vigor"), RogueSkillResult::NoPoints);
}

TEST(rogue_skills_equip_swaps_and_respec_refunds_everything) {
    RogueState s(Data());
    s.AddSkillPoints(6);
    s.Learn("t_golpe");
    s.Learn("t_nova");
    s.Learn("t_vigor");
    EXPECT_ENUM_EQ(s.EquipSkill(4, "t_golpe"), RogueSkillResult::BadSlot);
    EXPECT_ENUM_EQ(s.EquipSkill(-1, "t_golpe"), RogueSkillResult::BadSlot);
    EXPECT_ENUM_EQ(s.EquipSkill(2, "t_vigor"), RogueSkillResult::NotActive);
    EXPECT_ENUM_EQ(s.EquipSkill(2, "x"), RogueSkillResult::Unknown);
    EXPECT_ENUM_EQ(s.EquipSkill(1, "t_golpe"), RogueSkillResult::Ok);  // estava no 0: troca com a nova
    EXPECT_EQ(s.SkillSlot(0), std::string("t_nova"));
    EXPECT_EQ(s.SkillSlot(1), std::string("t_golpe"));
    EXPECT_ENUM_EQ(s.EquipSkill(3, "t_golpe"), RogueSkillResult::Ok);  // slot 3 vazio: o 1 fica vazio
    EXPECT_EQ(s.SkillSlot(1), std::string());
    EXPECT_EQ(s.SkillSlot(3), std::string("t_golpe"));
    EXPECT_ENUM_EQ(s.EquipSkill(3, ""), RogueSkillResult::Ok);
    EXPECT_EQ(s.SkillSlot(3), std::string());
    EXPECT_EQ(s.SkillPoints(), std::int64_t(2));
    EXPECT_ENUM_EQ(s.Respec(), RogueSkillResult::Ok);
    EXPECT_EQ(s.SkillPoints(), std::int64_t(6));
    EXPECT_EQ(s.SkillLevel("t_golpe"), 0);
    for (int k = 0; k < kRogueSkillSlots; ++k) EXPECT_EQ(s.SkillSlot(k), std::string());
    // Ativa não aprendida não entra no slot.
    EXPECT_ENUM_EQ(s.EquipSkill(0, "t_golpe"), RogueSkillResult::NotLearned);
}

TEST(rogue_skills_def_scales_with_level_like_def_nivel) {
    RogueState s(Data());
    RogueSkillLevelDef d;
    ASSERT_TRUE(s.SkillDefAt("t_golpe", 0, d));  // nível 0: valor base
    EXPECT_NEAR(Num(d, "dano"), 20.0, 1e-12);
    EXPECT_NEAR(Num(d, "qtd"), 1.0, 1e-12);
    ASSERT_TRUE(s.SkillDefAt("t_golpe", 3, d));  // 1 + 0.5 * 2 = 2x
    EXPECT_EQ(d.level, 3);
    EXPECT_NEAR(Num(d, "dano"), 40.0, 1e-12);
    EXPECT_NEAR(Num(d, "alcance"), 600.0, 1e-12);
    EXPECT_NEAR(Num(d, "qtd"), 2.0, 1e-12);
    EXPECT_NEAR(Num(d, "cd"), 2.0, 1e-12);      // cd e custo não escalam
    EXPECT_NEAR(Num(d, "custo"), 10.0, 1e-12);
    ASSERT_TRUE(s.SkillDefAt("t_nova", 2, d));
    EXPECT_NEAR(Num(d, "qtd"), 0.0, 1e-12);     // qtd 0 continua 0
    EXPECT_NEAR(Num(d, "raio"), 180.0, 1e-12);
    bool efeito = false;
    for (const auto& t : d.texts)
        if (t.first == "efeito") efeito = t.second == "nova";
    EXPECT_TRUE(efeito);
    EXPECT_FALSE(s.SkillDefAt("nao_existe", 1, d));
    // Nível atual (-1): ainda não aprendida = nível 0.
    ASSERT_TRUE(s.SkillDefAt("t_golpe", -1, d));
    EXPECT_EQ(d.level, 0);
}

TEST(rogue_skills_passives_apply_on_run_stats_and_add_missing_stat) {
    RogueState s(Data());
    s.AddSkillPoints(10);
    s.Learn("t_vigor");
    s.Learn("t_vigor");  // hp_max x1.2 x1.2
    s.Learn("t_passo");  // speed + 10
    const RogueStats p = s.ApplySkillPassives(Base());
    EXPECT_NEAR(Stat(p, "hp_max"), 144.0, 1e-9);
    EXPECT_NEAR(Stat(p, "speed"), 210.0, 1e-9);
    s.StartRun(1, Base());
    EXPECT_NEAR(Stat(s.RunStats(), "hp_max"), 144.0, 1e-9);
    // Guerreiro: stat que não está na base entra com 0 (exec_bonus), como aplicar_passivas.
    RogueState w(Data());
    ASSERT_TRUE(w.SetClass("guerreiro") == RogueSkillResult::Ok);
    w.AddSkillPoints(10);
    ASSERT_TRUE(w.Learn("w_keen_edge") == RogueSkillResult::Ok);
    ASSERT_TRUE(w.Learn("w_heavy_slash") == RogueSkillResult::Ok);
    ASSERT_TRUE(w.Learn("w_executioner") == RogueSkillResult::Ok);
    const RogueStats ws = w.ApplySkillPassives({{"damage", 20.0}});
    EXPECT_NEAR(Stat(ws, "damage"), 24.0, 1e-9);
    EXPECT_NEAR(Stat(ws, "exec_bonus"), 0.4, 1e-12);
    EXPECT_EQ(ws.back().first, std::string("exec_bonus"));
}

TEST(rogue_skills_cooldown_mana_and_cd_mult) {
    RogueState s(Data());
    s.AddSkillPoints(3);
    s.Learn("t_golpe");  // cd 2, custo 10
    EXPECT_ENUM_EQ(s.CheckUse(1, 100.0), RogueSkillResult::EmptySlot);
    EXPECT_ENUM_EQ(s.CheckUse(9, 100.0), RogueSkillResult::BadSlot);
    EXPECT_ENUM_EQ(s.CheckUse(0, 9.99), RogueSkillResult::NoMana);
    double cost = -1.0;
    EXPECT_ENUM_EQ(s.CommitUse(0, 5.0, &cost), RogueSkillResult::NoMana);
    EXPECT_NEAR(cost, 0.0, 1e-12);
    s.StartRun(7, {{"hp_max", 100.0}, {"skill_cd_mult", 0.5}});
    EXPECT_ENUM_EQ(s.CommitUse(0, 10.0, &cost), RogueSkillResult::Ok);
    EXPECT_NEAR(cost, 10.0, 1e-12);
    EXPECT_NEAR(s.SkillCooldownLeft("t_golpe"), 1.0, 1e-12);  // 2 x 0.5
    EXPECT_NEAR(s.SlotCooldownFraction(0), 0.5, 1e-12);
    EXPECT_ENUM_EQ(s.CheckUse(0, 100.0), RogueSkillResult::Cooldown);
    s.TickSkills(-1.0);
    s.TickSkills(0.4);
    EXPECT_NEAR(s.SkillCooldownLeft("t_golpe"), 0.6, 1e-12);
    s.TickSkills(1.0);
    EXPECT_NEAR(s.SkillCooldownLeft("t_golpe"), 0.0, 1e-12);
    EXPECT_ENUM_EQ(s.CheckUse(0, 10.0), RogueSkillResult::Ok);
    s.CommitUse(0, 10.0);
    s.StartRun(8, Base());  // corrida nova zera as recargas
    EXPECT_NEAR(s.SkillCooldownLeft("t_golpe"), 0.0, 1e-12);
}

TEST(rogue_skills_room_clear_and_boss_give_points_to_current_class) {
    RogueState s(Data());
    ASSERT_TRUE(s.SetClass("guerreiro") == RogueSkillResult::Ok);
    ASSERT_TRUE(s.SetExternalCards(true) == RogueRunResult::Ok);
    s.StartRun(3, Base());
    EXPECT_ENUM_EQ(s.SetClass("teste"), RogueSkillResult::WrongPhase);  // corrida viva
    std::int64_t expected = 0;
    while (s.Phase() != RoguePhase::Won) {
        ClearRoom(s);
        const bool last = s.Stage() + 1 >= s.StagesTotal();
        expected += 1 + (last ? 3 : 0);
        EXPECT_EQ(s.SkillPoints(), expected);
        const RogueDoor d = s.UseDoor();
        if (d == RogueDoor::Route) s.ChoosePath(0);
    }
    EXPECT_EQ(expected, std::int64_t(4 + 3));
    s.FinishRun();
    ASSERT_TRUE(s.SetClass("teste") == RogueSkillResult::Ok);
    EXPECT_EQ(s.SkillPoints(), std::int64_t(0));  // pontos são por classe
    ASSERT_TRUE(s.SetClass("guerreiro") == RogueSkillResult::Ok);
    EXPECT_EQ(s.SkillPoints(), expected);
    EXPECT_ENUM_EQ(s.SetClass("ladino"), RogueSkillResult::Unknown);
}

TEST(rogue_skills_save_round_trip_and_tolerant_reading) {
    RogueState s(Data());
    s.AddSkillPoints(4);
    s.Learn("t_golpe");
    s.Learn("t_vigor");
    s.SetClass("guerreiro");
    s.AddSkillPoints(2);
    s.Learn("w_charge");
    const std::string text = s.MetaToJson();
    EXPECT_TRUE(text.find("\"habilidades\":{\"teste\":{\"niveis\":{\"t_golpe\":1,\"t_vigor\":1},"
                          "\"slots\":[\"t_golpe\",\"\",\"\",\"\"],\"pontos\":2}") != std::string::npos);
    EXPECT_TRUE(text.find("\"classe\":\"guerreiro\"") != std::string::npos);
    EXPECT_TRUE(text.find("\"mago\"") == std::string::npos);  // classe sem nada guardado fica fora
    RogueState t(Data());
    EXPECT_ENUM_EQ(t.MetaFromJson(text), RogueLoadResult::Ok);
    EXPECT_EQ(t.MetaToJson(), text);
    EXPECT_EQ(t.StateHash(), s.StateHash());
    EXPECT_EQ(t.ClassId(), std::string("guerreiro"));
    EXPECT_EQ(t.SkillSlot(0), std::string("w_charge"));

    // Leitura tolerante: classe e habilidade desconhecidas fora, nível limitado, slot só com ativa aprendida e sem
    // repetir, pontos negativos viram 0, números como float (JSON do Godot), classe desconhecida = padrão.
    RogueState u(Data());
    EXPECT_ENUM_EQ(u.MetaFromJson("{\"versao\":1,\"habilidades\":{\"ladino\":{\"pontos\":9},\"teste\":{\"niveis\":"
                                  "{\"t_golpe\":9.0,\"x\":1,\"t_vigor\":-2},\"slots\":[\"t_golpe\",\"t_golpe\",\"t_vigor\","
                                  "\"t_nova\",\"t_golpe\"],\"pontos\":-4}},\"classe\":\"ladino\"}"),
                   RogueLoadResult::Ok);
    EXPECT_EQ(u.ClassId(), std::string("teste"));
    EXPECT_EQ(u.SkillLevel("t_golpe"), 3);
    EXPECT_EQ(u.SkillLevel("t_vigor"), 0);
    EXPECT_EQ(u.SkillSlot(0), std::string("t_golpe"));
    EXPECT_EQ(u.SkillSlot(1), std::string());
    EXPECT_EQ(u.SkillSlot(2), std::string());
    EXPECT_EQ(u.SkillSlot(3), std::string());
    EXPECT_EQ(u.SkillPoints(), std::int64_t(0));
}

TEST(rogue_skills_state_restore_keeps_cooldowns_and_parts_equal_whole) {
    auto play = [](RogueState& s, int from, int to) {
        for (int i = from; i < to; ++i) {
            if (i == 0) {
                s.AddSkillPoints(3);
                s.Learn("t_golpe");
                s.StartRun(11, Base());
            }
            if (s.CheckUse(0, 100.0) == RogueSkillResult::Ok) s.CommitUse(0, 100.0);
            s.TickSkills(0.25);
        }
    };
    RogueState whole(Data());
    play(whole, 0, 30);
    RogueState a(Data());
    play(a, 0, 13);
    const std::string mid = a.StateJson();
    EXPECT_TRUE(mid.find("\"cooldowns\":{\"t_golpe\":") != std::string::npos);
    RogueState b(Data());
    std::string err;
    ASSERT_TRUE(b.RestoreState(mid, &err));
    EXPECT_EQ(b.StateJson(), mid);
    play(b, 13, 30);
    EXPECT_EQ(b.StateHash(), whole.StateHash());
    // Recarga de habilidade que não é da classe, classe trocada ou valor ruim: erro e nada muda.
    const std::string before = b.StateJson();
    std::string bad = mid;
    bad.replace(bad.find("\"t_golpe\":", bad.find("\"cooldowns\"")), 10, "\"t_nada\":");
    EXPECT_FALSE(b.RestoreState(bad, &err));
    std::string badClass = mid;
    badClass.replace(badClass.find("\"classe\":\"teste\""), 16, "\"classe\":\"ladino\"");
    EXPECT_FALSE(b.RestoreState(badClass, &err));
    EXPECT_EQ(b.StateJson(), before);
}
