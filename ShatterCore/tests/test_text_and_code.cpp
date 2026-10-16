// Textos e código — RF-45 (sem percentual negativo; "+200% XP"), RF-61 (o core só emite chaves que
// existem em pt_BR e en), RNF-08 (nada de Unity/Unreal em ShatterCore/) e as proibições de CLAUDE.md
// verificadas por busca textual no código do motor (src/ e include/).
#include <regex>

#include "test_util.h"

using namespace shatter;

namespace {

namespace fs = std::filesystem;

std::string LocDir() { return tu::ContentDir() + "/Loc"; }

// Remove comentários // e /* */ e o conteúdo de literais de texto/caractere (mantém as aspas),
// para a busca textual não acusar palavras em comentários ("sem pow/exp/log/sin").
// Se `literals` não for nulo, recebe o conteúdo de cada literal de texto (para a busca do RF-61).
std::string StripCommentsAndStrings(const std::string& src, std::vector<std::string>* literals = nullptr) {
    std::string out;
    out.reserve(src.size());
    enum { Code, Line, Block, Str, Chr } st = Code;
    for (std::size_t i = 0; i < src.size(); ++i) {
        const char c = src[i];
        const char n = i + 1 < src.size() ? src[i + 1] : '\0';
        switch (st) {
            case Code:
                if (c == '/' && n == '/') { st = Line; ++i; }
                else if (c == '/' && n == '*') { st = Block; ++i; }
                else if (c == '"') { st = Str; out += c; if (literals) literals->emplace_back(); }
                else if (c == '\'') { st = Chr; out += c; }
                else out += c;
                break;
            case Line:
                if (c == '\n') { st = Code; out += c; }
                break;
            case Block:
                if (c == '*' && n == '/') { st = Code; ++i; }
                else if (c == '\n') out += c;
                break;
            case Str:
                if (c == '\\') {
                    if (literals) { literals->back() += c; literals->back() += n; }
                    ++i;
                } else if (c == '"') {
                    st = Code;
                    out += c;
                } else if (literals) {
                    literals->back() += c;
                }
                break;
            case Chr:
                if (c == '\\') ++i;
                else if (c == '\'') { st = Code; out += c; }
                break;
        }
    }
    return out;
}

std::vector<fs::path> SourceFiles(const std::vector<std::string>& dirs) {
    std::vector<fs::path> files;
    for (const std::string& d : dirs) {
        std::error_code ec;
        for (fs::recursive_directory_iterator it(fs::u8path(d), ec), end; !ec && it != end; it.increment(ec)) {
            const std::string ext = it->path().extension().u8string();
            if (ext == ".cpp" || ext == ".h" || ext == ".hpp" || ext == ".cc") files.push_back(it->path());
        }
    }
    return files;
}

std::string CoreDir() { return SHATTER_SOURCE_DIR; }

}  // namespace

TEST(text_rf61_every_key_the_core_emits_exists_in_pt_br_and_en) {
    const auto loc = tu::ReadLoc(LocDir());
    ASSERT_TRUE(!loc.empty());
    const char* keys[] = {kTipRaisePotion, kTipMorePotions, kTipLowLife, kTipAllGood};
    for (const char* k : keys) {
        const auto it = loc.find(k);
        if (it == loc.end()) { FAIL(std::string("chave sem texto: ") + k); continue; }
        EXPECT_FALSE(it->second.ptBR.empty());
        EXPECT_FALSE(it->second.en.empty());
    }
    // As chaves emitidas de fato em cenários variados (recuo, sem poção, tranquila) estão todas no Loc.
    const ContentDB& db = tu::RichDb();
    for (std::uint64_t seed = 1; seed <= 6; ++seed) {
        for (std::int64_t potions : {0, 3}) {
            ExpeditionRequest req = tu::MakeRequest(db, 1, seed, 1, potions);
            req.effectiveSeconds = 900.0;
            for (const std::string& k : SimulateExpedition(db, req).tipKeys) {
                if (loc.find(k) == loc.end()) FAIL("dica sem texto: " + k);
            }
        }
    }
}

