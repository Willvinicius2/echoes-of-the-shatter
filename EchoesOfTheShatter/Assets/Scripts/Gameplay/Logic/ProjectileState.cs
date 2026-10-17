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
        /// <summary>Multiplicador de dano do golpe forte carregado (1 = golpe comum).</summary>
        public double HitMultiplier = 1.0;
        /// <summary>Quantos alvos o projétil acerta antes de acabar: 1 sem perfuração; Pierce + 1 com perfuração; int.MaxValue atravessa todos.</summary>
        public int MaxHits = 1;
        /// <summary>Raio da explosão no ponto do impacto, em metros (0 = o projétil não explode). Habilidade com Behavior.Explodes.</summary>
        public float ExplosionRadiusMeters;
        /// <summary>Alvos que ESTE projétil já acertou (RF-16: um acerto por alvo por projétil; outro projétil do leque pode acertar o mesmo alvo).</summary>
        public readonly List<int> HitTargets = new List<int>(4);
        public bool Active;
    }
}
