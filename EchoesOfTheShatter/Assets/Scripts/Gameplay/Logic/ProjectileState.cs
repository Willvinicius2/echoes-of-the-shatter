using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>Um projétil em voo (em pool dentro do <see cref="ProjectileSystem"/>).</summary>
    public sealed class ProjectileState
    {
        public int Id;
        public Combatant Owner;
        public SkillInfo Skill;
        public PlanarVector Position;
        public PlanarVector Direction;
        public float SpeedMetersPerSecond;
        public float RemainingMeters;
        public float RadiusMeters;
        /// <summary>Golpe forte (o core aplica o multiplicador do kit pela carga): <see cref="ChargeFraction"/> vai ao HitRequest.</summary>
        public bool IsHeavy;
        /// <summary>Progresso da carga do golpe forte, 0 a 1.</summary>
        public double ChargeFraction;
        /// <summary>Quantos alvos o projétil acerta antes de acabar: 1 sem perfuração; Pierce + 1 com perfuração; int.MaxValue atravessa todos.</summary>
        public int MaxHits = 1;
        /// <summary>Raio da explosão no ponto do impacto, em metros (0 = o projétil não explode). Habilidade com Behavior.Explodes.</summary>
        public float ExplosionRadiusMeters;
        /// <summary>Alvos que ESTE projétil já acertou (RF-16: um acerto por alvo por projétil; outro projétil do leque pode acertar o mesmo alvo).</summary>
        public readonly List<int> HitTargets = new List<int>(4);
        public bool Active;
    }
}
