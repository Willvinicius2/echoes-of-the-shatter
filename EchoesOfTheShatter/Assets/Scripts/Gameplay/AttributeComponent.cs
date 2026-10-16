using System;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Dono dos handles do motor de regras de uma entidade na cena (atributos e efeitos) e da
    /// <see cref="Gameplay.Combatant"/> que o combate usa. A apresentação e a UI leem por aqui.
    /// Avisa mudança de vida, morte e volta à vida (eventos C#, lidos uma vez por quadro).
    /// Nunca altera vida: só o CombatSystem faz isso, pelo motor de regras.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class AttributeComponent : MonoBehaviour
    {
        double lastLife = double.NaN;
        bool wasDead;

        public Combatant Combatant { get; private set; }

        public event Action<AttributeComponent> LifeChanged;
        public event Action<AttributeComponent> Died;
        public event Action<AttributeComponent> Revived;

        public double Life => Combatant != null ? Combatant.Life : 0.0;
        public double MaxLife => Combatant != null ? Combatant.MaxLife : 0.0;
        public double Resource => Combatant != null ? Combatant.Resource : 0.0;
        public double MaxResource => Combatant != null ? Combatant.MaxResource : 0.0;
        public double Barrier => Combatant != null ? Combatant.Barrier : 0.0;
        public bool IsDead => Combatant == null || Combatant.IsDead;

        public Combatant CreateHero(IRulesCore rules, in HeroBuild build, ClassInfo classInfo, ItemBaseInfo weapon, float radiusMeters)
        {
            ReleaseHandles();
            var stats = rules.CreateHeroStats(build);
            var effects = rules.CreateEffectSet(stats, null);
            Combatant = new Combatant(CombatTeam.Hero, classInfo.Id, build.Level, stats, effects, classInfo, null, weapon, radiusMeters)
            {
                Owner = this,
                Position = transform.position.ToPlanar(),
                Forward = transform.forward.ToPlanar().NormalizedOr(PlanarVector.Forward),
            };
            return Combatant;
        }

        public Combatant CreateEnemy(IRulesCore rules, EnemyInfo enemy, int level, float radiusMeters)
        {
            return CreateEnemy(rules, enemy, level, radiusMeters, default);
        }

        /// <summary>
        /// Inimigo; com <paramref name="elite"/> sorteado (<see cref="CombatSystem.RollElite"/>) o core escreve os multiplicadores no bloco
        /// de atributos e devolve a barreira inicial, e o alvo passa a ser imune ao stun.
        /// </summary>
        public Combatant CreateEnemy(IRulesCore rules, EnemyInfo enemy, int level, float radiusMeters, EliteProfile elite)
        {
            ReleaseHandles();
            var stats = rules.CreateEnemyStats(enemy.Id, level);
            var barrier = !elite.IsNone ? rules.ApplyElite(stats, in elite) : 0.0;
            var effects = rules.CreateEffectSet(stats, enemy, elite.Rolled);
            Combatant = new Combatant(CombatTeam.Enemy, enemy.Id, level, stats, effects, null, enemy, null, radiusMeters)
            {
                Owner = this,
                Position = transform.position.ToPlanar(),
                Forward = transform.forward.ToPlanar().NormalizedOr(PlanarVector.Forward),
                Elite = elite,
                InitialBarrier = barrier,
            };
            return Combatant;
        }

        void LateUpdate()
        {
            var c = Combatant;
            if (c == null) return;
            if (c.Life != lastLife)
            {
                lastLife = c.Life;
                LifeChanged?.Invoke(this);
            }
            if (c.IsDead && !wasDead)
            {
                wasDead = true;
                Died?.Invoke(this);
            }
            else if (!c.IsDead && wasDead)
            {
                wasDead = false;
                Revived?.Invoke(this);
            }
        }

        void OnDestroy()
        {
            ReleaseHandles();
        }

        void ReleaseHandles()
        {
            if (Combatant == null) return;
            Combatant.Effects?.Dispose();
            Combatant.Stats.Dispose();
            Combatant = null;
        }
    }
}
