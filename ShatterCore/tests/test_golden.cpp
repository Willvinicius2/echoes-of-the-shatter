// Expedições de referência: seeds fixas comparadas com tests/data/golden/*.txt.
// O mesmo arquivo serve para conferir, no cliente (DLL nativa chamada pelo Unity), que o core compilado
// lá produz o MESMO resultHash (pega diferença de flags de ponto flutuante entre builds).
// Para regravar (só ao mudar uma regra de propósito): defina SHATTER_UPDATE_GOLDEN=1 e rode este teste.
#include <cstdlib>
#include <sstream>

#include "test_util.h"

using namespace shatter;

namespace {

struct GoldenCase {
    const char* name;
    int hours;
    std::uint64_t seed;
    int level;
    std::int64_t potions;
};

const GoldenCase kCases[] = {
    {"crypt_1h_seed1", 1, 1, 1, 3},
    {"crypt_4h_seed2", 4, 2, 1, 3},
    {"crypt_12h_seed3", 12, 3, 1, 3},
    {"crypt_2h_level6_capped", 2, 4, 6, 3},
    {"crypt_1h_no_potions", 1, 5, 1, 0},
};

std::string Describe(const ContentDB& db, const GoldenCase& c) {
    const ExpeditionResult r = SimulateExpedition(db, tu::MakeRequest(db, c.hours, c.seed, c.level, c.potions));
    std::ostringstream os;
    os << c.name << " hash=" << r.resultHash << " stop=" << static_cast<int>(r.stop) << " receipts=" << r.receipts.size()
       << " kills=" << r.kills << " items=" << r.items.size() << " xp=" << json::Serialize(json::Value(r.xpGained), false)
       << " seconds=" << json::Serialize(json::Value(r.effectiveSeconds), false) << "\n";
    return os.str();
}

bool UpdateRequested() {
#ifdef _MSC_VER
    char* v = nullptr;
    std::size_t len = 0;
    const bool set = _dupenv_s(&v, &len, "SHATTER_UPDATE_GOLDEN") == 0 && v != nullptr;
    std::free(v);
    return set;
#else
    return std::getenv("SHATTER_UPDATE_GOLDEN") != nullptr;
#endif
}

}  // namespace

TEST(golden_expeditions_match_reference_files) {
    const ContentDB& db = tu::RichDb();
    const std::string path = tu::DataDir() + "/golden/expeditions.txt";
    std::string actual;
    for (const GoldenCase& c : kCases) actual += Describe(db, c);
    if (UpdateRequested()) {
        std::ofstream out(std::filesystem::u8path(path), std::ios::binary | std::ios::trunc);
        out << actual;
        std::printf("    golden regravado: %s\n", path.c_str());
        return;
    }
    const std::string expected = tu::ReadFile(path);
    if (expected.empty()) { FAIL("golden ausente: " + path); return; }
    // Compara linha a linha para apontar qual caso divergiu.
    std::istringstream a(actual), e(expected);
    std::string la, le;
    while (std::getline(e, le)) {
        if (!std::getline(a, la)) { FAIL("faltou caso: " + le); return; }
        if (!le.empty() && le.back() == '\r') le.pop_back();
        if (la != le) FAIL("divergiu\n  esperado: " + le + "\n  obtido:   " + la);
    }
}
