using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    // Handles e estados da API C 1.1 que o IRulesCore ainda nao expoe: cinto de pocoes, esquiva, elite e chefe.
    // Cada um tem dono (SafeHandle ou estado do chamador) e segura o banco ate ser descartado.

    public enum PotionUseStatus { Ok = 0, Unknown = 1, NoCharges = 2, LockedOut = 3 }

    /// <summary>Resultado de usar uma pocao no cinto (<c>shatter_potions_use</c>). Diferente de Ok: nada mudou.</summary>
    public readonly struct PotionUseResult
    {
        public readonly PotionUseStatus Status;
        public readonly double HealAmount, BarrierAmount, BarrierSeconds, UseTime, MoveSpeedWhileUsing, Lockout;

        internal PotionUseResult(PotionUseStatus status, double heal, double barrier, double barrierSeconds, double useTime, double moveSpeed, double lockout)
        {
            Status = status;
            HealAmount = heal;
            BarrierAmount = barrier;
            BarrierSeconds = barrierSeconds;
            UseTime = useTime;
            MoveSpeedWhileUsing = moveSpeed;
            Lockout = lockout;
        }
    }

    public enum DodgeStartStatus { Ok = 0, NoCharges = 1, Active = 2, NotEnoughResource = 3 }

    /// <summary>Multiplicadores finais de um elite (base de rules.csv x modificador), de <c>shatter_elite_roll/_profile</c>.</summary>
    public readonly struct EliteInfo
    {
        public readonly double LifeMult, DamageMult, XpMult, BarrierFractionOfLife, MoveSpeedMult, AttackSpeedMult, RecoveryMult;
        public readonly double DeathExplosionRadius, DeathExplosionDamage, DeathExplosionFuse;
        public readonly string ModifierId;
        public readonly bool Rolled;
        internal readonly ShatterEliteInfo Raw;

        internal EliteInfo(in ShatterEliteInfo raw, string modifierId)
        {
            Raw = raw;
            LifeMult = raw.life_mult;
            DamageMult = raw.damage_mult;
            XpMult = raw.xp_mult;
            BarrierFractionOfLife = raw.barrier_fraction_of_life;
            MoveSpeedMult = raw.move_speed_mult;
            AttackSpeedMult = raw.attack_speed_mult;
            RecoveryMult = raw.recovery_mult;
            DeathExplosionRadius = raw.death_explosion_radius;
            DeathExplosionDamage = raw.death_explosion_damage;
            DeathExplosionFuse = raw.death_explosion_fuse;
            ModifierId = modifierId;
            Rolled = raw.rolled != 0;
        }
    }

    public enum BossEventKind
    {
        PatternStart = 0, PatternImpact, PatternEnd, PatternInterrupted, PhaseStart, SummonMarker, SummonSpawn, PhaseEnd,
        StaggerStart, StaggerEnd, ShieldDown, ShieldUp, Died,
    }

    public struct BossEvent
    {
        public BossEventKind Kind;
        public double Seconds;
        public int Phase;
        public int Count;
        public string PatternId;
        public string SkillId;
        public string EnemyId;
    }

    public enum BossState { Idle = 0, Waiting, Telegraph, Impact, Recovery, Stagger, Transition, Dead }

    public struct BossInfo
    {
        public double Life, MaxLife, ShieldDownRemaining, TurnRateDegPerSec, FacingX, FacingZ, StaggerRemaining, StunRemaining;
        public int Phase;
        public BossState State;
        public bool ShieldUp, Invulnerable;
    }

    public struct BossDamageResult
    {
        public double Applied, LifeAfter;
        public bool ShieldBlocked, Invulnerable, ClampedByPhase, Killed;
    }

    public sealed partial class NativeRulesCore
    {
        /// <summary>Cinto de pocoes nativo (cargas, recarga em serie, trava global) de um personagem.</summary>
        public unsafe NativePotionBelt CreatePotionBelt()
        {
            var handle = RequireDb();
            IntPtr raw = IntPtr.Zero;
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                NativeCallException.ThrowIfFailed("shatter_potions_create", ShatterNative.shatter_potions_create(handle.DangerousGetHandle(), &raw));
                return new NativePotionBelt(new PotionsHandle(raw), handle);
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        /// <summary>Esquiva nativa (3 cargas, recarga em serie, i-frames): estado POD guardado no objeto.</summary>
        public NativeDodge CreateDodge() => new NativeDodge(RequireDb());

        /// <summary>Sorteia o modificador de elite (consome SEMPRE 1 numero do fluxo de eventos) e devolve os multiplicadores.</summary>
        public unsafe EliteInfo RollElite(ref RngState eventsRng)
        {
            var handle = RequireDb();
            var rng = new ShatterRng { state = eventsRng.State, inc = eventsRng.Increment };
            ShatterEliteInfo info;
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                NativeCallException.ThrowIfFailed("shatter_elite_roll", ShatterNative.shatter_elite_roll(handle.DangerousGetHandle(), &rng, &info));
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
            eventsRng = new RngState { State = rng.state, Increment = rng.inc };
            return new EliteInfo(info, ReadModifierId(&info));
        }

        /// <summary>Elite com modificador conhecido (elite fixo: o modifierId do enemies.csv); vazio = so os multiplicadores base.</summary>
        public unsafe EliteInfo GetEliteProfile(string modifierId, bool rolled)
        {
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(modifierId);
            ShatterEliteInfo info;
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                int status;
                fixed (byte* p = id)
                    status = ShatterNative.shatter_elite_profile(handle.DangerousGetHandle(), p, (nuint)id.Length, rolled ? (byte)1 : (byte)0, &info);
                NativeCallException.ThrowIfFailed("shatter_elite_profile", status);
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
            return new EliteInfo(info, ReadModifierId(&info));
        }

        /// <summary>Escreve os multiplicadores do elite no bloco do inimigo (Life/Damage/MoveSpeed/AttackSpeed More) e devolve a barreira inicial.</summary>
        public unsafe double ApplyElite(IStatBlock enemyStats, in EliteInfo info)
        {
            var native = RequireNative(enemyStats);
            var handle = RequireDb();
            var raw = info.Raw;
            double barrier;
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                NativeCallException.ThrowIfFailed("shatter_elite_apply", ShatterNative.shatter_elite_apply(handle.DangerousGetHandle(), &raw, native.Handle.DangerousGetHandle(), &barrier));
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            return barrier;
        }

        /// <summary>Chefe nativo (fases, escudo frontal, rugido, invocacao e padroes por seed). Descarte-o ANTES do nucleo.</summary>
        public unsafe NativeBoss CreateBoss(string enemyId, int level, ulong seed)
        {
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(enemyId);
            IntPtr raw = IntPtr.Zero;
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                int status;
                fixed (byte* p = id) status = ShatterNative.shatter_boss_create(handle.DangerousGetHandle(), p, (nuint)id.Length, level, seed, &raw);
                if (status != 0) throw new ArgumentException($"boss '{enemyId}' failed ({(RulesStatus)status})");
                return new NativeBoss(new BossHandle(raw), handle);
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        static unsafe string ReadModifierId(ShatterEliteInfo* info)
        {
            var n = 0;
            while (n < 64 && info->modifier_id[n] != 0) n++;
            return Encoding.UTF8.GetString(info->modifier_id, n);
        }
    }

    /// <summary>Cinto de pocoes (<c>shatter_potions</c>). Dono: quem criou; segura o banco ate ser descartado.</summary>
    public sealed unsafe class NativePotionBelt : IDisposable
    {
        readonly PotionsHandle handle;
        readonly DbHandle db;
        bool holdsDb;

        internal NativePotionBelt(PotionsHandle handle, DbHandle db)
        {
            this.handle = handle;
            this.db = db;
            db.DangerousAddRef(ref holdsDb);
        }

        public void Tick(double dt)
        {
            Call(() => ShatterNative.shatter_potions_tick(db.DangerousGetHandle(), handle.DangerousGetHandle(), dt), "shatter_potions_tick");
        }

        public void Refill()
        {
            Call(() => ShatterNative.shatter_potions_refill(db.DangerousGetHandle(), handle.DangerousGetHandle()), "shatter_potions_refill");
        }

        /// <summary>+1 carga na pocao refillOnEliteKill com menos cargas; false se todas estavam cheias.</summary>
        public bool OnEliteKilled()
        {
            byte added = 0;
            bool a = false, d = false;
            try
            {
                handle.DangerousAddRef(ref a);
                db.DangerousAddRef(ref d);
                NativeCallException.ThrowIfFailed("shatter_potions_on_elite_killed",
                    ShatterNative.shatter_potions_on_elite_killed(db.DangerousGetHandle(), handle.DangerousGetHandle(), &added));
            }
            finally
            {
                if (d) db.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            return added != 0;
        }

        /// <summary>Usa a pocao: confere trava e cargas, gasta 1 carga e aplica cura/barreira em <paramref name="vitals"/>.</summary>
        public PotionUseResult Use(string potionId, IStatBlock stats, ref Vitals vitals)
        {
            if (!(stats is NativeStatBlock native)) throw new ArgumentException("stats must come from this rules core", nameof(stats));
            var id = NativeBuffers.Utf8(potionId);
            var v = new ShatterVitals { life = vitals.Life, resource = vitals.Resource, barrier = vitals.Barrier, barrier_seconds_left = vitals.BarrierSecondsLeft };
            ShatterPotionOutcome outcome;
            bool s2 = false, a = false, d = false;
            try
            {
                handle.DangerousAddRef(ref a);
                db.DangerousAddRef(ref d);
                native.Handle.DangerousAddRef(ref s2);
                int status;
                fixed (byte* p = id)
                    status = ShatterNative.shatter_potions_use(db.DangerousGetHandle(), handle.DangerousGetHandle(), p, (nuint)id.Length,
                        native.Handle.DangerousGetHandle(), &v, &outcome);
                NativeCallException.ThrowIfFailed("shatter_potions_use", status);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (d) db.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            if (outcome.status == 0)
                vitals = new Vitals { Life = v.life, Resource = v.resource, Barrier = v.barrier, BarrierSecondsLeft = v.barrier_seconds_left };
            return new PotionUseResult((PotionUseStatus)outcome.status, outcome.heal_amount, outcome.barrier_amount, outcome.barrier_seconds,
                outcome.use_time, outcome.move_speed_while_using, outcome.lockout);
        }

        /// <summary>JSON do cinto: lockout_remaining e, por pocao, charges, max_charges, recharge_remaining e hotkey_slot (duas chamadas).</summary>
        public string InfoJson()
        {
            var h = handle.DangerousGetHandle();
            var d = db.DangerousGetHandle();
            var status = NativeBuffers.ReadString((byte* o, nuint c, nuint* n) => ShatterNative.shatter_potions_info_json(d, h, o, c, n), out var json, 128);
            NativeCallException.ThrowIfFailed("shatter_potions_info_json", status);
            return json;
        }

        void Call(Func<int> call, string name)
        {
            bool a = false, d = false;
            try
            {
                handle.DangerousAddRef(ref a);
                db.DangerousAddRef(ref d);
                NativeCallException.ThrowIfFailed(name, call());
            }
            finally
            {
                if (d) db.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }

        public void Dispose()
        {
            handle.Dispose();
            if (holdsDb)
            {
                holdsDb = false;
                db.DangerousRelease();
            }
        }
    }

    /// <summary>Esquiva nativa: estado POD (<c>shatter_dodge_state</c>) guardado aqui; cargas nao sao salvas.</summary>
    public sealed unsafe class NativeDodge : IDisposable
    {
        readonly DbHandle db;
        ShatterDodgeState state;
        bool holdsDb;

        internal NativeDodge(DbHandle db)
        {
            this.db = db;
            db.DangerousAddRef(ref holdsDb);
            fixed (ShatterDodgeState* p = &state)
                NativeCallException.ThrowIfFailed("shatter_dodge_init", ShatterNative.shatter_dodge_init(db.DangerousGetHandle(), p));
        }

        public int Charges => state.charges;
        public bool IsActive => state.active != 0;

        public void Tick(double dt)
        {
            fixed (ShatterDodgeState* p = &state)
                NativeCallException.ThrowIfFailed("shatter_dodge_tick", ShatterNative.shatter_dodge_tick(db.DangerousGetHandle(), p, dt));
        }

        /// <summary>Comeca a esquiva; so com Ok gasta a carga.</summary>
        public DodgeStartStatus Start(double resourceAvailable)
        {
            int result;
            fixed (ShatterDodgeState* p = &state)
                NativeCallException.ThrowIfFailed("shatter_dodge_start", ShatterNative.shatter_dodge_start(db.DangerousGetHandle(), p, resourceAvailable, &result));
            return (DodgeStartStatus)result;
        }

        public bool IsInvulnerable
        {
            get
            {
                byte value;
                fixed (ShatterDodgeState* p = &state)
                    NativeCallException.ThrowIfFailed("shatter_dodge_invulnerable", ShatterNative.shatter_dodge_invulnerable(db.DangerousGetHandle(), p, &value));
                return value != 0;
            }
        }

        /// <summary>Recurso da esquiva perfeita se um golpe chegou durante os i-frames (senao 0).</summary>
        public double PerfectReward
        {
            get
            {
                double value;
                fixed (ShatterDodgeState* p = &state)
                    NativeCallException.ThrowIfFailed("shatter_dodge_perfect_reward", ShatterNative.shatter_dodge_perfect_reward(db.DangerousGetHandle(), p, &value));
                return value;
            }
        }

        public void Dispose()
        {
            if (holdsDb)
            {
                holdsDb = false;
                db.DangerousRelease();
            }
        }
    }

    /// <summary>Chefe nativo (<c>shatter_boss</c>). Guarda o banco; descarte antes do nucleo (o handle segura o banco ate aqui).</summary>
    public sealed unsafe class NativeBoss : IDisposable
    {
        readonly BossHandle handle;
        readonly DbHandle db;
        bool holdsDb;
        ShatterBossEvent[] buffer = new ShatterBossEvent[8];

        internal NativeBoss(BossHandle handle, DbHandle db)
        {
            this.handle = handle;
            this.db = db;
            db.DangerousAddRef(ref holdsDb);
        }

        public void Start() => Call(() => ShatterNative.shatter_boss_start(handle.DangerousGetHandle()), "shatter_boss_start");

        /// <summary>Reinicio total (morte do jogador); <paramref name="statsOrNull"/> perde o bonus de dano do stagger.</summary>
        public void Reset(IStatBlock statsOrNull)
        {
            var raw = statsOrNull is NativeStatBlock n ? n.Handle.DangerousGetHandle() : IntPtr.Zero;
            Call(() => ShatterNative.shatter_boss_reset(handle.DangerousGetHandle(), raw), "shatter_boss_reset");
        }

        /// <summary>Passo fixo; acrescenta os eventos do passo em <paramref name="events"/>.</summary>
        public void Step(double dt, double bossX, double bossZ, double playerX, double playerZ, IStatBlock stats, List<BossEvent> events)
        {
            var native = stats as NativeStatBlock;
            var ctx = new ShatterBossContext { boss = new ShatterVec2 { x = bossX, z = bossZ }, player = new ShatterVec2 { x = playerX, z = playerZ } };
            nuint count = 0;
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                if (native != null) native.Handle.DangerousAddRef(ref s2);
                var statsRaw = native != null ? native.Handle.DangerousGetHandle() : IntPtr.Zero;
                NativeCallException.ThrowIfFailed("shatter_boss_step", ShatterNative.shatter_boss_step(handle.DangerousGetHandle(), dt, &ctx, statsRaw, &count));
                if (count != 0 && events != null) ReadEvents(checked((int)count), events);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }

        /// <summary>Dano ja calculado por <c>ResolveHit</c> (defender_life = vida do chefe): escudo frontal, rugido e limiar de fase.</summary>
        public BossDamageResult ApplyDamage(double amount, double bossX, double bossZ, double originX, double originZ)
        {
            ShatterBossDamage r;
            bool a = false;
            try
            {
                handle.DangerousAddRef(ref a);
                NativeCallException.ThrowIfFailed("shatter_boss_apply_damage", ShatterNative.shatter_boss_apply_damage(handle.DangerousGetHandle(), amount,
                    new ShatterVec2 { x = bossX, z = bossZ }, new ShatterVec2 { x = originX, z = originZ }, &r));
            }
            finally
            {
                if (a) handle.DangerousRelease();
            }
            return new BossDamageResult
            {
                Applied = r.applied,
                LifeAfter = r.life_after,
                ShieldBlocked = r.shield_blocked != 0,
                Invulnerable = r.invulnerable != 0,
                ClampedByPhase = r.clamped_by_phase != 0,
                Killed = r.killed != 0,
            };
        }

        public bool ShieldCovers(double bossX, double bossZ, double originX, double originZ)
        {
            byte value;
            bool a = false;
            try
            {
                handle.DangerousAddRef(ref a);
                NativeCallException.ThrowIfFailed("shatter_boss_shield_covers", ShatterNative.shatter_boss_shield_covers(handle.DangerousGetHandle(),
                    new ShatterVec2 { x = bossX, z = bossZ }, new ShatterVec2 { x = originX, z = originZ }, &value));
            }
            finally
            {
                if (a) handle.DangerousRelease();
            }
            return value != 0;
        }

        public BossInfo Info
        {
            get
            {
                ShatterBossInfo i;
                bool a = false;
                try
                {
                    handle.DangerousAddRef(ref a);
                    NativeCallException.ThrowIfFailed("shatter_boss_info_get", ShatterNative.shatter_boss_info_get(handle.DangerousGetHandle(), &i));
                }
                finally
                {
                    if (a) handle.DangerousRelease();
                }
                return new BossInfo
                {
                    Life = i.life, MaxLife = i.max_life, ShieldDownRemaining = i.shield_down_remaining, TurnRateDegPerSec = i.turn_rate_deg_per_sec,
                    FacingX = i.facing_x, FacingZ = i.facing_z, StaggerRemaining = i.stagger_remaining, StunRemaining = i.stun_remaining,
                    Phase = i.phase, State = (BossState)i.state, ShieldUp = i.shield_up != 0, Invulnerable = i.invulnerable != 0,
                };
            }
        }

        void ReadEvents(int count, List<BossEvent> events)
        {
            if (buffer.Length < count) buffer = new ShatterBossEvent[count];
            nuint needed = 0;
            fixed (ShatterBossEvent* p = buffer)
            {
                NativeCallException.ThrowIfFailed("shatter_boss_events", ShatterNative.shatter_boss_events(handle.DangerousGetHandle(), p, (nuint)buffer.Length, &needed));
                var n = Math.Min(count, checked((int)needed));
                for (var i = 0; i < n; i++)
                {
                    var e = p + i;
                    events.Add(new BossEvent
                    {
                        Kind = (BossEventKind)e->kind,
                        Seconds = e->seconds,
                        Phase = e->phase,
                        Count = e->count,
                        PatternId = Text(e->pattern_id),
                        SkillId = Text(e->skill_id),
                        EnemyId = Text(e->enemy_id),
                    });
                }
            }
        }

        static string Text(byte* field)
        {
            var n = 0;
            while (n < 64 && field[n] != 0) n++;
            return Encoding.UTF8.GetString(field, n);
        }

        void Call(Func<int> call, string name)
        {
            bool a = false;
            try
            {
                handle.DangerousAddRef(ref a);
                NativeCallException.ThrowIfFailed(name, call());
            }
            finally
            {
                if (a) handle.DangerousRelease();
            }
        }

        public void Dispose()
        {
            handle.Dispose();
            if (holdsDb)
            {
                holdsDb = false;
                db.DangerousRelease();
            }
        }
    }
}