TEST(text_rf45_no_negative_percent_and_fervor_shows_plus_200) {
    const auto loc = tu::ReadLoc(LocDir());
    ASSERT_TRUE(!loc.empty());
    // "-65% de XP", "− 20 %", "-0.5%"... (hífen, sinal de menos U+2212 e travessão U+2013).
    const std::regex negative(R"((-|\xE2\x88\x92|\xE2\x80\x93)\s*\d+([.,]\d+)?\s*%)");
    int checked = 0;
    for (const auto& kv : loc) {
        if (kv.second.file != "expedition.csv" && kv.second.file != "ui.csv") continue;
        ++checked;
        for (const std::string* text : {&kv.second.ptBR, &kv.second.en}) {
            if (std::regex_search(*text, negative)) FAIL("percentual negativo em " + kv.first + ": " + *text);
        }
    }
    EXPECT_TRUE(checked > 20);
    // HUD manual: ícone do Fervor e "+200% XP" (×3 de fervor_xp_mult = +200%).
    const auto fervor = loc.find("ui.hud.fervor");
    const auto xp = loc.find("ui.hud.fervor_xp");
    ASSERT_TRUE(fervor != loc.end() && xp != loc.end());
    EXPECT_EQ(xp->second.ptBR, std::string("+200% XP"));
    EXPECT_EQ(xp->second.en, std::string("+200% XP"));
    ContentDB real;
    real.LoadDirectory(tu::ContentDir());
    ASSERT_TRUE(real.Finalize());
    EXPECT_NEAR((real.Rules().fervorXpMult - 1.0) * 100.0, 200.0, 1e-9);
}

TEST(code_rnf08_no_engine_headers_in_shattercore) {
    const std::regex include(R"(^\s*#\s*include\s*[<"]([^>"]+)[>"])");
    const std::regex engine(R"((UnityEngine|Unity|Unreal|UObject|CoreMinimal|Engine/|Runtime/|Kismet|GameFramework))",
                            std::regex::icase);
    const auto files = SourceFiles({CoreDir() + "/include", CoreDir() + "/src", CoreDir() + "/tests"});
    ASSERT_TRUE(files.size() > 20);
    for (const fs::path& f : files) {
        std::istringstream in(tu::ReadFile(f.u8string()));
        std::string line;
        while (std::getline(in, line)) {
            std::smatch m;
            if (std::regex_search(line, m, include) && std::regex_search(m[1].str(), engine))
                FAIL(f.filename().u8string() + ": include de motor: " + line);
        }
    }
}

TEST(code_claude_md_forbidden_constructs_absent_from_core) {
    // CLAUDE.md: sem exceções, sem RTTI, sem std::rand/random_device/distribuições da STL, sem
    // pow/exp/log/sin, sem strtod/printf dependentes de locale, sem fast-math. Busca em src/ e include/.
    const std::regex forbidden(
        R"(\b(throw|try|catch|dynamic_cast|typeid|rand|srand|random_device|mt19937|mt19937_64|uniform_int_distribution|uniform_real_distribution|pow|powf|exp|expf|log|logf|log2|log10|sin|cos|tan|atan|atan2|strtod|strtof|atof|stod|stof|sprintf|snprintf|printf|scanf|sscanf|getenv|time|clock)\b\s*\(|#\s*include\s*<(random|ctime|chrono|thread|mutex|atomic)>|ffast-math|fp:fast)");
    const auto files = SourceFiles({CoreDir() + "/include", CoreDir() + "/src"});
    ASSERT_TRUE(files.size() > 15);
    for (const fs::path& f : files) {
        const std::string code = StripCommentsAndStrings(tu::ReadFile(f.u8string()));
        std::smatch m;
        if (std::regex_search(code, m, forbidden)) FAIL(f.filename().u8string() + ": construção proibida: " + m[0].str());
    }
    // O CMake nunca liga fast-math.
    const std::string cmake = tu::ReadFile(CoreDir() + "/CMakeLists.txt");
    const std::string cmakeCode = std::regex_replace(cmake, std::regex("#[^\n]*"), "");
    EXPECT_TRUE(cmakeCode.find("fast-math") == std::string::npos && cmakeCode.find("fp:fast") == std::string::npos);
    EXPECT_TRUE(cmakeCode.find("-ffp-contract=off") != std::string::npos);
    EXPECT_TRUE(cmakeCode.find("/fp:precise") != std::string::npos);
}

