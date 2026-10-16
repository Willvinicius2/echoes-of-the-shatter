/* ShatterCore — API C estável para o Unity (P/Invoke). Contrato: docs/04_arquitetura.md, seção 9.2.
 *
 * Regras da fronteira:
 *  - C puro, convenção cdecl; toda função devolve shatter_status (0 = OK) ou um valor simples.
 *    Nenhuma exceção cruza a fronteira (as funções são noexcept do lado C++; falha de alocação é fatal).
 *  - Handles opacos (shatter_db, shatter_save, shatter_statblock, shatter_effects) criados pelas funções
 *    _create, _load_directory, _read e _from_* e liberados pela _destroy correspondente. O dono é sempre
 *    o chamador (SafeHandle no C#). Handle nulo é SHATTER_INVALID_ARGUMENT, nunca crash; _destroy(NULL)
 *    não faz nada.
 *  - Saída de tamanho variável vai para um buffer do chamador: (uint8_t* out, size_t cap, size_t* needed).
 *    Se cap < needed, devolve SHATTER_BUFFER_TOO_SMALL com *needed preenchido e NADA muda (nem RNG, nem
 *    save): o chamador repete com um buffer maior. A saída não tem terminador NUL (use *needed).
 *  - Texto: UTF-8 com comprimento explícito (const char* s, size_t len); não depende de NUL.
 *  - Erro detalhado em shatter_error* err (opcional, struct do chamador): sem erro global, sem thread_local.
 *  - Sem estado global: a biblioteca pode ser carregada uma vez e usada por várias sessões de Play.
 *  - Threads: shatter_db depois de finalizado é imutável e pode ser lido por várias threads ao mesmo tempo
 *    (simulação de expedição em Task.Run recebe só o shatter_db e JSON). shatter_save, shatter_statblock e
 *    shatter_effects pertencem a UMA thread (a main thread do Unity).
 *  - Caminho quente (golpe) em structs blittable; caminho frio (expedição, save, snapshot) em JSON UTF-8
 *    no mesmo formato do save (docs/06_dados.md, seção 6).
 *  - SHATTER_C_API_VERSION sobe a cada mudança incompatível de assinatura, struct ou JSON.
 */
#ifndef SHATTER_C_H
#define SHATTER_C_H

#include <stddef.h>
#include <stdint.h>

#define SHATTER_C_API_VERSION 1u

#if defined(_WIN32)
#  define SHATTER_CALL __cdecl
#  if defined(SHATTER_C_BUILDING_DLL)
#    define SHATTER_API __declspec(dllexport)
#  elif defined(SHATTER_C_STATIC)
#    define SHATTER_API
#  else
#    define SHATTER_API __declspec(dllimport)
#  endif
#else
#  define SHATTER_CALL
#  if defined(SHATTER_C_BUILDING_DLL)
#    define SHATTER_API __attribute__((visibility("default")))
#  else
#    define SHATTER_API
#  endif
#endif

