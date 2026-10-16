// Simulador de expedição — determinismo (RNF-01, RNF-02), regras do idle (RF-31..RF-43) e desempenho (RNF-03).
#include <chrono>
#include <map>
#include <memory>

#include "test_util.h"

using namespace shatter;

namespace {

using Overrides = std::vector<std::pair<std::string, std::string>>;

// Conteúdo rico com tabelas trocadas (para cenários determinísticos).
std::unique_ptr<ContentDB> MakeDb(const Overrides& ov) {
    auto db = std::make_unique<ContentDB>();
    for (const char* t : tu::kTableNames) {
        std::string text = tu::ReadFile(tu::RichDir() + "/" + t);
        for (const auto& o : ov)
            if (o.first == t) text = o.second;
        db->LoadTableCsv(t, text);
    }
    db->Finalize();
    return db;
}

std::string Rules(const std::string& from, const std::string& to) {
    return tu::Replace(tu::ReadFile(tu::RichDir() + "/rules.csv"), from, to);
}

// XP nunca sobe de nível nem bate no teto: isola Vigor e somas.
std::unique_ptr<ContentDB> BigXpDb() { return MakeDb({{"rules.csv", Rules("xp_base,100.0", "xp_base,1000000000.0")}}); }

// Um único encontro, sem sorte: 1 sentinela, ouro fixo, sem crítico/evasão. Duração idêntica em todo encontro.
std::unique_ptr<ContentDB> FlatDb() {
    return MakeDb({
        {"rules.csv", Rules("xp_base,100.0", "xp_base,1000000000.0")},
        {"encounters.csv", "id,groups,weight,travelTime,isBoss\nenc.crypt.patrol_a,enemy.hollow_sentinel:1:1:0,1,5,false\n"
                           "enc.crypt.guardian,enemy.crypt_guardian:1:1:0,1,10,true\n"},
        {"maps.csv", "id,monsterLevel,tier,encounters,bossEncounter,areaLootTable,idleAllowed\n"
                     "map.act1.crypt,4,0,enc.crypt.patrol_a,enc.crypt.guardian,loot.crypt.area,true\n"},
        {"loot_tables.csv", "id,rolls,dropChance,rarityWeightNormal,rarityWeightMagic,rarityWeightRare\n"
                            "loot.crypt.common,1,1,80,18,2\nloot.crypt.area,1,1,80,18,2\nloot.crypt.guardian,1,1,80,18,2\n"},
        {"loot_entries.csv", "tableId,kind,refId,weight,minAmount,maxAmount,minAreaLevel,maxAreaLevel,manualOnly\n"
                             "loot.crypt.common,stack,currency.gold,1,10,10,1,999,false\n"
                             "loot.crypt.area,stack,currency.gold,1,7,7,1,999,false\n"
                             "loot.crypt.guardian,stack,currency.gold,1,1,1,1,999,false\n"},
    });
}

// Inimigos que machucam de verdade (retreat/risco).
std::unique_ptr<ContentDB> HardDb() {
    std::string skills = tu::ReadFile(tu::RichDir() + "/skills.csv");
    skills = tu::Replace(skills, "skill.enemy.sentinel_strike,,,attack|melee|physical,melee,,8,", "skill.enemy.sentinel_strike,,,attack|melee|physical,melee,,30,");
    return MakeDb({{"skills.csv", skills}});
}

ExpeditionProgress RunChunks(const ContentDB& db, const ExpeditionRequest& req, std::uint32_t chunk) {
    ExpeditionProgress p;
    int guard = 0;
    while (p.stop == StopReason::None && ++guard < 1000000) p = SimulateRange(db, req, p, p.nextEncounter, chunk);
    return p;
}

std::int64_t Gold(const ExpeditionResult& r) {
    for (const StackEntry& s : r.stacks)
        if (s.id == "currency.gold") return s.amount;
    return 0;
}

}  // namespace

