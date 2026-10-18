using System;
using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Comportamento de um inimigo no passo fixo: alimenta a <see cref="EnemyBrainLogic"/> com a
    /// percepção do herói, publica o telegraph, resolve o impacto pela forma do ataque e gira no
    /// ritmo do dado. Pura: o <c>EnemyController</c> aplica o movimento (NavMeshAgent ou direto).
    /// </summary>
    public sealed class EnemyCombatLogic : ICombatActor, IAttackSelector, IInterruptible, IDisposable
    {
        readonly Combatant self;
        readonly IRulesCore rules;
        readonly EnemyInfo enemy;
        readonly SkillInfo[] attackSkills;
        CombatSystem combat;
        PlanarVector attackDirection = PlanarVector.Forward;
        PlanarVector attackOrigin;
        int activeTelegraphId;

        // Chefe (core): fases, escudo frontal, rugido, invocação e padrões por seed. Sem chefe nativo (stub), vale a IA comum (Brain).
        readonly List<BossEvent> bossEvents = new List<BossEvent>(8);
        IBossController boss;
        bool bossResolved;
        float bossStopDistance;

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
                // Elite (Veloz): o telegraph não encurta e a recuperação usa o recoveryMult; o core calcula pelo modificador.
                var timing = rules.GetActionTiming(self.Stats, skill, self.Elite.ModifierId);
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
        public float StopDistance => boss != null ? bossStopDistance : Brain.CurrentAttack >= 0 ? Brain.CurrentProfile.RangeMeters : 0f;

        /// <summary>Máquina de fases do chefe (null fora de chefe ou no stub).</summary>
        public IBossController Boss => boss;

        int IAttackSelector.SelectAttack()
        {
            if (combat == null) return attackSkills.Length > 0 ? 0 : -1;
            return combat.PickAttack(enemy);
        }

        /// <summary>true = inimigo parado e sem IA (o chefe antes do gatilho da arena). Sem passo, sem telegraph, sem movimento.</summary>
        public bool Dormant { get; set; }

        /// <summary>
        /// R-VIS-1 (docs/14, seção 8.2): atirador só começa a mirar com ele mesmo dentro da área visível do herói menos 1 m; fora dela
        /// anda para dentro. A área vem do frustum da câmera (<see cref="IsInsideVisibleArea"/>). A coluna de dados
        /// <c>requireOnScreen</c> do enemy_ai.csv ainda não existe: hoje o valor vem do layout (JSON) por grupo.
        /// </summary>
        public bool RequireOnScreen { get; set; }

        /// <summary>
        /// A investida do chefe (de, para, raio do corpo) bateria em pilar ou parede? Fornecida pela cena (física). Null = nunca bate.
        /// Quando bate, o core decide o resultado (<see cref="IBossController.WallHit"/>: stagger e escudo caído).
        /// </summary>
        public Func<PlanarVector, PlanarVector, float, bool> IsDashBlocked { get; set; }

        /// <summary>Posição (plano) dentro da área visível reduzida? Null = sem câmera: sempre dentro.</summary>
        public Func<PlanarVector, bool> IsInsideVisibleArea { get; set; }

        /// <summary>Velocidade máxima de movimento em m/s (patrulha usa uma fração dela).</summary>
        public float FullMoveSpeedMeters => WorldUnits.ToMeters(rules.GetMoveSpeedUu(self.Stats, enemy.MoveSpeedUu));

        /// <summary>
        /// true quando não há NavMeshAgent: a lógica integra a perseguição no passo fixo (A-04).
        /// Com agente, quem anda é o agente (a cena copia a posição dele de volta).
        /// </summary>
        public bool IntegratesMovement { get; set; }

        public void FixedTick(CombatSystem combatSystem, double dt)
        {
            if (Dormant)
            {
                WantsToMove = false;
                ChaseSpeed = 0f;
                return;
            }
            if (IntegratesMovement) self.Position += DirectVelocity() * (float)dt;
            combat = combatSystem;
            EnsureBoss(combatSystem);
            if (boss != null)
            {
                BossTick(combatSystem, dt);
                return;
            }
            var target = combatSystem.Hero;
            var hasTarget = target != null && !target.IsDead;
            var toTarget = hasTarget ? target.Position - self.Position : PlanarVector.Zero;

            // Fuga decidida pelo core (shatter_actor_flee_step, uma vez por tick de IA): foge do heroi e depois volta a lutar.
            if (UpdateFlee(combatSystem, dt, hasTarget, toTarget)) return;

            var input = new EnemyBrainInput
            {
                HasTarget = hasTarget,
                DistanceToTarget = hasTarget ? Math.Max(0f, toTarget.Magnitude - target.RadiusMeters) : float.MaxValue,
                CanAct = rules.CanAct(self.Stats),
                HoldFire = RequireOnScreen && IsInsideVisibleArea != null && !IsInsideVisibleArea(self.Position),
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

            if ((events & EnemyBrainEvents.TelegraphStarted) != 0)
            {
                BeginTelegraph(combatSystem);
                PublishPhase(combatSystem, CurrentAttackSkill, ActionPhase.Windup, Brain.CurrentProfile.Windup);
            }
            if ((events & EnemyBrainEvents.AttackImpact) != 0)
            {
                ResolveImpact(combatSystem);
                PublishPhase(combatSystem, CurrentAttackSkill, ActionPhase.Impact, Brain.CurrentProfile.Impact);
            }
            if ((events & EnemyBrainEvents.AttackEnded) != 0) PublishPhase(combatSystem, CurrentAttackSkill, ActionPhase.Recovery, Brain.CurrentProfile.Recovery);
            if ((events & EnemyBrainEvents.Interrupted) != 0)
            {
                EndTelegraph(combatSystem);
                PublishPhase(combatSystem, CurrentAttackSkill, ActionPhase.None, 0.0);
            }
            else if (before == EnemyBrainState.Recover && Brain.State != EnemyBrainState.Recover)
            {
                PublishPhase(combatSystem, CurrentAttackSkill, ActionPhase.None, 0.0);
            }

            var canMove = rules.CanMove(self.Stats);
            WantsToMove = hasTarget && canMove && Brain.WantsToMove && (input.DistanceToTarget > StopDistance || input.HoldFire);
            MoveTarget = hasTarget ? target.Position : self.Position;
            ChaseSpeed = WantsToMove ? WorldUnits.ToMeters(rules.GetMoveSpeedUu(self.Stats, enemy.MoveSpeedUu)) : 0f;
        }

        /// <summary>Estado do chefe vindo do core (vida, fase, escudo); default se este inimigo nao e chefe.</summary>
        public Echoes.Interop.BossInfo BossInfo => boss != null ? boss.Info : default;

        /// <summary>
        /// SO GRAVACAO (RecordMode -scenario boss): dano direto no chefe, vindo de <paramref name="origin"/> (fora do arco do escudo), para chegar a
        /// fase 2 sem a luta inteira. Passa pelo core (escudo, limiar de fase); nunca e chamado no jogo.
        /// </summary>
        public double DevDamageBoss(double amount, PlanarVector origin)
        {
            if (boss == null) return 0.0;
            return boss.ApplyDamage(amount, self.Position.X, self.Position.Z, origin.X, origin.Z).Applied;
        }

        /// <summary>O inimigo esta fugindo (a apresentacao toca a animacao de fuga).</summary>
        public bool IsFleeing { get; private set; }

        /// <summary>
        /// Um passo da fuga, decidido pelo core (shatter_actor_flee_step: fracao de vida, duracao e uma-vez-por-vida de enemy_ai.csv).
        /// Aqui so o movimento: devolve true enquanto foge (o passo de IA normal e pulado e o inimigo corre para longe do heroi).
        /// </summary>
        bool UpdateFlee(CombatSystem combatSystem, double dt, bool hasTarget, PlanarVector toTarget)
        {
            if (self.Effects == null) return false;
            var step = self.Effects.FleeStep(dt, self.Life, self.MaxLife, hasTarget, self.IsDead);
            if (step.Started) OnInterrupted(combatSystem); // cancela o telegraph e o golpe em curso
            IsFleeing = step.Fleeing;
            if (!IsFleeing) return false;
            var away = (-toTarget).NormalizedOr(self.Forward);
            self.Forward = away;
            WantsToMove = rules.CanMove(self.Stats);
            MoveTarget = self.Position + away * 10f;
            ChaseSpeed = WantsToMove ? WorldUnits.ToMeters(rules.GetMoveSpeedUu(self.Stats, enemy.MoveSpeedUu)) : 0f;
            return true;
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

        /// <summary>Stun ou stagger em cima do telegraph (ordem do core): cancela o aviso e o golpe. Chefe: o core manda PatternInterrupted no passo.</summary>
        public void OnInterrupted(CombatSystem combatSystem)
        {
            if (boss != null) return;
            if ((Brain.Interrupt() & EnemyBrainEvents.Interrupted) != 0) EndTelegraph(combatSystem);
        }

        public void Dispose()
        {
            boss?.Dispose();
            boss = null;
            self.Boss = null;
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
            IsFleeing = false;
            self.Effects?.FleeReset();
            dashing = false;
            Brain.Reset();
            if (boss == null) return;
            boss.Reset(self.Stats);
            boss.Start();
        }

        /// <summary>Velocidade de perseguição no plano quando não há NavMeshAgent (m/s); integrada em <see cref="FixedTick"/> se <see cref="IntegratesMovement"/>.</summary>
        public PlanarVector DirectVelocity()
        {
            if (!WantsToMove || self.Hitstop.IsActive) return PlanarVector.Zero;
            return (MoveTarget - self.Position).NormalizedOr(self.Forward) * ChaseSpeed;
        }

        void BeginTelegraph(CombatSystem combatSystem)
        {
            var skill = CurrentAttackSkill;
            if (skill == null) return;
            BeginTelegraph(combatSystem, skill, Brain.CurrentProfile.Windup, enemy.Attacks[Brain.CurrentAttack].Telegraphed);
        }

        void BeginTelegraph(CombatSystem combatSystem, SkillInfo skill, double windupSeconds, bool showOnGround)
        {
            // A direção é a de onde o inimigo olha agora (ele gira no ritmo do dado): quem contorna um
            // inimigo lento, como o Guardião, fica fora do cone (docs/13, item 4.2).
            attackDirection = self.Forward.NormalizedOr(PlanarVector.Forward);
            attackOrigin = self.Position; // o golpe sai de onde o aviso foi desenhado (knockback no meio não muda)
            activeTelegraphId = combatSystem.NextTelegraphId();

            var evt = new TelegraphEvent
            {
                TelegraphId = activeTelegraphId,
                Started = true,
                Owner = self,
                Origin = attackOrigin,
                Direction = attackDirection,
                DurationSeconds = windupSeconds,
                ShowOnGround = showOnGround,
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

        // Fases do ataque para a apresentacao (clipe, velocidade do clipe): mesmo evento do heroi, so o dono muda.
        void PublishPhase(CombatSystem combatSystem, SkillInfo skill, ActionPhase phase, double seconds)
        {
            if (skill == null) return;
            var evt = new SkillPhaseEvent { Owner = self, Skill = skill, Phase = phase, PhaseSeconds = seconds, Direction = attackDirection };
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
            ResolveImpact(combatSystem, CurrentAttackSkill);
        }

        void ResolveImpact(CombatSystem combatSystem, SkillInfo skill)
        {
            EndTelegraph(combatSystem);
            if (skill == null) return;

            var targets = combatSystem.Combatants;
            switch (skill.Shape)
            {
                case SkillShape.Projectile:
                {
                    var speed = WorldUnits.ToMeters(skill.ProjectileSpeedUu);
                    var range = WorldUnits.ToMeters(skill.RangeUu);
                    var radius = ProjectileSystem.BodyRadiusMeters(skill);
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

        // --- Chefe (shatter_boss): o core decide fase, escudo, rugido, invocação e o próximo padrão; o C# só entrega posições e reage ---

        void EnsureBoss(CombatSystem combatSystem)
        {
            if (bossResolved) return;
            bossResolved = true;
            if (!enemy.IsBoss || !rules.SupportsBoss) return;
            try
            {
                boss = rules.CreateBoss(enemy.Id, self.Level, combatSystem.RunSeed + (ulong)self.Id);
            }
            catch (ArgumentException)
            {
                return; // sem fases em boss_phases.csv: IA comum
            }
            self.Boss = boss;
            self.Effects?.BindBoss(boss);
            var reach = float.MaxValue;
            for (var i = 0; i < attackSkills.Length; i++) reach = Math.Min(reach, AttackReach(attackSkills[i]));
            bossStopDistance = reach == float.MaxValue ? 0f : reach;
            boss.Start();
        }

        void BossTick(CombatSystem combatSystem, double dt)
        {
            var target = combatSystem.Hero;
            var hasTarget = target != null && !target.IsDead;
            var toTarget = hasTarget ? target.Position - self.Position : PlanarVector.Zero;
            var aimAt = hasTarget ? target.Position : self.Position;

            if (dashing) AdvanceDash(combatSystem, dt);
            bossEvents.Clear();
            boss.Step(dt, self.Position.X, self.Position.Z, aimAt.X, aimAt.Z, self.Stats, bossEvents);
            var info = boss.Info;
            self.vitals.Life = info.Life; // o chefe guarda a própria vida (limiar de fase, escudo): o core é a fonte

            // Direção: o core gira no ritmo da fase e a trava da preparação ao fim do impacto; o escudo frontal usa essa mesma direção.
            var facing = new PlanarVector((float)info.FacingX, (float)info.FacingZ);
            if (facing.SqrMagnitude > 1e-8f) self.Forward = facing.NormalizedOr(self.Forward);

            for (var i = 0; i < bossEvents.Count; i++) HandleBossEvent(combatSystem, bossEvents[i]);

            // Recuperacao do padrao (o core entra em Recovery depois do impacto): a apresentacao toca o clipe de recuperacao com a duracao do core.
            if (info.State == BossState.Recovery && lastBossState != BossState.Recovery && bossSkill != null)
                PublishPhase(combatSystem, bossSkill, ActionPhase.Recovery, rules.GetActionTiming(self.Stats, bossSkill).Recovery);
            lastBossState = info.State;

            var distance = hasTarget ? Math.Max(0f, toTarget.Magnitude - target.RadiusMeters) : float.MaxValue;
            WantsToMove = hasTarget && info.State == BossState.Waiting && rules.CanMove(self.Stats) && distance > bossStopDistance;
            MoveTarget = hasTarget ? target.Position : self.Position;
            ChaseSpeed = WantsToMove ? WorldUnits.ToMeters(rules.GetMoveSpeedUu(self.Stats, enemy.MoveSpeedUu)) : 0f;
        }

        void HandleBossEvent(CombatSystem combatSystem, in BossEvent e)
        {
            switch (e.Kind)
            {
                case BossEventKind.PatternStart:
                {
                    var skill = rules.FindSkill(e.SkillId);
                    if (skill == null) break;
                    bossSkill = skill;
                    BeginTelegraph(combatSystem, skill, e.Seconds, true);
                    PublishPhase(combatSystem, skill, ActionPhase.Windup, e.Seconds);
                    break;
                }
                case BossEventKind.PatternImpact:
                    if (bossSkill != null && bossSkill.Shape == SkillShape.Dash) StartDash(combatSystem, bossSkill, e.Seconds);
                    else ResolveImpact(combatSystem, bossSkill);
                    PublishPhase(combatSystem, bossSkill, ActionPhase.Impact, e.Seconds);
                    break;
                case BossEventKind.PatternEnd:
                case BossEventKind.PatternInterrupted:
                    dashing = false;
                    EndTelegraph(combatSystem);
                    PublishPhase(combatSystem, bossSkill, ActionPhase.None, 0.0);
                    bossSkill = null;
                    break;
                default:
                {
                    var evt = new BossStateEvent { Owner = self, Kind = e.Kind, Phase = e.Phase, Seconds = e.Seconds, Count = e.Count, EnemyId = e.EnemyId };
                    combatSystem.Events.Publish(in evt);
                    break;
                }
            }
        }

        SkillInfo bossSkill;
        BossState lastBossState;

        // Investida do chefe (Escudo da fase 2): anda no passo fixo durante o impacto; bater em pilar chama o core.
        bool dashing;
        float dashRemaining;
        float dashSpeed;
        PlanarVector dashDirection;

        void StartDash(CombatSystem combatSystem, SkillInfo skill, double impactSeconds)
        {
            EndTelegraph(combatSystem);
            dashDirection = attackDirection;
            dashRemaining = WorldUnits.ToMeters(skill.RangeUu);
            dashSpeed = dashRemaining / (float)Math.Max(1e-3, impactSeconds);
            dashing = dashRemaining > 0f;
            if (!dashing) DashArrived(combatSystem);
        }

        void AdvanceDash(CombatSystem combatSystem, double dt)
        {
            var step = Math.Min(dashRemaining, dashSpeed * (float)dt);
            var target = self.Position + dashDirection * step;
            if (IsDashBlocked != null && IsDashBlocked(self.Position, target, self.RadiusMeters))
            {
                dashing = false;
                boss.WallHit(self.Stats); // stagger, padrão interrompido e escudo caído: decisão do core
                DashArrived(combatSystem);
                return;
            }
            self.Position = target;
            dashRemaining -= step;
            if (dashRemaining > 1e-4f) return;
            dashing = false;
            DashArrived(combatSystem);
        }

        // Dano na chegada (ou na batida), como a Investida do herói: em volta do corpo.
        void DashArrived(CombatSystem combatSystem)
        {
            var skill = bossSkill;
            if (skill == null) return;
            var radius = WorldUnits.ToMeters(skill.RadiusUu) + self.RadiusMeters;
            var targets = combatSystem.Combatants;
            for (var i = 0; i < targets.Count; i++)
            {
                var t = targets[i];
                if (t.IsDead || !CombatSystem.AreHostile(self, t)) continue;
                if (ShapeQuery.InCircle(self.Position, radius, t.Position, t.RadiusMeters)) combatSystem.ApplySkillHit(self, t, skill, self.Position);
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
