using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// <see cref="IEffectSet"/> sobre o handle <c>shatter_effects</c>. Os modificadores entram e saem do
    /// <see cref="NativeStatBlock"/> do alvo pelo proprio core. Duas coisas que a API C v1 nao traz ficam
    /// aqui, vindas do conteudo do stub: a imunidade a atordoamento por inimigo (elite, chefe, familia
    /// construct; docs/13 item 3) e as tags de cada efeito nos eventos de dano.
    /// </summary>
    internal sealed unsafe class NativeEffectSet : IEffectSet
    {
        const uint TriggerNone = 0;
        const uint EventExpired = 1;

        readonly EffectsHandle handle;
        readonly DbHandle db;
        readonly NativeStatBlock target;
        readonly StubContent stubContent;
        readonly ActorHandle actor;
        ActorApplyResult lastApply;
        ShatterEffectEvent[] eventBuffer = new ShatterEffectEvent[8];
        bool holdsDb;

        public NativeEffectSet(EffectsHandle handle, DbHandle db, NativeStatBlock target, StubContent stubContent, ActorHandle actor)
        {
            this.handle = handle;
            this.db = db;
            this.target = target;
            this.stubContent = stubContent;
            this.actor = actor;
            target.Actor = actor; // CanAct/CanMove do IRulesCore consideram stun e stagger
            // O conjunto de efeitos segura o banco ate ser descartado: descartar o NativeRulesCore antes nao o libera.
            db.DangerousAddRef(ref holdsDb);
        }

        public int ActiveCount
        {
            get
            {
                var addRef = false;
                try
                {
                    handle.DangerousAddRef(ref addRef);
                    var raw = handle.DangerousGetHandle();
                    var status = NativeBuffers.ReadString((byte* o, nuint c, nuint* n) =>
                        ShatterNative.shatter_effects_active_json(raw, o, c, n), out var json, 256);
                    NativeCallException.ThrowIfFailed("shatter_effects_active_json", status);
                    var count = 0;
                    var at = 0;
                    while ((at = json.IndexOf("\"effect_id\"", at, StringComparison.Ordinal)) >= 0)
                    {
                        count++;
                        at += 11;
                    }
                    return count;
                }
                finally
                {
                    if (addRef) handle.DangerousRelease();
                }
            }
        }

        public bool Apply(string effectId, double magnitude, string sourceId)
        {
            if (string.IsNullOrEmpty(effectId)) return false;
            var id = NativeBuffers.Utf8(effectId);
            var source = NativeBuffers.Utf8(sourceId);
            bool a = false, d = false, t = false, c = false;
            try
            {
                handle.DangerousAddRef(ref a);
                db.DangerousAddRef(ref d);
                target.Handle.DangerousAddRef(ref t);
                actor.DangerousAddRef(ref c);
                ShatterActorApply result = default;
                int status;
                fixed (byte* pId = id)
                fixed (byte* pSource = source)
                {
                    // Stun e Guarda Quebrada passam pelo actor (imunidade por inimigo, stagger, timer unico) em vez de effects_apply.
                    status = ShatterNative.shatter_actor_apply_effect(actor.DangerousGetHandle(), db.DangerousGetHandle(),
                        pId, (nuint)id.Length, pSource, (nuint)source.Length, magnitude, handle.DangerousGetHandle(),
                        target.Handle.DangerousGetHandle(), &result);
                }
                lastApply = default;
                if (status == (int)RulesStatus.NotFound || status == (int)RulesStatus.ContentInvalid) return false;
                NativeCallException.ThrowIfFailed("shatter_actor_apply_effect", status);
                lastApply = new ActorApplyResult
                {
                    Applied = result.applied != 0,
                    Stunned = result.stunned != 0,
                    StunBlocked = result.stun_blocked != 0,
                    Interrupted = result.interrupted != 0,
                    Staggered = result.staggered != 0,
                    RemoveBarrier = result.remove_barrier != 0,
                    StunSeconds = result.stun_seconds,
                    StaggerSeconds = result.stagger_seconds,
                    GuardBreakStacks = result.guard_break_stacks,
                };
                return lastApply.Applied;
            }
            finally
            {
                if (c) actor.DangerousRelease();
                if (t) target.Handle.DangerousRelease();
                if (d) db.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }

        public ActorApplyResult LastApply => lastApply;

        public void Tick(double dt, List<EffectTickEvent> outEvents)
        {
            bool a = false, d = false, t = false;
            try
            {
                handle.DangerousAddRef(ref a);
                db.DangerousAddRef(ref d);
                target.Handle.DangerousAddRef(ref t);
                var raw = handle.DangerousGetHandle();
                nuint count = 0;
                var status = ShatterNative.shatter_effects_tick(raw, db.DangerousGetHandle(), dt, target.Handle.DangerousGetHandle(), &count);
                NativeCallException.ThrowIfFailed("shatter_effects_tick", status);
                byte staggerEnded;
                bool c = false;
                try
                {
                    actor.DangerousAddRef(ref c);
                    NativeCallException.ThrowIfFailed("shatter_actor_tick",
                        ShatterNative.shatter_actor_tick(actor.DangerousGetHandle(), dt, target.Handle.DangerousGetHandle(), &staggerEnded));
                }
                finally
                {
                    if (c) actor.DangerousRelease();
                }
                if (count == 0 || outEvents == null) return;

                var n = checked((int)count);
                if (eventBuffer.Length < n) eventBuffer = new ShatterEffectEvent[n];
                nuint needed = 0;
                fixed (ShatterEffectEvent* p = eventBuffer)
                    status = ShatterNative.shatter_effects_events(raw, p, (nuint)eventBuffer.Length, &needed);
                NativeCallException.ThrowIfFailed("shatter_effects_events", status);

                var written = Math.Min(n, checked((int)needed));
                fixed (ShatterEffectEvent* p = eventBuffer)
                {
                    for (var i = 0; i < written; i++)
                    {
                        var e = p + i;
                        var len = (int)Math.Min(e->effect_id_len, 127u);
                        var evt = new EffectTickEvent
                        {
                            Expired = e->kind == EventExpired,
                            EffectId = Encoding.UTF8.GetString(e->effect_id, len),
                        };
                        if (!evt.Expired)
                        {
                            evt.Damage = new DamageByType { Physical = e->damage[0], Fire = e->damage[1], Cold = e->damage[2], Lightning = e->damage[3] };
                            if (stubContent != null && stubContent.Effects.TryGetValue(evt.EffectId, out var data)) evt.Tags = data.Tags;
                        }
                        outEvents.Add(evt);
                    }
                }
            }
            finally
            {
                if (t) target.Handle.DangerousRelease();
                if (d) db.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }

        public int StackCount(string effectId)
        {
            if (string.IsNullOrEmpty(effectId)) return 0;
            var id = NativeBuffers.Utf8(effectId);
            var addRef = false;
            try
            {
                handle.DangerousAddRef(ref addRef);
                int count;
                int status;
                fixed (byte* p = id) status = ShatterNative.shatter_effects_stack_count(handle.DangerousGetHandle(), p, (nuint)id.Length, &count);
                NativeCallException.ThrowIfFailed("shatter_effects_stack_count", status);
                return count;
            }
            finally
            {
                if (addRef) handle.DangerousRelease();
            }
        }

        public void Clear()
        {
            bool a = false, t = false;
            try
            {
                handle.DangerousAddRef(ref a);
                target.Handle.DangerousAddRef(ref t);
                var status = ShatterNative.shatter_effects_clear(handle.DangerousGetHandle(), target.Handle.DangerousGetHandle());
                NativeCallException.ThrowIfFailed("shatter_effects_clear", status);
            }
            finally
            {
                if (t) target.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }

        public void Dispose()
        {
            if (ReferenceEquals(target.Actor, actor)) target.Actor = null;
            actor.Dispose();
            handle.Dispose();
            if (holdsDb)
            {
                holdsDb = false;
                db.DangerousRelease();
            }
        }
    }
}