TEST(expedition_rnf02_one_part_equals_ten_parts_equals_random_parts) {
    const ContentDB& db = tu::RichDb();
    for (std::uint64_t seed : {1ull, 99ull, 123456789ull}) {
        const ExpeditionRequest req = tu::MakeRequest(db, 1, seed);
        const ExpeditionResult whole = SimulateExpedition(db, req);
        ASSERT_TRUE(whole.receipts.size() > 20);
        EXPECT_TRUE(whole.resultHash != 0);
        const std::uint32_t n = static_cast<std::uint32_t>(whole.receipts.size());
        const std::uint32_t tenth = (n + 9) / 10;
        for (std::uint32_t chunk : {1u, tenth, 7u, 1000000u}) {
            const ExpeditionResult parts = FinalizeExpedition(db, req, RunChunks(db, req, chunk));
            EXPECT_EQ(parts.resultHash, whole.resultHash);
            EXPECT_EQ(parts.receipts.size(), whole.receipts.size());
            EXPECT_EQ(parts.kills, whole.kills);
            EXPECT_NEAR(parts.xpGained, whole.xpGained, 0.0);
        }
        // Partes de tamanho aleatório.
        Pcg32 rng(seed ^ 0xABCDEF);
        ExpeditionProgress p;
        while (p.stop == StopReason::None) p = SimulateRange(db, req, p, p.nextEncounter, 1 + rng.NextBelow(13));
        EXPECT_EQ(FinalizeExpedition(db, req, p).resultHash, whole.resultHash);
    }
}

TEST(expedition_rnf01_same_seed_100_runs_same_hash_and_seeds_differ) {
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest req = tu::MakeRequest(db, 1, 777);
    req.effectiveSeconds = 600.0;
    const std::uint64_t h = SimulateExpedition(db, req).resultHash;
    for (int i = 0; i < 100; ++i) {
        if (SimulateExpedition(db, req).resultHash != h) { FAIL("hash divergiu"); return; }
    }
    ExpeditionRequest other = req;
    other.seed = 778;
    EXPECT_NE(SimulateExpedition(db, other).resultHash, h);
}

TEST(expedition_rnf02_changing_combat_does_not_change_loot_stream) {
    // Fluxos separados: um coeficiente de dano diferente muda o combate, mas o loot sorteado em
    // encontros que terminam iguais continua o mesmo (mesma tabela, mesmo índice de encontro).
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest req = tu::MakeRequest(db, 1, 4242);
    req.effectiveSeconds = 300.0;
    const ExpeditionResult a = SimulateExpedition(db, req);
    ASSERT_TRUE(a.receipts.size() >= 3);
    // Mesma seed, mas começando com mais vida base (muda dano recebido, não kills nem loot por encontro).
    ExpeditionRequest req2 = req;
    req2.snapshot.character.level = 2;
    const ExpeditionResult b = SimulateExpedition(db, req2);
    EXPECT_NE(a.resultHash, b.resultHash);
    const std::size_t n = std::min(a.receipts.size(), b.receipts.size());
    int sameTemplates = 0;
    for (std::size_t i = 0; i < n; ++i) {
        if (a.receipts[i].templateId == b.receipts[i].templateId) ++sameTemplates;  // fluxo Events independente
    }
    EXPECT_TRUE(sameTemplates >= static_cast<int>(n) - 1);
}

TEST(expedition_result_matches_receipts_rf41_rf42) {
    const std::unique_ptr<ContentDB> dbp = BigXpDb();
    const ContentDB& db = *dbp;
    ExpeditionRequest req = tu::MakeRequest(db, 12, 31337);
    const ExpeditionResult r = SimulateExpedition(db, req);
    ASSERT_TRUE(r.receipts.size() > 100);
    double xp = 0.0;
    std::map<std::string, double> stacks;
    int kills = 0, potions = 0;
    for (const EncounterReceipt& rc : r.receipts) {
        const double v = db.Rules().vigorByBand[rc.vigorBand];
        xp += rc.xpRaw * v;
        for (const StackEntry& s : rc.loot.stacks) stacks[s.id] += static_cast<double>(s.amount) * v;
        kills += rc.kills;
        potions += rc.potionsUsed;
    }
    EXPECT_NEAR(r.xpGained, xp, 1e-6);
    EXPECT_EQ(r.kills, kills);
    EXPECT_EQ(r.potionsUsed, potions);
    for (const StackEntry& s : r.stacks) EXPECT_EQ(s.amount, static_cast<std::int64_t>(std::floor(stacks[s.id] + 1e-9)));
    EXPECT_FALSE(r.xpCapped);
    EXPECT_NEAR(r.effectiveSeconds, r.receipts.back().startTime + r.receipts.back().duration, 1e-9);
    EXPECT_TRUE(r.effectiveSeconds <= 12 * 3600.0);
}

