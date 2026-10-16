using System;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Uma entidade do combate (herói ou inimigo) no plano XZ. Guarda os handles do motor de regras
    /// (atributos e efeitos) e os valores correntes (<see cref="Vitals"/>). Vida e recurso só mudam pelo
    /// <see cref="CombatSystem"/> e pelas lógicas do mesmo assembly, sempre via <see cref="IRulesCore"/>.
    /// </summary>
    public sealed class Combatant
    {
        internal Vitals vitals;
        PlanarVector knockbackVelocity;
        float knockbackTimeLeft;

        public Combatant(CombatTeam team, string contentId, int level, IStatBlock stats, IEffectSet effects,
            ClassInfo classInfo, EnemyInfo enemyInfo, ItemBaseInfo weapon, float radiusMeters)
        {
            Team = team;
            ContentId = contentId ?? string.Empty;
            Level = level;
            Stats = stats ?? throw new ArgumentNullException(nameof(stats));
            Effects = effects;
            Class = classInfo;
            Enemy = enemyInfo;
            Weapon = weapon;
            RadiusMeters = radiusMeters;
            Forward = PlanarVector.Forward;
        }

        /// <summary>Identificador na sessão de combate (ordem de registro). 0 = não registrado.</summary>
        public int Id { get; internal set; }
        public CombatTeam Team { get; }
        public string ContentId { get; }
        public int Level { get; }
        public IStatBlock Stats { get; }
        public IEffectSet Effects { get; }
        public ClassInfo Class { get; }
        public EnemyInfo Enemy { get; }
        public ItemBaseInfo Weapon { get; }
        public float RadiusMeters { get; }
        public ICombatActor Actor { get; internal set; }
        public bool IsRegistered { get; internal set; }

        /// <summary>Quem é dono desta entidade na cena (o MonoBehaviour), para a apresentação achar o objeto.</summary>
        public object Owner { get; set; }

        public PlanarVector Position { get; set; }
        public PlanarVector Forward { get; set; }

        public Vitals Vitals => vitals;
        public double Life => vitals.Life;
        public double Resource => vitals.Resource;
        public double Barrier => vitals.Barrier;
        public double MaxLife => Stats.Get(StatId.Life);
        public double MaxResource => Stats.Get(StatId.Resource);
        public bool IsDead => vitals.Life <= 0.0;
        public bool IsBoss => Enemy != null && Enemy.IsBoss;
        public bool IsElite => Enemy != null && Enemy.IsElite;

        public bool IsInvulnerable { get; internal set; }
        public HitstopTimer Hitstop { get; } = new HitstopTimer();

        /// <summary>Segundos desde o último golpe dado ou recebido.</summary>
        public double SecondsSinceCombat { get; internal set; } = double.MaxValue;

        public bool IsKnockedBack => knockbackTimeLeft > 0f;

        internal void SetVitals(in Vitals value)
        {
            vitals = value;
        }

        internal void StartKnockback(PlanarVector direction, float distanceMeters, float seconds)
        {
            if (distanceMeters <= 0f) return;
            if (seconds <= 0f)
            {
                Position += direction.Normalized * distanceMeters;
                return;
            }
            knockbackVelocity = direction.Normalized * (distanceMeters / seconds);
            knockbackTimeLeft = seconds;
        }

        /// <summary>Deslocamento de knockback deste quadro (a cena aplica no CharacterController/agente).</summary>
        public PlanarVector ConsumeKnockback(float deltaTime)
        {
            if (knockbackTimeLeft <= 0f || deltaTime <= 0f) return PlanarVector.Zero;
            var t = Math.Min(deltaTime, knockbackTimeLeft);
            knockbackTimeLeft -= t;
            return knockbackVelocity * t;
        }

        public override string ToString() => $"{ContentId}#{Id}";
    }
}
