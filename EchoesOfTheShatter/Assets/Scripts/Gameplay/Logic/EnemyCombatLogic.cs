using System;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Comportamento de um inimigo no passo fixo: alimenta a <see cref="EnemyBrainLogic"/> com a
    /// percepção do herói, publica o telegraph, resolve o impacto pela forma do ataque e gira no
    /// ritmo do dado. Pura: o <c>EnemyController</c> aplica o movimento (NavMeshAgent ou direto).
    /// </summary>
    public sealed class EnemyCombatLogic : ICombatActor, IAttackSelector
    {
        readonly Combatant self;
        readonly IRulesCore rules;
        readonly EnemyInfo enemy;
        readonly SkillInfo[] attackSkills;
        CombatSystem combat;
        PlanarVector attackDirection = PlanarVector.Forward;
        PlanarVector attackOrigin;
        int activeTelegraphId;

        public EnemyCombatLogic(Combatant self, IRulesCore rules)
        {
            this.self = self ?? throw new ArgumentNullException(nameof(self));
            this.rules = rules ?? throw new ArgumentNullException(nameof(rules));
            enemy = self.Enemy ?? throw new ArgumentException("combatant must be an enemy", nameof(self));

            var attacks = enemy.Attacks;
            attackSkills = new SkillInfo[attacks.Count];
            var profiles = new EnemyAttackProfile[attacks.Count];
            for (var i = 0; i < attacks.Count; i++)
            {
                var skill = attacks[i].Skill;
                attackSkills[i] = skill;
                var timing = rules.GetActionTiming(self.Stats, skill);
                profiles[i] = new EnemyAttackProfile(AttackReach(skill), timing.Windup, timing.Impact, timing.Recovery);
            }
            Brain = new EnemyBrainLogic(WorldUnits.ToMeters(enemy.AggroRangeUu), profiles, this);
        }

        public EnemyBrainLogic Brain { get; }
        public Combatant Self => self;
        public SkillInfo CurrentAttackSkill =>
            Brain.CurrentAttack >= 0 && Brain.CurrentAttack < attackSkills.Length ? attackSkills[Brain.CurrentAttack] : null;

        /// <summary>Eventos do último passo.</summary>
        public EnemyBrainEvents LastEvents { get; private set; }

        /// <summary>Mudança de estado da IA (de, para), para o log de depuração dos 5 estados (RF-20).</summary>
        public event Action<EnemyBrainState, EnemyBrainState> StateChanged;

        /// <summary>Velocidade de perseguição em m/s (0 se parado ou atordoado).</summary>
        public float ChaseSpeed { get; private set; }

        /// <summary>A IA quer andar até o alvo neste momento.</summary>
        public bool WantsToMove { get; private set; }

        /// <summary>Posição do alvo para o agente de navegação.</summary>
        public PlanarVector MoveTarget { get; private set; }

        /// <summary>Distância (até a borda do alvo) em que a perseguição para: o alcance do ataque escolhido.</summary>
        public float StopDistance => Brain.CurrentAttack >= 0 ? Brain.CurrentProfile.RangeMeters : 0f;

        int IAttackSelector.SelectAttack()
        {
            if (combat == null) return attackSkills.Length > 0 ? 0 : -1;
            return combat.PickAttack(enemy);
        }

        public void FixedTick(CombatSystem combatSystem, double dt)
        {
            combat = combatSystem;
            var target = combatSystem.Hero;
            var hasTarget = target != null && !target.IsDead;
            var toTarget = hasTarget ? target.Position - self.Position : PlanarVector.Zero;
            var input = new EnemyBrainInput
            {
                HasTarget = hasTarget,
                DistanceToTarget = hasTarget ? Math.Max(0f, toTarget.Magnitude - target.RadiusMeters) : float.MaxValue,
                CanAct = rules.CanAct(self.Stats),
            };

            // Parado não acompanha o herói com o olhar; gira só depois do aggro.
            if (hasTarget && Brain.CanRotate && Brain.State != EnemyBrainState.Idle)
            {
                var maxDegrees = (float)(enemy.TurnRateDegreesPerSecond * dt);
                self.Forward = PlanarVector.RotateTowards(self.Forward, toTarget, maxDegrees);
            }

            var before = Brain.State;
            var events = Brain.Tick(dt, in input);
            LastEvents = events;
            if (Brain.State != before) StateChanged?.Invoke(before, Brain.State);

            if ((events & EnemyBrainEvents.TelegraphStarted) != 0) BeginTelegraph(combatSystem);
            if ((events & EnemyBrainEvents.AttackImpact) != 0) ResolveImpact(combatSystem);
            if ((events & EnemyBrainEvents.Interrupted) != 0) EndTelegraph(combatSystem);

            var canMove = rules.CanMove(self.Stats);
            WantsToMove = hasTarget && canMove && Brain.WantsToMove && input.DistanceToTarget > StopDistance;
            MoveTarget = hasTarget ? target.Position : self.Position;
            ChaseSpeed = WantsToMove ? WorldUnits.ToMeters(rules.GetMoveSpeedUu(self.Stats, enemy.MoveSpeedUu)) : 0f;
        }

        public void FrozenTick(CombatSystem combatSystem, double dt)
        {
            WantsToMove = false;
            ChaseSpeed = 0f;
        }

        public void OnIncomingHitAvoided(CombatSystem combatSystem, Combatant attacker)
        {
        }

        public void OnKilled(CombatSystem combatSystem, Combatant victim)
        {
        }

        public void OnDeath(CombatSystem combatSystem)
        {
            EndTelegraph(combatSystem);
            var before = Brain.State;
            Brain.Kill();
            StateChanged?.Invoke(before, Brain.State);
            WantsToMove = false;
            ChaseSpeed = 0f;
        }

        public void OnRevive(CombatSystem combatSystem)
        {
            Brain.Reset();
        }

        /// <summary>Velocidade no plano para este quadro quando não há NavMeshAgent (m/s).</summary>
        public PlanarVector DirectVelocity()
        {
            if (!WantsToMove || self.Hitstop.IsActive) return PlanarVector.Zero;
            return (MoveTarget - self.Position).NormalizedOr(self.Forward) * ChaseSpeed;
        }

        void BeginTelegraph(CombatSystem combatSystem)
        {
            var skill = CurrentAttackSkill;
            if (skill == null) return;
            // A direção é a de onde o inimigo olha agora (ele gira no ritmo do dado): quem contorna um
            // inimigo lento, como o Guardião, fica fora do cone (docs/13, item 4.2).
            attackDirection = self.Forward.NormalizedOr(PlanarVector.Forward);
            attackOrigin = self.Position; // o golpe sai de onde o aviso foi desenhado (knockback no meio não muda)
            activeTelegraphId = combatSystem.NextTelegraphId();

            var attack = enemy.Attacks[Brain.CurrentAttack];
            var evt = new TelegraphEvent
            {
                TelegraphId = activeTelegraphId,
                Started = true,
                Owner = self,
                Origin = attackOrigin,
                Direction = attackDirection,
                DurationSeconds = Brain.CurrentProfile.Windup,
                ShowOnGround = attack.Telegraphed,
            };
            switch (skill.Shape)
            {
                case SkillShape.Area:
                    evt.Shape = TelegraphShape.Circle;
                    evt.RangeMeters = WorldUnits.ToMeters(skill.RadiusUu);
                    break;
                case SkillShape.Projectile:
                    evt.Shape = TelegraphShape.Line;
                    evt.RangeMeters = WorldUnits.ToMeters(skill.RangeUu);
                    evt.WidthMeters = WorldUnits.ToMeters(skill.RadiusUu) * 2f;
                    break;
                default:
                    evt.Shape = TelegraphShape.Cone;
                    evt.RangeMeters = WorldUnits.ToMeters(skill.RangeUu);
                    evt.HalfAngleDegrees = (float)(skill.ConeAngleDegrees * 0.5);
                    break;
            }
            combatSystem.Events.Publish(in evt);
        }

        void EndTelegraph(CombatSystem combatSystem)
        {
            if (activeTelegraphId == 0) return;
            var evt = new TelegraphEvent { TelegraphId = activeTelegraphId, Started = false, Owner = self };
            activeTelegraphId = 0;
            combatSystem.Events.Publish(in evt);
        }

        void ResolveImpact(CombatSystem combatSystem)
        {
            EndTelegraph(combatSystem);
            var skill = CurrentAttackSkill;
            if (skill == null) return;

            var targets = combatSystem.Combatants;
            switch (skill.Shape)
            {
                case SkillShape.Projectile:
                {
                    var speed = WorldUnits.ToMeters(skill.ProjectileSpeedUu);
                    var range = WorldUnits.ToMeters(skill.RangeUu);
                    var radius = WorldUnits.ToMeters(skill.RadiusUu);
                    var count = Math.Max(1, skill.Projectiles);
                    for (var i = 0; i < count; i++)
                        combatSystem.Projectiles.Spawn(combatSystem, self, skill, attackOrigin, attackDirection, speed, range, radius);
                    break;
                }
                case SkillShape.Area:
                {
                    var radius = WorldUnits.ToMeters(skill.RadiusUu);
                    for (var i = 0; i < targets.Count; i++)
                    {
                        var t = targets[i];
                        if (t.IsDead || !CombatSystem.AreHostile(self, t)) continue;
                        if (ShapeQuery.InCircle(attackOrigin, radius, t.Position, t.RadiusMeters))
                            combatSystem.ApplySkillHit(self, t, skill, attackOrigin);
                    }
                    break;
                }
                default:
                {
                    var range = WorldUnits.ToMeters(skill.RangeUu);
                    var half = (float)(skill.ConeAngleDegrees * 0.5);
                    for (var i = 0; i < targets.Count; i++)
                    {
                        var t = targets[i];
                        if (t.IsDead || !CombatSystem.AreHostile(self, t)) continue;
                        if (ShapeQuery.InCone(attackOrigin, attackDirection, range, half, t.Position, t.RadiusMeters))
                            combatSystem.ApplySkillHit(self, t, skill, attackOrigin);
                    }
                    break;
                }
            }
        }

        /// <summary>Distância em que o telegraph começa: a mesma da consulta do impacto (o aviso não mente).</summary>
        static float AttackReach(SkillInfo skill)
        {
            switch (skill.Shape)
            {
                case SkillShape.Area: return WorldUnits.ToMeters(skill.RadiusUu);
                default: return WorldUnits.ToMeters(skill.RangeUu);
            }
        }
    }
}