TEST(expedition_rf36_vigor_bands_70_and_40_percent) {
    const std::unique_ptr<ContentDB> dbp = FlatDb();
    const ContentDB& db = *dbp;
    auto run = [&](int hours) {
        ExpeditionRequest req = tu::MakeRequest(db, hours, 9);
        return SimulateExpedition(db, req);
    };
    const ExpeditionResult h4 = run(4), h8 = run(8), h12 = run(12);
    ASSERT_TRUE(h4.xpGained > 0.0 && Gold(h4) > 0);
    EXPECT_NEAR(h8.xpGained / h4.xpGained, 1.0 + 0.7, 0.017);
    EXPECT_NEAR(h12.xpGained / h4.xpGained, 1.0 + 0.7 + 0.4, 0.021);
    EXPECT_NEAR(static_cast<double>(Gold(h8)) / static_cast<double>(Gold(h4)), 1.7, 0.017);
    EXPECT_NEAR(static_cast<double>(Gold(h12)) / static_cast<double>(Gold(h4)), 2.1, 0.021);
    // Vigor não afeta itens: o número de itens segue o número de encontros, sem fator.
    EXPECT_EQ(h4.receipts.front().vigorBand, static_cast<std::uint8_t>(0));
    EXPECT_EQ(h12.receipts.back().vigorBand, static_cast<std::uint8_t>(2));
}

TEST(expedition_rf33_xp_level_cap_two_above_area) {
    const ContentDB& db = tu::RichDb();  // Cripta: nível de monstro 4 => teto no nível 6
    ExpeditionRequest atCap = tu::MakeRequest(db, 4, 5, 6);
    const ExpeditionResult r6 = SimulateExpedition(db, atCap);
    EXPECT_NEAR(r6.xpGained, 0.0, 1e-12);
    EXPECT_TRUE(r6.xpCapped);
    EXPECT_TRUE(r6.kills > 0);
    ExpeditionRequest below = tu::MakeRequest(db, 4, 5, 5);
    below.snapshot.character.xp = 100.0;
    const ExpeditionResult r5 = SimulateExpedition(db, below);
    EXPECT_NEAR(r5.xpGained, db.XpToNextLevel(5) - 100.0, 1e-6);  // sobe até o nível 6 e para
    EXPECT_TRUE(r5.xpCapped);
    ExpeditionRequest fresh = tu::MakeRequest(db, 1, 5, 1);
    fresh.effectiveSeconds = 120.0;
    const ExpeditionResult r1 = SimulateExpedition(db, fresh);
    EXPECT_TRUE(r1.xpGained > 0.0);
    EXPECT_FALSE(r1.xpCapped);
}

