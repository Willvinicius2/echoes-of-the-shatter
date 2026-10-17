using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Entrega o <see cref="IBasicKit"/> de uma classe. Os valores vêm do core (<c>basic_kits.csv</c> e as chaves de <c>rules.csv</c>, docs/18
    /// seção 8.1) por <see cref="CoreBasicKit"/>. Sem kit no core (stub, classe sem linha), devolve null e o herói usa a entrada antiga
    /// (um clique = um golpe do espaço 0), sem combo, carga nem defesa.
    /// </summary>
    public static class BasicKitSource
    {
        /// <summary>
        /// Só para testes de PlayMode: fábrica de kit usada no lugar do core (os testes declaram os próprios valores falsos; o jogo nunca a define).
        /// Quem define precisa devolver null para limpar.
        /// </summary>
        public static System.Func<IRulesCore, string, IBasicKit> TestFactory { get; set; }

        public static IBasicKit For(IRulesCore rules, string classId)
        {
            return TestFactory != null ? TestFactory(rules, classId) : CoreBasicKit.Create(rules, classId);
        }
    }
}
