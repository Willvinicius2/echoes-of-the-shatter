using System.Collections.Generic;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// Confere o layout das structs blittable com a DLL (docs/tecnico/04_arquitetura.md, secao 9.2): monta a mesma
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

        /// <summary>Lista do layout da API 1.1 e 1.2 (kLayoutExt): 114 valores, na ordem de shatter_c.cpp (gerada do proprio kLayoutExt).</summary>
        public static uint[] BuildExt()
        {
            var v = new List<uint>(114);

            ShatterRulesExt s_shatter_rules_ext = default;
            v.Add((uint)sizeof(ShatterRulesExt));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_recharge));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_duration));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_iframes));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_distance));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_cost_resource));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_buffer));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_perfect_resource));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_cancel_recovery_fraction));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.guard_break_stagger_seconds));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.guard_break_stagger_damage_taken));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.guard_break_immunity_boss));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.guard_break_immunity_other));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.boss_shield_down_seconds));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.elite_life_mult));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.elite_damage_mult));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.elite_xp_mult));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.potion_lockout));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.out_of_combat_seconds));
            v.Add(Off(&s_shatter_rules_ext, &s_shatter_rules_ext.dodge_max_charges));
            ShatterVitals s_shatter_vitals = default;
            v.Add((uint)sizeof(ShatterVitals));
            v.Add(Off(&s_shatter_vitals, &s_shatter_vitals.life));
            v.Add(Off(&s_shatter_vitals, &s_shatter_vitals.resource));
            v.Add(Off(&s_shatter_vitals, &s_shatter_vitals.barrier));
            v.Add(Off(&s_shatter_vitals, &s_shatter_vitals.barrier_seconds_left));
            v.Add(Off(&s_shatter_vitals, &s_shatter_vitals.potion_barrier));
            ShatterActionTiming s_shatter_action_timing = default;
            v.Add((uint)sizeof(ShatterActionTiming));
            v.Add(Off(&s_shatter_action_timing, &s_shatter_action_timing.windup));
            v.Add(Off(&s_shatter_action_timing, &s_shatter_action_timing.impact));
            v.Add(Off(&s_shatter_action_timing, &s_shatter_action_timing.recovery));
            v.Add(Off(&s_shatter_action_timing, &s_shatter_action_timing.cooldown));
            v.Add(Off(&s_shatter_action_timing, &s_shatter_action_timing.cost));
            ShatterPotionOutcome s_shatter_potion_outcome = default;
            v.Add((uint)sizeof(ShatterPotionOutcome));
            v.Add(Off(&s_shatter_potion_outcome, &s_shatter_potion_outcome.heal_amount));
            v.Add(Off(&s_shatter_potion_outcome, &s_shatter_potion_outcome.barrier_amount));
            v.Add(Off(&s_shatter_potion_outcome, &s_shatter_potion_outcome.barrier_seconds));
            v.Add(Off(&s_shatter_potion_outcome, &s_shatter_potion_outcome.use_time));
            v.Add(Off(&s_shatter_potion_outcome, &s_shatter_potion_outcome.move_speed_while_using));
            v.Add(Off(&s_shatter_potion_outcome, &s_shatter_potion_outcome.lockout));
            v.Add(Off(&s_shatter_potion_outcome, &s_shatter_potion_outcome.status));
            ShatterDodgeState s_shatter_dodge_state = default;
            v.Add((uint)sizeof(ShatterDodgeState));
            v.Add(Off(&s_shatter_dodge_state, &s_shatter_dodge_state.recharge_remaining));
            v.Add(Off(&s_shatter_dodge_state, &s_shatter_dodge_state.elapsed));
            v.Add(Off(&s_shatter_dodge_state, &s_shatter_dodge_state.charges));
            v.Add(Off(&s_shatter_dodge_state, &s_shatter_dodge_state.active));
            ShatterActorApply s_shatter_actor_apply = default;
            v.Add((uint)sizeof(ShatterActorApply));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.stun_seconds));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.stagger_seconds));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.guard_break_stacks));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.applied));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.stunned));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.stun_blocked));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.interrupted));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.staggered));
            v.Add(Off(&s_shatter_actor_apply, &s_shatter_actor_apply.remove_barrier));
            ShatterActorInfo s_shatter_actor_info = default;
            v.Add((uint)sizeof(ShatterActorInfo));
            v.Add(Off(&s_shatter_actor_info, &s_shatter_actor_info.stun_remaining));
            v.Add(Off(&s_shatter_actor_info, &s_shatter_actor_info.stagger_remaining));
            v.Add(Off(&s_shatter_actor_info, &s_shatter_actor_info.immunity_remaining));
            v.Add(Off(&s_shatter_actor_info, &s_shatter_actor_info.can_act));
            v.Add(Off(&s_shatter_actor_info, &s_shatter_actor_info.stun_immune));
            ShatterEliteInfo s_shatter_elite_info = default;
            v.Add((uint)sizeof(ShatterEliteInfo));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.life_mult));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.damage_mult));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.xp_mult));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.barrier_fraction_of_life));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.move_speed_mult));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.attack_speed_mult));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.recovery_mult));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.death_explosion_radius));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.death_explosion_damage));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.death_explosion_fuse));
            v.Add(Off(&s_shatter_elite_info, s_shatter_elite_info.modifier_id));
            v.Add(Off(&s_shatter_elite_info, &s_shatter_elite_info.rolled));
            ShatterVec2 s_shatter_vec2 = default;
            v.Add((uint)sizeof(ShatterVec2));
            v.Add(Off(&s_shatter_vec2, &s_shatter_vec2.x));
            v.Add(Off(&s_shatter_vec2, &s_shatter_vec2.z));
            ShatterBossContext s_shatter_boss_context = default;
            v.Add((uint)sizeof(ShatterBossContext));
            v.Add(Off(&s_shatter_boss_context, &s_shatter_boss_context.boss));
            v.Add(Off(&s_shatter_boss_context, &s_shatter_boss_context.player));
            ShatterBossEvent s_shatter_boss_event = default;
            v.Add((uint)sizeof(ShatterBossEvent));
            v.Add(Off(&s_shatter_boss_event, &s_shatter_boss_event.seconds));
            v.Add(Off(&s_shatter_boss_event, &s_shatter_boss_event.kind));
            v.Add(Off(&s_shatter_boss_event, &s_shatter_boss_event.phase));
            v.Add(Off(&s_shatter_boss_event, &s_shatter_boss_event.count));
            v.Add(Off(&s_shatter_boss_event, s_shatter_boss_event.pattern_id));
            v.Add(Off(&s_shatter_boss_event, s_shatter_boss_event.skill_id));
            v.Add(Off(&s_shatter_boss_event, s_shatter_boss_event.enemy_id));
            ShatterBossInfo s_shatter_boss_info = default;
            v.Add((uint)sizeof(ShatterBossInfo));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.life));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.max_life));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.shield_down_remaining));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.turn_rate_deg_per_sec));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.facing_x));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.facing_z));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.stagger_remaining));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.stun_remaining));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.phase));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.state));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.shield_up));
            v.Add(Off(&s_shatter_boss_info, &s_shatter_boss_info.invulnerable));
            ShatterBossDamage s_shatter_boss_damage = default;
            v.Add((uint)sizeof(ShatterBossDamage));
            v.Add(Off(&s_shatter_boss_damage, &s_shatter_boss_damage.applied));
            v.Add(Off(&s_shatter_boss_damage, &s_shatter_boss_damage.life_after));
            v.Add(Off(&s_shatter_boss_damage, &s_shatter_boss_damage.shield_blocked));
            v.Add(Off(&s_shatter_boss_damage, &s_shatter_boss_damage.invulnerable));
            v.Add(Off(&s_shatter_boss_damage, &s_shatter_boss_damage.clamped_by_phase));
            v.Add(Off(&s_shatter_boss_damage, &s_shatter_boss_damage.killed));
            ShatterBossProgress s_shatter_boss_progress = default;
            v.Add((uint)sizeof(ShatterBossProgress));
            v.Add(Off(&s_shatter_boss_progress, &s_shatter_boss_progress.kills));
            v.Add(Off(&s_shatter_boss_progress, &s_shatter_boss_progress.kills_since_unique));
            ShatterForecastEx s_shatter_forecast_ex = default;
            v.Add((uint)sizeof(ShatterForecastEx));
            v.Add(Off(&s_shatter_forecast_ex, &s_shatter_forecast_ex.baseForecast));
            v.Add(Off(&s_shatter_forecast_ex, &s_shatter_forecast_ex.calibration));

            return v.ToArray();
        }

        /// <summary>Lista do layout ext2 (rodada 2): 3 valores.</summary>
        public static uint[] BuildExt2()
        {
            ShatterRulesExt2 r = default;
            return new[] { (uint)sizeof(ShatterRulesExt2), Off(&r, &r.unarmed_weapon_damage_physical), Off(&r, &r.require_on_screen_margin) };
        }

        /// <summary>Lista do layout ext3 (API 1.3, fuga): tamanho de shatter_flee_result e os offsets de remaining, fleeing, started, ended, can_flee.</summary>
        public static uint[] BuildExt3()
        {
            ShatterFleeResult r = default;
            return new[] { (uint)sizeof(ShatterFleeResult), Off(&r, &r.remaining), Off(&r, &r.fleeing), Off(&r, &r.started), Off(&r, &r.ended), Off(&r, &r.can_flee) };
        }

        /// <summary>Lista do layout ext4 (API 1.4, inventario): [tamanho de shatter_inventory_info, 4 offsets, tamanho de shatter_equip_result, 4 offsets].</summary>
        public static uint[] BuildExt4()
        {
            ShatterInventoryInfo i = default;
            ShatterEquipResult e = default;
            return new[]
            {
                (uint)sizeof(ShatterInventoryInfo), Off(&i, &i.backpack_capacity), Off(&i, &i.backpack_used), Off(&i, &i.stash_capacity), Off(&i, &i.stash_used),
                (uint)sizeof(ShatterEquipResult), Off(&e, &e.result), Off(&e, &e.slot), Off(&e, &e.displaced_uid), Off(&e, &e.displaced),
            };
        }

        /// <summary>
        /// Lista do layout ext5 (API 1.5, combate basico): [offset de from_guard_arc em shatter_hit_input; tamanho de shatter_combat_rules e 7 offsets;
        /// tamanho de shatter_basic_kit, os offsets dos 9 doubles, light_chain_count, guard_perfect_effect_count, light_chain, heavy_skill,
        /// charge_effect, guard_effect e guard_perfect_effects] = 26 valores.
        /// </summary>
        public static uint[] BuildExt5()
        {
            ShatterHitInput h = default;
            ShatterCombatRules c = default;
            ShatterBasicKit k = default;
            return new[]
            {
                Off(&h, &h.from_guard_arc),
                (uint)sizeof(ShatterCombatRules), Off(&c, &c.combo_window), Off(&c, &c.combo_window_after_dodge), Off(&c, &c.attack_buffer),
                Off(&c, &c.heavy_hold_threshold), Off(&c, &c.light_windup_credit_max), Off(&c, &c.guard_lower_time), Off(&c, &c.dash_shot_range),
                (uint)sizeof(ShatterBasicKit), Off(&k, &k.heavy_charge_time), Off(&k, &k.heavy_max_mult), Off(&k, &k.guard_arc), Off(&k, &k.guard_max_hold),
                Off(&k, &k.guard_cooldown), Off(&k, &k.guard_perfect_window), Off(&k, &k.guard_perfect_cooldown), Off(&k, &k.guard_perfect_resource),
                Off(&k, &k.guard_drain_per_damage), Off(&k, &k.light_chain_count), Off(&k, &k.guard_perfect_effect_count), Off(&k, k.light_chain),
                Off(&k, k.heavy_skill), Off(&k, k.charge_effect), Off(&k, k.guard_effect), Off(&k, k.guard_perfect_effects),
            };
        }

        /// <summary>
        /// Lista do layout ext6 (API 1.6, economia): [tamanho de shatter_craft_result e offsets de result, changed_affix, gold_spent, shards_spent,
        /// shards_gained; tamanho de shatter_vendor_result e offsets de result, evicted, evicted_rarity, gold; tamanho de shatter_flask_result e
        /// offsets de result, potion_index, charges_after, flasks_left] = 16 valores.
        /// </summary>
        public static uint[] BuildExt6()
        {
            ShatterCraftResult c = default;
            ShatterVendorResult v = default;
            ShatterFlaskResult f = default;
            return new[]
            {
                (uint)sizeof(ShatterCraftResult), Off(&c, &c.result), Off(&c, &c.changed_affix), Off(&c, &c.gold_spent), Off(&c, &c.shards_spent), Off(&c, &c.shards_gained),
                (uint)sizeof(ShatterVendorResult), Off(&v, &v.result), Off(&v, &v.evicted), Off(&v, &v.evicted_rarity), Off(&v, &v.gold),
                (uint)sizeof(ShatterFlaskResult), Off(&f, &f.result), Off(&f, &f.potion_index), Off(&f, &f.charges_after), Off(&f, &f.flasks_left),
            };
        }

        public static bool CheckExt6(out string message)
        {
            var values = BuildExt6();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext6(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext6 status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }

        /// <summary>
        /// Lista do layout ext7 (API 1.7, core da Cripta): [tamanho de shatter_xp_info e offsets de awarded, xp_in_level, xp_to_next, level_before, level,
        /// level_cap, reserved; tamanho de shatter_fervor_info e offsets de xp_mult, gold_mat_mult, rare_mult, xp_bonus, gold_mat_bonus, rare_bonus] = 15 valores.
        /// </summary>
        public static uint[] BuildExt7()
        {
            ShatterXpInfo x = default;
            ShatterFervorInfo f = default;
            return new[]
            {
                (uint)sizeof(ShatterXpInfo), Off(&x, &x.awarded), Off(&x, &x.xp_in_level), Off(&x, &x.xp_to_next), Off(&x, &x.level_before), Off(&x, &x.level),
                Off(&x, &x.level_cap), Off(&x, &x.reserved),
                (uint)sizeof(ShatterFervorInfo), Off(&f, &f.xp_mult), Off(&f, &f.gold_mat_mult), Off(&f, &f.rare_mult), Off(&f, &f.xp_bonus), Off(&f, &f.gold_mat_bonus),
                Off(&f, &f.rare_bonus),
            };
        }

        public static bool CheckExt7(out string message)
        {
            var values = BuildExt7();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext7(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext7 status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }

        /// <summary>Lista do layout ext8 (API 1.7, movimento do herói): [tamanho de shatter_hero_move_rules, offset de accel_seconds, offset de decel_seconds].</summary>
        public static uint[] BuildExt8()
        {
            ShatterHeroMoveRules m = default;
            return new[] { (uint)sizeof(ShatterHeroMoveRules), Off(&m, &m.accel_seconds), Off(&m, &m.decel_seconds) };
        }

        public static bool CheckExt8(out string message)
        {
            var values = BuildExt8();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext8(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext8 status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }

        public static bool CheckExt5(out string message)
        {
            var values = BuildExt5();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext5(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext5 status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }

        public static bool CheckExt4(out string message)
        {
            var values = BuildExt4();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext4(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext4 status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }

        public static bool CheckExt3(out string message)
        {
            var values = BuildExt3();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext3(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext3 status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
        }

        public static bool CheckExt2(out string message)
        {
            var values = BuildExt2();
            ShatterError err = default;
            int status;
            fixed (uint* p = values) status = ShatterNative.shatter_layout_check_ext2(p, (nuint)values.Length, &err);
            if (status == 0)
            {
                message = string.Empty;
                return true;
            }
            message = $"shatter_layout_check_ext2 status {status}: {NativeBuffers.ErrorMessage(ref err)}";
            return false;
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
