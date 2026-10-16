using System.Collections.Generic;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// Confere o layout das structs blittable com a DLL (docs/04_arquitetura.md, secao 9.2): monta a mesma
    /// lista de <c>kLayout</c> (shatter_c.cpp) — para cada struct, sizeof e depois offsetof dos campos,
    /// na ordem fixa — e chama <c>shatter_layout_check</c>.
    /// </summary>
    internal static unsafe class NativeLayout
    {
        static uint Off(void* origin, void* field) => (uint)((byte*)field - (byte*)origin);

        public static uint[] Build()
        {
            var v = new List<uint>(82);

            ShatterError error = default;
            v.Add((uint)sizeof(ShatterError));
            v.Add(Off(&error, &error.code));
            v.Add(Off(&error, &error.line));
            v.Add(Off(&error, error.message));

            ShatterRng rng = default;
            v.Add((uint)sizeof(ShatterRng));
            v.Add(Off(&rng, &rng.state));
            v.Add(Off(&rng, &rng.inc));

            ShatterRules rules = default;
            v.Add((uint)sizeof(ShatterRules));
            v.Add(Off(&rules, &rules.crit_multiplier_base));
            v.Add(Off(&rules, &rules.max_ai_rules));
            v.Add(Off(&rules, &rules.sim_fast_enabled));

            ShatterModifier mod = default;
            v.Add((uint)sizeof(ShatterModifier));
            v.Add(Off(&mod, &mod.value));
            v.Add(Off(&mod, &mod.required_tags));
            v.Add(Off(&mod, &mod.stat));
            v.Add(Off(&mod, &mod.kind));

            ShatterHitInput hin = default;
            v.Add((uint)sizeof(ShatterHitInput));
            v.Add(Off(&hin, hin.base_damage));
            v.Add(Off(&hin, &hin.coefficient));
            v.Add(Off(&hin, &hin.defender_life));
            v.Add(Off(&hin, &hin.defender_barrier));
            v.Add(Off(&hin, &hin.skill_tags));
            v.Add(Off(&hin, &hin.is_damage_over_time));
            v.Add(Off(&hin, &hin.can_be_blocked));

            ShatterHitResult hr = default;
            v.Add((uint)sizeof(ShatterHitResult));
            v.Add(Off(&hr, hr.after_modifiers));
            v.Add(Off(&hr, hr.after_mitigation));
            v.Add(Off(&hr, &hr.total_damage));
            v.Add(Off(&hr, &hr.absorbed_by_barrier));
            v.Add(Off(&hr, &hr.life_lost));
            v.Add(Off(&hr, &hr.defender_life_after));
            v.Add(Off(&hr, &hr.defender_barrier_after));
            v.Add(Off(&hr, &hr.outcome));
            v.Add(Off(&hr, &hr.critical));
            v.Add(Off(&hr, &hr.landed));
            v.Add(Off(&hr, &hr.killed));

            ShatterEffectEvent ev = default;
            v.Add((uint)sizeof(ShatterEffectEvent));
            v.Add(Off(&ev, &ev.kind));
            v.Add(Off(&ev, &ev.effect_id_len));
            v.Add(Off(&ev, ev.damage));
            v.Add(Off(&ev, ev.effect_id));

            ShatterClockInput ci = default;
            v.Add((uint)sizeof(ShatterClockInput));
            v.Add(Off(&ci, &ci.local_now_utc));
            v.Add(Off(&ci, &ci.steam_now_utc));
            v.Add(Off(&ci, &ci.last_seen_utc));
            v.Add(Off(&ci, &ci.has_steam_time));

            ShatterTrustedNow tn = default;
            v.Add((uint)sizeof(ShatterTrustedNow));
            v.Add(Off(&tn, &tn.now));
            v.Add(Off(&tn, &tn.used_steam));
            v.Add(Off(&tn, &tn.rollback_detected));

            ShatterOfflineWindow ow = default;
            v.Add((uint)sizeof(ShatterOfflineWindow));
            v.Add(Off(&ow, &ow.effective_seconds));
            v.Add(Off(&ow, &ow.finished));
            v.Add(Off(&ow, &ow.ended_by_rollback));

            ShatterLootContext lc = default;
            v.Add((uint)sizeof(ShatterLootContext));
            v.Add(Off(&lc, &lc.quantity_mult));
            v.Add(Off(&lc, &lc.mode));
            v.Add(Off(&lc, &lc.area_level));
            v.Add(Off(&lc, &lc.rares_already_dropped));
            v.Add(Off(&lc, &lc.max_rares));

            ShatterLoadReport lr = default;
            v.Add((uint)sizeof(ShatterLoadReport));
            v.Add(Off(&lr, &lr.status));
            v.Add(Off(&lr, &lr.used_backup));

            ShatterSaveSummary ss = default;
            v.Add((uint)sizeof(ShatterSaveSummary));
            v.Add(Off(&ss, &ss.next_item_uid));
            v.Add(Off(&ss, &ss.last_seen_utc));
            v.Add(Off(&ss, &ss.last_rest_day));
            v.Add(Off(&ss, &ss.content_version));
            v.Add(Off(&ss, &ss.save_version));
            v.Add(Off(&ss, &ss.character_count));
            v.Add(Off(&ss, &ss.marker_charges));
            v.Add(Off(&ss, &ss.expedition_slots));
            v.Add(Off(&ss, &ss.expedition_count));
            v.Add(Off(&ss, &ss.running_expedition));

            ShatterAreaRunReward ar = default;
            v.Add((uint)sizeof(ShatterAreaRunReward));
            v.Add(Off(&ar, &ar.charges_gained));
            v.Add(Off(&ar, &ar.new_conquest));

            ShatterForecast fc = default;
            v.Add((uint)sizeof(ShatterForecast));
            v.Add(Off(&fc, &fc.xp_p10));
            v.Add(Off(&fc, &fc.gold_p10));
            v.Add(Off(&fc, &fc.retreat_probability));
            v.Add(Off(&fc, &fc.worst_resist_gap));

            return v.ToArray();
        }

        /// <summary>Lista do layout da API 1.1 (kLayoutExt): 37 valores, na ordem de shatter_c.cpp.</summary>
        public static uint[] BuildExt()
        {
            var v = new List<uint>(37);

            ShatterRulesExt re = default;
            v.Add((uint)sizeof(ShatterRulesExt));
            v.Add(Off(&re, &re.guard_break_stagger_seconds));
            v.Add(Off(&re, &re.potion_lockout));
            v.Add(Off(&re, &re.dodge_max_charges));

            ShatterVitals vi = default;
            v.Add((uint)sizeof(ShatterVitals));
            v.Add(Off(&vi, &vi.barrier_seconds_left));

            ShatterActionTiming at = default;
            v.Add((uint)sizeof(ShatterActionTiming));
            v.Add(Off(&at, &at.cost));

            ShatterPotionOutcome po = default;
            v.Add((uint)sizeof(ShatterPotionOutcome));
            v.Add(Off(&po, &po.status));

            ShatterDodgeState ds = default;
            v.Add((uint)sizeof(ShatterDodgeState));
            v.Add(Off(&ds, &ds.charges));
            v.Add(Off(&ds, &ds.active));

            ShatterActorApply aa = default;
            v.Add((uint)sizeof(ShatterActorApply));
            v.Add(Off(&aa, &aa.guard_break_stacks));
            v.Add(Off(&aa, &aa.applied));
            v.Add(Off(&aa, &aa.remove_barrier));

            ShatterActorInfo ai = default;
            v.Add((uint)sizeof(ShatterActorInfo));
            v.Add(Off(&ai, &ai.can_act));

            ShatterEliteInfo ei = default;
            v.Add((uint)sizeof(ShatterEliteInfo));
            v.Add(Off(&ei, ei.modifier_id));
            v.Add(Off(&ei, &ei.rolled));

            v.Add((uint)sizeof(ShatterVec2));
            v.Add((uint)sizeof(ShatterBossContext));

            ShatterBossEvent be = default;
            v.Add((uint)sizeof(ShatterBossEvent));
            v.Add(Off(&be, &be.kind));
            v.Add(Off(&be, be.pattern_id));
            v.Add(Off(&be, be.skill_id));
            v.Add(Off(&be, be.enemy_id));

            ShatterBossInfo bi = default;
            v.Add((uint)sizeof(ShatterBossInfo));
            v.Add(Off(&bi, &bi.phase));
            v.Add(Off(&bi, &bi.shield_up));

            ShatterBossDamage bd = default;
            v.Add((uint)sizeof(ShatterBossDamage));
            v.Add(Off(&bd, &bd.shield_blocked));

            v.Add((uint)sizeof(ShatterBossProgress));

            ShatterForecastEx fe = default;
            v.Add((uint)sizeof(ShatterForecastEx));
            v.Add(Off(&fe, &fe.calibration));

            return v.ToArray();
        }

        /// <summary>Confere o layout 1.1 com <c>shatter_layout_check_ext</c>.</summary>
        public static bool CheckExt(out string message)
        {
            var values = BuildExt();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }

        /// <summary>OK se tamanhos e offsets batem; senao a mensagem diz o primeiro que difere.</summary>
        public static bool Check(out string message)
        {
            var values = Build();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }
    }
}
