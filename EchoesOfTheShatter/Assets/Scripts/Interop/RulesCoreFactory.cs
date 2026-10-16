namespace Echoes.Interop
{
    /// <summary>
    /// Escolhe a implementação do motor de regras. Hoje só existe o stub em C#; quando a DLL
    /// <c>shattercore</c> e o <c>shatter_c.h</c> chegarem, a implementação P/Invoke entra aqui
    /// e o stub sai (a interface <see cref="IRulesCore"/> não muda).
    /// </summary>
    public static class RulesCoreFactory
    {
        public static IRulesCore CreateDefault()
        {
            return new StubRulesCore();
        }
    }
}
