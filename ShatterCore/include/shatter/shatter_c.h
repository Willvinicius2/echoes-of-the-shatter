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
    SHATTER_TAG_COLD = 1 << 6, SHATTER_TAG_LIGHTNING = 1 << 7, SHATTER_TAG_PHYSICAL = 1 << 8,
    /* Tag de EFEITO de defesa (API 1.5, docs/18 8.1): ver shatter_hit_input.from_guard_arc. Não é tag de habilidade. */
    SHATTER_TAG_GUARD = 1 << 9
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
    /* API 1.5 (antes reserved[0]; 0 = fora do arco, o que os chamadores antigos já mandavam): 1 = ESTE golpe veio de dentro
     * do arco da defesa do alvo (o C# faz a geometria). Só então valem os modificadores de dano recebido dos efeitos com a
     * tag guard (effect.guarding.*). Os demais modificadores do alvo não dependem disto. */
    uint8_t from_guard_arc;
    uint8_t reserved[1];
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
    SHATTER_START_IDLE_INCOMPATIBLE, SHATTER_START_UNKNOWN_CONTENT,
    SHATTER_START_CLOCK_ROLLBACK     /* 1.1+: o relógio voltou (RF-48); só o início confiável devolve; nada muda */
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
/* RETIRADA na API 1.1 (docs/11, M-03): devolve INVALID_ARGUMENT. Use shatter_save_start_expedition_trusted (start_utc do
 * relógio confiável e seed derivada pelo core). Era: inicia no save (snapshot congelado, cargas descontadas). */
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
/* RETIRADA na API 1.1 (docs/11, A-05): devolve INVALID_ARGUMENT (*collected = 0). O resultado vinha do chamador. Use
 * shatter_save_collect_expedition_trusted: o core recalcula o resultado pelo pedido salvo (RF-55, sem duplicar; o
 * chamador grava o save uma vez em seguida). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_collect_expedition(const shatter_db* db, shatter_save* save,
                                                                       size_t index, const char* result_json,
                                                                       size_t len, uint8_t* collected,
                                                                       shatter_error* err) SHATTER_NOEXCEPT;

/* ================================================================================================
 * API C 1.1 (SHATTER_C_API_MINOR 1) — ADIÇÃO sobre a v1 (docs/09_mudancas_contrato.md, seção 7).
 * Regras novas do protótipo (docs/13): poções, esquiva, stun e Guarda Quebrada, elite, chefe, Único, e o que o
 * IRulesCore do C# precisa para não calcular regra (docs/11, A-01). As structs e funções da v1 não mudaram.
 * As structs novas têm layout próprio, conferido por shatter_layout_info_ext/shatter_layout_check_ext (o layout da
 * v1, SHATTER_LAYOUT_COUNT, continua o mesmo).
 *
 * POSSE (docs/11, A-06) — vale para TODA a API, v1 e 1.1:
 *  - Quem cria destrói: cada handle (shatter_db, shatter_save, shatter_statblock, shatter_effects, shatter_potions,
 *    shatter_actor, shatter_boss) é do chamador (SafeHandle no C#); a DLL nunca guarda ponteiro do chamador depois
 *    de a função voltar, exceto os vínculos abaixo.
 *  - Vínculos que EXIGEM ordem de destruição: shatter_boss guarda o shatter_db que o criou; o shatter_db tem que
 *    sobreviver a todo handle criado a partir dele (destrua o boss e os demais ANTES do db). shatter_statblock,
 *    shatter_effects e shatter_actor NÃO guardam o db: o db é passado a cada chamada.
 *  - shatter_effects_* e shatter_actor_* recebem o shatter_statblock da entidade a cada chamada: o chamador DEVE passar
 *    sempre o MESMO bloco para o mesmo contêiner (os mods "fx:<id>" e "stagger" ficam no bloco que recebeu a chamada).
 *  - Buffers de saída são do chamador; a DLL só escreve até `cap` e informa *needed. Eventos (efeitos e chefe) ficam
 *    no handle até o próximo tick/step, e são lidos por cópia.
 *  - Strings de entrada: UTF-8 com comprimento; a DLL copia o que precisa. Strings de saída em struct: terminadas
 *    em NUL, cortadas em fronteira de caractere.
 *  - Thread: shatter_db finalizado é imutável (leitura concorrente); TODO o resto é de uma thread só.
 *  - O que o chamador manda como resultado de expedição, tempo de início ou seed NÃO é confiável: o core recalcula
 *    a partir do estado salvo (shatter_save_collect_expedition_trusted, shatter_save_start_expedition_trusted).
 * ============================================================================================== */
#define SHATTER_C_API_MINOR 6u   /* 6: economia do protótipo: Vendedor, recompra, Frasco de Recarga e Encantador (docs/09 seção 13); 5: combate básico: kits de classe, chaves do combo, defesa com arco, pierce, regen em movimento, recurso por golpe (docs/09 seção 12); 4: inventário, equipamento, venda, loot no chão (docs/09 seção 11); 3: fuga do inimigo no shatter_actor (docs/09 seção 10); 2: shatter_vitals.potion_barrier, layout ext completo, início confiável com relógio (docs/09 seção 9) */

typedef struct shatter_potions shatter_potions;   /* cinto de poções de UM personagem (cargas, recarga, trava) */
typedef struct shatter_actor shatter_actor;       /* stun, imunidades e Guarda Quebrada de UMA entidade */
typedef struct shatter_boss shatter_boss;         /* máquina de fases do chefe (guarda o shatter_db que a criou) */

typedef struct shatter_rules_ext {   /* chaves novas de rules.csv (docs/13); o C# não guarda número de balanceamento */
    double dodge_recharge, dodge_duration, dodge_iframes, dodge_distance, dodge_cost_resource, dodge_buffer;
    double dodge_perfect_resource, dodge_cancel_recovery_fraction;
    double guard_break_stagger_seconds, guard_break_stagger_damage_taken;
    double guard_break_immunity_boss, guard_break_immunity_other, boss_shield_down_seconds;
    double elite_life_mult, elite_damage_mult, elite_xp_mult;
    double potion_lockout, out_of_combat_seconds;
    int32_t dodge_max_charges;
    int32_t reserved;
} shatter_rules_ext;

typedef struct shatter_vitals {      /* vida, recurso e barreira de uma entidade (o C# guarda; o core calcula) */
    double life, resource, barrier;
    double barrier_seconds_left;     /* > 0: a barreira (de poção) some ao chegar a 0 */
    double potion_barrier;           /* parte de `barrier` que veio da poção (só ela some junto); 0 = o core assume tudo */
} shatter_vitals;

typedef struct shatter_action_timing {   /* tempos das 3 fases com a velocidade aplicada, recarga e custo */
    double windup, impact, recovery, cooldown, cost;
} shatter_action_timing;

enum { SHATTER_POTION_OK = 0, SHATTER_POTION_UNKNOWN = 1, SHATTER_POTION_NO_CHARGES = 2, SHATTER_POTION_LOCKED_OUT = 3 };
typedef struct shatter_potion_outcome {
    double heal_amount;              /* vida que de fato entrou (já limitada à vida máxima) */
    double barrier_amount;           /* barreira nova (substitui a anterior da poção) */
    double barrier_seconds;
    double use_time;                 /* s bebendo */
    double move_speed_while_using;   /* fração da velocidade durante o uso */
    double lockout;                  /* trava global iniciada (s) */
    int32_t status;                  /* SHATTER_POTION_* (diferente de OK: nada mudou) */
    int32_t reserved;
} shatter_potion_outcome;