TEST(expedition_rf34_no_top_tier_and_rare_cap_in_many_expeditions) {
    // Raro garantido em todo item: o teto de 4 por expedição tem de segurar o excedente.
    const std::unique_ptr<ContentDB> dbp = MakeDb({
        {"loot_tables.csv", "id,rolls,dropChance,rarityWeightNormal,rarityWeightMagic,rarityWeightRare\n"
                            "loot.crypt.common,1,1,0,0,1\nloot.crypt.area,1,1,0,0,1\nloot.crypt.guardian,1,1,0,0,1\n"},
        {"loot_entries.csv", "tableId,kind,refId,weight,minAmount,maxAmount,minAreaLevel,maxAreaLevel,manualOnly\n"
                             "loot.crypt.common,item_base,item_base.leather_vest,1,1,1,1,999,false\n"
                             "loot.crypt.area,item_base,item_base.bone_helm,1,1,1,1,999,false\n"
                             "loot.crypt.guardian,item_base,item_base.leather_vest,1,1,1,1,999,false\n"},
    });
    const ContentDB& db = *dbp;
    for (std::uint64_t seed = 1; seed <= 20; ++seed) {
        ExpeditionRequest req = tu::MakeRequest(db, 2, seed);
        const ExpeditionResult r = SimulateExpedition(db, req);
        int rares = 0, magic = 0;
        for (const ItemInstance& it : r.items) {
            rares += it.rarity == Rarity::Rare ? 1 : 0;
            magic += it.rarity == Rarity::Magic ? 1 : 0;
            if (it.rarity == Rarity::Unique || !it.uniqueId.empty()) { FAIL("unico na expedicao"); return; }
        }
        if (rares > 4) { FAIL("mais de 4 Raros"); return; }
        EXPECT_EQ(rares, 4);
        EXPECT_EQ(r.raresDropped, 4);
        EXPECT_TRUE(magic > 10);  // o excedente virou Mágico
    }
    // Tabela do Guardião (com Único, livro, pedra e fragmento) usada em toda parte: nada de topo.
    const std::unique_ptr<ContentDB> dbp2 = MakeDb({
        {"enemies.csv", tu::Replace(tu::ReadFile(tu::RichDir() + "/enemies.csv"), "life:80:8|armor:10:0,10,2,loot.crypt.common", "life:80:8|armor:10:0,10,2,loot.crypt.guardian")},
    });
    for (std::uint64_t seed = 1; seed <= 20; ++seed) {
        const ExpeditionResult r = SimulateExpedition(*dbp2, tu::MakeRequest(*dbp2, 1, seed));
        for (const ItemInstance& it : r.items)
            if (it.rarity == Rarity::Unique) { FAIL("unico no idle"); return; }
        for (const StackEntry& s : r.stacks)
            if (s.id.rfind("book.", 0) == 0 || s.id.rfind("map_stone.", 0) == 0 || s.id == "material.echo_fragment") { FAIL("item de topo no idle"); return; }
    }
}

TEST(expedition_rf38_retreat_with_and_without_potions_keeps_loot) {
    const std::unique_ptr<ContentDB> dbp = HardDb();
    const ContentDB& db = *dbp;
    int earlier = 0, runs = 0;
    for (std::uint64_t seed = 1; seed <= 12; ++seed) {
        ExpeditionRequest withPotions = tu::MakeRequest(db, 4, seed, 1, 6);
        ExpeditionRequest noPotions = tu::MakeRequest(db, 4, seed, 1, 0);
        const ExpeditionResult a = SimulateExpedition(db, withPotions);
        const ExpeditionResult b = SimulateExpedition(db, noPotions);
        EXPECT_ENUM_EQ(b.stop, StopReason::Retreat);  // sem poção e com vida baixa: recua (motivo registrado)
        EXPECT_EQ(b.potionsUsed, 0);
        EXPECT_TRUE(a.potionsUsed > 0);
        ++runs;
        if (b.effectiveSeconds <= a.effectiveSeconds) ++earlier;
        // O loot dos encontros vencidos antes do recuo é entregue.
        EXPECT_TRUE(b.encountersCleared >= 1 || b.receipts.size() == 1);
        if (b.encountersCleared >= 1) EXPECT_TRUE(Gold(b) > 0 || !b.items.empty());
        if (b.receipts.back().outcome == EncounterOutcome::Retreated) {
            EXPECT_NEAR(b.receipts.back().xpRaw, 0.0, 0.0);
            EXPECT_TRUE(b.receipts.back().loot.items.empty() && b.receipts.back().loot.stacks.empty());
        }
    }
    EXPECT_TRUE(earlier >= runs - 1);  // sem poções recua mais cedo (ou no mesmo ponto)
    // Falhas de cura são contadas e geram dica.
    ExpeditionRequest req = tu::MakeRequest(db, 4, 3, 1, 0);
    const ExpeditionResult r = SimulateExpedition(db, req);
    EXPECT_TRUE(r.healFailures > 0);
    bool tip = false;
    for (const std::string& k : r.tipKeys) tip = tip || k == "tip.expedition.raise_potion_threshold";
    EXPECT_TRUE(tip);
}

