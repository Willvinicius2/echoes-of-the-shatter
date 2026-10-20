using System;

namespace Echoes.Interop
{
    /// <summary>
    /// Atributos de uma entidade (handle <c>shatter_statblock</c> da API C). O dono é o C#:
    /// descartar com <see cref="IDisposable.Dispose"/>. Pertence à thread principal.
    /// </summary>
    public interface IStatBlock : IDisposable
    {
        /// <summary>Valor final sem tags de contexto.</summary>
        double Get(StatId stat);

        /// <summary>Valor final no contexto das tags (habilidade e/ou tipo de dano).</summary>
        double GetTagged(StatId stat, SkillTags contextTags);

        /// <summary>Muda a cada alteração de modificador; quem espelha os valores relê quando muda.</summary>
        ulong Revision { get; }
    }
}