#ifdef __cplusplus
#  define SHATTER_NOEXCEPT noexcept
extern "C" {
#else
#  define SHATTER_NOEXCEPT
#endif

/* ------------------------------------------------------------------------------------------------
 * Status e erro
 * ---------------------------------------------------------------------------------------------- */
typedef int32_t shatter_status;
enum {
    SHATTER_OK = 0,
    SHATTER_INVALID_ARGUMENT = 1, /* ponteiro nulo, índice fora, enum inválido, UTF-8 inválido */
    SHATTER_BUFFER_TOO_SMALL = 2, /* *needed tem o tamanho certo; nada mudou */
    SHATTER_PARSE_ERROR = 3,      /* JSON ou save ilegível (err->line quando houver) */
    SHATTER_CONTENT_INVALID = 4,  /* CSV inválido / banco não finalizado / ID inexistente no conteúdo */
    SHATTER_IO_ERROR = 5,         /* arquivo ou pasta inacessível; gravação segura falhou */
    SHATTER_VERSION_MISMATCH = 6, /* save de versão futura (save_version ou content_version maior) */
    SHATTER_NOT_FOUND = 7,        /* arquivo ou ID não existe */
    SHATTER_INTERNAL = 8          /* bug: estado impossível */
};

typedef struct shatter_error {
    int32_t code;        /* shatter_status */
    int32_t line;        /* linha do CSV ou do JSON (0 = sem linha) */
    char message[256];   /* UTF-8 terminado em NUL, em inglês (log técnico), cortado em fronteira de caractere */
} shatter_error;

/* ------------------------------------------------------------------------------------------------
 * Handles opacos
 * ---------------------------------------------------------------------------------------------- */
typedef struct shatter_db shatter_db;               /* ContentDB (imutável depois de finalizado) */
typedef struct shatter_save shatter_save;           /* SaveData (mutável, main thread) */
typedef struct shatter_statblock shatter_statblock; /* StatBlock de uma entidade */
typedef struct shatter_effects shatter_effects;     /* EffectContainer de uma entidade */

/* ------------------------------------------------------------------------------------------------
 * Structs blittable (layout conferido por shatter_layout_check; padding explícito)
 * ---------------------------------------------------------------------------------------------- */
typedef struct shatter_rng {   /* Pcg32: estado e incremento; a struct é do chamador */
    uint64_t state;
    uint64_t inc;
} shatter_rng;

/* Fluxos de RNG (rng.h). */
enum { SHATTER_RNG_COMBAT = 1, SHATTER_RNG_LOOT = 2, SHATTER_RNG_EVENTS = 3 };

/* Constantes de regra (constants.h / rules.csv), lidas do banco: o C# nunca guarda número de balanceamento. */
typedef struct shatter_rules {
    double crit_multiplier_base, evasion_cap, block_cap, block_mitigation, resist_cap, resist_floor;
    double armor_damage_factor, armor_max_reduction, trigger_icd_min, cooldown_min, realtime_step;
    double sim_step, sim_step_fast, max_offline_hours, max_expedition_hours, min_expedition_hours;
    double ai_base_dodge, retreat_life_fraction, vigor_h1_4, vigor_h5_8, vigor_h9_12, vigor_band_hours;
    double fervor_xp_mult, fervor_gold_mat_mult, fervor_rare_mult;
    double clock_rollback_tolerance_s, steam_clock_max_skew_s, xp_base, xp_scale, xp_exponent;
    int32_t max_ai_rules, max_rares_per_expedition, xp_cap_levels_above_area;
    int32_t charges_max, charges_per_hour, charges_clear_area, charges_boss, charges_new_area, charges_daily_rest;
    int32_t max_level;
    uint8_t sim_fast_enabled;
    uint8_t reserved[7];
} shatter_rules;

/* Atributos (StatId, stats.h): o índice é o da enum; o nome em texto é o do CSV. */
enum {
    SHATTER_STAT_LIFE = 0, SHATTER_STAT_LIFE_REGEN, SHATTER_STAT_RESOURCE, SHATTER_STAT_RESOURCE_REGEN,
    SHATTER_STAT_ARMOR, SHATTER_STAT_EVASION_CHANCE, SHATTER_STAT_BLOCK_CHANCE, SHATTER_STAT_RESIST_FIRE,
    SHATTER_STAT_RESIST_COLD, SHATTER_STAT_RESIST_LIGHTNING, SHATTER_STAT_DAMAGE, SHATTER_STAT_ATTACK_SPEED,
    SHATTER_STAT_CAST_SPEED, SHATTER_STAT_CRIT_CHANCE, SHATTER_STAT_CRIT_MULTIPLIER, SHATTER_STAT_MOVE_SPEED,
    SHATTER_STAT_COOLDOWN_RECOVERY, SHATTER_STAT_AREA_OF_EFFECT, SHATTER_STAT_PROJECTILE_COUNT,
    SHATTER_STAT_DAMAGE_TAKEN, SHATTER_STAT_POTION_EFFECT, SHATTER_STAT_COUNT
};
/* Tags (bitmask, types.h). */
enum {
    SHATTER_TAG_ATTACK = 1 << 0, SHATTER_TAG_SPELL = 1 << 1, SHATTER_TAG_MELEE = 1 << 2,
    SHATTER_TAG_PROJECTILE = 1 << 3, SHATTER_TAG_AREA = 1 << 4, SHATTER_TAG_FIRE = 1 << 5,
    SHATTER_TAG_COLD = 1 << 6, SHATTER_TAG_LIGHTNING = 1 << 7, SHATTER_TAG_PHYSICAL = 1 << 8
};
/* Tipos de dano: índice dos vetores [4] (physical, fire, cold, lightning). */
enum { SHATTER_DAMAGE_PHYSICAL = 0, SHATTER_DAMAGE_FIRE = 1, SHATTER_DAMAGE_COLD = 2, SHATTER_DAMAGE_LIGHTNING = 3 };
enum { SHATTER_MOD_FLAT = 0, SHATTER_MOD_INCREASED = 1, SHATTER_MOD_MORE = 2 };

typedef struct shatter_modifier {
    double value;            /* fração para increased/more (0.2 = +20%) */
    uint32_t required_tags;  /* 0 = vale sempre */
    uint16_t stat;           /* SHATTER_STAT_* */
    uint8_t kind;            /* SHATTER_MOD_* */
    uint8_t reserved;
} shatter_modifier;

/* Golpe (damage.h). Atacante e defensor vão como handles na chamada. */
typedef struct shatter_hit_input {
    double base_damage[4];        /* por tipo, antes do coeficiente */
    double coefficient;           /* coeficiente da habilidade (rank incluso) */
    double defender_life;         /* vida atual do alvo */
    double defender_barrier;      /* barreira atual do alvo */
    uint32_t skill_tags;          /* SHATTER_TAG_* */
    uint8_t is_damage_over_time;  /* tick de DoT: sem crítico/evasão/bloqueio, sem RNG */
    uint8_t can_be_blocked;
    uint8_t reserved[2];
} shatter_hit_input;

enum { SHATTER_HIT = 0, SHATTER_HIT_EVADED = 1, SHATTER_HIT_BLOCKED = 2 };
typedef struct shatter_hit_result {
    double after_modifiers[4];
    double after_mitigation[4];
    double total_damage;
    double absorbed_by_barrier;
    double life_lost;
    double defender_life_after;
    double defender_barrier_after;
    uint8_t outcome;   /* SHATTER_HIT* */
    uint8_t critical;
    uint8_t landed;
    uint8_t killed;
    uint8_t reserved[4];
} shatter_hit_result;

/* Efeitos (effects.h). */
enum { SHATTER_TRIGGER_NONE = 0, SHATTER_TRIGGER_ON_HIT, SHATTER_TRIGGER_ON_CRIT, SHATTER_TRIGGER_ON_BLOCK,
       SHATTER_TRIGGER_ON_KILL, SHATTER_TRIGGER_ON_TAKE_DAMAGE };
enum { SHATTER_EFFECT_EVENT_DAMAGE_TICK = 0, SHATTER_EFFECT_EVENT_EXPIRED = 1 };
typedef struct shatter_effect_event {
    uint32_t kind;            /* SHATTER_EFFECT_EVENT_* */
    uint32_t effect_id_len;   /* bytes do ID (se > 127, effect_id vem cortado) */
    double damage[4];         /* DAMAGE_TICK: dano bruto; passe por shatter_resolve_hit com is_damage_over_time */
    char effect_id[128];      /* UTF-8, terminado em NUL */
} shatter_effect_event;

/* Relógio (clock.h). Tudo em horário Unix UTC. */
typedef struct shatter_clock_input {
    int64_t local_now_utc;    /* DateTimeOffset.UtcNow.ToUnixTimeSeconds() */
    int64_t steam_now_utc;    /* SteamUtils.GetServerRealTime(), se houver */
    int64_t last_seen_utc;    /* do save (0 = save novo) */
    uint8_t has_steam_time;
    uint8_t reserved[7];
} shatter_clock_input;
typedef struct shatter_trusted_now {
    int64_t now;
    uint8_t used_steam;
    uint8_t rollback_detected;
    uint8_t reserved[6];
} shatter_trusted_now;
typedef struct shatter_offline_window {
    double effective_seconds;
    uint8_t finished;
    uint8_t ended_by_rollback;
    uint8_t reserved[6];
} shatter_offline_window;

/* Loot (loot.h). */
enum { SHATTER_LOOT_MANUAL = 0, SHATTER_LOOT_IDLE = 1 };
typedef struct shatter_loot_context {
    double quantity_mult;          /* 1.0; Pedras de Rota somam aqui */
    int32_t mode;                  /* SHATTER_LOOT_* */
    int32_t area_level;
    int32_t rares_already_dropped;
    int32_t max_rares;             /* -1 = sem teto */
} shatter_loot_context;

/* Save (save.h). status = LoadStatus: 0 ok, 1 missing, 2 bad_json, 3 bad_format_tag, 4 checksum_mismatch,
 * 5 too_new, 6 migration_failed, 7 bad_data. */
typedef struct shatter_load_report {
    int32_t status;
    int32_t used_backup;           /* 0 = principal; 1..3 = backup usado (a UI avisa o jogador) */
} shatter_load_report;
typedef struct shatter_save_summary {
    uint64_t next_item_uid;
    int64_t last_seen_utc;
    int64_t last_rest_day;
    uint32_t content_version;
    int32_t save_version;
    int32_t character_count;
    int32_t marker_charges;
    int32_t expedition_slots;
    int32_t expedition_count;
    int32_t running_expedition;    /* índice da expedição Running, ou -1 */
    int32_t reserved;
} shatter_save_summary;
typedef struct shatter_area_run_reward {
    int32_t charges_gained;
    uint8_t new_conquest;
    uint8_t reserved[3];
} shatter_area_run_reward;

/* Resultado de shatter_expedition_check / start (StartCheck, expedition.h). */
enum {
    SHATTER_START_OK = 0, SHATTER_START_MAP_NOT_CONQUERED, SHATTER_START_NOT_ENOUGH_CHARGES,
    SHATTER_START_ANOTHER_RUNNING, SHATTER_START_INVALID_DURATION, SHATTER_START_TOO_MANY_RULES,
    SHATTER_START_IDLE_INCOMPATIBLE, SHATTER_START_UNKNOWN_CONTENT
};
/* Motivo de parada (StopReason); no JSON vai como texto ("duration_reached", "retreat"...). */
enum {
    SHATTER_STOP_NONE = 0, SHATTER_STOP_DURATION_REACHED, SHATTER_STOP_RETREAT, SHATTER_STOP_CLOCK_ROLLBACK,
    SHATTER_STOP_INCOMPATIBLE_BUILD, SHATTER_STOP_CONTENT_MISMATCH
};
typedef struct shatter_forecast {
    double xp_p10, xp_p50, xp_p90;
    double gold_p10, gold_p50, gold_p90;
    double retreat_probability;
    int32_t worst_resist_gap;      /* SHATTER_DAMAGE_* */
    int32_t reserved;
} shatter_forecast;

/* Flags de shatter_expedition_simulate / finalize. */
enum { SHATTER_RESULT_RECEIPTS = 1 };  /* inclui os recibos por encontro no JSON (pode passar de 1 MB em 12 h) */

/* ------------------------------------------------------------------------------------------------
 * Versão e layout
 * ---------------------------------------------------------------------------------------------- */
SHATTER_API uint32_t SHATTER_CALL shatter_api_version(void) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_core_version(uint32_t* major, uint32_t* minor) SHATTER_NOEXCEPT;
/* Nome estável de um status ("ok", "buffer_too_small"...); ponteiro para texto estático. */
SHATTER_API const char* SHATTER_CALL shatter_status_name(shatter_status status) SHATTER_NOEXCEPT;

/* Layout das structs blittable: sizeof e offsetof em ordem fixa (lista em shatter_layout_info).
 * O C# monta a mesma lista com Marshal.SizeOf/OffsetOf e chama shatter_layout_check na inicialização:
 * OK se tudo bate; SHATTER_VERSION_MISMATCH se n ou algum valor difere (err->line = 1 + índice do 1º). */
#define SHATTER_LAYOUT_COUNT 82u
SHATTER_API shatter_status SHATTER_CALL shatter_layout_info(uint32_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_check(const uint32_t* values, size_t n,
                                                             shatter_error* err) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Conteúdo (ContentDB)
 * ---------------------------------------------------------------------------------------------- */
/* Lê todos os *.csv da pasta e finaliza. Sempre devolve um handle em *out (mesmo com erro de conteúdo,
 * para ler a lista em shatter_db_errors_json); o chamador o destrói. Banco com erro recusa as consultas
 * com SHATTER_CONTENT_INVALID. Retorno: OK, CONTENT_INVALID ou IO_ERROR (pasta ou tabela faltando). */
SHATTER_API shatter_status SHATTER_CALL shatter_db_load_directory(const char* path, size_t path_len, shatter_db** out,
                                                                  shatter_error* err) SHATTER_NOEXCEPT;
/* Banco vazio para carregar tabela a tabela (testes, ferramentas). Não é seguro entre threads até finalizar. */
SHATTER_API shatter_status SHATTER_CALL shatter_db_create(shatter_db** out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_db_load_table(shatter_db* db, const char* table, size_t table_len,
                                                              const char* csv, size_t csv_len,
                                                              shatter_error* err) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_db_finalize(shatter_db* db, shatter_error* err) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_db_destroy(shatter_db* db) SHATTER_NOEXCEPT;
/* [{"table":"skills.csv","line":4,"message":"E_FK: ..."}] */
SHATTER_API shatter_status SHATTER_CALL shatter_db_errors_json(const shatter_db* db, uint8_t* out, size_t cap,
                                                               size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_db_content_version(const shatter_db* db, uint32_t* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_db_rules(const shatter_db* db, shatter_rules* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_db_xp_to_next_level(const shatter_db* db, int32_t level,
                                                                    double* out) SHATTER_NOEXCEPT;
/* Dados de um ID de conteúdo em JSON (para nome/ícone/tooltip e tempos de habilidade): o tipo vem do
 * prefixo (class., skill., effect., enemy., affix., item_base., unique., loot., enc., map.).
 * ID que não existe: SHATTER_NOT_FOUND. */
SHATTER_API shatter_status SHATTER_CALL shatter_db_lookup_json(const shatter_db* db, const char* id, size_t id_len,
                                                               uint8_t* out, size_t cap,
                                                               size_t* needed) SHATTER_NOEXCEPT;
/* IDs em ordem do CSV de "maps", "affixes" ou "item_bases": ["map.act1.crypt", ...]. */
SHATTER_API shatter_status SHATTER_CALL shatter_db_ids_json(const shatter_db* db, const char* table, size_t table_len,
                                                            uint8_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * RNG (rng.h)
 * ---------------------------------------------------------------------------------------------- */
SHATTER_API shatter_status SHATTER_CALL shatter_rng_for_stream(uint64_t seed, uint32_t stream, uint64_t index,
                                                               shatter_rng* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_rng_next_u32(shatter_rng* rng, uint32_t* out) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Atributos (StatBlock) — main thread
 * ---------------------------------------------------------------------------------------------- */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_create(shatter_statblock** out) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_statblock_destroy(shatter_statblock* sb) SHATTER_NOEXCEPT;
/* BuildStatBlock de um personagem (JSON no formato CharacterState do save). */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_from_character_json(const shatter_db* db, const char* json,
                                                                             size_t len, shatter_statblock** out,
                                                                             shatter_error* err) SHATTER_NOEXCEPT;
/* BuildStatBlock do personagem `character_index` do save. */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_from_save(const shatter_db* db, const shatter_save* save,
                                                                   size_t character_index, shatter_statblock** out,
                                                                   shatter_error* err) SHATTER_NOEXCEPT;
/* BuildEnemyStatBlock: inimigo no nível de monstro `level`. */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_for_enemy(const shatter_db* db, const char* enemy_id,
                                                                   size_t enemy_id_len, int32_t level,
                                                                   shatter_statblock** out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_set_base(shatter_statblock* sb, uint32_t stat,
                                                                  double value) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_get_base(const shatter_statblock* sb, uint32_t stat,
                                                                  double* out) SHATTER_NOEXCEPT;
/* Valor final no contexto de tags (0 = sem tags). Usa o cache do core (não é seguro entre threads). */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_get(const shatter_statblock* sb, uint32_t stat,
                                                             uint32_t context_tags, double* out) SHATTER_NOEXCEPT;
/* Mesma fórmula com outra base (dano da habilidade daquele tipo). */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_apply_tagged(const shatter_statblock* sb, uint32_t stat,
                                                                      uint32_t context_tags, double base,
                                                                      double* out) SHATTER_NOEXCEPT;
/* source: quem deu o mod ("item:12", "fx:effect.burn"...), para remover depois. */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_add_modifier(shatter_statblock* sb,
                                                                      const shatter_modifier* mod, const char* source,
                                                                      size_t source_len) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_remove_modifiers_from(shatter_statblock* sb,
                                                                               const char* source, size_t source_len,
                                                                               uint32_t* removed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_clear_modifiers(shatter_statblock* sb) SHATTER_NOEXCEPT;
/* Muda a cada alteração: o C# relê os atributos exibidos quando a revisão muda. */
SHATTER_API shatter_status SHATTER_CALL shatter_statblock_revision(const shatter_statblock* sb,
                                                                  uint64_t* out) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Golpe (caminho quente: sem alocação, sem JSON). A MESMA função do simulador.
 * Consome sempre 3 números do rng (crítico, evasão, bloqueio); DoT não consome nenhum.
 * ---------------------------------------------------------------------------------------------- */
SHATTER_API shatter_status SHATTER_CALL shatter_resolve_hit(const shatter_statblock* attacker,
                                                           const shatter_statblock* defender,
                                                           const shatter_hit_input* input,
                                                           const shatter_rules* rules, shatter_rng* rng,
                                                           shatter_hit_result* out) SHATTER_NOEXCEPT;
/* Recarga efetiva de habilidade: max(cooldown_min, base / cooldown_recovery). */
SHATTER_API shatter_status SHATTER_CALL shatter_effective_cooldown(double base_cooldown, double cooldown_recovery,
                                                                  const shatter_rules* rules,
                                                                  double* out) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Efeitos (EffectContainer) — main thread
 * ---------------------------------------------------------------------------------------------- */
SHATTER_API shatter_status SHATTER_CALL shatter_effects_create(shatter_effects** out) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_effects_destroy(shatter_effects* fx) SHATTER_NOEXCEPT;
/* Aplica um efeito do banco em `target` (os mods vão para o StatBlock com source "fx:<id>").
 * *applied = 0 se bloqueado por recarga interna, regra de cadeia ou StrongestOnly mais fraco. */
SHATTER_API shatter_status SHATTER_CALL shatter_effects_apply(shatter_effects* fx, const shatter_db* db,
                                                             const char* effect_id, size_t effect_id_len,
                                                             const char* source_entity, size_t source_len,
                                                             double magnitude, uint32_t triggered_by,
                                                             shatter_statblock* target,
                                                             uint8_t* applied) SHATTER_NOEXCEPT;
/* Avança dt (sempre o passo fixo). Os eventos deste tick ficam no handle até o próximo tick:
 * *event_count diz quantos; leia com shatter_effects_events. */
SHATTER_API shatter_status SHATTER_CALL shatter_effects_tick(shatter_effects* fx, const shatter_db* db, double dt,
                                                            shatter_statblock* target,
                                                            size_t* event_count) SHATTER_NOEXCEPT;
/* Copia os eventos do último tick (cap em número de eventos). */
SHATTER_API shatter_status SHATTER_CALL shatter_effects_events(const shatter_effects* fx, shatter_effect_event* out,
                                                              size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_effects_stack_count(const shatter_effects* fx, const char* effect_id,
                                                                   size_t effect_id_len,
                                                                   int32_t* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_effects_clear(shatter_effects* fx,
                                                             shatter_statblock* target) SHATTER_NOEXCEPT;
/* Efeitos ativos (ícones de buff): [{"effect_id","source","magnitude","remaining"}], em ordem de aplicação. */
SHATTER_API shatter_status SHATTER_CALL shatter_effects_active_json(const shatter_effects* fx, uint8_t* out, size_t cap,
                                                                   size_t* needed) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Relógio (clock.h)
 * ---------------------------------------------------------------------------------------------- */
SHATTER_API shatter_status SHATTER_CALL shatter_clock_resolve_now(const shatter_clock_input* in,
                                                                 const shatter_rules* rules,
                                                                 shatter_trusted_now* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_clock_expedition_window(int64_t start_utc, int32_t duration_hours,
                                                                       const shatter_trusted_now* now,
                                                                       int64_t last_seen_utc,
                                                                       const shatter_rules* rules,
                                                                       shatter_offline_window* out) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Loot (manual)
 * ---------------------------------------------------------------------------------------------- */
/* Rola uma tabela. Se `save` não for nulo, os uids dos itens vêm do contador do save (reservados só se
 * a saída couber). Saída: {"items":[ItemInstance...],"stacks":[{"id","amount"}],"rares_dropped":n}. */
SHATTER_API shatter_status SHATTER_CALL shatter_loot_roll(const shatter_db* db, shatter_save* save,
                                                         const char* table_id, size_t table_id_len,
                                                         const shatter_loot_context* ctx, shatter_rng* rng,
                                                         uint8_t* out, size_t cap, size_t* needed,
                                                         shatter_error* err) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Save (save.h) — main thread. O C# não serializa nem grava o save: tudo passa por aqui.
 * ---------------------------------------------------------------------------------------------- */
SHATTER_API shatter_status SHATTER_CALL shatter_save_create(shatter_save** out) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_save_destroy(shatter_save* save) SHATTER_NOEXCEPT;
/* Lê slot (`base_path` sem extensão: ".../saves/slot_1"): principal ou o backup mais recente válido.
 * Com `db` (opcional), recusa save com content_version maior que o do jogo (VERSION_MISMATCH, *out nulo,
 * arquivo intocado; RNF-10). Retorno: OK, NOT_FOUND (nada existe), VERSION_MISMATCH (save_version ou
 * content_version futuro) ou PARSE_ERROR (todos corrompidos: NUNCA sobrescreva sem confirmação). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_read(const shatter_db* db, const char* base_path, size_t len,
                                                         shatter_save** out, shatter_load_report* report,
                                                         shatter_error* err) SHATTER_NOEXCEPT;
/* Gravação segura: .tmp conferido → 3 backups rotativos → rename. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_write(const shatter_save* save, const char* base_path,
                                                          size_t len, shatter_error* err) SHATTER_NOEXCEPT;
/* Arquivo completo (envelope format/save_version/sha256/data), como iria para o disco. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_to_json(const shatter_save* save, uint8_t pretty, uint8_t* out,
                                                            size_t cap, size_t* needed) SHATTER_NOEXCEPT;
/* Lê um arquivo completo (confere checksum e migra). *load_status = LoadStatus. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_from_json(const char* json, size_t len, shatter_save** out,
                                                              int32_t* load_status,
                                                              shatter_error* err) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_save_summary_get(const shatter_save* save,
                                                                shatter_save_summary* out) SHATTER_NOEXCEPT;
/* last_seen novo = max(atual, now.now) (nunca anda para trás). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_touch_last_seen(shatter_save* save,
                                                                    const shatter_trusted_now* now) SHATTER_NOEXCEPT;
/* Descanso diário das Cargas do Marco (+4 por dia UTC, sem acumular). *charges = cargas depois. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_apply_daily_rest(const shatter_db* db, shatter_save* save,
                                                                     const shatter_trusted_now* now,
                                                                     int32_t* charges) SHATTER_NOEXCEPT;
/* Personagem `index` no formato CharacterState do save (snapshot para exibir ou montar atributos). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_character_json(const shatter_save* save, size_t index,
                                                                   uint8_t* out, size_t cap,
                                                                   size_t* needed) SHATTER_NOEXCEPT;
/* Fim de uma corrida manual numa área: cargas e domínio (RF-35, RF-50). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_record_area_run(const shatter_db* db, shatter_save* save,
                                                                    size_t character_index, const char* map_id,
                                                                    size_t map_id_len, uint8_t reached_end,
                                                                    uint8_t boss_defeated,
                                                                    shatter_area_run_reward* out) SHATTER_NOEXCEPT;
/* Junta ao baú um loot no formato de shatter_loot_roll (itens com os uids já reservados; pilhas somadas). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_add_loot(shatter_save* save, const char* loot_json, size_t len,
                                                             shatter_error* err) SHATTER_NOEXCEPT;

/* ------------------------------------------------------------------------------------------------
 * Expedição (expedition.h). Parâmetros de início em JSON:
 *   {"character_index":0,"map_id":"map.act1.crypt","objective":"xp","rules":[AiRule...],
 *    "duration_hours":4,"seed":"123456789","start_utc":1700000000}
 * AiRule = {"condition":"life_below","param":0.35,"action":"use_potion","ref_id":""} (formato do save).
 * ---------------------------------------------------------------------------------------------- */
/* Só confere (não muda o save). *start_check = SHATTER_START_*; saída = IDs que bloqueiam (RF-43). */
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_check(const shatter_db* db, const shatter_save* save,
                                                                const char* params_json, size_t len,
                                                                int32_t* start_check, uint8_t* out, size_t cap,
                                                                size_t* needed, shatter_error* err) SHATTER_NOEXCEPT;
/* Inicia no save (snapshot congelado, cargas descontadas). Recusa = OK com *start_check != 0 e save intacto. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_start_expedition(const shatter_db* db, shatter_save* save,
                                                                     const char* params_json, size_t len,
                                                                     int32_t* start_check,
                                                                     shatter_error* err) SHATTER_NOEXCEPT;
/* Pedido pronto para simular da expedição `index`: janela offline (relógio) aplicada em effective_seconds
 * e "ended_by_rollback" no JSON. Não muda o save. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_expedition_request(const shatter_db* db, const shatter_save* save,
                                                                       size_t index, const shatter_clock_input* clock,
                                                                       shatter_offline_window* window, uint8_t* out,
                                                                       size_t cap, size_t* needed,
                                                                       shatter_error* err) SHATTER_NOEXCEPT;
/* Simula tudo (pode rodar fora da main thread: só lê o db e o JSON). Saída = ExpeditionResult em JSON
 * ("result_hash" como texto decimal). flags: SHATTER_RESULT_RECEIPTS. */
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_simulate(const shatter_db* db, const char* request_json,
                                                                   size_t len, uint32_t flags, uint8_t* out,
                                                                   size_t cap, size_t* needed,
                                                                   shatter_error* err) SHATTER_NOEXCEPT;
/* Simulação em fatias (cancelamento entre elas): progress_json nulo = início. Saída = ExpeditionProgress em
 * JSON (o estado inteiro; passe-o de volta na próxima fatia). "stop" != "none" = acabou. */
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_simulate_range(const shatter_db* db,
                                                                         const char* request_json, size_t request_len,
                                                                         const char* progress_json,
                                                                         size_t progress_len, uint32_t first_encounter,
                                                                         uint32_t count, uint8_t* out, size_t cap,
                                                                         size_t* needed,
                                                                         shatter_error* err) SHATTER_NOEXCEPT;
/* Fecha as fatias: mesmo resultado (e resultHash) de shatter_expedition_simulate. */
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_finalize(const shatter_db* db, const char* request_json,
                                                                   size_t request_len, const char* progress_json,
                                                                   size_t progress_len, uint32_t flags, uint8_t* out,
                                                                   size_t cap, size_t* needed,
                                                                   shatter_error* err) SHATTER_NOEXCEPT;
/* Previsão em faixa para a tela da Ilsa (RF-40). */
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_forecast(const shatter_db* db, const char* request_json,
                                                                   size_t len, uint64_t base_seed, int32_t samples,
                                                                   shatter_forecast* out,
                                                                   shatter_error* err) SHATTER_NOEXCEPT;
/* Coleta sem duplicar (RF-55): itens, pilhas e XP entram e o status vira collected no MESMO save; o
 * chamador grava uma vez em seguida. *collected = 0 se já coletada (nada muda). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_collect_expedition(const shatter_db* db, shatter_save* save,
                                                                       size_t index, const char* result_json,
                                                                       size_t len, uint8_t* collected,
                                                                       shatter_error* err) SHATTER_NOEXCEPT;

#ifdef __cplusplus
}  /* extern "C" */
#endif

#endif /* SHATTER_C_H */