typedef struct shatter_dodge_state {   /* cargas NÃO são salvas; charges < 0 = cheia (use shatter_dodge_init) */
    double recharge_remaining;
    double elapsed;
    int32_t charges;
    uint8_t active;
    uint8_t reserved[3];
} shatter_dodge_state;
enum { SHATTER_DODGE_OK = 0, SHATTER_DODGE_NO_CHARGES = 1, SHATTER_DODGE_ACTIVE = 2, SHATTER_DODGE_NOT_ENOUGH_RESOURCE = 3 };

typedef struct shatter_actor_apply {   /* resultado de aplicar um efeito (stun / Guarda Quebrada) */
    double stun_seconds, stagger_seconds;
    int32_t guard_break_stacks;
    uint8_t applied;            /* o efeito entrou no contêiner */
    uint8_t stunned;            /* stun começou */
    uint8_t stun_blocked;       /* alvo imune ao stun: nada aplicado */
    uint8_t interrupted;        /* cancele a preparação (telegraph) em andamento */
    uint8_t staggered;          /* Guarda Quebrada: acúmulos consumidos, alvo atordoado */
    uint8_t remove_barrier;     /* zere a barreira/escudo do alvo */
    uint8_t reserved[2];
} shatter_actor_apply;
typedef struct shatter_flee_result {   /* um passo da fuga do inimigo (shatter_actor_flee_step) */
    double remaining;          /* segundos de fuga que faltam */
    uint8_t fleeing;           /* 1 = foge neste passo (se afasta do alvo) */
    uint8_t started;           /* 1 = começou neste passo (cancele telegraph e golpe em curso) */
    uint8_t ended;             /* 1 = acabou neste passo */
    uint8_t can_flee;          /* 1 = o inimigo tem fleeLifeFraction > 0 no enemy_ai.csv */
    uint8_t reserved[4];
} shatter_flee_result;
typedef struct shatter_actor_info {
    double stun_remaining, stagger_remaining, immunity_remaining;
    uint8_t can_act, stun_immune, reserved[6];
} shatter_actor_info;

typedef struct shatter_elite_info {    /* multiplicadores finais de um elite (base de rules.csv × modificador) */
    double life_mult, damage_mult, xp_mult, barrier_fraction_of_life;
    double move_speed_mult, attack_speed_mult, recovery_mult;
    double death_explosion_radius, death_explosion_damage, death_explosion_fuse;
    char modifier_id[64];            /* vazio = só os multiplicadores base */
    uint8_t rolled;                  /* 1 = elite sorteado (multiplicadores base valem) */
    uint8_t reserved[7];
} shatter_elite_info;

typedef struct shatter_vec2 { double x, z; } shatter_vec2;
typedef struct shatter_boss_context { shatter_vec2 boss, player; } shatter_boss_context;
enum {
    SHATTER_BOSS_EVT_PATTERN_START = 0, SHATTER_BOSS_EVT_PATTERN_IMPACT, SHATTER_BOSS_EVT_PATTERN_END,
    SHATTER_BOSS_EVT_PATTERN_INTERRUPTED, SHATTER_BOSS_EVT_PHASE_START, SHATTER_BOSS_EVT_SUMMON_MARKER,
    SHATTER_BOSS_EVT_SUMMON_SPAWN, SHATTER_BOSS_EVT_PHASE_END, SHATTER_BOSS_EVT_STAGGER_START,
    SHATTER_BOSS_EVT_STAGGER_END, SHATTER_BOSS_EVT_SHIELD_DOWN, SHATTER_BOSS_EVT_SHIELD_UP, SHATTER_BOSS_EVT_DIED
};
typedef struct shatter_boss_event {
    double seconds;                  /* PATTERN_START: telegraph; PATTERN_IMPACT: duração do impacto; PHASE_START: rugido;
                                        SUMMON_MARKER: tempo até surgirem; STAGGER_START e SHIELD_DOWN: duração */
    uint32_t kind;                   /* SHATTER_BOSS_EVT_* */
    int32_t phase;
    int32_t count;                   /* SUMMON_*: quantos */
    int32_t reserved;
    char pattern_id[64];
    char skill_id[64];
    char enemy_id[64];               /* SUMMON_*: o invocado (sem XP e sem loot; morre com o chefe) */
} shatter_boss_event;
enum { SHATTER_BOSS_IDLE = 0, SHATTER_BOSS_WAITING, SHATTER_BOSS_TELEGRAPH, SHATTER_BOSS_IMPACT, SHATTER_BOSS_RECOVERY,
       SHATTER_BOSS_STAGGER, SHATTER_BOSS_TRANSITION, SHATTER_BOSS_DEAD };
typedef struct shatter_boss_info {
    double life, max_life, shield_down_remaining, turn_rate_deg_per_sec, facing_x, facing_z;
    double stagger_remaining, stun_remaining;
    int32_t phase;
    int32_t state;                   /* SHATTER_BOSS_* */
    uint8_t shield_up, invulnerable, reserved[6];
} shatter_boss_info;
typedef struct shatter_boss_damage {
    double applied, life_after;
    uint8_t shield_blocked;          /* escudo frontal: 0 de dano, sem Ímpeto, sem knockback */
    uint8_t invulnerable;            /* rugido da transição */
    uint8_t clamped_by_phase;        /* dano excedente cortado no limiar da próxima fase */
    uint8_t killed;
    uint8_t reserved[4];
} shatter_boss_damage;
typedef struct shatter_boss_progress { int32_t kills, kills_since_unique; } shatter_boss_progress;

typedef struct shatter_forecast_ex {
    shatter_forecast base;
    int32_t calibration;             /* SHATTER_CALIBRATION_*: a previsão mostra "estimativa" se MANUAL_ESTIMATE */
    int32_t reserved;
} shatter_forecast_ex;
enum { SHATTER_CALIBRATION_NONE = 0, SHATTER_CALIBRATION_MANUAL_ESTIMATE = 1, SHATTER_CALIBRATION_BOT_PARITY = 2 };

/* Resultado de shatter_save_collect_expedition_trusted. */
enum { SHATTER_COLLECT_COLLECTED = 0, SHATTER_COLLECT_ALREADY = 1, SHATTER_COLLECT_NOT_FINISHED = 2 };