TEST(expedition_rf38_gear_swap_after_start_does_not_change_result) {
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest req = tu::MakeRequest(db, 1, 55);
    req.effectiveSeconds = 600;
    const std::uint64_t before = SimulateExpedition(db, req).resultHash;
    // O jogador troca o equipamento do personagem vivo; o pedido guarda a CÓPIA congelada.
    CharacterState live = req.snapshot.character;
    ItemInstance helm;
    helm.uid = 77;
    helm.baseId = "item_base.bone_helm";
    live.equipment[static_cast<std::size_t>(ItemSlot::Head)] = helm;
    live.level = 10;
    EXPECT_EQ(SimulateExpedition(db, req).resultHash, before);
    ExpeditionRequest changed = req;
    changed.snapshot.character = live;
    EXPECT_NE(SimulateExpedition(db, changed).resultHash, before);  // prova de que o equipamento importaria
}

TEST(expedition_rf39_rule_order_first_valid_wins_and_max_six_rules) {
    const ContentDB& db = tu::RichDb();
    auto rule = [](AiCondition c, double p, const char* skill) {
        AiRule r;
        r.condition = c;
        r.param = p;
        r.action = AiAction::UseSkill;
        r.refId = skill;
        return r;
    };
    ExpeditionRequest a = tu::MakeRequest(db, 1, 8);
    a.effectiveSeconds = 600;
    a.rules = {rule(AiCondition::Always, 0, "skill.warrior.iron_cut"), rule(AiCondition::Always, 0, "skill.warrior.cleave")};
    ExpeditionRequest b = a;
    b.rules = {rule(AiCondition::Always, 0, "skill.warrior.cleave"), rule(AiCondition::Always, 0, "skill.warrior.iron_cut")};
    EXPECT_NE(SimulateExpedition(db, a).resultHash, SimulateExpedition(db, b).resultHash);  // a ordem decide
    // A 7ª regra nunca é avaliada: o resultado é igual ao de 6 regras.
    ExpeditionRequest six = a;
    six.rules.clear();
    for (int i = 0; i < 6; ++i) six.rules.push_back(rule(AiCondition::EnemiesAtLeast, 99, "skill.warrior.cleave"));
    ExpeditionRequest seven = six;
    seven.rules.push_back(rule(AiCondition::Always, 0, "skill.warrior.cleave"));
    EXPECT_EQ(SimulateExpedition(db, six).resultHash, SimulateExpedition(db, seven).resultHash);
    // Regra inválida (habilidade fora da barra / em recarga) é pulada; sem regra válida, ataque básico.
    ExpeditionRequest bad = a;
    bad.rules = {rule(AiCondition::Always, 0, "skill.warrior.unsupported_roar")};
    ExpeditionRequest none = a;
    none.rules.clear();
    EXPECT_EQ(SimulateExpedition(db, bad).resultHash, SimulateExpedition(db, none).resultHash);
}

