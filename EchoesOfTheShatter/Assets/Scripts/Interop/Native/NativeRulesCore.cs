using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// <see cref="IRulesCore"/> sobre a DLL <c>shattercore</c> (API C v1, shatter_c.h): P/Invoke, SafeHandle e o
    /// padrao de duas chamadas para buffers (docs/04_arquitetura.md, secao 9).
    ///
    /// Roda NATIVO: carga e validacao do conteudo, versao do conteudo, constantes de regra usadas no passo
    /// fixo, atributos (heroi, inimigo, vazio), resolucao do golpe, recarga efetiva, RNG por fluxo e os
    /// efeitos (aplicar, avancar, empilhar, limpar).
    ///
    /// Segue no STUB (<see cref="StillInStub"/>) o que o v1 da API C ainda nao oferece. O stub e
    /// carregado junto, dos mesmos CSV, e responde so por isso.
    /// </summary>
    public sealed class NativeRulesCore : IRulesCore
    {
        public const string Name = "shattercore-native";

        /// <summary>O que o v1 da API C ainda nao entrega e continua no <see cref="StubRulesCore"/> (lista para o log e o relatorio).</summary>
        public static readonly IReadOnlyList<string> StillInStub = new[]
        {
            "Registros de conteudo tipados (FindClass/FindSkill/FindEnemy/FindItemBase/FindPotion, Potions): a API so devolve JSON por ID (shatter_db_lookup_json), sem lista de classes, habilidades, inimigos nem pocoes",
            "[A-01, Backend etapa2] Constantes de combate em tempo real (esquiva, buffer de entrada, trava de pocao, fora de combate): nao ha em shatter_rules; so realtime_step e cooldown_min vem da DLL",
            "[A-01, Backend etapa2] GetActionTiming (tempos de acao com velocidade de ataque/conjuracao)",
            "[A-01, Backend etapa2] CreateVitals/TickVitals/GainResource/TrySpendResource e ResolvePotion",
            "[A-01, Backend etapa2] PickAttack (sorteio ponderado do ataque do inimigo)",
            "GetEffectiveCost, GetMoveSpeedUu, CanAct/CanMove: o core nao expoe (formulas de uma linha sobre StatBlock.Get)",
            "NextBelow e NextUnit: a API so tem shatter_rng_next_u32, sem o sorteio limitado nem o unitario",
            "Imunidade a atordoamento por inimigo (elite, chefe, familia construct) e as tags dos efeitos nos eventos de dano: shatter_effects_apply nao recebe o inimigo e o evento nao traz tags",
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
        public IReadOnlyList<string> LoadWarnings => stub.LoadWarnings;
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
            stub.Combat.FixedStep = loaded.realtime_step;
            stub.Combat.MinCooldown = loaded.cooldown_min;
            return RulesStatus.Ok;
        }

        // --- Conteudo tipado (stub) --------------------------------------------------------------------

        public ClassInfo FindClass(string id) => stub.FindClass(id);
        public SkillInfo FindSkill(string id) => stub.FindSkill(id);
        public EnemyInfo FindEnemy(string id) => stub.FindEnemy(id);
        public ItemBaseInfo FindItemBase(string id) => stub.FindItemBase(id);
        public PotionInfo FindPotion(string id) => stub.FindPotion(id);

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
                return new NativeStatBlock(new StatBlockHandle(raw));
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

        public unsafe IEffectSet CreateEffectSet(IStatBlock target, EnemyInfo enemyOrNull)
        {
            var handle = RequireDb();
            if (!(target is NativeStatBlock native)) throw new ArgumentException("target must come from this rules core", nameof(target));
            IntPtr raw = IntPtr.Zero;
            NativeCallException.ThrowIfFailed("shatter_effects_create", ShatterNative.shatter_effects_create(&raw));
            return new NativeEffectSet(new EffectsHandle(raw), handle, native, stub.ContentOrNull, StubRulesCore.IsStunImmune(enemyOrNull));
        }

        // --- RNG ---------------------------------------------------------------------------------------

        public unsafe RngState CreateRng(ulong seed, RngStream stream, ulong index)
        {
            ShatterRng r = default;
            NativeCallException.ThrowIfFailed("shatter_rng_for_stream", ShatterNative.shatter_rng_for_stream(seed, (uint)stream, index, &r));
            return new RngState { State = r.state, Increment = r.inc };
        }

        // A API v1 so tem next_u32: o sorteio limitado, o unitario e o ponderado seguem no stub, que usa o mesmo PCG32.
        public uint NextBelow(ref RngState rng, uint bound) => stub.NextBelow(ref rng, bound);
        public double NextUnit(ref RngState rng) => stub.NextUnit(ref rng);
        public int PickAttack(ref RngState rng, EnemyInfo enemy) => stub.PickAttack(ref rng, enemy);

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

            var rng = new ShatterRng { state = combatRng.State, inc = combatRng.Increment };
            ShatterHitResult output = default;
            bool a = false, d = false;
            try
            {
                attacker.Handle.DangerousAddRef(ref a);
                defender.Handle.DangerousAddRef(ref d);
                int status;
                fixed (ShatterRules* r = &rules)
                    status = ShatterNative.shatter_resolve_hit(attacker.Handle.DangerousGetHandle(), defender.Handle.DangerousGetHandle(), &input, r, &rng, &output);
                NativeCallException.ThrowIfFailed("shatter_resolve_hit", status);
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
            if (!rulesLoaded) throw new InvalidOperationException("rules content not loaded (call LoadContent first)");
            var recovery = stats != null ? stats.Get(StatId.CooldownRecovery) : 1.0;
            if (recovery <= 0.0) recovery = 1.0;
            double value;
            int status;
            fixed (ShatterRules* r = &rules) status = ShatterNative.shatter_effective_cooldown(skill.Cooldown, recovery, r, &value);
            NativeCallException.ThrowIfFailed("shatter_effective_cooldown", status);
            return value;
        }

        // --- Ainda no stub (ver StillInStub) -----------------------------------------------------------

        public DamageByType GetSkillBaseDamage(SkillInfo skill, ItemBaseInfo weaponOrNull) => stub.GetSkillBaseDamage(skill, weaponOrNull);
        public ActionTiming GetActionTiming(IStatBlock stats, SkillInfo skill) => stub.GetActionTiming(stats, skill);
        public double GetEffectiveCost(IStatBlock stats, SkillInfo skill) => stub.GetEffectiveCost(stats, skill);
        public double GetMoveSpeedUu(IStatBlock stats, double baseMoveSpeedUu) => stub.GetMoveSpeedUu(stats, baseMoveSpeedUu);
        public bool CanAct(IStatBlock stats) => stub.CanAct(stats);
        public bool CanMove(IStatBlock stats) => stub.CanMove(stats);
        public Vitals CreateVitals(IStatBlock stats, ClassInfo classOrNull) => stub.CreateVitals(stats, classOrNull);
        public void TickVitals(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull, double dt, bool inCombat) => stub.TickVitals(ref vitals, stats, classOrNull, dt, inCombat);
        public void GainResource(ref Vitals vitals, IStatBlock stats, double amount) => stub.GainResource(ref vitals, stats, amount);
        public bool TrySpendResource(ref Vitals vitals, double amount) => stub.TrySpendResource(ref vitals, amount);
        public PotionOutcome ResolvePotion(PotionInfo potion, IStatBlock stats, in Vitals vitals) => stub.ResolvePotion(potion, stats, in vitals);

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