TEST(text_rf61_core_code_has_no_player_visible_text) {
    // O core só devolve IDs e chaves; mensagens de erro são log técnico em inglês (ASCII). Um literal com
    // acento ou outro caractere não ASCII em src/ ou include/ indicaria texto para o jogador no código.
    const auto files = SourceFiles({CoreDir() + "/include", CoreDir() + "/src"});
    int literals = 0;
    for (const fs::path& f : files) {
        std::vector<std::string> lits;
        StripCommentsAndStrings(tu::ReadFile(f.u8string()), &lits);
        for (const std::string& lit : lits) {
            ++literals;
            for (const char c : lit) {
                if (static_cast<unsigned char>(c) >= 0x80) {
                    FAIL(f.filename().u8string() + ": literal com texto nao ASCII: " + lit);
                    break;
                }
            }
        }
    }
    EXPECT_TRUE(literals > 100);
}

TEST(text_rf28_item_names_agree_in_gender_for_every_base_and_affix) {
    // Parte automática do RF-28 [SC+UE]: a base guarda o gênero (item_bases.csv) e o Loc tem o nome com o
    // mesmo gênero; cada prefixo tem as formas m/f (singular e plural) com o gênero certo; sufixos são
    // invariáveis. Para todo par base × afixo a forma escolhida pelo gênero (e número) da base concorda.
    // A revisão humana de 20 nomes fica no roteiro manual (UE).
    ContentDB db;
    db.LoadDirectory(tu::ContentDir());
    ASSERT_TRUE(db.Finalize());
    const auto loc = tu::ReadLoc(LocDir());
    ASSERT_TRUE(!db.ItemBases().empty() && !db.Affixes().empty());
    auto entry = [&](const std::string& key) -> const tu::LocEntry* {
        const auto it = loc.find(key);
        if (it == loc.end() || it->second.ptBR.empty() || it->second.en.empty()) {
            FAIL("sem texto pt_BR/en: " + key);
            return nullptr;
        }
        return &it->second;
    };
    int pairs = 0;
    for (const ItemBaseData& base : db.ItemBases()) {
        const tu::LocEntry* bn = entry(base.id + ".name");
        if (bn == nullptr) continue;
        const std::string g(1, base.grammaticalGender);
        if (bn->gender != g) FAIL(base.id + ": genero no Loc (" + bn->gender + ") != item_bases.csv (" + g + ")");
        const bool plural = bn->context.find("plural") != std::string::npos;
        for (const AffixData& a : db.Affixes()) {
            ++pairs;
            if (a.kind == AffixKind::Suffix) {
                const tu::LocEntry* sn = entry(a.id + ".name");
                if (sn != nullptr && sn->context.find("invari") == std::string::npos)
                    FAIL(a.id + ": sufixo sem forma unica marcada como invariavel");
                continue;
            }
            const bool fem = base.grammaticalGender == 'f';
            const char* form = fem ? (plural ? "_fp" : "_f") : (plural ? "_mp" : "");
            const std::string key = a.id + ".name" + form;
            const tu::LocEntry* an = entry(key);
            if (an != nullptr && an->gender != g)
                FAIL(base.id + " x " + a.id + ": forma " + key + " tem genero " + an->gender + ", a base e " + g);
        }
    }
    EXPECT_EQ(pairs, static_cast<int>(db.ItemBases().size() * db.Affixes().size()));
}