TEST(expedition_can_start_checks_rf31_rf35_rf37_rf39_rf43) {
    const ContentDB& db = tu::RichDb();
    CharacterState c = tu::MakeWarrior(db);
    std::vector<ContentId> blocking;
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 4, 12, false, 3, &blocking), StartCheck::Ok);
    // RF-31: área não dominada.
    CharacterState fresh = c;
    fresh.conqueredMaps.clear();
    EXPECT_ENUM_EQ(CanStartExpedition(db, fresh, "map.act1.crypt", 4, 12, false, 3, nullptr), StartCheck::MapNotConquered);
    // RF-35: 5 h com 3 cargas é recusada; 3 h com 3 cargas passa.
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 5, 3, false, 3, nullptr), StartCheck::NotEnoughCharges);
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 3, 3, false, 3, nullptr), StartCheck::Ok);
    // RF-37: segunda expedição.
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 1, 12, true, 3, nullptr), StartCheck::AnotherExpeditionRunning);
    // RF-39: duração e regras.
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 0, 12, false, 3, nullptr), StartCheck::InvalidDuration);
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 13, 99, false, 3, nullptr), StartCheck::InvalidDuration);
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 12, 12, false, 6, nullptr), StartCheck::Ok);
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.act1.crypt", 4, 12, false, 7, nullptr), StartCheck::TooManyRules);
    // RF-43: build com habilidade sem IdleProfile.
    CharacterState roar = c;
    roar.skillBar[3] = "skill.warrior.unsupported_roar";
    EXPECT_ENUM_EQ(CanStartExpedition(db, roar, "map.act1.crypt", 4, 12, false, 3, &blocking), StartCheck::IdleIncompatible);
    ASSERT_TRUE(blocking.size() == 1);
    EXPECT_EQ(blocking[0], std::string("skill.warrior.unsupported_roar"));
    // Conteúdo desconhecido.
    EXPECT_ENUM_EQ(CanStartExpedition(db, c, "map.ghost", 4, 12, false, 3, nullptr), StartCheck::UnknownContent);
    // Endgame: só até 1 tier abaixo do maior tier vencido na mão.
    CharacterState eg = c;
    eg.conqueredMaps = {"map.endgame.ossuary", "map.endgame.ossuary_deep"};
    eg.highestTierCleared = 1;
    EXPECT_ENUM_EQ(CanStartExpedition(db, eg, "map.endgame.ossuary", 4, 12, false, 3, nullptr), StartCheck::MapNotConquered);
    eg.highestTierCleared = 2;
    EXPECT_ENUM_EQ(CanStartExpedition(db, eg, "map.endgame.ossuary", 4, 12, false, 3, nullptr), StartCheck::Ok);
    EXPECT_ENUM_EQ(CanStartExpedition(db, eg, "map.endgame.ossuary_deep", 4, 12, false, 3, nullptr), StartCheck::MapNotConquered);
}

TEST(expedition_stops_and_error_paths) {
    const ContentDB& db = tu::RichDb();
    // Pedido com ID removido do conteúdo: ContentMismatch, sem recibos.
    ExpeditionRequest req = tu::MakeRequest(db, 1, 3);
    req.snapshot.character.skills[0].skillId = "skill.warrior.removed";
    const ExpeditionResult r = SimulateExpedition(db, req);
    EXPECT_ENUM_EQ(r.stop, StopReason::ContentMismatch);
    EXPECT_TRUE(r.receipts.empty());
    ExpeditionRequest noMap = tu::MakeRequest(db, 1, 3);
    noMap.mapId = "map.removed";
    EXPECT_ENUM_EQ(SimulateExpedition(db, noMap).stop, StopReason::ContentMismatch);
    // Build incompatível: parada registrada.
    ExpeditionRequest roar = tu::MakeRequest(db, 1, 3);
    roar.snapshot.character.skillBar[3] = "skill.warrior.unsupported_roar";
    EXPECT_ENUM_EQ(SimulateExpedition(db, roar).stop, StopReason::IncompatibleBuild);
    // Tempo efetivo zero: nada entra.
    ExpeditionRequest zero = tu::MakeRequest(db, 1, 3);
    zero.effectiveSeconds = 0;
    const ExpeditionResult rz = SimulateExpedition(db, zero);
    EXPECT_ENUM_EQ(rz.stop, StopReason::DurationReached);
    EXPECT_TRUE(rz.receipts.empty());
    // SimulateRange com índice errado: devolve o progresso com ContentMismatch.
    ExpeditionRequest ok = tu::MakeRequest(db, 1, 3);
    ExpeditionProgress p = SimulateRange(db, ok, ExpeditionProgress(), 0, 3);
    ASSERT_EQ(p.receipts.size(), static_cast<std::size_t>(3));
    const ExpeditionProgress bad = SimulateRange(db, ok, p, 7, 3);
    EXPECT_ENUM_EQ(bad.stop, StopReason::ContentMismatch);
    EXPECT_EQ(bad.receipts.size(), static_cast<std::size_t>(3));
    EXPECT_EQ(bad.nextEncounter, p.nextEncounter);
}

