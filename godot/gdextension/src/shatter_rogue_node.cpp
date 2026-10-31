#include "shatter_rogue_node.h"

#include <cstdint>
#include <functional>
#include <vector>

#include <godot_cpp/classes/json.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

namespace godot {

namespace {

using Reader = std::function<shatter_status(uint8_t*, size_t, size_t*)>;

// Lê uma saída de tamanho variável da API C (cap < needed devolve BUFFER_TOO_SMALL e repete com o tamanho certo).
String ler_texto(const Reader& leitor) {
    std::vector<uint8_t> buf(4096);
    for (int i = 0; i < 3; ++i) {
        size_t needed = 0;
        shatter_status st = leitor(buf.data(), buf.size(), &needed);
        if (st == SHATTER_OK) {
            return String::utf8(reinterpret_cast<const char*>(buf.data()), static_cast<int64_t>(needed));
        }
        if (st != SHATTER_BUFFER_TOO_SMALL) {
            return String();
        }
        buf.resize(needed);
    }
    return String();
}

Variant json_de(const Reader& leitor) {
    String t = ler_texto(leitor);
    return t.is_empty() ? Variant() : JSON::parse_string(t);
}

Dictionary dict_de(const Reader& leitor) {
    Variant v = json_de(leitor);
    return v.get_type() == Variant::DICTIONARY ? Dictionary(v) : Dictionary();
}

std::string utf8(const String& s) {
    CharString c = s.utf8();
    return std::string(c.get_data(), static_cast<size_t>(c.length()));
}

}  // namespace

ShatterRogue::~ShatterRogue() {
    if (rogue_ != nullptr) {
        shatter_rogue_destroy(rogue_);
    }
}

String ShatterRogue::carregar_dados(const String& pasta) {
    if (rogue_ != nullptr) {
        shatter_rogue_destroy(rogue_);
        rogue_ = nullptr;
    }
    std::string p = utf8(pasta);
    shatter_error err{};
    shatter_status st = shatter_rogue_load_directory(p.data(), p.size(), &rogue_, &err);
    if (st != SHATTER_OK) {
        rogue_ = nullptr;
        return String("shatter_rogue_load_directory: ") + String::utf8(err.message);
    }
    return String();
}

void ShatterRogue::definir_save(const String& caminho) {
    save_path_ = caminho;
    std::string p = utf8(caminho);
    shatter_rogue_save_path_set(rogue_, p.data(), p.size());
}

int ShatterRogue::meta_carregar() {
    int32_t r = SHATTER_ROGUE_LOAD_MISSING;
    shatter_rogue_meta_load(rogue_, &r);
    return r;
}

bool ShatterRogue::meta_salvar() {
    shatter_error err{};
    return shatter_rogue_meta_save(rogue_, &err) == SHATTER_OK;
}

String ShatterRogue::meta_texto_save() const {
    return ler_texto([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_meta_save_json(rogue_, o, c, n); });
}

#define ROGUE_ACAO_ID(nome, fn)                                     \
    int ShatterRogue::nome(const String& id) {                      \
        std::string s = utf8(id);                                   \
        int32_t r = -1;                                             \
        fn(rogue_, s.data(), s.size(), &r);                         \
        return r;                                                   \
    }
#define ROGUE_CONSULTA_ID(nome, fn)                                 \
    int ShatterRogue::nome(const String& id) const {                \
        std::string s = utf8(id);                                   \
        int32_t r = -1;                                             \
        fn(rogue_, s.data(), s.size(), &r);                         \
        return r;                                                   \
    }

ROGUE_ACAO_ID(meta_comprar, shatter_rogue_meta_buy)
ROGUE_CONSULTA_ID(meta_pode_comprar, shatter_rogue_meta_can_buy)
ROGUE_ACAO_ID(meta_criar, shatter_rogue_meta_craft)
ROGUE_CONSULTA_ID(meta_pode_criar, shatter_rogue_meta_can_craft)
ROGUE_ACAO_ID(meta_equipar, shatter_rogue_meta_equip)

void ShatterRogue::meta_preparar_corrida() {
    shatter_rogue_meta_prepare_run(rogue_);
}

int ShatterRogue::meta_creditar(const Dictionary& ganhos) {
    std::string j = utf8(JSON::stringify(ganhos));
    shatter_error err{};
    return shatter_rogue_meta_credit(rogue_, j.data(), j.size(), &err);
}

Dictionary ShatterRogue::meta_estado() const {
    return dict_de([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_meta_json(rogue_, o, c, n); });
}

Dictionary ShatterRogue::drop_de(const String& inimigo) const {
    std::string s = utf8(inimigo);
    return dict_de([&](uint8_t* o, size_t c, size_t* n) {
        return shatter_rogue_drop_json(rogue_, s.data(), s.size(), o, c, n);
    });
}

int ShatterRogue::habilidade_liberada(const String& upgrade) const {
    std::string s = utf8(upgrade);
    uint8_t r = 0;
    if (shatter_rogue_skill_unlocked(rogue_, s.data(), s.size(), &r) == SHATTER_NOT_FOUND) {
        return -1;  // upgrade que o core não conhece (habilidade de outra classe)
    }
    return r != 0 ? 1 : 0;
}

double ShatterRogue::configuracao(const String& chave) const {
    std::string s = utf8(chave);
    double r = 0.0;
    shatter_rogue_setting(rogue_, s.data(), s.size(), &r);
    return r;
}

Dictionary ShatterRogue::aplicar_stats(const Dictionary& base, bool com_corrida) const {
    std::string j = utf8(JSON::stringify(base));
    shatter_error err{};
    return dict_de([&](uint8_t* o, size_t c, size_t* n) {
        return shatter_rogue_stats_apply(rogue_, j.data(), j.size(), com_corrida ? 1 : 0, o, c, n, &err);
    });
}

bool ShatterRogue::corrida_iniciar(int64_t semente, const Dictionary& base) {
    std::string j = utf8(JSON::stringify(base));
    shatter_error err{};
    return shatter_rogue_run_start(rogue_, static_cast<uint64_t>(semente), j.data(), j.size(), &err) == SHATTER_OK;
}

int ShatterRogue::corrida_fase() const {
    int32_t r = SHATTER_ROGUE_PHASE_NONE;
    shatter_rogue_run_phase(rogue_, &r);
    return r;
}

Array ShatterRogue::corrida_caminhos(int etapa) const {
    Variant v = json_de([&](uint8_t* o, size_t c, size_t* n) {
        return shatter_rogue_run_paths_json(rogue_, static_cast<uint32_t>(etapa), o, c, n);
    });
    return v.get_type() == Variant::ARRAY ? Array(v) : Array();
}

Dictionary ShatterRogue::corrida_inimigo_morto(const String& inimigo) {
    std::string s = utf8(inimigo);
    uint8_t limpou = 0;
    int32_t r = -1;
    shatter_rogue_run_enemy_killed(rogue_, s.data(), s.size(), &limpou, &r);
    Dictionary d;
    d["resultado"] = r;
    d["sala_limpa"] = limpou != 0;
    return d;
}

Dictionary ShatterRogue::corrida_escolher_carta(const String& upgrade, double hp) {
    std::string s = utf8(upgrade);
    double hp_out = hp;
    int32_t r = -1;
    shatter_rogue_run_choose_card(rogue_, s.data(), s.size(), hp, &hp_out, &r);
    Dictionary d;
    d["resultado"] = r;
    d["hp"] = hp_out;
    return d;
}

Dictionary ShatterRogue::corrida_descansar(double hp) {
    double hp_out = hp;
    int32_t r = -1;
    shatter_rogue_run_rest(rogue_, hp, &hp_out, &r);
    Dictionary d;
    d["resultado"] = r;
    d["hp"] = hp_out;
    return d;
}

#define ROGUE_ACAO_RESULTADO(nome, fn)  \
    int ShatterRogue::nome() {          \
        int32_t r = -1;                 \
        fn(rogue_, &r);                 \
        return r;                       \
    }

ROGUE_ACAO_RESULTADO(corrida_porta, shatter_rogue_run_door)
ROGUE_ACAO_RESULTADO(corrida_jogador_morreu, shatter_rogue_run_player_died)
ROGUE_ACAO_RESULTADO(corrida_terminar, shatter_rogue_run_finish)

int ShatterRogue::corrida_cartas_externas(bool ligado) {
    int32_t r = -1;
    shatter_rogue_run_external_cards_set(rogue_, ligado ? 1 : 0, &r);
    return r;
}

int ShatterRogue::corrida_escolher_caminho(int indice) {
    int32_t r = -1;
    shatter_rogue_run_choose_path(rogue_, static_cast<uint32_t>(indice), &r);
    return r;
}

Dictionary ShatterRogue::corrida_estado() const {
    return dict_de([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_run_json(rogue_, o, c, n); });
}

Dictionary ShatterRogue::corrida_stats() const {
    return dict_de([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_run_stats_json(rogue_, o, c, n); });
}

Dictionary ShatterRogue::corrida_resumo() const {
    return dict_de([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_run_summary_json(rogue_, o, c, n); });
}

// --- Habilidades por classe (API 1.10) ---
ROGUE_ACAO_ID(classe_definir, shatter_rogue_class_set)
ROGUE_ACAO_ID(habilidade_aprender, shatter_rogue_skill_learn)
ROGUE_CONSULTA_ID(habilidade_pode_aprender, shatter_rogue_skill_can_learn)
ROGUE_ACAO_RESULTADO(habilidades_redistribuir, shatter_rogue_skill_respec)

Dictionary ShatterRogue::habilidades_estado() const {
    return dict_de([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_skills_json(rogue_, o, c, n); });
}

Dictionary ShatterRogue::habilidade_def(const String& id, int nivel) const {
    std::string s = utf8(id);
    return dict_de([&](uint8_t* o, size_t c, size_t* n) {
        return shatter_rogue_skill_def_json(rogue_, s.data(), s.size(), nivel, o, c, n);
    });
}

int ShatterRogue::habilidade_equipar(int slot, const String& id) {
    std::string s = utf8(id);
    int32_t r = -1;
    shatter_rogue_skill_equip(rogue_, slot < 0 ? UINT32_MAX : static_cast<uint32_t>(slot), s.data(), s.size(), &r);
    return r;
}

int ShatterRogue::habilidades_ganhar_pontos(int64_t pontos) {
    int32_t r = -1;
    shatter_rogue_skill_points_add(rogue_, pontos, &r);
    return r;
}

void ShatterRogue::habilidades_tick(double dt) {
    shatter_rogue_skill_tick(rogue_, dt);
}

int ShatterRogue::habilidade_pode_usar(int slot, double mana) const {
    int32_t r = -1;
    shatter_rogue_skill_can_use(rogue_, slot < 0 ? UINT32_MAX : static_cast<uint32_t>(slot), mana, &r);
    return r;
}

Dictionary ShatterRogue::habilidade_usar(int slot, double mana) {
    double custo = 0.0;
    int32_t r = -1;
    shatter_rogue_skill_commit_use(rogue_, slot < 0 ? UINT32_MAX : static_cast<uint32_t>(slot), mana, &custo, &r);
    Dictionary d;
    d["resultado"] = r;
    d["custo"] = custo;
    return d;
}

double ShatterRogue::habilidade_recarga(int slot) const {
    double f = 0.0;
    shatter_rogue_skill_cooldown(rogue_, slot < 0 ? UINT32_MAX : static_cast<uint32_t>(slot), &f);
    return f;
}

Dictionary ShatterRogue::aplicar_passivas(const Dictionary& base) const {
    std::string j = utf8(JSON::stringify(base));
    shatter_error err{};
    return dict_de([&](uint8_t* o, size_t c, size_t* n) {
        return shatter_rogue_skill_passives_apply(rogue_, j.data(), j.size(), o, c, n, &err);
    });
}

// --- Hordas (API 1.11) ---
int ShatterRogue::ondas_iniciar(const String& fase, int64_t semente) {
    std::string f = utf8(fase);
    int32_t r = -1;
    shatter_rogue_wave_start(rogue_, f.data(), f.size(), static_cast<uint64_t>(semente), &r);
    return r;
}

void ShatterRogue::ondas_parar() {
    shatter_rogue_wave_stop(rogue_);
}

Array ShatterRogue::ondas_tick(double dt) {
    uint32_t n = 0;
    shatter_rogue_wave_tick(rogue_, dt, &n);
    // A fila também guarda o chefe de uma fase de onda única, que nasce no iniciar: lê sempre.
    Variant v = json_de([&](uint8_t* o, size_t c, size_t* m) { return shatter_rogue_wave_take_json(rogue_, o, c, m); });
    return v.get_type() == Variant::ARRAY ? Array(v) : Array();
}

Dictionary ShatterRogue::ondas_morto(int64_t id) {
    uint8_t completa = 0;
    int32_t r = -1;
    shatter_rogue_wave_killed(rogue_, id < 0 || id > static_cast<int64_t>(UINT32_MAX) ? 0u : static_cast<uint32_t>(id),
                              &completa, &r);
    Dictionary d;
    d["resultado"] = r;
    d["completa"] = completa != 0;
    return d;
}

Dictionary ShatterRogue::ondas_estado() const {
    return dict_de([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_wave_json(rogue_, o, c, n); });
}

Dictionary ShatterRogue::ondas_definicoes() const {
    return dict_de([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_wave_defs_json(rogue_, o, c, n); });
}

String ShatterRogue::ondas_estado_texto() const {
    return ler_texto([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_wave_state_json(rogue_, o, c, n); });
}

bool ShatterRogue::ondas_restaurar(const String& texto) {
    std::string j = utf8(texto);
    shatter_error err{};
    return shatter_rogue_wave_state_restore(rogue_, j.data(), j.size(), &err) == SHATTER_OK;
}

String ShatterRogue::ondas_hash() const {
    return ler_texto([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_wave_state_hash(rogue_, o, c, n); });
}

String ShatterRogue::estado_texto() const {
    return ler_texto([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_state_json(rogue_, o, c, n); });
}

bool ShatterRogue::estado_restaurar(const String& texto) {
    std::string j = utf8(texto);
    shatter_error err{};
    return shatter_rogue_state_restore(rogue_, j.data(), j.size(), &err) == SHATTER_OK;
}

String ShatterRogue::estado_hash() const {
    return ler_texto([&](uint8_t* o, size_t c, size_t* n) { return shatter_rogue_state_hash(rogue_, o, c, n); });
}

void ShatterRogue::_bind_methods() {
    ClassDB::bind_method(D_METHOD("carregar_dados", "pasta"), &ShatterRogue::carregar_dados);
    ClassDB::bind_method(D_METHOD("definir_save", "caminho"), &ShatterRogue::definir_save);
    ClassDB::bind_method(D_METHOD("meta_carregar"), &ShatterRogue::meta_carregar);
    ClassDB::bind_method(D_METHOD("meta_salvar"), &ShatterRogue::meta_salvar);
    ClassDB::bind_method(D_METHOD("meta_texto_save"), &ShatterRogue::meta_texto_save);
    ClassDB::bind_method(D_METHOD("meta_comprar", "id"), &ShatterRogue::meta_comprar);
    ClassDB::bind_method(D_METHOD("meta_pode_comprar", "id"), &ShatterRogue::meta_pode_comprar);
    ClassDB::bind_method(D_METHOD("meta_criar", "id"), &ShatterRogue::meta_criar);
    ClassDB::bind_method(D_METHOD("meta_pode_criar", "id"), &ShatterRogue::meta_pode_criar);
    ClassDB::bind_method(D_METHOD("meta_equipar", "id"), &ShatterRogue::meta_equipar);
    ClassDB::bind_method(D_METHOD("meta_preparar_corrida"), &ShatterRogue::meta_preparar_corrida);
    ClassDB::bind_method(D_METHOD("meta_creditar", "ganhos"), &ShatterRogue::meta_creditar);
    ClassDB::bind_method(D_METHOD("meta_estado"), &ShatterRogue::meta_estado);
    ClassDB::bind_method(D_METHOD("drop_de", "inimigo"), &ShatterRogue::drop_de);
    ClassDB::bind_method(D_METHOD("habilidade_liberada", "upgrade"), &ShatterRogue::habilidade_liberada);
    ClassDB::bind_method(D_METHOD("configuracao", "chave"), &ShatterRogue::configuracao);
    ClassDB::bind_method(D_METHOD("aplicar_stats", "base", "com_corrida"), &ShatterRogue::aplicar_stats);
    ClassDB::bind_method(D_METHOD("corrida_iniciar", "semente", "base"), &ShatterRogue::corrida_iniciar);
    ClassDB::bind_method(D_METHOD("corrida_fase"), &ShatterRogue::corrida_fase);
    ClassDB::bind_method(D_METHOD("corrida_caminhos", "etapa"), &ShatterRogue::corrida_caminhos);
    ClassDB::bind_method(D_METHOD("corrida_inimigo_morto", "inimigo"), &ShatterRogue::corrida_inimigo_morto);
    ClassDB::bind_method(D_METHOD("corrida_escolher_carta", "upgrade", "hp"), &ShatterRogue::corrida_escolher_carta);
    ClassDB::bind_method(D_METHOD("corrida_descansar", "hp"), &ShatterRogue::corrida_descansar);
    ClassDB::bind_method(D_METHOD("corrida_porta"), &ShatterRogue::corrida_porta);
    ClassDB::bind_method(D_METHOD("corrida_cartas_externas", "ligado"), &ShatterRogue::corrida_cartas_externas);
    ClassDB::bind_method(D_METHOD("corrida_escolher_caminho", "indice"), &ShatterRogue::corrida_escolher_caminho);
    ClassDB::bind_method(D_METHOD("corrida_jogador_morreu"), &ShatterRogue::corrida_jogador_morreu);
    ClassDB::bind_method(D_METHOD("corrida_terminar"), &ShatterRogue::corrida_terminar);
    ClassDB::bind_method(D_METHOD("corrida_estado"), &ShatterRogue::corrida_estado);
    ClassDB::bind_method(D_METHOD("corrida_stats"), &ShatterRogue::corrida_stats);
    ClassDB::bind_method(D_METHOD("corrida_resumo"), &ShatterRogue::corrida_resumo);
    ClassDB::bind_method(D_METHOD("classe_definir", "classe"), &ShatterRogue::classe_definir);
    ClassDB::bind_method(D_METHOD("habilidades_estado"), &ShatterRogue::habilidades_estado);
    ClassDB::bind_method(D_METHOD("habilidade_def", "id", "nivel"), &ShatterRogue::habilidade_def);
    ClassDB::bind_method(D_METHOD("habilidade_pode_aprender", "id"), &ShatterRogue::habilidade_pode_aprender);
    ClassDB::bind_method(D_METHOD("habilidade_aprender", "id"), &ShatterRogue::habilidade_aprender);
    ClassDB::bind_method(D_METHOD("habilidade_equipar", "slot", "id"), &ShatterRogue::habilidade_equipar);
    ClassDB::bind_method(D_METHOD("habilidades_redistribuir"), &ShatterRogue::habilidades_redistribuir);
    ClassDB::bind_method(D_METHOD("habilidades_ganhar_pontos", "pontos"), &ShatterRogue::habilidades_ganhar_pontos);
    ClassDB::bind_method(D_METHOD("habilidades_tick", "dt"), &ShatterRogue::habilidades_tick);
    ClassDB::bind_method(D_METHOD("habilidade_pode_usar", "slot", "mana"), &ShatterRogue::habilidade_pode_usar);
    ClassDB::bind_method(D_METHOD("habilidade_usar", "slot", "mana"), &ShatterRogue::habilidade_usar);
    ClassDB::bind_method(D_METHOD("habilidade_recarga", "slot"), &ShatterRogue::habilidade_recarga);
    ClassDB::bind_method(D_METHOD("aplicar_passivas", "base"), &ShatterRogue::aplicar_passivas);
    ClassDB::bind_method(D_METHOD("ondas_iniciar", "fase", "semente"), &ShatterRogue::ondas_iniciar);
    ClassDB::bind_method(D_METHOD("ondas_parar"), &ShatterRogue::ondas_parar);
    ClassDB::bind_method(D_METHOD("ondas_tick", "dt"), &ShatterRogue::ondas_tick);
    ClassDB::bind_method(D_METHOD("ondas_morto", "id"), &ShatterRogue::ondas_morto);
    ClassDB::bind_method(D_METHOD("ondas_estado"), &ShatterRogue::ondas_estado);
    ClassDB::bind_method(D_METHOD("ondas_definicoes"), &ShatterRogue::ondas_definicoes);
    ClassDB::bind_method(D_METHOD("ondas_estado_texto"), &ShatterRogue::ondas_estado_texto);
    ClassDB::bind_method(D_METHOD("ondas_restaurar", "texto"), &ShatterRogue::ondas_restaurar);
    ClassDB::bind_method(D_METHOD("ondas_hash"), &ShatterRogue::ondas_hash);
    ClassDB::bind_method(D_METHOD("estado_texto"), &ShatterRogue::estado_texto);
    ClassDB::bind_method(D_METHOD("estado_restaurar", "texto"), &ShatterRogue::estado_restaurar);
    ClassDB::bind_method(D_METHOD("estado_hash"), &ShatterRogue::estado_hash);
}

}  // namespace godot
