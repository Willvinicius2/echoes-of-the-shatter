using System;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// <see cref="IStatBlock"/> sobre o handle <c>shatter_statblock</c>. Os valores sao calculados e
    /// guardados em cache pelo core; aqui so se le. Pertence a thread principal.
    /// </summary>
    internal sealed unsafe class NativeStatBlock : IStatBlock
    {
        internal readonly StatBlockHandle Handle;

        /// <summary>Stun/Guarda Quebrada desta entidade (<c>shatter_actor</c>), ligado pelo <see cref="NativeEffectSet"/>; nulo sem efeitos.</summary>
        internal ActorHandle Actor;

        /// <summary>Herói: a velocidade de movimento do atributo já é uu/s (<c>shatter_move_speed</c> com base &lt;= 0).</summary>
        internal bool IsHero;

        public NativeStatBlock(StatBlockHandle handle)
        {
            Handle = handle ?? throw new ArgumentNullException(nameof(handle));
        }

        public double Get(StatId stat) => GetTagged(stat, SkillTags.None);

        public double GetTagged(StatId stat, SkillTags contextTags)
        {
            var addRef = false;
            try
            {
                Handle.DangerousAddRef(ref addRef);
                double value;
                var status = ShatterNative.shatter_statblock_get(Handle.DangerousGetHandle(), (uint)stat, (uint)contextTags, &value);
                NativeCallException.ThrowIfFailed("shatter_statblock_get", status);
                return value;
            }
            finally
            {
                if (addRef) Handle.DangerousRelease();
            }
        }

        public ulong Revision
        {
            get
            {
                var addRef = false;
                try
                {
                    Handle.DangerousAddRef(ref addRef);
                    ulong value;
                    var status = ShatterNative.shatter_statblock_revision(Handle.DangerousGetHandle(), &value);
                    NativeCallException.ThrowIfFailed("shatter_statblock_revision", status);
                    return value;
                }
                finally
                {
                    if (addRef) Handle.DangerousRelease();
                }
            }
        }

        public void Dispose() => Handle.Dispose();
    }
}