TEST(expedition_never_exceeds_effective_seconds) {
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest req = tu::MakeRequest(db, 1, 21);
    req.effectiveSeconds = 1000.0;
    const ExpeditionResult r = SimulateExpedition(db, req);
    EXPECT_ENUM_EQ(r.stop, StopReason::DurationReached);
    EXPECT_TRUE(r.effectiveSeconds <= 1000.0);
    EXPECT_TRUE(r.effectiveSeconds > 900.0);  // o próximo encontro (<= ~20 s) já não caberia
    // effectiveSeconds acima da duração escolhida é limitado pela duração (1 h) e pelo teto offline.
    ExpeditionRequest huge = tu::MakeRequest(db, 1, 21);
    huge.effectiveSeconds = 1e9;
    EXPECT_TRUE(SimulateExpedition(db, huge).effectiveSeconds <= 3600.0);
    ExpeditionRequest twelve = tu::MakeRequest(db, 12, 21);
    twelve.durationHours = 12;
    twelve.effectiveSeconds = 1e9;
    EXPECT_TRUE(SimulateExpedition(db, twelve).effectiveSeconds <= 12 * 3600.0);
}

TEST(expedition_rf40_forecast_band_contains_real_results) {
    const std::unique_ptr<ContentDB> dbp = BigXpDb();
    const ContentDB& db = *dbp;
    ExpeditionRequest req = tu::MakeRequest(db, 1, 1);
    req.effectiveSeconds = 600.0;
    const ExpeditionForecast f = ForecastExpedition(db, req, 987654321ull, 200);
    EXPECT_TRUE(f.xpP10 <= f.xpP50 && f.xpP50 <= f.xpP90);
    EXPECT_TRUE(f.goldP10 <= f.goldP50 && f.goldP50 <= f.goldP90);
    EXPECT_TRUE(f.xpP90 > f.xpP10);
    int inside = 0;
    const int total = 1000;
    for (int k = 0; k < total; ++k) {
        ExpeditionRequest real = req;
        real.seed = 5000 + static_cast<std::uint64_t>(k);
        const double xp = SimulateExpedition(db, real).xpGained;
        if (xp >= f.xpP10 && xp <= f.xpP90) ++inside;
    }
    EXPECT_TRUE(inside >= 800);
    // Previsão é determinística.
    const ExpeditionForecast f2 = ForecastExpedition(db, req, 987654321ull, 200);
    EXPECT_NEAR(f2.xpP50, f.xpP50, 0.0);
    EXPECT_NEAR(f.retreatProbability, 0.0, 1e-12);
    // Maior fonte de dano: sentinelas físicas (e cuspidores de fogo) — o tipo é um dos dois.
    EXPECT_TRUE(f.worstResistGap == DamageType::Physical || f.worstResistGap == DamageType::Fire);
    // Com inimigos fortes e sem poções, a probabilidade de recuo aparece na faixa.
    const std::unique_ptr<ContentDB> hard = HardDb();
    ExpeditionRequest hr = tu::MakeRequest(*hard, 1, 1, 1, 0);
    hr.effectiveSeconds = 900.0;
    EXPECT_TRUE(ForecastExpedition(*hard, hr, 5, 20).retreatProbability > 0.5);
}

TEST(expedition_rnf03_twelve_hours_under_two_seconds_release) {
    const ContentDB& db = tu::RichDb();
    ExpeditionRequest req = tu::MakeRequest(db, 12, 2026);
    const auto t0 = std::chrono::steady_clock::now();
    const ExpeditionResult r = SimulateExpedition(db, req);
    const double sec = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::printf("    12 h simuladas em %.3f s (%zu encontros)\n", sec, r.receipts.size());
    EXPECT_TRUE(r.receipts.size() > 500);
#ifdef NDEBUG
    EXPECT_TRUE(sec < 2.0);
#endif
}
