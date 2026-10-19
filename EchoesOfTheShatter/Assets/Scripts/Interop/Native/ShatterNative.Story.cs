using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace Echoes.Interop.Native
{
    // Historia da campanha (shatter_c.h, shatter_story_*; docs/tecnico/09 secao 15): Ecos da Queda, veredito Exorcizar/Devorar e Fome.
    // Tudo e regra do core; o C# so chama e mostra.

    /// <summary><c>shatter_story</c>: tabelas de Story/ carregadas (imutavel; main thread).</summary>
    internal sealed class StoryHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        public StoryHandle() : base(true) { }

        public StoryHandle(IntPtr raw) : base(true) { SetHandle(raw); }

        protected override bool ReleaseHandle()
        {
            ShatterNative.shatter_story_destroy(handle);
            return true;
        }
    }

    internal static unsafe partial class ShatterNative
    {
        const string StoryLib = "shattercore";

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_story_load_directory(byte* path, nuint pathLen, IntPtr db, IntPtr* output, ShatterError* err);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern void shatter_story_destroy(IntPtr story);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_story_record_echo(IntPtr story, IntPtr save, byte* echoId, nuint echoIdLen, byte* isNew);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_story_apply_verdict(IntPtr story, IntPtr save, byte* verdictId, nuint verdictIdLen, int* result);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_story_state_json(IntPtr story, IntPtr save, byte* output, nuint cap, nuint* needed);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_story_region_json(IntPtr story, IntPtr save, byte* regionId, nuint regionIdLen, byte* output, nuint cap, nuint* needed);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_story_skill_revealed(IntPtr story, IntPtr save, byte* regionId, nuint regionIdLen, byte* skillId, nuint skillIdLen, byte* revealed);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_statblock_add_modifier(IntPtr statblock, ShatterModifier* mod, byte* source, nuint sourceLen);

        [DllImport(StoryLib, CallingConvention = CallingConvention.Cdecl)]
        public static extern int shatter_statblock_remove_modifiers_from(IntPtr statblock, byte* source, nuint sourceLen, uint* removed);
    }

    /// <summary>
    /// As tabelas de Story/ carregadas pelo core. Fica vivo na cena enquanto o jogo precisa da historia; descartar libera a memoria da DLL.
    /// </summary>
    public sealed unsafe class StoryDb : IDisposable
    {
        readonly StoryHandle handle;

        StoryDb(StoryHandle handle)
        {
            this.handle = handle;
        }

        internal IntPtr Raw => handle.DangerousGetHandle();

        public void Dispose() => handle.Dispose();

        /// <summary>
        /// Carrega e valida a pasta <paramref name="storyDirectory"/> (a Story/ ao lado dos CSV do conteudo), conferindo mapas, inimigos e habilidades
        /// contra <paramref name="rules"/>. Devolve null e preenche <paramref name="error"/> se a pasta faltar ou uma tabela for invalida.
        /// </summary>
        public static StoryDb Load(NativeRulesCore rules, string storyDirectory, out string error)
        {
            error = string.Empty;
            if (rules == null) { error = "no rules core"; return null; }
            var path = NativeBuffers.Utf8(storyDirectory);
            IntPtr raw = IntPtr.Zero;
            ShatterError err = default;
            int status;
            fixed (byte* p = path) status = ShatterNative.shatter_story_load_directory(p, (nuint)path.Length, rules.DbPointer, &raw, &err);
            if (status != 0 || raw == IntPtr.Zero)
            {
                error = $"shatter_story_load_directory: {(RulesStatus)status}: {NativeBuffers.ErrorMessage(ref err)}";
                if (raw != IntPtr.Zero) ShatterNative.shatter_story_destroy(raw);
                return null;
            }
            return new StoryDb(new StoryHandle(raw));
        }
    }
}
