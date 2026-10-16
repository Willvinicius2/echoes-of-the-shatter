using System;
using Echoes.Interop.Native;

namespace Echoes.Interop
{
    /// <summary>
    /// Escolhe a implementacao do motor de regras: a DLL nativa <c>shattercore</c> (P/Invoke sobre
    /// <c>shatter_c.h</c>) e, se ela nao carregar, o <see cref="StubRulesCore"/> provisorio em C#.
    /// A interface <see cref="IRulesCore"/> nao muda.
    /// </summary>
    public static class RulesCoreFactory
    {
        /// <summary>Motivo da ultima queda para o stub (vazio se a DLL nativa foi usada).</summary>
        public static string LastFallbackReason { get; private set; } = string.Empty;

        /// <summary>
        /// Nativo se a DLL carregar e bater com a versao e o layout; senao o stub, avisando por
        /// <paramref name="logWarning"/> (o jogo passa o <c>Debug.LogWarning</c>; este assembly nao ve a Unity).
        /// </summary>
        public static IRulesCore CreateDefault(Action<string> logWarning = null)
        {
            if (NativeRulesCore.TryCreate(out var native, out var reason))
            {
                LastFallbackReason = string.Empty;
                return native;
            }
            LastFallbackReason = reason;
            logWarning?.Invoke("[Rules] shattercore nativa indisponivel, usando o StubRulesCore provisorio em C#. Motivo: " + reason);
            return new StubRulesCore();
        }

        /// <summary>Sempre o stub (testes que comparam as duas implementacoes).</summary>
        public static IRulesCore CreateStub() => new StubRulesCore();
    }
}
