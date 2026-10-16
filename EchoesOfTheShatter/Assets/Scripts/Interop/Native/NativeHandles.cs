using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace Echoes.Interop.Native
{
    // Dono de cada handle opaco da API C: o C# (docs/04_arquitetura.md, secao 9.2). Descartar libera a
    // memoria da DLL; uma chamada em andamento segura o handle por DangerousAddRef/DangerousRelease.

    /// <summary><c>shatter_db</c>: ContentDB imutavel depois de finalizado.</summary>
    internal sealed class DbHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public DbHandle() : base(true) { }

        public DbHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_db_destroy(handle);
            return true;
        }
    }

    /// <summary><c>shatter_statblock</c>: atributos de uma entidade (main thread).</summary>
    internal sealed class StatBlockHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public StatBlockHandle() : base(true) { }

        public StatBlockHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_statblock_destroy(handle);
            return true;
        }
    }

    /// <summary><c>shatter_effects</c>: efeitos ativos de uma entidade (main thread).</summary>
    internal sealed class EffectsHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public EffectsHandle() : base(true) { }

        public EffectsHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_effects_destroy(handle);
            return true;
        }
    }

    /// <summary><c>shatter_actor</c>: stun, imunidades e Guarda Quebrada de uma entidade (main thread).</summary>
    internal sealed class ActorHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public ActorHandle() : base(true) { }

        public ActorHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_actor_destroy(handle);
            return true;
        }
    }

    /// <summary><c>shatter_potions</c>: cinto de pocoes de um personagem (main thread).</summary>
    internal sealed class PotionsHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public PotionsHandle() : base(true) { }

        public PotionsHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_potions_destroy(handle);
            return true;
        }
    }

    /// <summary><c>shatter_boss</c>: maquina de fases do chefe; guarda o banco que o criou (destruir o boss ANTES do banco).</summary>
    internal sealed class BossHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public BossHandle() : base(true) { }

        public BossHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_boss_destroy(handle);
            return true;
        }
    }

    /// <summary>Falha de uma chamada nativa que o chamador nao previu (bug ou uso fora do contrato).</summary>
    public sealed class NativeCallException : InvalidOperationException
    {
        public RulesStatus Status { get; }

        public NativeCallException(string function, int status, string detail = null)
            : base(Format(function, status, detail))
        {
            Status = (RulesStatus)status;
        }

        static string Format(string function, int status, string detail)
        {
            var text = $"{function} failed with status {status} ({(RulesStatus)status})";
            return string.IsNullOrEmpty(detail) ? text : text + ": " + detail;
        }

        internal static void ThrowIfFailed(string function, int status)
        {
            if (status != 0) throw new NativeCallException(function, status);
        }
    }
}
