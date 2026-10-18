using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// O lado do herói que o <see cref="CombatSystem"/> consulta a cada golpe recebido (docs/18, 8.1): a geometria do arco da defesa, a janela da
    /// defesa perfeita e o que ela ganha, o dreno de recurso. Os números vêm do <see cref="IBasicKit"/> (core); a regra de dano continua no core
    /// (<see cref="HitRequest.FromGuardArc"/>).
    /// </summary>
    public interface IHeroGuardian
    {
        /// <summary>O herói está andando (a regeneração do recurso do Foco cai enquanto anda).</summary>
        bool IsMoving { get; }

        /// <summary>O golpe vindo de <paramref name="from"/> bate dentro do arco da defesa? Falso se não está defendendo.</summary>
        bool GuardCovers(PlanarVector from);

        /// <summary>Dentro da janela da defesa perfeita.</summary>
        bool GuardPerfectOpen { get; }

        double GuardPerfectResource { get; }
        IReadOnlyList<string> GuardPerfectEffects { get; }

        /// <summary>Recurso gasto por ponto de dano evitado (0 = a defesa não gasta).</summary>
        double GuardDrainPerDamage { get; }
    }

    /// <summary>Um golpe foi absorvido pela defesa (dentro do arco). <see cref="Perfect"/> = defesa perfeita: 0 de dano.</summary>
    public struct GuardBlockEvent
    {
        public Combatant Attacker;
        public Combatant Target;
        public SkillInfo Skill;
        public bool Perfect;
        public PlanarVector Position;
    }
}
