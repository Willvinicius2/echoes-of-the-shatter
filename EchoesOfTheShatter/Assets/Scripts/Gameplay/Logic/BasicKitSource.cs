using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Entrega o <see cref="IBasicKit"/> de uma classe. Os valores vêm do core (<c>basic_kits.csv</c> e as chaves novas de <c>rules.csv</c>,
    /// docs/18 seção 8.1). Enquanto o core não expõe a tabela (branch etapa3/combate-core do Backend), devolve null e o herói usa a entrada
    /// antiga (um clique = um golpe do espaço 0), sem combo, carga nem defesa.
    /// TODO(backend): trocar o corpo por um adaptador sobre a API C quando o merge chegar; a máquina em <see cref="HeroCombatLogic"/> não muda.
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
            return TestFactory != null ? TestFactory(rules, classId) : null;
        }
    }
}
