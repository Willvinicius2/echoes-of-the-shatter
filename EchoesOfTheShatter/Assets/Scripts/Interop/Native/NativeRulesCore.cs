using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// <see cref="IRulesCore"/> sobre a DLL <c>shattercore</c> (API C 1.1, shatter_c.h): P/Invoke, SafeHandle e o
    /// padrao de duas chamadas para buffers (docs/04_arquitetura.md, secao 9).
    ///
    /// Roda NATIVO: carga e validacao do conteudo, versao do conteudo, constantes de regra (rules.csv e as chaves novas por
    /// <c>shatter_db_rules_ext</c>: esquiva, buffer, trava de pocao, fora de combate), atributos (heroi, inimigo, vazio),
    /// golpe e recarga lendo as constantes do BANCO (<c>_db</c>, A-06), vida/recurso/barreira, tempos de acao, custo,
    /// velocidade de movimento, CanAct/CanMove (com o <c>shatter_actor</c>), PickAttack, pocoes (<c>shatter_potion_resolve</c>),
    /// RNG por fluxo e efeitos (stun e Guarda Quebrada pelo actor). Tambem expoe, alem do IRulesCore, o cinto de pocoes, a
    /// esquiva, o elite e o chefe nativos (<see cref="CreatePotionBelt"/>, <see cref="CreateDodge"/>, <see cref="RollElite"/>,
    /// <see cref="CreateBoss"/>).
    ///
    /// Segue no STUB (<see cref="StillInStub"/>) so o que o core ainda nao tem. O stub e carregado junto, dos mesmos CSV.
    /// </summary>
    public sealed partial class NativeRulesCore : IRulesCore
    {
        public const string Name = "shattercore-native";

        /// <summary>O que a API C 1.3 ainda nao entrega e continua no <see cref="StubRulesCore"/> (lista para o log e o relatorio). Save, expedicao e fuga ja sao nativos.</summary>
        public static readonly IReadOnlyList<string> StillInStub = new[]
        {
            "Registros de conteudo tipados (FindClass/FindSkill/FindEnemy/FindItemBase/FindPotion, Potions, ClassInfo/EnemyInfo/SkillInfo/PotionInfo): a API so devolve JSON por ID (shatter_db_lookup_json), sem listas tipadas",
            "NextBelow e NextUnit: a API so tem shatter_rng_next_u32, sem o sorteio limitado nem o unitario",
            "Tags dos efeitos nos eventos de dano de DoT (o evento nativo nao traz tags; vem do conteudo do stub)",
            "Sequenciamento de fases do ataque comum (EnemyBrainLogic: Idle/Chase/Telegraph/Attack/Recover) e da ação do herói (ActionTimeline): o C# so avança as fases com os tempos do core; chefe usa o shatter_boss",
        };

        // Registro dos nucleos vivos (A-06): o editor/jogo descarta todos ao sair do Play, recarregar o dominio ou fechar,
        // mesmo com "Enter Play Mode Options" (sem recarga de dominio), em que nenhum static pode guardar handle entre sessoes.
        static readonly object LiveLock = new object();
        static readonly List<WeakReference<NativeRulesCore>> Live = new List<WeakReference<NativeRulesCore>>();

        /// <summary>Quantos nucleos nativos ainda nao foram descartados.</summary>
        public static int LiveCount
        {
            get
            {
                lock (LiveLock)
                {
                    PruneLive();
                    return Live.Count;
                }
            }
        }

        /// <summary>Descarta todos os nucleos nativos vivos (saida do Play, antes da recarga de dominio, ao fechar).</summary>
        public static void DisposeAllLive()
        {
            List<NativeRulesCore> victims = new List<NativeRulesCore>();
            lock (LiveLock)
            {
                foreach (var weak in Live)
                {
                    if (weak.TryGetTarget(out var core)) victims.Add(core);
                }
                Live.Clear();
            }
            foreach (var core in victims) core.Dispose();
        }

        static void PruneLive()
        {
            Live.RemoveAll(w => !w.TryGetTarget(out var c) || c.disposed);
        }

        readonly StubRulesCore stub = new StubRulesCore();
        bool disposed;
        DbHandle db;
        ShatterRules rules;
        bool rulesLoaded;
        uint apiVersion;
        ShatterRulesExt rulesExt;
        // Kits basicos por classe (basic_kits.csv), lidos do core na carga. Classe sem kit nao tem entrada.
        readonly Dictionary<string, BasicKitInfo> kits = new Dictionary<string, BasicKitInfo>(StringComparer.Ordinal);

        NativeRulesCore(uint apiVersion)
        {
            this.apiVersion = apiVersion;
            lock (LiveLock)
            {
                PruneLive();
                Live.Add(new WeakReference<NativeRulesCore>(this));
            }
        }

        /// <summary>
        /// Confere a DLL (carga, <c>shatter_api_version</c> e <c>shatter_layout_check</c>) sem lancar excecao.
        /// Em falha, <paramref name="reason"/> diz por que (para o aviso no Console).
        /// </summary>
        public static bool TryCreate(out NativeRulesCore core, out string reason)
        {
            core = null;
            try
            {
                var version = ShatterNative.shatter_api_version();
                if (version != ShatterNative.ExpectedApiVersion)
                {
                    reason = $"shattercore.dll tem API v{version}, o C# espera v{ShatterNative.ExpectedApiVersion}";
                    return false;
                }
                if (!NativeLayout.Check(out var layoutMessage))
                {
                    reason = "layout das structs diverge da DLL: " + layoutMessage;
                    return false;
                }
                var minor = ShatterNative.shatter_api_minor();
                if (minor < ShatterNative.ExpectedApiMinor)
                {
                    reason = $"shattercore.dll tem API 1.{minor}, o C# espera 1.{ShatterNative.ExpectedApiMinor} (combate basico: kits de classe, chaves do combo, defesa com arco, pierce, regen em movimento; fuga do inimigo, vitals com potion_barrier, relogio no inicio da expedicao, layout 114 valores)";
                    return false;
                }
                if (!NativeLayout.CheckExt(out var extMessage))
                {
                    reason = "layout 1.1 das structs diverge da DLL: " + extMessage;
                    return false;
                }
                if (!NativeLayout.CheckExt2(out var ext2Message))
                {
                    reason = "layout ext2 (rodada 2) das structs diverge da DLL: " + ext2Message;
                    return false;
                }
                if (!NativeLayout.CheckExt4(out var ext4Message))
                {
                    reason = "layout ext4 (inventario) das structs diverge da DLL: " + ext4Message;
                    return false;
                }
                if (!NativeLayout.CheckExt3(out var ext3Message))
                {
                    reason = "layout ext3 (fuga) das structs diverge da DLL: " + ext3Message;
                    return false;
                }
                if (!NativeLayout.CheckExt5(out var ext5Message))
                {
                    reason = "layout ext5 (combate basico) das structs diverge da DLL: " + ext5Message;
                    return false;
                }
                core = new NativeRulesCore(version);
                reason = string.Empty;
                return true;
            }
            catch (DllNotFoundException e)
            {
                reason = "shattercore.dll nao carregou (ausente, ponteiro do Git LFS ou nao e x64): " + e.Message;
            }
            catch (EntryPointNotFoundException e)
            {
                reason = "shattercore.dll sem um simbolo esperado (DLL de outra versao): " + e.Message;
            }
            catch (BadImageFormatException e)
            {
                reason = "shattercore.dll com formato invalido (nao e x64?): " + e.Message;
            }
            catch (Exception e)
            {
                reason = "falha ao inicializar a shattercore.dll: " + e.Message;
            }
            return false;
        }

        // --- Estado e carga ------------------------------------------------------------------------------

        public uint ApiVersion => apiVersion;
        public string ImplementationName => Name;
        public bool IsProvisional => false;
        public bool IsLoaded => db != null && !db.IsInvalid && stub.IsLoaded;
        // Constantes de combate vem da DLL (rules_ext), nao dos valores provisorios do stub: nada a avisar.
        public IReadOnlyList<string> LoadWarnings => Array.Empty<string>();
        public CombatRules Combat => stub.Combat;
        public IReadOnlyList<PotionInfo> Potions => stub.Potions;

        public unsafe uint ContentVersion
        {
            get
            {
                var handle = RequireDb();
                var addRef = false;
                try
                {
                    handle.DangerousAddRef(ref addRef);
                    uint version;
                    NativeCallException.ThrowIfFailed("shatter_db_content_version", ShatterNative.shatter_db_content_version(handle.DangerousGetHandle(), &version));
                    return version;
                }
                finally
                {
                    if (addRef) handle.DangerousRelease();
                }
            }
        }

        public unsafe RulesStatus LoadContent(string dataDirectory, List<RulesError> errors)
        {
            if (errors == null) throw new ArgumentNullException(nameof(errors));
            if (string.IsNullOrEmpty(dataDirectory))
            {
                errors.Add(new RulesError(RulesStatus.InvalidArgument, string.Empty, 0, "data directory is empty"));
                return RulesStatus.InvalidArgument;
            }

            db?.Dispose();
            db = null;
            rulesLoaded = false;
            kits.Clear();

            var path = NativeBuffers.Utf8(dataDirectory);
            IntPtr raw = IntPtr.Zero;
            ShatterError err = default;
            int status;
            fixed (byte* p = path) status = ShatterNative.shatter_db_load_directory(p, (nuint)path.Length, &raw, &err);

            // A API devolve sempre um handle (mesmo com erro de conteudo) para ler a lista de erros.
            var handle = raw != IntPtr.Zero ? new DbHandle(raw) : null;
            if (status != 0)
            {
                var before = errors.Count;
                if (handle != null)
                {
                    var addRef = false;
                    try
                    {
                        handle.DangerousAddRef(ref addRef);
                        var h = handle.DangerousGetHandle();
                        var jsonStatus = NativeBuffers.ReadString((byte* o, nuint c, nuint* n) =>
                            ShatterNative.shatter_db_errors_json(h, o, c, n), out var json, 512);
                        if (jsonStatus == 0) NativeErrorJson.Parse(json, (RulesStatus)status, errors);
                    }
                    finally
                    {
                        if (addRef) handle.DangerousRelease();
                    }
                }
                if (errors.Count == before)
                    errors.Add(new RulesError((RulesStatus)status, string.Empty, err.line, NativeBuffers.ErrorMessage(ref err)));
                handle?.Dispose();
                return (RulesStatus)status;
            }

            // Constantes que o gameplay le por passo (realtime_step, cooldown_min) e o stub de conteudo.
            ShatterRules loaded = default;
            var rulesStatus = ShatterNative.shatter_db_rules(raw, &loaded);
            if (rulesStatus != 0)
            {
                handle.Dispose();
                errors.Add(new RulesError((RulesStatus)rulesStatus, "rules.csv", 0, "shatter_db_rules failed"));
                return (RulesStatus)rulesStatus;
            }

            ShatterRulesExt2 ext2 = default;
            var ext2Status = ShatterNative.shatter_db_rules_ext2(raw, &ext2);
            if (ext2Status != 0)
            {
                handle.Dispose();
                errors.Add(new RulesError((RulesStatus)ext2Status, "rules.csv", 0, "shatter_db_rules_ext2 failed"));
                return (RulesStatus)ext2Status;
            }

            ShatterRulesExt ext = default;
            var extStatus = ShatterNative.shatter_db_rules_ext(raw, &ext);
            if (extStatus != 0)
            {
                handle.Dispose();
                errors.Add(new RulesError((RulesStatus)extStatus, "rules.csv", 0, "shatter_db_rules_ext failed"));
                return (RulesStatus)extStatus;
            }

            ShatterCombatRules combatRules = default;
            var combatRulesStatus = ShatterNative.shatter_db_combat_rules(raw, &combatRules);
            if (combatRulesStatus != 0)
            {
                handle.Dispose();
                errors.Add(new RulesError((RulesStatus)combatRulesStatus, "rules.csv", 0, "shatter_db_combat_rules failed"));
                return (RulesStatus)combatRulesStatus;
            }

            var stubErrors = new List<RulesError>();
            var stubStatus = stub.LoadContent(dataDirectory, stubErrors);
            if (stubStatus != RulesStatus.Ok)
            {
                handle.Dispose();
                errors.AddRange(stubErrors);
                return stubStatus;
            }

            db = handle;
            rules = loaded;
            rulesLoaded = true;
            rulesExt = ext;
            var combat = stub.Combat;
            combat.FixedStep = loaded.realtime_step;
            combat.MinCooldown = loaded.cooldown_min;
            combat.DodgeMaxCharges = ext.dodge_max_charges;
            combat.DodgeRechargeSeconds = ext.dodge_recharge;
            combat.DodgeDurationSeconds = ext.dodge_duration;
            combat.DodgeInvulnerableSeconds = ext.dodge_iframes;
            combat.DodgeDistanceUu = ext.dodge_distance;
            combat.DodgeResourceCost = ext.dodge_cost_resource;
            combat.DodgePerfectResource = ext.dodge_perfect_resource;
            combat.InputBufferSeconds = ext.dodge_buffer;
            combat.DodgeCancelRecoveryFraction = ext.dodge_cancel_recovery_fraction;
            combat.OutOfCombatSeconds = ext.out_of_combat_seconds;
            combat.PotionLockoutSeconds = ext.potion_lockout;
            combat.RequireOnScreenMarginUu = ext2.require_on_screen_margin;
            combat.UnarmedWeaponDamagePhysical = ext2.unarmed_weapon_damage_physical;
            combat.ComboWindowSeconds = combatRules.combo_window;
            combat.ComboWindowAfterDodgeSeconds = combatRules.combo_window_after_dodge;
            combat.AttackBufferSeconds = combatRules.attack_buffer;
            combat.HeavyHoldThresholdSeconds = combatRules.heavy_hold_threshold;
            combat.LightWindupCreditMax = combatRules.light_windup_credit_max;
            combat.GuardLowerTimeSeconds = combatRules.guard_lower_time;
            combat.DashShotRangeUu = combatRules.dash_shot_range;
            ApplyCoreEnemyData();
            ApplyCoreSkillData();
            ApplyCoreBasicKits();
            return RulesStatus.Ok;
        }

        // --- Conteudo tipado (stub) --------------------------------------------------------------------

        public ClassInfo FindClass(string id) => stub.FindClass(id);
        public SkillInfo FindSkill(string id) => stub.FindSkill(id);
        public EnemyInfo FindEnemy(string id) => stub.FindEnemy(id);
        public ItemBaseInfo FindItemBase(string id) => stub.FindItemBase(id);
        public PotionInfo FindPotion(string id) => stub.FindPotion(id);

        /// <summary>Dados de um ID de conteudo em JSON (afixo, base, unico...) para tooltips; nulo se nao existe.</summary>
        public string ContentJson(string id) => LookupJson(id, 512);

        /// <summary>Dados de um ID de conteudo em JSON (<c>shatter_db_lookup_json</c>, duas chamadas); nulo se nao existe.</summary>
        internal unsafe string LookupJson(string id, int initialCapacity = 256)
        {
            var handle = RequireDb();
            var bytes = NativeBuffers.Utf8(id);
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                var raw = handle.DangerousGetHandle();
                string json;
                int status;
                fixed (byte* p = bytes)
                {
                    var idAddress = (IntPtr)p;
                    var len = (nuint)bytes.Length;
                    status = NativeBuffers.ReadString((byte* o, nuint c, nuint* n) =>
                        ShatterNative.shatter_db_lookup_json(raw, (byte*)idAddress, len, o, c, n), out json, initialCapacity);
                }
                if (status == (int)RulesStatus.NotFound) return null;
                NativeCallException.ThrowIfFailed("shatter_db_lookup_json", status);
                return json;
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        // --- Atributos ---------------------------------------------------------------------------------

        public unsafe IStatBlock CreateHeroStats(in HeroBuild build)
        {
            var handle = RequireDb();
            if (build.Save != null) return build.Save.StatsOfCharacter(this, build.SaveCharacterIndex, build.Level);
            var json = Encoding.UTF8.GetBytes(BuildCharacterJson(build));
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                IntPtr raw = IntPtr.Zero;
                ShatterError err = default;
                int status;
                fixed (byte* p = json) status = ShatterNative.shatter_statblock_from_character_json(handle.DangerousGetHandle(), p, (nuint)json.Length, &raw, &err);
                if (status != 0)
                    throw new ArgumentException($"hero stats failed ({(RulesStatus)status}): {NativeBuffers.ErrorMessage(ref err)}");
                return new NativeStatBlock(new StatBlockHandle(raw)) { IsHero = true };
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        public unsafe IStatBlock CreateEnemyStats(string enemyId, int level)
        {
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(enemyId);
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                IntPtr raw = IntPtr.Zero;
                int status;
                fixed (byte* p = id) status = ShatterNative.shatter_statblock_for_enemy(handle.DangerousGetHandle(), p, (nuint)id.Length, level, &raw);
                if (status != 0) throw new ArgumentException($"unknown enemy '{enemyId}' ({(RulesStatus)status})");
                return new NativeStatBlock(new StatBlockHandle(raw));
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        public unsafe IStatBlock CreateEmptyStats()
        {
            IntPtr raw = IntPtr.Zero;
            NativeCallException.ThrowIfFailed("shatter_statblock_create", ShatterNative.shatter_statblock_create(&raw));
            return new NativeStatBlock(new StatBlockHandle(raw));
        }

        public IEffectSet CreateEffectSet(IStatBlock target, EnemyInfo enemyOrNull) => CreateEffectSet(target, enemyOrNull, false);

        public unsafe IEffectSet CreateEffectSet(IStatBlock target, EnemyInfo enemyOrNull, bool rolledElite)
        {
            var handle = RequireDb();
            if (!(target is NativeStatBlock native)) throw new ArgumentException("target must come from this rules core", nameof(target));
            IntPtr fx = IntPtr.Zero;
            NativeCallException.ThrowIfFailed("shatter_effects_create", ShatterNative.shatter_effects_create(&fx));
            var effects = new EffectsHandle(fx);
            // Imunidade a atordoamento (stunImmune, chefe, elite) vem do core pelo actor; enemy_id vazio = alvo comum (heroi).
            var enemyId = NativeBuffers.Utf8(enemyOrNull?.Id);
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                IntPtr rawActor = IntPtr.Zero;
                int status;
                fixed (byte* p = enemyId) status = ShatterNative.shatter_actor_create(handle.DangerousGetHandle(), p, (nuint)enemyId.Length, rolledElite ? (byte)1 : (byte)0, &rawActor);
                if (status != 0)
                {
                    effects.Dispose();
                    throw new NativeCallException("shatter_actor_create", status);
                }
                return new NativeEffectSet(effects, handle, native, stub.ContentOrNull, new ActorHandle(rawActor));
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        // --- RNG ---------------------------------------------------------------------------------------

        public unsafe RngState CreateRng(ulong seed, RngStream stream, ulong index)
        {
            ShatterRng r = default;
            NativeCallException.ThrowIfFailed("shatter_rng_for_stream", ShatterNative.shatter_rng_for_stream(seed, (uint)stream, index, &r));
            return new RngState { State = r.state, Increment = r.inc };
        }

        // A API so tem next_u32: o sorteio limitado e o unitario seguem no stub, que usa o mesmo PCG32.
        public uint NextBelow(ref RngState rng, uint bound) => stub.NextBelow(ref rng, bound);
        public double NextUnit(ref RngState rng) => stub.NextUnit(ref rng);
        public unsafe int PickAttack(ref RngState rng, EnemyInfo enemy)
        {
            if (enemy == null) return -1;
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(enemy.Id);
            var native = new ShatterRng { state = rng.State, inc = rng.Increment };
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                int index;
                int status;
                fixed (byte* p = id) status = ShatterNative.shatter_pick_attack(handle.DangerousGetHandle(), p, (nuint)id.Length, &native, &index);
                if (status == (int)RulesStatus.NotFound) return -1;
                NativeCallException.ThrowIfFailed("shatter_pick_attack", status);
                rng = new RngState { State = native.state, Increment = native.inc };
                return index;
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        // --- Golpe e recarga -------------------------------------------------------------------------

        public unsafe HitResult ResolveHit(in HitRequest request, ref RngState combatRng)
        {
            if (!(request.Attacker is NativeStatBlock attacker) || !(request.Defender is NativeStatBlock defender))
                throw new ArgumentException("attacker and defender must come from this rules core");
            if (!rulesLoaded) throw new InvalidOperationException("rules content not loaded (call LoadContent first)");

            ShatterHitInput input = default;
            input.base_damage[0] = request.BaseDamage.Physical;
            input.base_damage[1] = request.BaseDamage.Fire;
            input.base_damage[2] = request.BaseDamage.Cold;
            input.base_damage[3] = request.BaseDamage.Lightning;
            input.coefficient = request.Coefficient;
            input.defender_life = request.DefenderLife;
            input.defender_barrier = request.DefenderBarrier;
            input.skill_tags = (uint)request.SkillTags;
            input.is_damage_over_time = request.IsDamageOverTime ? (byte)1 : (byte)0;
            input.can_be_blocked = request.CanBeBlocked ? (byte)1 : (byte)0;
            input.from_guard_arc = request.FromGuardArc ? (byte)1 : (byte)0;

            var rng = new ShatterRng { state = combatRng.State, inc = combatRng.Increment };
            ShatterHitResult output = default;
            bool a = false, d = false;
            try
            {
                attacker.Handle.DangerousAddRef(ref a);
                defender.Handle.DangerousAddRef(ref d);
                var database = RequireDb();
                bool b = false;
                try
                {
                    database.DangerousAddRef(ref b);
                    // Constantes de regra vem do BANCO (A-06): o C# nao manda numero de balanceamento.
                    if (request.IsHeavy || request.ChargeFraction != 0.0)
                    {
                        // Ataque forte: o multiplicador da carga e do core (1 + (heavyMaxMult - 1) * fracao, como `more` neste golpe).
                        var classBytes = NativeBuffers.Utf8(request.ClassId);
                        ShatterError err = default;
                        int heavyStatus;
                        fixed (byte* cid = classBytes)
                            heavyStatus = ShatterNative.shatter_resolve_hit_charged(database.DangerousGetHandle(), attacker.Handle.DangerousGetHandle(),
                                defender.Handle.DangerousGetHandle(), &input, cid, (nuint)classBytes.Length, request.ChargeFraction, &rng, &output, &err);
                        if (heavyStatus != 0)
                            throw new NativeCallException("shatter_resolve_hit_charged", heavyStatus, NativeBuffers.ErrorMessage(ref err));
                    }
                    else
                    {
                        var status = ShatterNative.shatter_resolve_hit_db(database.DangerousGetHandle(), attacker.Handle.DangerousGetHandle(),
                            defender.Handle.DangerousGetHandle(), &input, &rng, &output);
                        NativeCallException.ThrowIfFailed("shatter_resolve_hit_db", status);
                    }
                }
                finally
                {
                    if (b) database.DangerousRelease();
                }
            }
            finally
            {
                if (d) defender.Handle.DangerousRelease();
                if (a) attacker.Handle.DangerousRelease();
            }

            combatRng = new RngState { State = rng.state, Increment = rng.inc };
            var result = new HitResult
            {
                Outcome = (HitOutcome)output.outcome,
                Critical = output.critical != 0,
                Landed = output.landed != 0,
                AfterModifiers = new DamageByType { Physical = output.after_modifiers[0], Fire = output.after_modifiers[1], Cold = output.after_modifiers[2], Lightning = output.after_modifiers[3] },
                AfterMitigation = new DamageByType { Physical = output.after_mitigation[0], Fire = output.after_mitigation[1], Cold = output.after_mitigation[2], Lightning = output.after_mitigation[3] },
                TotalDamage = output.total_damage,
                AbsorbedByBarrier = output.absorbed_by_barrier,
                LifeLost = output.life_lost,
                DefenderLifeAfter = output.defender_life_after,
                DefenderBarrierAfter = output.defender_barrier_after,
                Killed = output.killed != 0,
            };
            return result;
        }

        public unsafe double GetEffectiveCooldown(IStatBlock stats, SkillInfo skill)
        {
            // Habilidade sem recarga fica sem recarga (o core aplicaria o piso cooldown_min): mesma regra do stub.
            if (skill == null || skill.Cooldown <= 0.0) return 0.0;
            var handle = RequireDb();
            var recovery = stats != null ? stats.Get(StatId.CooldownRecovery) : 1.0;
            if (recovery <= 0.0) recovery = 1.0;
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                double value;
                var status = ShatterNative.shatter_effective_cooldown_db(handle.DangerousGetHandle(), skill.Cooldown, recovery, &value);
                NativeCallException.ThrowIfFailed("shatter_effective_cooldown_db", status);
                return value;
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        // --- Tempos, custo, velocidade, CanAct/CanMove (core) -------------------------------------------

        /// <summary>Dano base por tipo: arma, desarmado ou o da habilidade; a MESMA conta do simulador (<c>shatter_skill_base_damage</c>).</summary>
        public unsafe DamageByType GetSkillBaseDamage(SkillInfo skill, ItemBaseInfo weaponOrNull)
        {
            if (skill == null) return default;
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(skill.Id);
            var weapon = NativeBuffers.Utf8(weaponOrNull?.Id);
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                var d = stackalloc double[4];
                int status;
                fixed (byte* p = id)
                fixed (byte* w = weapon)
                    status = ShatterNative.shatter_skill_base_damage(handle.DangerousGetHandle(), p, (nuint)id.Length, w, (nuint)weapon.Length, d);
                NativeCallException.ThrowIfFailed("shatter_skill_base_damage", status);
                return new DamageByType { Physical = d[0], Fire = d[1], Cold = d[2], Lightning = d[3] };
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        // Colunas que so o cliente usa e o core valida e expoe no lookup_json (docs/09 C-27): patrolSpeedMult e requireOnScreen.
        void ApplyCoreEnemyData()
        {
            var content = stub.ContentOrNull;
            if (content == null) return;
            foreach (var pair in content.Enemies)
            {
                var json = LookupJson(pair.Key, 2048);
                if (json == null) continue;
                var patrol = JsonNumber(json, "\"patrol_speed_mult\":");
                if (patrol > 0.0) pair.Value.PatrolSpeedMult = patrol;
                pair.Value.RequireOnScreen = json.IndexOf("\"require_on_screen\":true", StringComparison.Ordinal) >= 0;
                pair.Value.FleeLifeFraction = JsonNumber(json, "\"flee_life_fraction\":");
                pair.Value.FleeSeconds = JsonNumber(json, "\"flee_seconds\":");
                pair.Value.FleeOncePerLife = json.IndexOf("\"flee_once_per_life\":false", StringComparison.Ordinal) < 0;
            }
        }

        // Perfuracao e comportamento de forma (docs/18 8.2 e 8.3): o core valida, classifica e expoe no lookup_json (pierce, behavior).
        void ApplyCoreSkillData()
        {
            var content = stub.ContentOrNull;
            if (content == null) return;
            foreach (var pair in content.Skills)
            {
                var json = LookupJson(pair.Key, 2048);
                if (json == null) continue;
                var skill = pair.Value;
                skill.Pierce = (int)JsonNumber(json, "\"pierce\":");
                skill.Behavior = new SkillBehavior(
                    json.IndexOf("\"explodes\":true", StringComparison.Ordinal) >= 0,
                    json.IndexOf("\"fan\":true", StringComparison.Ordinal) >= 0,
                    json.IndexOf("\"self_centered\":true", StringComparison.Ordinal) >= 0,
                    json.IndexOf("\"ground_targeted\":true", StringComparison.Ordinal) >= 0,
                    json.IndexOf("\"dash_back_shot\":true", StringComparison.Ordinal) >= 0);
            }
        }

        // Kit basico de cada classe (shatter_basic_kit_get). Classe sem linha em basic_kits.csv: NOT_FOUND, sem kit.
        unsafe void ApplyCoreBasicKits()
        {
            kits.Clear();
            var content = stub.ContentOrNull;
            if (content == null) return;
            var handle = RequireDb();
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                var raw = handle.DangerousGetHandle();
                foreach (var classId in content.Classes.Keys)
                {
                    var id = NativeBuffers.Utf8(classId);
                    ShatterBasicKit kit = default;
                    int status;
                    fixed (byte* p = id) status = ShatterNative.shatter_basic_kit_get(raw, p, (nuint)id.Length, &kit);
                    if (status == (int)RulesStatus.NotFound) continue;
                    NativeCallException.ThrowIfFailed("shatter_basic_kit_get", status);
                    var chain = new string[Math.Max(0, Math.Min(kit.light_chain_count, 3))];
                    for (var i = 0; i < chain.Length; i++) chain[i] = FixedId(kit.light_chain + i * 64, 64);
                    var perfect = new string[Math.Max(0, Math.Min(kit.guard_perfect_effect_count, 4))];
                    for (var i = 0; i < perfect.Length; i++) perfect[i] = FixedId(kit.guard_perfect_effects + i * 64, 64);
                    kits[classId] = new BasicKitInfo
                    {
                        ClassId = classId,
                        LightChain = chain,
                        HeavySkill = FixedId(kit.heavy_skill, 64),
                        HeavyChargeSeconds = kit.heavy_charge_time,
                        HeavyMaxMultiplier = kit.heavy_max_mult,
                        ChargeEffect = FixedId(kit.charge_effect, 64),
                        GuardEffect = FixedId(kit.guard_effect, 64),
                        GuardArcDegrees = kit.guard_arc,
                        GuardMaxHoldSeconds = kit.guard_max_hold,
                        GuardCooldownSeconds = kit.guard_cooldown,
                        GuardPerfectWindowSeconds = kit.guard_perfect_window,
                        GuardPerfectCooldownSeconds = kit.guard_perfect_cooldown,
                        GuardPerfectEffects = perfect,
                        GuardPerfectResource = kit.guard_perfect_resource,
                        GuardDrainPerDamage = kit.guard_drain_per_damage,
                    };
                }
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        static unsafe string FixedId(byte* p, int max)
        {
            var n = 0;
            while (n < max && p[n] != 0) n++;
            return Encoding.UTF8.GetString(p, n);
        }

        /// <summary>Kit basico da classe (combo, golpe forte e defesa), lido do core na carga; null se a classe nao tem kit.</summary>
        public BasicKitInfo FindBasicKit(string classId) => classId != null && kits.TryGetValue(classId, out var kit) ? kit : null;

        static double JsonNumber(string json, string key)
        {
            var at = json.IndexOf(key, StringComparison.Ordinal);
            if (at < 0) return 0.0;
            at += key.Length;
            var end = at;
            while (end < json.Length && (char.IsDigit(json[end]) || json[end] == '.' || json[end] == '-' || json[end] == 'e' || json[end] == 'E' || json[end] == '+')) end++;
            return double.TryParse(json.Substring(at, end - at), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : 0.0;
        }

        public ActionTiming GetActionTiming(IStatBlock stats, SkillInfo skill) => GetActionTiming(stats, skill, null);

        public unsafe ActionTiming GetActionTiming(IStatBlock stats, SkillInfo skill, string eliteModifierIdOrNull)
        {
            if (skill == null) return default;
            var timing = SkillTiming(stats, skill, eliteModifierIdOrNull);
            return new ActionTiming(timing.windup, timing.impact, timing.recovery);
        }

        public double GetEffectiveCost(IStatBlock stats, SkillInfo skill)
        {
            if (skill == null) return 0.0;
            return SkillTiming(stats, skill).cost;
        }

        unsafe ShatterActionTiming SkillTiming(IStatBlock stats, SkillInfo skill, string modifierId = null)
        {
            var native = RequireNative(stats);
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(skill.Id);
            var modifier = NativeBuffers.Utf8(modifierId);
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                ShatterActionTiming timing;
                int status;
                fixed (byte* p = id)
                fixed (byte* m = modifier)
                    status = ShatterNative.shatter_skill_timing(handle.DangerousGetHandle(), p, (nuint)id.Length, native.Handle.DangerousGetHandle(), m, (nuint)modifier.Length, &timing);
                NativeCallException.ThrowIfFailed("shatter_skill_timing", status);
                return timing;
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }

        public unsafe double GetMoveSpeedUu(IStatBlock stats, double baseMoveSpeedUu)
        {
            var native = RequireNative(stats);
            // Heroi: o atributo ja vem em uu/s (class_stats.csv); inimigo: base do enemies.csv x atributo.
            var baseUu = native.IsHero ? 0.0 : baseMoveSpeedUu;
            bool s2 = false;
            try
            {
                native.Handle.DangerousAddRef(ref s2);
                double value;
                NativeCallException.ThrowIfFailed("shatter_move_speed", ShatterNative.shatter_move_speed(native.Handle.DangerousGetHandle(), baseUu, &value));
                return value;
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
            }
        }

        public bool CanAct(IStatBlock stats) => stats == null || Can(stats, true);
        public bool CanMove(IStatBlock stats) => stats == null || Can(stats, false);

        unsafe bool Can(IStatBlock stats, bool act)
        {
            var native = RequireNative(stats);
            bool s2 = false, a = false;
            var actor = native.Actor;
            try
            {
                native.Handle.DangerousAddRef(ref s2);
                if (actor != null && !actor.IsClosed) actor.DangerousAddRef(ref a); else actor = null;
                var raw = actor != null ? actor.DangerousGetHandle() : IntPtr.Zero;
                byte value;
                var status = act
                    ? ShatterNative.shatter_can_act(native.Handle.DangerousGetHandle(), raw, &value)
                    : ShatterNative.shatter_can_move(native.Handle.DangerousGetHandle(), raw, &value);
                NativeCallException.ThrowIfFailed(act ? "shatter_can_act" : "shatter_can_move", status);
                return value != 0;
            }
            finally
            {
                if (a) actor.DangerousRelease();
                if (s2) native.Handle.DangerousRelease();
            }
        }

        // --- Vida, recurso, barreira e pocoes (core) ---------------------------------------------------

        public unsafe Vitals CreateVitals(IStatBlock stats, ClassInfo classOrNull)
        {
            var native = RequireNative(stats);
            var handle = RequireDb();
            var classId = NativeBuffers.Utf8(classOrNull?.Id);
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                ShatterVitals v;
                int status;
                fixed (byte* p = classId)
                    status = ShatterNative.shatter_vitals_create(handle.DangerousGetHandle(), native.Handle.DangerousGetHandle(), p, (nuint)classId.Length, &v);
                NativeCallException.ThrowIfFailed("shatter_vitals_create", status);
                return FromNative(v);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }

        public unsafe void TickVitals(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull, double dt, bool inCombat)
        {
            var native = RequireNative(stats);
            var handle = RequireDb();
            var classId = NativeBuffers.Utf8(classOrNull?.Id);
            var v = ToNative(vitals);
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                int status;
                fixed (byte* p = classId)
                    status = ShatterNative.shatter_vitals_tick(handle.DangerousGetHandle(), &v, native.Handle.DangerousGetHandle(), p, (nuint)classId.Length, dt, inCombat ? (byte)1 : (byte)0);
                NativeCallException.ThrowIfFailed("shatter_vitals_tick", status);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            vitals = FromNative(v);
        }

        /// <summary>
        /// Como <see cref="TickVitals(ref Vitals, IStatBlock, ClassInfo, double, bool)"/>, com o herói andando ou parado: o recurso regenera
        /// pela fração <c>regen_mult_while_moving</c> da classe (Foco 0,3) quando <paramref name="moving"/> (<c>shatter_vitals_tick_ex</c>).
        /// </summary>
        public unsafe void TickVitals(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull, double dt, bool inCombat, bool moving)
        {
            var native = RequireNative(stats);
            var handle = RequireDb();
            var classId = NativeBuffers.Utf8(classOrNull?.Id);
            var v = ToNative(vitals);
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                int status;
                fixed (byte* p = classId)
                    status = ShatterNative.shatter_vitals_tick_ex(handle.DangerousGetHandle(), &v, native.Handle.DangerousGetHandle(), p, (nuint)classId.Length, dt,
                        inCombat ? (byte)1 : (byte)0, moving ? (byte)1 : (byte)0);
                NativeCallException.ThrowIfFailed("shatter_vitals_tick_ex", status);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            vitals = FromNative(v);
        }

        /// <summary>Recurso por golpe que acerta (<c>shatter_vitals_gain_on_hit</c>): o valor do classes.csv, limitado ao maximo.</summary>
        public unsafe void GainResourceOnHit(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull)
            => GainResourceFromClass(ref vitals, stats, classOrNull, onBlock: false);

        /// <summary>Recurso por bloqueio (<c>shatter_vitals_gain_on_block</c>).</summary>
        public unsafe void GainResourceOnBlock(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull)
            => GainResourceFromClass(ref vitals, stats, classOrNull, onBlock: true);

        unsafe void GainResourceFromClass(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull, bool onBlock)
        {
            if (classOrNull == null) return;
            var native = RequireNative(stats);
            var handle = RequireDb();
            var classId = NativeBuffers.Utf8(classOrNull.Id);
            var v = ToNative(vitals);
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                int status;
                fixed (byte* p = classId)
                {
                    status = onBlock
                        ? ShatterNative.shatter_vitals_gain_on_block(handle.DangerousGetHandle(), &v, native.Handle.DangerousGetHandle(), p, (nuint)classId.Length)
                        : ShatterNative.shatter_vitals_gain_on_hit(handle.DangerousGetHandle(), &v, native.Handle.DangerousGetHandle(), p, (nuint)classId.Length);
                }
                NativeCallException.ThrowIfFailed(onBlock ? "shatter_vitals_gain_on_block" : "shatter_vitals_gain_on_hit", status);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            vitals = FromNative(v);
        }

        public unsafe void GainResource(ref Vitals vitals, IStatBlock stats, double amount)
        {
            if (amount <= 0.0) return;
            var native = RequireNative(stats);
            var v = ToNative(vitals);
            bool s2 = false;
            try
            {
                native.Handle.DangerousAddRef(ref s2);
                NativeCallException.ThrowIfFailed("shatter_vitals_gain_resource", ShatterNative.shatter_vitals_gain_resource(&v, native.Handle.DangerousGetHandle(), amount));
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
            }
            vitals = FromNative(v);
        }

        public unsafe bool TrySpendResource(ref Vitals vitals, double amount)
        {
            if (amount <= 0.0) return true;
            var v = ToNative(vitals);
            byte ok;
            NativeCallException.ThrowIfFailed("shatter_vitals_spend_resource", ShatterNative.shatter_vitals_spend_resource(&v, amount, &ok));
            vitals = FromNative(v);
            return ok != 0;
        }

        public unsafe PotionOutcome ResolvePotion(PotionInfo potion, IStatBlock stats, in Vitals vitals)
        {
            if (potion == null) return new PotionOutcome(vitals.Life, vitals.Barrier, vitals.BarrierSecondsLeft, 0.0);
            var native = RequireNative(stats);
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(potion.Id);
            var v = ToNative(vitals);
            ShatterPotionOutcome outcome;
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                int status;
                fixed (byte* p = id)
                    status = ShatterNative.shatter_potion_resolve(handle.DangerousGetHandle(), p, (nuint)id.Length, native.Handle.DangerousGetHandle(), &v, &outcome);
                NativeCallException.ThrowIfFailed("shatter_potion_resolve", status);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            if (outcome.status != 0) return new PotionOutcome(vitals.Life, vitals.Barrier, vitals.BarrierSecondsLeft, 0.0);
            var seconds = outcome.barrier_amount > 0.0 ? outcome.barrier_seconds : vitals.BarrierSecondsLeft;
            return new PotionOutcome(v.life, v.barrier, seconds, outcome.heal_amount);
        }

        static Vitals FromNative(in ShatterVitals v) => new Vitals { Life = v.life, Resource = v.resource, Barrier = v.barrier, BarrierSecondsLeft = v.barrier_seconds_left, PotionBarrier = v.potion_barrier };

        static ShatterVitals ToNative(in Vitals v) => new ShatterVitals { life = v.Life, resource = v.Resource, barrier = v.Barrier, barrier_seconds_left = v.BarrierSecondsLeft, potion_barrier = v.PotionBarrier };

        static NativeStatBlock RequireNative(IStatBlock stats)
        {
            if (stats is NativeStatBlock native) return native;
            throw new ArgumentException("stats must come from this rules core", nameof(stats));
        }

        /// <summary>
        /// Libera o banco nativo. StatBlocks e efeitos criados continuam sendo dos seus donos; o banco so e
        /// destruido quando o ultimo efeito/chamada em andamento solta o handle (SafeHandle).
        /// </summary>
        public void Dispose()
        {
            disposed = true;
            db?.Dispose();
            db = null;
            rulesLoaded = false;
            stub.Dispose();
        }

        DbHandle RequireDb()
        {
            if (db == null || db.IsInvalid || db.IsClosed) throw new InvalidOperationException("rules content not loaded (call LoadContent first)");
            return db;
        }

        // --- JSON do personagem (formato CharacterState do save, docs/06_dados.md, secao 6) -------------

        string BuildCharacterJson(in HeroBuild build)
        {
            var sb = new StringBuilder(256);
            sb.Append("{\"name\":\"\",\"class_id\":");
            AppendString(sb, build.ClassId);
            sb.Append(",\"spec_id\":\"\",\"level\":").Append(Math.Max(1, build.Level));
            sb.Append(",\"xp\":0,\"passives\":[],\"skills\":[],\"skill_bar\":[],\"equipment\":{");
            var first = true;
            var equipment = build.EquipmentBaseIds;
            if (equipment != null)
            {
                for (var i = 0; i < equipment.Count; i++)
                {
                    var baseId = equipment[i];
                    if (string.IsNullOrEmpty(baseId)) continue;
                    var info = stub.FindItemBase(baseId);
                    if (info == null) throw new ArgumentException($"unknown item base '{baseId}'");
                    if (!first) sb.Append(',');
                    first = false;
                    AppendString(sb, info.Slot);
                    sb.Append(":{\"base_id\":");
                    AppendString(sb, baseId);
                    sb.Append(",\"rarity\":\"normal\",\"item_level\":").Append(info.ItemLevel);
                    sb.Append(",\"unique_id\":\"\",\"affixes\":[],\"has_inscription\":false}");
                }
            }
            sb.Append("},\"conquered_maps\":[],\"highest_tier_cleared\":0,\"potions\":0,\"play_time_seconds\":0}");
            return sb.ToString();
        }

        static void AppendString(StringBuilder sb, string value)
        {
            sb.Append('"');
            if (value != null)
            {
                foreach (var c in value)
                {
                    switch (c)
                    {
                        case '"': sb.Append("\\\""); break;
                        case '\\': sb.Append("\\\\"); break;
                        default:
                            if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                            else sb.Append(c);
                            break;
                    }
                }
            }
            sb.Append('"');
        }
    }
}