#define SHATTER_LAYOUT_EXT_COUNT 114u
SHATTER_API uint32_t SHATTER_CALL shatter_api_minor(void) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext(uint32_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext(const uint32_t* values, size_t n,
                                                                 shatter_error* err) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_db_rules_ext(const shatter_db* db, shatter_rules_ext* out) SHATTER_NOEXCEPT;

/* Rodada 2 (docs/13, R2): chaves novas de rules.csv, em struct à parte para não mexer no layout de shatter_rules_ext.
 * Layout próprio: shatter_layout_info_ext2 / shatter_layout_check_ext2. */
typedef struct shatter_rules_ext2 {
    double unarmed_weapon_damage_physical;   /* dano físico base quando não há arma (golpes que escalam com arma) */
    double require_on_screen_margin;         /* uu: margem interna da área visível de R-VIS-1 */
} shatter_rules_ext2;
#define SHATTER_LAYOUT_EXT2_COUNT 3u
SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext2(uint32_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext2(const uint32_t* values, size_t n,
                                                                  shatter_error* err) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_db_rules_ext2(const shatter_db* db, shatter_rules_ext2* out) SHATTER_NOEXCEPT;
/* Dano base por tipo [physical, fire, cold, lightning] de uma habilidade: o da arma `weapon_base_id` se a habilidade
 * escala com arma (base de item vazia/nula = SEM arma: unarmed_weapon_damage_physical só no físico), senão o da própria
 * habilidade. É a MESMA conta do simulador idle. */
SHATTER_API shatter_status SHATTER_CALL shatter_skill_base_damage(const shatter_db* db, const char* skill_id,
                                                                  size_t skill_id_len, const char* weapon_base_id,
                                                                  size_t weapon_base_id_len, double out[4]) SHATTER_NOEXCEPT;

/* --- Golpe e recarga lendo as constantes do BANCO (docs/11, A-06 item 2): o chamador não manda número de regra. --- */
SHATTER_API shatter_status SHATTER_CALL shatter_resolve_hit_db(const shatter_db* db, const shatter_statblock* attacker,
                                                               const shatter_statblock* defender,
                                                               const shatter_hit_input* input, shatter_rng* rng,
                                                               shatter_hit_result* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_effective_cooldown_db(const shatter_db* db, double base_cooldown,
                                                                      double cooldown_recovery,
                                                                      double* out) SHATTER_NOEXCEPT;

/* --- Vida, recurso e barreira (IRulesCore: CreateVitals, TickVitals, Gain/TrySpendResource) --- */
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_create(const shatter_db* db, const shatter_statblock* stats,
                                                              const char* class_id, size_t class_id_len,
                                                              shatter_vitals* out) SHATTER_NOEXCEPT;
/* Regeneração de vida e recurso, decaimento do recurso fora de combate (da classe) e fim da barreira temporária.
 * class_id pode ser nulo (alvo sem classe). */
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_tick(const shatter_db* db, shatter_vitals* vitals,
                                                            const shatter_statblock* stats, const char* class_id,
                                                            size_t class_id_len, double dt,
                                                            uint8_t in_combat) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_gain_resource(shatter_vitals* vitals,
                                                                     const shatter_statblock* stats,
                                                                     double amount) SHATTER_NOEXCEPT;
/* *ok = 0 (sem gastar) se faltar recurso. */
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_spend_resource(shatter_vitals* vitals, double amount,
                                                                      uint8_t* ok) SHATTER_NOEXCEPT;

/* --- Tempos de ação, velocidade e ataque de inimigo (IRulesCore: GetActionTiming, GetEffectiveCost, GetMoveSpeedUu,
 *     CanAct, CanMove, PickAttack) --- */
/* modifier_id (opcional, elite): o telegraph não encurta com a velocidade de ataque do modificador e a recuperação usa
 * o recoveryMult dele. */
SHATTER_API shatter_status SHATTER_CALL shatter_skill_timing(const shatter_db* db, const char* skill_id,
                                                             size_t skill_id_len, const shatter_statblock* stats,
                                                             const char* modifier_id, size_t modifier_id_len,
                                                             shatter_action_timing* out) SHATTER_NOEXCEPT;
/* base_uu_per_sec > 0 (inimigo: "move_speed" do enemies.csv): base × atributo. base_uu_per_sec <= 0 (herói): o próprio
 * atributo, que já vem em uu/s do class_stats.csv (move_speed = 450). */
SHATTER_API shatter_status SHATTER_CALL shatter_move_speed(const shatter_statblock* stats, double base_uu_per_sec,
                                                           double* out) SHATTER_NOEXCEPT;
/* `actor` (opcional): stun e stagger também impedem. */
SHATTER_API shatter_status SHATTER_CALL shatter_can_act(const shatter_statblock* stats, const shatter_actor* actor,
                                                        uint8_t* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_can_move(const shatter_statblock* stats, const shatter_actor* actor,
                                                         uint8_t* out) SHATTER_NOEXCEPT;
/* Índice do ataque do inimigo (escolha ponderada, consome 1 número do rng — use o fluxo de eventos). */
SHATTER_API shatter_status SHATTER_CALL shatter_pick_attack(const shatter_db* db, const char* enemy_id,
                                                            size_t enemy_id_len, shatter_rng* rng,
                                                            int32_t* out) SHATTER_NOEXCEPT;

/* --- Poções (docs/13, item 2) --- */
/* Aplica a poção SEM cinto (pura): cura limitada à vida máxima, ou barreira nova. Altera `vitals`. */
SHATTER_API shatter_status SHATTER_CALL shatter_potion_resolve(const shatter_db* db, const char* potion_id,
                                                               size_t potion_id_len, const shatter_statblock* stats,
                                                               shatter_vitals* vitals,
                                                               shatter_potion_outcome* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_potions_create(const shatter_db* db, shatter_potions** out) SHATTER_NOEXCEPT;
/* Cinto do personagem `character_index` do save (normalizado pelo potions.csv; poção ausente entra cheia). */
SHATTER_API shatter_status SHATTER_CALL shatter_potions_from_save(const shatter_db* db, const shatter_save* save,
                                                                  size_t character_index,
                                                                  shatter_potions** out) SHATTER_NOEXCEPT;
/* Grava as cargas e a recarga de volta no save (a trava global não é salva). */
SHATTER_API shatter_status SHATTER_CALL shatter_potions_to_save(const shatter_potions* potions, shatter_save* save,
                                                                size_t character_index) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_potions_destroy(shatter_potions* potions) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_potions_tick(const shatter_db* db, shatter_potions* potions,
                                                             double dt) SHATTER_NOEXCEPT;
/* Usa a poção: confere trava e cargas, gasta 1 carga e inicia a trava; com OK aplica cura/barreira em `vitals`.
 * out->status != OK: nada mudou. */
SHATTER_API shatter_status SHATTER_CALL shatter_potions_use(const shatter_db* db, shatter_potions* potions,
                                                            const char* potion_id, size_t potion_id_len,
                                                            const shatter_statblock* stats, shatter_vitals* vitals,
                                                            shatter_potion_outcome* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_potions_refill(const shatter_db* db, shatter_potions* potions) SHATTER_NOEXCEPT;
/* +1 carga na poção refillOnEliteKill com menos cargas. *added = 0 se todas estavam cheias. */
SHATTER_API shatter_status SHATTER_CALL shatter_potions_on_elite_killed(const shatter_db* db, shatter_potions* potions,
                                                                        uint8_t* added) SHATTER_NOEXCEPT;
/* [{"potion_id","kind","charges","max_charges","recharge_remaining","hotkey_slot"}], ordem do potions.csv;
 * o objeto inclui "lockout_remaining": {"lockout_remaining":0,"slots":[...]}. */
SHATTER_API shatter_status SHATTER_CALL shatter_potions_info_json(const shatter_db* db, const shatter_potions* potions,
                                                                  uint8_t* out, size_t cap,
                                                                  size_t* needed) SHATTER_NOEXCEPT;

/* --- Esquiva (docs/13, item 1). Estado POD do chamador. --- */
SHATTER_API shatter_status SHATTER_CALL shatter_dodge_init(const shatter_db* db, shatter_dodge_state* state) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_dodge_tick(const shatter_db* db, shatter_dodge_state* state,
                                                           double dt) SHATTER_NOEXCEPT;
/* *status = SHATTER_DODGE_*; só com OK gasta a carga. */
SHATTER_API shatter_status SHATTER_CALL shatter_dodge_start(const shatter_db* db, shatter_dodge_state* state,
                                                            double resource_available,
                                                            int32_t* status) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_dodge_invulnerable(const shatter_db* db, const shatter_dodge_state* state,
                                                                   uint8_t* out) SHATTER_NOEXCEPT;
/* Recurso da esquiva perfeita se um golpe chegou durante os i-frames (senão 0). */
SHATTER_API shatter_status SHATTER_CALL shatter_dodge_perfect_reward(const shatter_db* db,
                                                                     const shatter_dodge_state* state,
                                                                     double* out) SHATTER_NOEXCEPT;

/* --- Stun, imunidades e Guarda Quebrada (docs/13, item 3). Uma shatter_actor por entidade. --- */
/* enemy_id vazio = alvo comum (herói). elite != 0: elite sorteado (imune ao stun). */
SHATTER_API shatter_status SHATTER_CALL shatter_actor_create(const shatter_db* db, const char* enemy_id,
                                                             size_t enemy_id_len, uint8_t elite,
                                                             shatter_actor** out) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_actor_destroy(shatter_actor* actor) SHATTER_NOEXCEPT;
/* Aplica um efeito no alvo (contêiner + bloco DELE). Efeito com interruptsAction vira stun real; a Guarda Quebrada
 * usa timer único e, no limite de acúmulos, atordoa alvos imunes ao stun (stagger). */
SHATTER_API shatter_status SHATTER_CALL shatter_actor_apply_effect(shatter_actor* actor, const shatter_db* db,
                                                                   const char* effect_id, size_t effect_id_len,
                                                                   const char* source, size_t source_len,
                                                                   double magnitude, shatter_effects* fx,
                                                                   shatter_statblock* target,
                                                                   shatter_actor_apply* out) SHATTER_NOEXCEPT;
/* Avança stun, stagger e imunidade. *stagger_ended = 1 quando o stagger acabou neste passo. */
SHATTER_API shatter_status SHATTER_CALL shatter_actor_tick(shatter_actor* actor, double dt, shatter_statblock* target,
                                                           uint8_t* stagger_ended) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_actor_info_get(const shatter_actor* actor,
                                                               shatter_actor_info* out) SHATTER_NOEXCEPT;

/* --- Fuga do inimigo (API 1.3; enemy_ai.csv: fleeLifeFraction, fleeSeconds, fleeOncePerLife) ---
 * A decisão é do core: o cliente NÃO compara vida com fração nem conta tempo de fuga. Chame uma vez por tick de IA do
 * inimigo (ator criado com o enemy_id dele; sem linha em enemy_ai.csv ou fração 0 = nunca foge, can_flee = 0).
 * Vida < fração x vida máx., com alvo, inicia (started = 1) e dura fleeSeconds; acaba por tempo ou sem alvo (ended = 1).
 * fleeOncePerLife: só uma fuga por vida até shatter_actor_flee_reset. Morto (dead != 0) não foge. Iniciar e acabar nunca
 * ocorrem no mesmo passo. dt >= 0 finito; life/max_life finitos. Estado é só do ator (sem rng). */
SHATTER_API shatter_status SHATTER_CALL shatter_actor_flee_step(shatter_actor* actor, double dt, double life,
                                                                double max_life, uint8_t has_target, uint8_t dead,
                                                                shatter_flee_result* out) SHATTER_NOEXCEPT;
/* Revive: zera a fuga em curso e libera o "uma vez por vida". */
SHATTER_API shatter_status SHATTER_CALL shatter_actor_flee_reset(shatter_actor* actor) SHATTER_NOEXCEPT;
/* Layout de shatter_flee_result: [tamanho, offsets de remaining, fleeing, started, ended, can_flee]. */
#define SHATTER_LAYOUT_EXT3_COUNT 6u
SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext3(uint32_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext3(const uint32_t* values, size_t n,
                                                                  shatter_error* err) SHATTER_NOEXCEPT;

/* --- Inventário, equipamento, venda e loot no chão (API 1.4; docs/16 seção 4, docs/09 seção 11) ---
 * Tudo é regra do core. Capacidades, preços e posições liberadas vêm de rules.csv (inventory_capacity, stash_capacity,
 * sell_price_*, sell_level_factor, equip_slot_*). Itens são achados por uid (uint64). Os códigos de resultado abaixo
 * voltam em *result (a função devolve OK; INVALID_ARGUMENT só para ponteiro nulo ou personagem fora da faixa).
 * Uma operação que não dá certo (resultado != OK) não muda nada. Sem RNG: mesmo estado, mesmo resultado. */
enum {
    SHATTER_INV_OK = 0, SHATTER_INV_NOT_FOUND, SHATTER_INV_FULL, SHATTER_INV_SLOT_MISMATCH, SHATTER_INV_SLOT_LOCKED,
    SHATTER_INV_SLOT_EMPTY, SHATTER_INV_UNKNOWN_CONTENT
};
enum { SHATTER_CONTAINER_BACKPACK = 0, SHATTER_CONTAINER_STASH = 1 };
enum { SHATTER_PICKUP_BACKPACK = 0, SHATTER_PICKUP_STASH = 1, SHATTER_PICKUP_FULL = 2, SHATTER_PICKUP_NOT_FOUND = 3 };
typedef struct shatter_inventory_info {
    int32_t backpack_capacity, backpack_used, stash_capacity, stash_used;
} shatter_inventory_info;
typedef struct shatter_equip_result {
    int32_t result;            /* SHATTER_INV_* */
    int32_t slot;              /* posição usada (ordem de ItemSlot; -1 se nenhuma) */
    uint64_t displaced_uid;    /* item que estava na posição e voltou para a Mochila (0 = nenhum) */
    uint8_t displaced;
    uint8_t reserved[7];
} shatter_equip_result;

SHATTER_API shatter_status SHATTER_CALL shatter_inventory_info_get(const shatter_db* db, const shatter_save* save,
                                                                   size_t character_index,
                                                                   shatter_inventory_info* out) SHATTER_NOEXCEPT;
/* Posição de equipamento liberada no protótipo? (rules.csv equip_slot_*). slot na ordem de ItemSlot (0..10). */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_slot_enabled(const shatter_db* db, int32_t slot,
                                                                       uint8_t* enabled) SHATTER_NOEXCEPT;
/* Itens do contêiner (SHATTER_CONTAINER_*) como array JSON de ItemInstance, na ordem atual. O Baú é compartilhado
 * (character_index só precisa existir). O equipamento vem em shatter_save_character_json ("equipment"). */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_list_json(const shatter_save* save, size_t character_index,
                                                                    int32_t container, uint8_t* out, size_t cap,
                                                                    size_t* needed) SHATTER_NOEXCEPT;
/* Ordena a Mochila por posição, raridade (Único primeiro), itemLevel (maior primeiro), base e uid. */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_sort(const shatter_db* db, shatter_save* save,
                                                               size_t character_index) SHATTER_NOEXCEPT;
/* Move entre Mochila e Baú (to = SHATTER_CONTAINER_*). Destino cheio = INV_FULL. */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_move(const shatter_db* db, shatter_save* save,
                                                               size_t character_index, uint64_t uid, int32_t to,
                                                               int32_t* result) SHATTER_NOEXCEPT;
/* Equipa o item da Mochila. slot = -1: posição padrão da base (anel: a primeira livre). Valida a posição (liberada e
 * compatível; ring serve em ring2). O antigo volta para a Mochila. Com `stats` (opcional, o bloco do herói), só os
 * modificadores dos itens trocados saem/entram: o resto do bloco (buffs, efeitos) fica. */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_equip(const shatter_db* db, shatter_save* save,
                                                                size_t character_index, uint64_t uid, int32_t slot,
                                                                shatter_statblock* stats,
                                                                shatter_equip_result* out) SHATTER_NOEXCEPT;
/* Desequipa para a Mochila (INV_FULL se não houver espaço; INV_SLOT_EMPTY se a posição está vazia). */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_unequip(const shatter_db* db, shatter_save* save,
                                                                  size_t character_index, int32_t slot,
                                                                  shatter_statblock* stats,
                                                                  shatter_equip_result* out) SHATTER_NOEXCEPT;
/* Comparação para o tooltip: o item `uid` (Mochila, Baú ou chão) contra o equipado em `slot` (-1 = padrão). JSON:
 * {"result":n,"slot":"head","equipped_uid":"0","is_weapon":false,"weapon_dps_before":0,"weapon_dps_after":0,
 *  "deltas":[{"stat":"armor","before":8,"after":13}]} (só os atributos que mudam). Nada é alterado. */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_compare(const shatter_db* db, const shatter_save* save,
                                                                  size_t character_index, uint64_t uid, int32_t slot,
                                                                  uint8_t* out, size_t cap,
                                                                  size_t* needed) SHATTER_NOEXCEPT;
/* Valor de venda (Ouro) do item `uid` achado na Mochila, no Baú, no chão ou equipado. Sem vendedor obrigatório. */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_sell_value(const shatter_db* db, const shatter_save* save,
                                                                     size_t character_index, uint64_t uid,
                                                                     int64_t* value) SHATTER_NOEXCEPT;
/* Vende da Mochila ou do Baú: o item some e o valor entra em currency.gold, no mesmo salvamento. Idempotente: repetir
 * o uid dá INV_NOT_FOUND e não paga de novo. Equipado não vende (desequipe antes). *gold = valor pago. */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_sell(const shatter_db* db, shatter_save* save,
                                                               size_t character_index, int32_t container, uint64_t uid,
                                                               int64_t* gold, int32_t* result) SHATTER_NOEXCEPT;
/* Destrói o item da Mochila ou do Baú. */
SHATTER_API shatter_status SHATTER_CALL shatter_inventory_discard(shatter_save* save, size_t character_index,
                                                                  int32_t container, uint64_t uid,
                                                                  int32_t* result) SHATTER_NOEXCEPT;
/* Conjunto visual (docs/04 17.4): uniques.visualSetId, depois item_bases.visualSetId, depois "vset.starter".
 * unique_id pode ser nulo/vazio. Saída: texto UTF-8 sem NUL (duas chamadas). Base inexistente: NOT_FOUND. */
SHATTER_API shatter_status SHATTER_CALL shatter_item_visual_set_id(const shatter_db* db, const char* base_id,
                                                                   size_t base_id_len, const char* unique_id,
                                                                   size_t unique_id_len, uint8_t* out, size_t cap,
                                                                   size_t* needed) SHATTER_NOEXCEPT;

/* Loot no chão. O chão NÃO é salvo (vale até sair da Cripta; o cliente chama shatter_save_ground_clear). Ouro e Lascas
 * (pilhas) entram direto no save ("ímã"); itens ficam no chão com uid. */
/* Rola a tabela como shatter_loot_roll (mesmo contexto e RNG de loot), coloca os itens no chão e devolve o mesmo JSON
 * {"items":[...],"stacks":[...],"rares_dropped":n}. Buffer pequeno: nada muda (nem rng, nem uid, nem chão). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_drop_loot(const shatter_db* db, shatter_save* save,
                                                               const char* table_id, size_t table_id_len,
                                                               const shatter_loot_context* ctx, shatter_rng* rng,
                                                               uint8_t* out, size_t cap, size_t* needed,
                                                               shatter_error* err) SHATTER_NOEXCEPT;
/* Coloca no chão um loot já rolado (ex.: saída de shatter_save_roll_boss_loot, com o Único). Pilhas entram no save. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_add_loot(shatter_save* save, const char* loot_json,
                                                                     size_t len, shatter_error* err) SHATTER_NOEXCEPT;
/* Itens no chão: {"items":[ItemInstance...]} em ordem de queda. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_list(const shatter_save* save, uint8_t* out, size_t cap,
                                                                 size_t* needed) SHATTER_NOEXCEPT;
/* Pegar: chão -> Mochila; Mochila cheia e item Único -> Baú; senão SHATTER_PICKUP_FULL e o item FICA no chão. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_pickup(const shatter_db* db, shatter_save* save,
                                                            size_t character_index, uint64_t uid,
                                                            int32_t* dest) SHATTER_NOEXCEPT;
/* Some com um item do chão (destruir) ou limpa o chão todo. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_discard(shatter_save* save, uint64_t uid,
                                                                    int32_t* result) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_save_ground_clear(shatter_save* save) SHATTER_NOEXCEPT;

/* Layout de shatter_inventory_info e shatter_equip_result: [tamanho de info, 4 offsets, tamanho de equip_result, 4 offsets]. */
#define SHATTER_LAYOUT_EXT4_COUNT 10u
SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext4(uint32_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext4(const uint32_t* values, size_t n,
                                                                  shatter_error* err) SHATTER_NOEXCEPT;

/* --- Combate básico (API 1.5; docs/18, docs/09 seção 12) ---
 * A máquina de combate básica (combo, buffer, carga, cancelamentos) roda no C# (HeroCombatLogic, docs/18 8.1). O core
 * guarda e valida os NÚMEROS (basic_kits.csv e as 7 chaves novas de rules.csv), resolve dano, efeitos, defesa e recurso. */

/* Chaves novas de rules.csv (docs/18 1.2). Tempos em s; light_windup_credit_max é fração; dash_shot_range em uu. */
typedef struct shatter_combat_rules {
    double combo_window, combo_window_after_dodge, attack_buffer, heavy_hold_threshold;
    double light_windup_credit_max, guard_lower_time, dash_shot_range;
} shatter_combat_rules;
SHATTER_API shatter_status SHATTER_CALL shatter_db_combat_rules(const shatter_db* db,
                                                                shatter_combat_rules* out) SHATTER_NOEXCEPT;

#define SHATTER_KIT_ID_SIZE 64u            /* cada ID cabe em 63 bytes + NUL (validado no carregamento) */
#define SHATTER_KIT_MAX_LIGHT_CHAIN 3u
#define SHATTER_KIT_MAX_PERFECT_EFFECTS 4u
/* Kit básico de uma classe (basic_kits.csv). Os campos de texto são IDs de conteúdo, UTF-8, terminados em NUL. */
typedef struct shatter_basic_kit {
    double heavy_charge_time;          /* s da carga depois de heavy_hold_threshold */
    double heavy_max_mult;             /* multiplicador de dano na carga máxima: 1 + (max - 1) * progresso, linear */
    double guard_arc;                  /* graus, arco TOTAL da defesa (360 = cúpula) */
    double guard_max_hold;             /* s; 0 = ilimitado */
    double guard_cooldown;             /* s de espera depois de soltar (ou de cair sozinha) */
    double guard_perfect_window;       /* s depois do aperto; 0 = sem defesa perfeita */
    double guard_perfect_cooldown;     /* s mínimos desde o último aperto para a janela abrir de novo */
    double guard_perfect_resource;     /* recurso ganho pela perfeita (substitui resourceOnBlock) */
    double guard_drain_per_damage;     /* recurso gasto por ponto de dano evitado; 0 = não gasta */
    int32_t light_chain_count;         /* 1 a 3 */
    int32_t guard_perfect_effect_count;/* 0 a 4 */
    char light_chain[3][64];           /* golpes leves em ordem; o mesmo ID pode repetir */
    char heavy_skill[64];
    char charge_effect[64];            /* reaplicado a cada tick enquanto carrega */
    char guard_effect[64];             /* reaplicado a cada tick enquanto defende; tag guard */
    char guard_perfect_effects[4][64]; /* aplicados no atacante corpo a corpo pela defesa perfeita */
} shatter_basic_kit;
/* Kit da classe. SHATTER_NOT_FOUND se a classe não existe ou não tem linha em basic_kits.csv (tabela opcional). */
SHATTER_API shatter_status SHATTER_CALL shatter_basic_kit_get(const shatter_db* db, const char* class_id,
                                                              size_t class_id_len, shatter_basic_kit* out) SHATTER_NOEXCEPT;

/* Golpe do ATAQUE FORTE carregado (docs/18 1.4). O core calcula o multiplicador com o heavy_max_mult do kit da classe:
 * 1 + (heavy_max_mult - 1) * charge_fraction (linear) e o aplica como `more` SÓ neste golpe (depois dos modificadores do
 * atacante, antes do crítico). O resto é igual a shatter_resolve_hit_db (3 números de rng, constantes do banco).
 * charge_fraction = progresso da carga, 0 (mínima) a 1 (máxima). Fora de [0, 1] ou NaN: INVALID_ARGUMENT com mensagem em
 * err, sem efeito (o rng não avança). Classe sem kit: NOT_FOUND. Não cabe campo novo em shatter_hit_input (só sobra 1
 * byte livre e o tamanho 64 é contrato): por isso função própria, com o ID da classe. */
SHATTER_API shatter_status SHATTER_CALL shatter_resolve_hit_charged(
    const shatter_db* db, const shatter_statblock* attacker, const shatter_statblock* defender,
    const shatter_hit_input* input, const char* class_id, size_t class_id_len, double charge_fraction,
    shatter_rng* rng, shatter_hit_result* out, shatter_error* err) SHATTER_NOEXCEPT;

/* Como shatter_vitals_tick, com `moving` (!= 0: o herói está andando). A regeneração do RECURSO é multiplicada por
 * regen_mult_while_moving da classe (Foco: 0,3); a vida não muda. moving = 0 é igual a shatter_vitals_tick. */
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_tick_ex(const shatter_db* db, shatter_vitals* vitals,
                                                               const shatter_statblock* stats, const char* class_id,
                                                               size_t class_id_len, double dt, uint8_t in_combat,
                                                               uint8_t moving) SHATTER_NOEXCEPT;
/* Recurso por golpe que acerta / por bloqueio, da classe (classes.csv resourceOnHit / resourceOnBlock), limitado ao máximo.
 * É a MESMA regra do simulador idle. class_id pode ser nulo/vazio (sem classe: nada). */
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_gain_on_hit(const shatter_db* db, shatter_vitals* vitals,
                                                                   const shatter_statblock* stats, const char* class_id,
                                                                   size_t class_id_len) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_vitals_gain_on_block(const shatter_db* db, shatter_vitals* vitals,
                                                                     const shatter_statblock* stats, const char* class_id,
                                                                     size_t class_id_len) SHATTER_NOEXCEPT;

/* Layout 1.5: [offsetof(shatter_hit_input, from_guard_arc),
 *              sizeof(shatter_combat_rules), 7 offsets,
 *              sizeof(shatter_basic_kit), offsets de heavy_charge_time, heavy_max_mult, guard_arc, guard_max_hold,
 *              guard_cooldown, guard_perfect_window, guard_perfect_cooldown, guard_perfect_resource,
 *              guard_drain_per_damage, light_chain_count, guard_perfect_effect_count, light_chain, heavy_skill,
 *              charge_effect, guard_effect, guard_perfect_effects]. Chamar o check na inicialização, como os outros. */
#define SHATTER_LAYOUT_EXT5_COUNT 26u
SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext5(uint32_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext5(const uint32_t* values, size_t n,
                                                                  shatter_error* err) SHATTER_NOEXCEPT;

/* --- Elite (docs/13, item 5) --- */
/* Sorteia o modificador (consome SEMPRE 1 número do rng de eventos) e devolve os multiplicadores de um elite sorteado. */
SHATTER_API shatter_status SHATTER_CALL shatter_elite_roll(const shatter_db* db, shatter_rng* events_rng,
                                                           shatter_elite_info* out) SHATTER_NOEXCEPT;
/* Elite com modificador conhecido (elite fixo: o modifierId do enemies.csv; rolled = 0). modifier_id vazio = nenhum. */
SHATTER_API shatter_status SHATTER_CALL shatter_elite_profile(const shatter_db* db, const char* modifier_id,
                                                              size_t modifier_id_len, uint8_t rolled,
                                                              shatter_elite_info* out) SHATTER_NOEXCEPT;
/* Escreve os multiplicadores no bloco do inimigo (Life/Damage/MoveSpeed/AttackSpeed More; fonte "elite") e devolve a
 * barreira inicial. Idempotente (reaplica no mesmo bloco sem multiplicar de novo). SÓ `modifier_id` e `rolled` da struct
 * valem: os multiplicadores são montados pelo banco, o chamador não os escolhe. Chame depois de shatter_statblock_for_enemy. */
SHATTER_API shatter_status SHATTER_CALL shatter_elite_apply(const shatter_db* db, const shatter_elite_info* info,
                                                            shatter_statblock* stats, double* barrier) SHATTER_NOEXCEPT;

/* --- Chefe: fases, escudo frontal, rugido, invocação e padrões por seed (docs/13, itens 4 e 6) --- */
SHATTER_API shatter_status SHATTER_CALL shatter_boss_create(const shatter_db* db, const char* enemy_id,
                                                            size_t enemy_id_len, int32_t level, uint64_t seed,
                                                            shatter_boss** out) SHATTER_NOEXCEPT;
SHATTER_API void SHATTER_CALL shatter_boss_destroy(shatter_boss* boss) SHATTER_NOEXCEPT;
/* Reinício total (morte do jogador). `stats` (opcional) perde o bônus de dano do stagger. As invocadas saem no chamador. */
SHATTER_API shatter_status SHATTER_CALL shatter_boss_reset(shatter_boss* boss, shatter_statblock* stats) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_boss_start(shatter_boss* boss) SHATTER_NOEXCEPT;
/* Passo fixo. Os eventos ficam no handle até o próximo step/apply (leia com shatter_boss_events). */
SHATTER_API shatter_status SHATTER_CALL shatter_boss_step(shatter_boss* boss, double dt,
                                                          const shatter_boss_context* ctx, shatter_statblock* stats,
                                                          size_t* event_count) SHATTER_NOEXCEPT;
/* Dano já calculado por shatter_resolve_hit_db (defender_life = life do chefe): aplica escudo frontal, rugido e limiar. */
SHATTER_API shatter_status SHATTER_CALL shatter_boss_apply_damage(shatter_boss* boss, double amount, shatter_vec2 boss_pos,
                                                                  shatter_vec2 origin,
                                                                  shatter_boss_damage* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_boss_apply_effect(shatter_boss* boss, const shatter_db* db,
                                                                  const char* effect_id, size_t effect_id_len,
                                                                  const char* source, size_t source_len,
                                                                  double magnitude, shatter_effects* fx,
                                                                  shatter_statblock* stats,
                                                                  shatter_actor_apply* out) SHATTER_NOEXCEPT;
/* A investida bateu em pilar ou parede: se o padrão em impacto tem wallStaggerSeconds > 0, o chefe entra em stagger, o padrão é
 * interrompido e o escudo cai (eventos PATTERN_INTERRUPTED, STAGGER_START, SHIELD_DOWN). *applied = 0 e nada muda fora do
 * impacto, sem wallStaggerSeconds ou se já estiver em stagger. */
SHATTER_API shatter_status SHATTER_CALL shatter_boss_wall_hit(shatter_boss* boss, shatter_statblock* stats,
                                                              uint8_t* applied) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_boss_events(const shatter_boss* boss, shatter_boss_event* out,
                                                            size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_boss_info_get(const shatter_boss* boss, shatter_boss_info* out) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_boss_shield_covers(const shatter_boss* boss, shatter_vec2 boss_pos,
                                                                   shatter_vec2 origin, uint8_t* out) SHATTER_NOEXCEPT;

/* --- Único do chefe (docs/13, item 9) --- */
SHATTER_API shatter_status SHATTER_CALL shatter_save_boss_progress_get(const shatter_save* save, size_t character_index,
                                                                       const char* enemy_id, size_t enemy_id_len,
                                                                       shatter_boss_progress* out) SHATTER_NOEXCEPT;
/* Rola o loot do chefe no modo manual com o contador do personagem (1ª vitória garantida, chance fixa, garantido no
 * pityKills) e AVANÇA o contador no save. Saída = loot no formato de shatter_loot_roll (os uids vêm do save).
 * ORDEM (RF-55): grave o save (shatter_save_write) ANTES de entregar o item com shatter_save_add_loot. Se o buffer for
 * pequeno, nada muda (nem rng, nem contador, nem uid). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_roll_boss_loot(const shatter_db* db, shatter_save* save,
                                                                    size_t character_index, const char* enemy_id,
                                                                    size_t enemy_id_len, int32_t area_level,
                                                                    shatter_rng* loot_rng, uint8_t* out, size_t cap,
                                                                    size_t* needed, shatter_error* err) SHATTER_NOEXCEPT;

/* --- Expedição confiável (docs/11, A-05 e M-03) --- */
/* Previsão com o selo de calibração. */
SHATTER_API shatter_status SHATTER_CALL shatter_expedition_forecast_ex(const shatter_db* db, const char* request_json,
                                                                       size_t len, uint64_t base_seed, int32_t samples,
                                                                       shatter_forecast_ex* out,
                                                                       shatter_error* err) SHATTER_NOEXCEPT;
/* Inicia a expedição: start_utc = max(now->now, last_seen do save) e a seed é derivada pelo core do estado do save. Os
 * campos "seed" e "start_utc" do JSON de parâmetros são PROIBIDOS (INVALID_ARGUMENT). Relógio voltando (flag
 * rollback_detected do chamador OU now < last_seen do SAVE − tolerância): *start_check = SHATTER_START_CLOCK_ROLLBACK e
 * nada muda (RF-48). Início aceito: last_seen do save sobe para o início. Prefira shatter_save_start_expedition_clock,
 * que resolve o relógio por dentro. Substitui shatter_save_start_expedition (que passa a recusar com INVALID_ARGUMENT). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_start_expedition_trusted(const shatter_db* db, shatter_save* save,
                                                                              const char* params_json, size_t len,
                                                                              const shatter_trusted_now* now,
                                                                              int32_t* start_check,
                                                                              shatter_error* err) SHATTER_NOEXCEPT;
/* Como _trusted, mas recebe o relógio cru (shatter_clock_input) e resolve o "agora" por dentro (ResolveNow com o last_seen
 * do SAVE, como a coleta): o chamador não escolhe nem o início nem a seed. */
SHATTER_API shatter_status SHATTER_CALL shatter_save_start_expedition_clock(const shatter_db* db, shatter_save* save,
                                                                            const char* params_json, size_t len,
                                                                            const shatter_clock_input* clock,
                                                                            int32_t* start_check,
                                                                            shatter_error* err) SHATTER_NOEXCEPT;
/* Coleta: o core RECALCULA o resultado pelo pedido salvo (snapshot, seed, início) e pelo relógio confiável; nada do
 * resultado vem do chamador. *collect_status = SHATTER_COLLECT_*: NOT_FINISHED (a janela ainda não acabou: nada
 * muda), ALREADY (já coletada) ou COLLECTED (itens, pilhas e XP entram no save e o status vira collected).
 * Saída = ExpeditionResult em JSON (como shatter_expedition_simulate; flags SHATTER_RESULT_RECEIPTS). Buffer pequeno:
 * nada muda. Substitui shatter_save_collect_expedition (que passa a recusar com INVALID_ARGUMENT). */
SHATTER_API shatter_status SHATTER_CALL shatter_save_collect_expedition_trusted(const shatter_db* db, shatter_save* save,
                                                                                size_t index,
                                                                                const shatter_clock_input* clock,
                                                                                uint32_t flags, int32_t* collect_status,
                                                                                uint8_t* out, size_t cap,
                                                                                size_t* needed,
                                                                                shatter_error* err) SHATTER_NOEXCEPT;

/* --- Economia do protótipo: Vendedor, Frasco de Recarga e Encantador (API 1.6; docs/16 seção 11, docs/09 seção 13) ---
 * Tudo é regra do core. Números em rules.csv (vendor_*, refill_flask_*, craft_*, reforge_*, polish_*, dismantle_*) e nas
 * tabelas craft_costs.csv e vendor_stock.csv. Ouro (currency.gold), Lascas (material.shards) e Frasco
 * (consumable.refill_flask) são pilhas do save (shatter_currency_get). Itens são achados por uid na Mochila, no Baú ou no
 * equipamento do personagem. Uma operação com resultado != OK não muda NADA (cobra e aplica juntas, ou nenhuma das duas).
 * Sorteio só no fluxo próprio Crafting (RngStream 4): semente = função pura de (craft_seed do save, uid, craft_steps do
 * item, operação); recarregar o save antes de confirmar não muda o resultado. O C# nunca calcula custo nem sorteia. */
enum {
    SHATTER_CRAFT_OK = 0, SHATTER_CRAFT_NOT_FOUND, SHATTER_CRAFT_UNIQUE, SHATTER_CRAFT_WRONG_RARITY,
    SHATTER_CRAFT_AFFIX_LIMIT, SHATTER_CRAFT_ALREADY_INSCRIBED, SHATTER_CRAFT_POLISH_MAX, SHATTER_CRAFT_NO_CANDIDATE,
    SHATTER_CRAFT_NO_GOLD, SHATTER_CRAFT_NO_SHARDS, SHATTER_CRAFT_EQUIPPED_DISMANTLE, SHATTER_CRAFT_UNKNOWN_CONTENT,
    SHATTER_CRAFT_BAD_INDEX
};
enum { SHATTER_CRAFT_OP_REFINE = 0, SHATTER_CRAFT_OP_REFORGE = 1, SHATTER_CRAFT_OP_ADD = 2, SHATTER_CRAFT_OP_POLISH = 3,
       SHATTER_CRAFT_OP_DISMANTLE = 4 };
enum {
    SHATTER_VENDOR_OK = 0, SHATTER_VENDOR_NOT_FOUND, SHATTER_VENDOR_FULL, SHATTER_VENDOR_NO_GOLD, SHATTER_VENDOR_CARRY_CAP,
    SHATTER_VENDOR_BAD_QUANTITY, SHATTER_VENDOR_UNKNOWN_CONTENT
};
enum { SHATTER_FLASK_CTX_RUN = 0, SHATTER_FLASK_CTX_ARENA = 1, SHATTER_FLASK_CTX_IDLE = 2 };
enum {
    SHATTER_FLASK_OK = 0, SHATTER_FLASK_NO_FLASK, SHATTER_FLASK_ARENA_LOCKED, SHATTER_FLASK_IDLE_FORBIDDEN,
    SHATTER_FLASK_POTIONS_FULL, SHATTER_FLASK_LOCKED_OUT, SHATTER_FLASK_UNKNOWN_CONTENT
};
typedef struct shatter_craft_result {
    int32_t result;              /* SHATTER_CRAFT_* */
    int32_t changed_affix;       /* Lapidar: afixo lapidado; Adicionar: afixo novo; Reforjar com trava: onde ficou o travado; senão -1 */
    int64_t gold_spent;          /* o que foi de fato cobrado (0 se result != OK) */
    int64_t shards_spent;
    int64_t shards_gained;       /* Desmontar */
} shatter_craft_result;
typedef struct shatter_vendor_result {
    int32_t result;              /* SHATTER_VENDOR_* */
    int32_t evicted;             /* venda: 1 = a recompra cheia expulsou o item mais antigo */
    int32_t evicted_rarity;      /* raridade do expulso (0 comum, 1 mágico, 2 raro, 3 único) */
    int32_t reserved;
    int64_t gold;                /* venda: Ouro recebido; recompra e compra: Ouro gasto */
} shatter_vendor_result;
typedef struct shatter_flask_result {
    int32_t result;              /* SHATTER_FLASK_* */
    int32_t potion_index;        /* posição da poção restaurada no cinto (ordem de potions.csv); -1 se nenhuma */
    int32_t charges_after;       /* cargas dessa poção depois */
    int32_t flasks_left;         /* frascos que sobraram */
} shatter_flask_result;

/* Saldo de uma pilha do save (Ouro, Lascas, frasco...). Id desconhecido = 0, OK. */
SHATTER_API shatter_status SHATTER_CALL shatter_currency_get(const shatter_save* save, const char* id, size_t id_len,
                                                             int64_t* amount) SHATTER_NOEXCEPT;

/* Prévia SEM custo e sem mudar nada: {"op","result","gold","shards","shards_gain","affix_count_min","affix_count_max",
 * "polish_step","polish_from","polish_to","shards_with_lock","shards_no_lock","reforges","expedition_running",
 * "have_gold","have_shards"}. result = SHATTER_CRAFT_* (NO_GOLD/NO_SHARDS trazem os custos para mostrar em vermelho).
 * `arg`: Reforjar = afixo travado (-1 nenhum); Lapidar = afixo; Adicionar = candidato (-1 aceito aqui); demais ignoram. */
SHATTER_API shatter_status SHATTER_CALL shatter_craft_quote_json(const shatter_db* db, const shatter_save* save,
                                                                 size_t character_index, uint64_t uid, int32_t op,
                                                                 int32_t arg, uint8_t* out, size_t cap,
                                                                 size_t* needed) SHATTER_NOEXCEPT;
/* Refinar: Comum vira Mágico com 1 a 2 afixos. */
SHATTER_API shatter_status SHATTER_CALL shatter_craft_refine(const shatter_db* db, shatter_save* save,
                                                             size_t character_index, uint64_t uid,
                                                             shatter_craft_result* out) SHATTER_NOEXCEPT;
/* Reforjar: sorteia de novo os afixos mantendo a quantidade; locked_affix_index = afixo travado (-1 nenhum). */
SHATTER_API shatter_status SHATTER_CALL shatter_craft_reforge(const shatter_db* db, shatter_save* save,
                                                              size_t character_index, uint64_t uid,
                                                              int32_t locked_affix_index,
                                                              shatter_craft_result* out) SHATTER_NOEXCEPT;
/* Adicionar afixo, passo 1: até add_affix_candidates candidatos {"result","gold","shards","candidates":[{"affix_id",
 * "min","max"}]}. Não altera nada; fechar e reabrir devolve os mesmos candidatos. */
SHATTER_API shatter_status SHATTER_CALL shatter_craft_add_affix_offer(const shatter_db* db, const shatter_save* save,
                                                                      size_t character_index, uint64_t uid,
                                                                      uint8_t* out, size_t cap,
                                                                      size_t* needed) SHATTER_NOEXCEPT;
/* Adicionar afixo, passo 2: escolhe o candidato (índice da oferta) e confirma. */
SHATTER_API shatter_status SHATTER_CALL shatter_craft_add_affix_apply(const shatter_db* db, shatter_save* save,
                                                                      size_t character_index, uint64_t uid,
                                                                      int32_t candidate_index,
                                                                      shatter_craft_result* out) SHATTER_NOEXCEPT;
/* Lapidar: um passo num afixo (sem sorteio). */
SHATTER_API shatter_status SHATTER_CALL shatter_craft_polish(const shatter_db* db, shatter_save* save,
                                                             size_t character_index, uint64_t uid, int32_t affix_index,
                                                             shatter_craft_result* out) SHATTER_NOEXCEPT;
/* Desmontar: o item some (Mochila ou Baú; equipado recusa) e devolve Lascas (out->shards_gained). */
SHATTER_API shatter_status SHATTER_CALL shatter_craft_dismantle(const shatter_db* db, shatter_save* save,
                                                                size_t character_index, uint64_t uid,
                                                                shatter_craft_result* out) SHATTER_NOEXCEPT;

/* Vender ao Vendedor: como shatter_inventory_sell, mas o item vai para a recompra (10 últimos). A recompra cheia expulsa
 * o mais antigo (out->evicted); a UI deve avisar antes com shatter_vendor_buyback_json (would_evict, evict_rarity). */
SHATTER_API shatter_status SHATTER_CALL shatter_vendor_sell(const shatter_db* db, shatter_save* save,
                                                            size_t character_index, int32_t container, uint64_t uid,
                                                            shatter_vendor_result* out) SHATTER_NOEXCEPT;
/* {"capacity","count","would_evict","evict_rarity","items":[{"item":ItemInstance,"paid","price"}]}, o mais recente primeiro. */
SHATTER_API shatter_status SHATTER_CALL shatter_vendor_buyback_json(const shatter_db* db, const shatter_save* save,
                                                                    uint8_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
/* Recompra o item de `uid` (idempotente: repetir dá NOT_FOUND e não cobra de novo). Cobra 1,25 x o valor pago. */
SHATTER_API shatter_status SHATTER_CALL shatter_vendor_buyback(const shatter_db* db, shatter_save* save,
                                                               size_t character_index, uint64_t uid,
                                                               shatter_vendor_result* out) SHATTER_NOEXCEPT;
/* Estoque: [{"id","ref_id","price_gold","carry_cap","owned"}]. */
SHATTER_API shatter_status SHATTER_CALL shatter_vendor_stock_json(const shatter_db* db, const shatter_save* save,
                                                                  uint8_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
/* Compra `qty` (>= 1) do estoque `stock_id`; respeita o máximo levado e o Ouro. */
SHATTER_API shatter_status SHATTER_CALL shatter_vendor_buy(const shatter_db* db, shatter_save* save,
                                                           const char* stock_id, size_t stock_id_len, int32_t qty,
                                                           shatter_vendor_result* out) SHATTER_NOEXCEPT;
/* Frasco de Recarga: restaura refill_flask_charges cargas da poção com MENOS cargas (empate: a Vida) do cinto `potions`
 * (o cinto vivo do personagem), sem passar do máximo; gasta 1 frasco do save e inicia a trava global. context =
 * SHATTER_FLASK_CTX_*: ARENA e IDLE recusam. Recusa não muda nada nem gasta o frasco. */
SHATTER_API shatter_status SHATTER_CALL shatter_flask_use(const shatter_db* db, shatter_save* save, shatter_potions* potions,
                                                          int32_t context, shatter_flask_result* out) SHATTER_NOEXCEPT;

/* Layout 1.6: [sizeof(shatter_craft_result), offsets de result, changed_affix, gold_spent, shards_spent, shards_gained,
 *              sizeof(shatter_vendor_result), offsets de result, evicted, evicted_rarity, gold,
 *              sizeof(shatter_flask_result), offsets de result, potion_index, charges_after, flasks_left]. */
#define SHATTER_LAYOUT_EXT6_COUNT 16u
SHATTER_API shatter_status SHATTER_CALL shatter_layout_info_ext6(uint32_t* out, size_t cap, size_t* needed) SHATTER_NOEXCEPT;
SHATTER_API shatter_status SHATTER_CALL shatter_layout_check_ext6(const uint32_t* values, size_t n,
                                                                  shatter_error* err) SHATTER_NOEXCEPT;

#ifdef __cplusplus
}  /* extern "C" */
#endif

#endif /* SHATTER_C_H */
