using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    // Cinto de poções, esquiva, elite e chefe nativos (API C 1.1) atrás das interfaces do Interop.
    // Cada handle tem dono (SafeHandle) e segura o banco até ser descartado.

    public sealed partial class NativeRulesCore
    {
        public bool SupportsBoss => true;

        public unsafe IPotionBelt CreatePotionBelt()
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

        public IDodgeCharges CreateDodge() => new NativeDodge(RequireDb(), rulesExt.dodge_max_charges, rulesExt.dodge_recharge);

        public unsafe EliteProfile RollElite(ref RngState eventsRng)
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
            return new EliteProfile(info, ReadModifierId(&info));
        }

        public unsafe EliteProfile GetEliteProfile(string modifierId, bool rolled)
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
            return new EliteProfile(info, ReadModifierId(&info));
        }

        public unsafe double ApplyElite(IStatBlock enemyStats, in EliteProfile profile)
        {
            var native = RequireNative(enemyStats);
            var handle = RequireDb();
            var raw = profile.Raw;
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

        public unsafe IBossController CreateBoss(string enemyId, int level, ulong seed)
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

    /// <summary>Cinto de poções (<c>shatter_potions</c>). O estado lido (cargas, recarga, trava) é cacheado e relido só depois de uma chamada que o muda.</summary>
    internal sealed unsafe class NativePotionBelt : IPotionBelt
    {
        readonly PotionsHandle handle;
        readonly DbHandle db;
        bool holdsDb;
        bool dirty = true;
        byte[] json = new byte[512];
        int jsonLength;
        PotionBeltEntry[] entries = Array.Empty<PotionBeltEntry>();
        double lockout;
        string[] potionIds = Array.Empty<string>();

        internal NativePotionBelt(PotionsHandle handle, DbHandle db)
        {
            this.handle = handle;
            this.db = db;
            db.DangerousAddRef(ref holdsDb);
            Refresh();
        }

        public int Count
        {
            get
            {
                Refresh();
                return entries.Length;
            }
        }

        public PotionBeltEntry GetEntry(int index)
        {
            Refresh();
            return index >= 0 && index < entries.Length ? entries[index] : default;
        }

        public double LockoutRemaining
        {
            get
            {
                Refresh();
                return lockout;
            }
        }

        public void Tick(double dt)
        {
            Call(() => ShatterNative.shatter_potions_tick(db.DangerousGetHandle(), handle.DangerousGetHandle(), dt), "shatter_potions_tick");
            dirty = true;
        }

        public void Refill()
        {
            Call(() => ShatterNative.shatter_potions_refill(db.DangerousGetHandle(), handle.DangerousGetHandle()), "shatter_potions_refill");
            dirty = true;
        }

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
            dirty = true;
            return added != 0;
        }

        public PotionUseStatus TryUse(int index, IStatBlock stats)
        {
            Refresh();
            if (index < 0 || index >= potionIds.Length) return PotionUseStatus.Unknown;
            if (!(stats is NativeStatBlock native)) throw new ArgumentException("stats must come from this rules core", nameof(stats));
            // O efeito (cura/barreira) é aplicado ao fim do tempo de uso por ResolvePotion; aqui só o estado do cinto
            // (carga e trava), então o uso roda sobre vitais descartáveis.
            var scratch = new ShatterVitals();
            ShatterPotionOutcome outcome;
            var bytes = NativeBuffers.Utf8(potionIds[index]);
            bool s2 = false, a = false, d = false;
            try
            {
                handle.DangerousAddRef(ref a);
                db.DangerousAddRef(ref d);
                native.Handle.DangerousAddRef(ref s2);
                int status;
                fixed (byte* p = bytes)
                    status = ShatterNative.shatter_potions_use(db.DangerousGetHandle(), handle.DangerousGetHandle(), p, (nuint)bytes.Length,
                        native.Handle.DangerousGetHandle(), &scratch, &outcome);
                NativeCallException.ThrowIfFailed("shatter_potions_use", status);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (d) db.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            dirty = true;
            return (PotionUseStatus)outcome.status;
        }

        void Refresh()
        {
            if (!dirty) return;
            bool a = false, d = false;
            try
            {
                handle.DangerousAddRef(ref a);
                db.DangerousAddRef(ref d);
                var h = handle.DangerousGetHandle();
                var dbRaw = db.DangerousGetHandle();
                var status = NativeBuffers.ReadBytes((byte* o, nuint c, nuint* n) => ShatterNative.shatter_potions_info_json(dbRaw, h, o, c, n), out var buffer, out var length, json.Length);
                NativeCallException.ThrowIfFailed("shatter_potions_info_json", status);
                json = buffer;
                jsonLength = length;
            }
            finally
            {
                if (d) db.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
            Parse();
            dirty = false;
        }

        static readonly byte[] KeyLockout = Encoding.ASCII.GetBytes("\"lockout_remaining\":");
        static readonly byte[] KeyCharges = Encoding.ASCII.GetBytes("\"charges\":");
        static readonly byte[] KeyMax = Encoding.ASCII.GetBytes("\"max_charges\":");
        static readonly byte[] KeyRecharge = Encoding.ASCII.GetBytes("\"recharge_remaining\":");
        static readonly byte[] KeyPotionId = Encoding.ASCII.GetBytes("\"potion_id\":\"");

        // Lê os números do JSON do cinto sem alocar por passo:
        // {"lockout_remaining":0,"slots":[{"potion_id":"...","charges":3,"max_charges":3,"recharge_remaining":0,...}]}
        void Parse()
        {
            var pos = 0;
            lockout = Seek(KeyLockout, ref pos) ? ReadValue(ref pos) : 0.0;
            var count = 0;
            var scan = pos;
            while (FindKey(KeyCharges, scan, out var at))
            {
                count++;
                scan = at + 1;
            }
            if (entries.Length != count) entries = new PotionBeltEntry[count];
            var idsKnown = potionIds.Length == count;
            if (!idsKnown) potionIds = new string[count];
            for (var i = 0; i < count; i++)
            {
                if (!idsKnown && FindKey(KeyPotionId, pos, out var idAt))
                {
                    var start = idAt + KeyPotionId.Length;
                    var end = start;
                    while (end < jsonLength && json[end] != (byte)'"') end++;
                    potionIds[i] = Encoding.UTF8.GetString(json, start, end - start);
                }
                Seek(KeyCharges, ref pos);
                var charges = (int)ReadValue(ref pos);
                Seek(KeyMax, ref pos);
                var max = (int)ReadValue(ref pos);
                Seek(KeyRecharge, ref pos);
                var recharge = ReadValue(ref pos);
                entries[i] = new PotionBeltEntry(charges, max, recharge);
            }
        }

        bool FindKey(byte[] key, int from, out int at)
        {
            for (var i = from; i <= jsonLength - key.Length; i++)
            {
                var match = true;
                for (var k = 0; k < key.Length; k++)
                {
                    if (json[i + k] != key[k])
                    {
                        match = false;
                        break;
                    }
                }
                if (match)
                {
                    at = i;
                    return true;
                }
            }
            at = -1;
            return false;
        }

        // Posiciona pos no primeiro caractere do valor depois da chave.
        bool Seek(byte[] key, ref int pos)
        {
            if (!FindKey(key, pos, out var at)) return false;
            pos = at + key.Length;
            return true;
        }

        double ReadValue(ref int pos)
        {
            var i = pos;
            var negative = false;
            if (i < jsonLength && json[i] == (byte)'-')
            {
                negative = true;
                i++;
            }
            double value = 0.0;
            while (i < jsonLength && json[i] >= (byte)'0' && json[i] <= (byte)'9') value = value * 10.0 + (json[i++] - (byte)'0');
            if (i < jsonLength && json[i] == (byte)'.')
            {
                i++;
                var scale = 0.1;
                while (i < jsonLength && json[i] >= (byte)'0' && json[i] <= (byte)'9')
                {
                    value += (json[i++] - (byte)'0') * scale;
                    scale *= 0.1;
                }
            }
            if (i < jsonLength && (json[i] == (byte)'e' || json[i] == (byte)'E'))
            {
                i++;
                var expNegative = false;
                if (i < jsonLength && (json[i] == (byte)'-' || json[i] == (byte)'+'))
                {
                    expNegative = json[i] == (byte)'-';
                    i++;
                }
                var exp = 0;
                while (i < jsonLength && json[i] >= (byte)'0' && json[i] <= (byte)'9') exp = exp * 10 + (json[i++] - (byte)'0');
                value *= Math.Pow(10.0, expNegative ? -exp : exp);
            }
            pos = i;
            return negative ? -value : value;
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

    /// <summary>Esquiva nativa: estado POD (<c>shatter_dodge_state</c>) guardado aqui; cargas não são salvas.</summary>
    internal sealed unsafe class NativeDodge : IDodgeCharges
    {
        readonly DbHandle db;
        readonly int maxCharges;
        readonly double rechargeSeconds;
        ShatterDodgeState state;
        bool holdsDb;

        internal NativeDodge(DbHandle db, int maxCharges, double rechargeSeconds)
        {
            this.db = db;
            this.maxCharges = maxCharges;
            this.rechargeSeconds = rechargeSeconds;
            db.DangerousAddRef(ref holdsDb);
            Reset();
        }

        public int Charges => state.charges;
        public int MaxCharges => maxCharges;
        public bool IsFull => state.charges >= maxCharges;
        public bool IsEmpty => state.charges <= 0;
        public bool IsDodging => state.active != 0;
        public double Elapsed => state.elapsed;

        public double RechargeFraction => IsFull || rechargeSeconds <= 0.0 ? 0.0 : Math.Min(1.0, Math.Max(0.0, 1.0 - state.recharge_remaining / rechargeSeconds));

        public void Reset()
        {
            fixed (ShatterDodgeState* p = &state)
                NativeCallException.ThrowIfFailed("shatter_dodge_init", ShatterNative.shatter_dodge_init(db.DangerousGetHandle(), p));
        }

        public void Tick(double dt)
        {
            fixed (ShatterDodgeState* p = &state)
                NativeCallException.ThrowIfFailed("shatter_dodge_tick", ShatterNative.shatter_dodge_tick(db.DangerousGetHandle(), p, dt));
        }

        public DodgeStartStatus TryStart(double resourceAvailable)
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

    /// <summary>Chefe nativo (<c>shatter_boss</c>). Guarda o banco; o handle segura o banco até ser descartado.</summary>
    internal sealed unsafe class NativeBoss : IBossController
    {
        internal readonly BossHandle Handle;
        readonly DbHandle db;
        bool holdsDb;
        ShatterBossEvent[] buffer = new ShatterBossEvent[8];

        // Os eventos do core ficam no handle: o Step os zera e ApplyDamage/ApplyEffect ACRESCENTAM. So o que ainda nao foi lido
        // (depois de consumed) e entregue, uma vez: o que um aplicar gerou entre dois passos sai junto com o proximo Step.
        readonly List<BossEvent> pending = new List<BossEvent>(4);
        int consumed;

        internal NativeBoss(BossHandle handle, DbHandle db)
        {
            Handle = handle;
            this.db = db;
            db.DangerousAddRef(ref holdsDb);
        }

        public void Start() => Call(() => ShatterNative.shatter_boss_start(Handle.DangerousGetHandle()), "shatter_boss_start");

        public void Reset(IStatBlock statsOrNull)
        {
            var raw = statsOrNull is NativeStatBlock n ? n.Handle.DangerousGetHandle() : IntPtr.Zero;
            Call(() => ShatterNative.shatter_boss_reset(Handle.DangerousGetHandle(), raw), "shatter_boss_reset");
        }

        public void Step(double dt, double bossX, double bossZ, double playerX, double playerZ, IStatBlock stats, List<BossEvent> events)
        {
            var native = stats as NativeStatBlock ?? throw new ArgumentException("stats must come from this rules core", nameof(stats));
            var ctx = new ShatterBossContext { boss = new ShatterVec2 { x = bossX, z = bossZ }, player = new ShatterVec2 { x = playerX, z = playerZ } };
            nuint count = 0;
            bool a = false, s2 = false;
            try
            {
                Handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                NativeCallException.ThrowIfFailed("shatter_boss_step", ShatterNative.shatter_boss_step(Handle.DangerousGetHandle(), dt, &ctx, native.Handle.DangerousGetHandle(), &count));
                consumed = 0; // o Step zerou a lista do core
                if (events != null)
                {
                    events.AddRange(pending);
                    ReadEvents(0, events);
                }
                pending.Clear();
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) Handle.DangerousRelease();
            }
        }

        public BossDamageResult ApplyDamage(double amount, double bossX, double bossZ, double originX, double originZ)
        {
            ShatterBossDamage r;
            bool a = false;
            try
            {
                Handle.DangerousAddRef(ref a);
                NativeCallException.ThrowIfFailed("shatter_boss_apply_damage", ShatterNative.shatter_boss_apply_damage(Handle.DangerousGetHandle(), amount,
                    new ShatterVec2 { x = bossX, z = bossZ }, new ShatterVec2 { x = originX, z = originZ }, &r));
            }
            finally
            {
                if (a) Handle.DangerousRelease();
            }
            DrainEvents();
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

        public bool WallHit(IStatBlock stats)
        {
            var native = stats as NativeStatBlock ?? throw new ArgumentException("stats must come from this rules core", nameof(stats));
            byte applied;
            bool a = false, s2 = false;
            try
            {
                Handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                NativeCallException.ThrowIfFailed("shatter_boss_wall_hit", ShatterNative.shatter_boss_wall_hit(Handle.DangerousGetHandle(), native.Handle.DangerousGetHandle(), &applied));
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) Handle.DangerousRelease();
            }
            DrainEvents(); // os eventos (PatternInterrupted, StaggerStart, ShieldDown) saem no proximo Step
            return applied != 0;
        }

        public bool ShieldCovers(double bossX, double bossZ, double originX, double originZ)
        {
            byte value;
            bool a = false;
            try
            {
                Handle.DangerousAddRef(ref a);
                NativeCallException.ThrowIfFailed("shatter_boss_shield_covers", ShatterNative.shatter_boss_shield_covers(Handle.DangerousGetHandle(),
                    new ShatterVec2 { x = bossX, z = bossZ }, new ShatterVec2 { x = originX, z = originZ }, &value));
            }
            finally
            {
                if (a) Handle.DangerousRelease();
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
                    Handle.DangerousAddRef(ref a);
                    NativeCallException.ThrowIfFailed("shatter_boss_info_get", ShatterNative.shatter_boss_info_get(Handle.DangerousGetHandle(), &i));
                }
                finally
                {
                    if (a) Handle.DangerousRelease();
                }
                return new BossInfo
                {
                    Life = i.life, MaxLife = i.max_life, ShieldDownRemaining = i.shield_down_remaining, TurnRateDegPerSec = i.turn_rate_deg_per_sec,
                    FacingX = i.facing_x, FacingZ = i.facing_z, StaggerRemaining = i.stagger_remaining, StunRemaining = i.stun_remaining,
                    Phase = i.phase, State = (BossState)i.state, ShieldUp = i.shield_up != 0, Invulnerable = i.invulnerable != 0,
                };
            }
        }

        /// <summary>Le o que um ApplyDamage/ApplyEffect acrescentou a lista do core e guarda para sair no proximo Step.</summary>
        internal void DrainEvents()
        {
            bool a = false;
            try
            {
                Handle.DangerousAddRef(ref a);
                ReadEvents(consumed, pending);
            }
            finally
            {
                if (a) Handle.DangerousRelease();
            }
        }

        // Copia os eventos do core de from ate o fim para events e marca tudo como lido.
        void ReadEvents(int from, List<BossEvent> events)
        {
            nuint needed = 0;
            for (var attempt = 0; attempt < 2; attempt++)
            {
                int status;
                fixed (ShatterBossEvent* p = buffer)
                    status = ShatterNative.shatter_boss_events(Handle.DangerousGetHandle(), p, (nuint)buffer.Length, &needed);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new ShatterBossEvent[checked((int)needed)];
                    continue;
                }
                NativeCallException.ThrowIfFailed("shatter_boss_events", status);
                break;
            }
            var n = checked((int)needed);
            fixed (ShatterBossEvent* p = buffer)
            {
                for (var i = from; i < n; i++)
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
            consumed = n;
        }

        static string Text(byte* field)
        {
            var n = 0;
            while (n < 64 && field[n] != 0) n++;
            return n == 0 ? string.Empty : Encoding.UTF8.GetString(field, n);
        }

        void Call(Func<int> call, string name)
        {
            bool a = false;
            try
            {
                Handle.DangerousAddRef(ref a);
                NativeCallException.ThrowIfFailed(name, call());
            }
            finally
            {
                if (a) Handle.DangerousRelease();
            }
        }

        public void Dispose()
        {
            Handle.Dispose();
            if (holdsDb)
            {
                holdsDb = false;
                db.DangerousRelease();
            }
        }
    }
}
