using System.Runtime.InteropServices;

namespace Echoes.Interop.Native
{
    // Espelho blittable das structs de ShatterCore/include/shatter/shatter_c.h (API C v1).
    // Layout conferido na inicializacao por NativeLayout contra shatter_layout_check.
    // Os campos usam o nome do header de proposito (a conferencia de layout le na mesma ordem).

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterError
    {
        public int code;
        public int line;
        public fixed byte message[256];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterRng
    {
        public ulong state;
        public ulong inc;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterRules
    {
        public double crit_multiplier_base, evasion_cap, block_cap, block_mitigation, resist_cap, resist_floor;
        public double armor_damage_factor, armor_max_reduction, trigger_icd_min, cooldown_min, realtime_step;
        public double sim_step, sim_step_fast, max_offline_hours, max_expedition_hours, min_expedition_hours;
        public double ai_base_dodge, retreat_life_fraction, vigor_h1_4, vigor_h5_8, vigor_h9_12, vigor_band_hours;
        public double fervor_xp_mult, fervor_gold_mat_mult, fervor_rare_mult;
        public double clock_rollback_tolerance_s, steam_clock_max_skew_s, xp_base, xp_scale, xp_exponent;
        public int max_ai_rules, max_rares_per_expedition, xp_cap_levels_above_area;
        public int charges_max, charges_per_hour, charges_clear_area, charges_boss, charges_new_area, charges_daily_rest;
        public int max_level;
        public byte sim_fast_enabled;
        public fixed byte reserved[7];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterModifier
    {
        public double value;
        public uint required_tags;
        public ushort stat;
        public byte kind;
        public byte reserved;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterHitInput
    {
        public fixed double base_damage[4];
        public double coefficient;
        public double defender_life;
        public double defender_barrier;
        public uint skill_tags;
        public byte is_damage_over_time;
        public byte can_be_blocked;
        public fixed byte reserved[2];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterHitResult
    {
        public fixed double after_modifiers[4];
        public fixed double after_mitigation[4];
        public double total_damage;
        public double absorbed_by_barrier;
        public double life_lost;
        public double defender_life_after;
        public double defender_barrier_after;
        public byte outcome;
        public byte critical;
        public byte landed;
        public byte killed;
        public fixed byte reserved[4];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterEffectEvent
    {
        public uint kind;
        public uint effect_id_len;
        public fixed double damage[4];
        public fixed byte effect_id[128];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterClockInput
    {
        public long local_now_utc;
        public long steam_now_utc;
        public long last_seen_utc;
        public byte has_steam_time;
        public fixed byte reserved[7];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterTrustedNow
    {
        public long now;
        public byte used_steam;
        public byte rollback_detected;
        public fixed byte reserved[6];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterOfflineWindow
    {
        public double effective_seconds;
        public byte finished;
        public byte ended_by_rollback;
        public fixed byte reserved[6];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterLootContext
    {
        public double quantity_mult;
        public int mode;
        public int area_level;
        public int rares_already_dropped;
        public int max_rares;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterLoadReport
    {
        public int status;
        public int used_backup;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterSaveSummary
    {
        public ulong next_item_uid;
        public long last_seen_utc;
        public long last_rest_day;
        public uint content_version;
        public int save_version;
        public int character_count;
        public int marker_charges;
        public int expedition_slots;
        public int expedition_count;
        public int running_expedition;
        public int reserved;
    }

    [StructLayout(LayoutKind.Sequential)]
    internal unsafe struct ShatterAreaRunReward
    {
        public int charges_gained;
        public byte new_conquest;
        public fixed byte reserved[3];
    }

    [StructLayout(LayoutKind.Sequential)]
    internal struct ShatterForecast
    {
        public double xp_p10, xp_p50, xp_p90;
        public double gold_p10, gold_p50, gold_p90;
        public double retreat_probability;
        public int worst_resist_gap;
        public int reserved;
    }
}
