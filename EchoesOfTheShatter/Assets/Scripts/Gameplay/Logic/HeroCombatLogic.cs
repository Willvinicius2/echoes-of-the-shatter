using System;
using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Comportamento do herói no passo fixo: barra de 6 habilidades (fases windup/impact/recovery,
    /// recarga e custo vindos do motor de regras), esquiva com cargas, 2 poções, buffer de entrada.
    /// Pura (sem UnityEngine): o <c>HeroController</c> entrega a entrada e aplica o movimento.
    /// Faz o papel do <c>SkillComponent</c> previsto em docs/04_arquitetura.md, seção 10.4.
    /// </summary>
    public sealed partial class HeroCombatLogic : ICombatActor, IInterruptible, IDisposable
    {
        public const int SlotCount = 6;

        readonly Combatant self;
        readonly IRulesCore rules;
        readonly CombatRules combatRules;
        readonly SkillSlot[] slots = new SkillSlot[SlotCount];
        readonly List<PotionSlot> potions = new List<PotionSlot>(2);
        readonly IPotionBelt belt;
        readonly ActionTimeline action = new ActionTimeline();
        readonly InputBuffer buffer;
        readonly List<int> hitThisSwing = new List<int>(8);

        SkillSlot currentSlot;
        BasicActionKind basicKind;
        double chargeFraction;
        PlanarVector castDirection = PlanarVector.Forward;
        PlanarVector dodgeDirection = PlanarVector.Forward;
        float dodgeSpeed;
        float dashSpeed;
        PlanarVector dashDirection = PlanarVector.Forward;
        PlanarVector groundCenter;
        PotionSlot drinking;
        double drinkRemaining;

        public HeroCombatLogic(Combatant self, IRulesCore rules, IReadOnlyList<string> skillBarIds)
            : this(self, rules, skillBarIds, null)
        {
        }

        /// <summary>
        /// <paramref name="basicKit"/>: valores do combo, da carga e da defesa (docs/18). Com kit, o botão esquerdo e o direito entram por
        /// <see cref="ButtonDown"/>/<see cref="ButtonUp"/> (máquina de entrada em HeroCombatLogic.BasicKit.cs); sem kit, a entrada antiga.
        /// </summary>
        public HeroCombatLogic(Combatant self, IRulesCore rules, IReadOnlyList<string> skillBarIds, IBasicKit basicKit)
        {
            this.self = self ?? throw new ArgumentNullException(nameof(self));
            this.rules = rules ?? throw new ArgumentNullException(nameof(rules));
            combatRules = rules.Combat;
            buffer = new InputBuffer(combatRules.InputBufferSeconds);
            // Cargas, recarga em série, trava de poção e i-frames da esquiva vêm do core (shatter_potions_*, shatter_dodge_*).
            Dodge = rules.CreateDodge();
            belt = rules.CreatePotionBelt();

            for (var i = 0; i < SlotCount; i++)
            {
                var id = skillBarIds != null && i < skillBarIds.Count ? skillBarIds[i] : null;
                var skill = string.IsNullOrEmpty(id) ? null : rules.FindSkill(id);
                var unlocked = skill != null && self.Level >= skill.UnlockLevel;
                slots[i] = new SkillSlot(i, skill, unlocked);
            }

            var potionInfos = rules.Potions;
            for (var i = 0; i < potionInfos.Count; i++) potions.Add(new PotionSlot(potionInfos[i], belt, i));
            InitBasicKit(basicKit);
        }

        public Combatant Self => self;
        public IDodgeCharges Dodge { get; }
        public ActionTimeline Action => action;
        public SkillInfo CurrentSkill => currentSlot?.Skill;
        public bool IsCasting => action.IsActive;
        public bool IsDrinking => drinking != null;
        public PotionSlot DrinkingPotion => drinking;
        public double PotionLockoutRemaining => belt.LockoutRemaining;
        public int PotionCount => potions.Count;
        public PotionSlot GetPotion(int index) => index >= 0 && index < potions.Count ? potions[index] : null;
        public SkillSlot GetSlot(int index) => index >= 0 && index < SlotCount ? slots[index] : null;
        public PlanarVector CastDirection => castDirection;
        public PlanarVector DodgeDirection => dodgeDirection;

        /// <summary>Direção de movimento pedida (WASD), em coordenadas de mundo; módulo até 1.</summary>
        public PlanarVector MoveInput { get; set; }

        /// <summary>Ponto do chão sob o mouse.</summary>
        public PlanarVector AimPoint { get; set; }

        /// <summary>Velocidade de caminhada em m/s (base da classe × atributo MoveSpeed).</summary>
        public float WalkSpeed => TestSettings.HeroSpeedOverrideMetersPerSecond > 0f
            ? TestSettings.HeroSpeedOverrideMetersPerSecond
            : self.Class != null
                ? WorldUnits.ToMeters(rules.GetMoveSpeedUu(self.Stats, self.Class.MoveSpeedUu))
                : 0f;

        public void Press(HeroCommand command)
        {
            buffer.Push(command);
        }

        /// <summary>Há um comando esperando no buffer de entrada.</summary>
        public bool HasPendingCommand => buffer.HasPending;

        /// <summary>true se um ataque básico novo sairia agora (para o botão segurado repetir).</summary>
        public bool IsReadyForAction => !self.IsDead && !action.IsActive && !Dodge.IsDodging && drinking == null;

        /// <summary>Velocidade no plano deste instante (m/s). Integrada em <see cref="FixedTick"/>; a cena só segue <see cref="Combatant.Position"/>.</summary>
        public PlanarVector CurrentVelocity()
        {
            if (self.IsDead || self.Hitstop.IsActive) return PlanarVector.Zero;
            if (Dodge.IsDodging) return dodgeDirection * dodgeSpeed;
            if (action.IsActive)
            {
                if (currentSlot?.Skill != null && currentSlot.Skill.Shape == SkillShape.Dash && action.Phase == ActionPhase.Impact)
                    return dashDirection * dashSpeed;
                return PlanarVector.Zero;
            }
            if (!rules.CanMove(self.Stats)) return PlanarVector.Zero;
            var speed = WalkSpeed;
            if (drinking != null) speed *= (float)drinking.Potion.MoveSpeedWhileUsing;
            // TODO(etapa3/economia): aceleração e desaceleração suaves. Quando o Backend entregar hero_move_accel_seconds (0,10) e hero_move_decel_seconds (0,08)
            // em CombatRules, trocar este retorno por uma velocidade suavizada (estado no passo fixo, MoveTowards pelo tempo do core; nada de número aqui)
            // e cobrir com teste de lógica (zero ao máximo em accel s, máximo a zero em decel s, parado sem entrada).
            return MoveInput.ClampMagnitude(1f) * speed;
        }

        /// <summary>
        /// Para onde o modelo olha neste quadro: esquiva = direção da esquiva; ação (golpe ou magia) = a mira travada no início (castDirection);
        /// andando sem ação = a direção do movimento (o pé acompanha o chão); parado = mantém a última direção.
        /// </summary>
        public PlanarVector FacingDirection()
        {
            if (Dodge.IsDodging) return dodgeDirection;
            if (action.IsActive) return castDirection;
            if (IsAiming) return (AimPoint - self.Position).NormalizedOr(self.Forward); // defendendo ou carregando: encara a mira, o pé anda
            var velocity = CurrentVelocity();
            if (velocity.SqrMagnitude > 1e-6f) return velocity.NormalizedOr(self.Forward);
            return self.Forward;
        }

        public void FixedTick(CombatSystem combat, double dt)
        {
            // Deslocamento no passo fixo (A-04): andar, esquiva e Investida integram aqui, nunca por quadro.
            self.Position += CurrentVelocity() * (float)dt;
            for (var i = 0; i < SlotCount; i++)
            {
                var slot = slots[i];
                slot.Cooldown.Tick(dt);
                if (slot.Skill != null) slot.EffectiveCost = rules.GetEffectiveCost(self.Stats, slot.Skill);
            }
            tick++;
            Dodge.Tick(dt);
            belt.Tick(dt);
            buffer.Tick(dt);

            if (drinking != null)
            {
                drinkRemaining -= dt;
                if (drinkRemaining <= 1e-9) FinishDrinking(combat);
            }

            if (action.IsActive)
            {
                var events = action.Tick(dt);
                HandleActionEvents(combat, events);
            }

            if (kit != null) TickBasicKit(combat);
            TryRunBufferedCommand(combat);
            self.IsInvulnerable = Dodge.IsInvulnerable;
            if (!action.IsActive) self.Forward = FacingDirection();
        }

        public void FrozenTick(CombatSystem combat, double dt)
        {
            // Hitstop: nada avança (timers congelados). A velocidade sai zero em CurrentVelocity.
            tick++; // o relógio da máquina de entrada segue: o botão segurado continua contando
        }

        public void OnIncomingHitAvoided(CombatSystem combat, Combatant attacker)
        {
            // Esquiva perfeita: o core diz quanto de recurso vale um golpe que chegou nos i-frames (0 fora deles).
            var reward = Dodge.PerfectReward;
            if (reward > 0.0) combat.GainResource(self, reward);
        }

        public void OnKilled(CombatSystem combat, Combatant victim)
        {
            // docs/13, item 2: matar elite dá +1 carga na poção com menos cargas (o core escolhe; empate: a Vida).
            if (victim == null || !victim.IsElite) return;
            belt.OnEliteKilled();
        }

        /// <summary>Stun ou stagger em cima da preparação: cancela a ação (o core manda; o C# só cumpre).</summary>
        public void OnInterrupted(CombatSystem combat)
        {
            if (action.IsActive && action.Phase == ActionPhase.Windup) EndAction(combat);
            if (kit != null) CancelAllBasic(combat);
        }

        public void Dispose()
        {
            Dodge.Dispose();
            belt.Dispose();
        }

        public void OnDeath(CombatSystem combat)
        {
            if (action.IsActive) EndAction(combat);
            if (kit != null) CancelAllBasic(combat);
            Dodge.Reset();
            drinking = null;
            buffer.Consume();
            self.IsInvulnerable = false;
        }

        public void OnRevive(CombatSystem combat)
        {
            // docs/13, item 2: poções enchem no checkpoint e no reinício da luta.
            belt.Refill();
            for (var i = 0; i < SlotCount; i++) slots[i].Cooldown.Reset();
            Dodge.Reset();
            buffer.Consume();
            if (kit != null) CancelAllBasic(combat);
        }

        void TryRunBufferedCommand(CombatSystem combat)
        {
            if (!buffer.HasPending || self.IsDead) return;
            var command = buffer.Pending;
            switch (command)
            {
                case HeroCommand.Dodge:
                    TryDodge(combat);
                    break;
                case HeroCommand.Potion1:
                case HeroCommand.Potion2:
                    TryPotion(combat, command, command == HeroCommand.Potion1 ? 0 : 1);
                    break;
                case HeroCommand.None:
                    break;
                default:
                    TrySkill(combat, command, (int)command);
                    break;
            }
        }

        void TryDodge(CombatSystem combat)
        {
            if (Dodge.IsDodging || drinking != null) return; // espera no buffer
            if (action.IsActive && !CanCancelIntoDodge()) return;
            if (!rules.CanMove(self.Stats)) return;
            // Cargas, recurso e esquiva em andamento: o core decide (shatter_dodge_start); só a carga é gasta com Ok.
            var status = Dodge.TryStart(self.Resource);
            if (status == DodgeStartStatus.Active) return; // espera no buffer
            if (status == DodgeStartStatus.NoCharges)
            {
                buffer.Consume();
                Deny(combat, HeroCommand.Dodge, DenyReason.NoDodgeCharges);
                return;
            }
            if (status == DodgeStartStatus.NotEnoughResource)
            {
                buffer.Consume();
                Deny(combat, HeroCommand.Dodge, DenyReason.NoResource);
                return;
            }
            if (combatRules.DodgeResourceCost > 0.0) combat.TrySpendResource(self, combatRules.DodgeResourceCost);
            if (action.IsActive) EndAction(combat);
            if (kit != null) OnDodgeCommitted(combat);
            buffer.Consume();

            // Direção do movimento; parado, para trás da mira (docs/13, item 1).
            var away = (self.Position - AimPoint).NormalizedOr(-self.Forward);
            dodgeDirection = MoveInput.NormalizedOr(away);
            var duration = Math.Max(1e-3, combatRules.DodgeDurationSeconds);
            dodgeSpeed = (float)(WorldUnits.ToMeters(combatRules.DodgeDistanceUu) / duration);
            self.Forward = dodgeDirection;
            self.IsInvulnerable = Dodge.IsInvulnerable;

            var evt = new DodgeStartedEvent
            {
                Owner = self,
                Direction = dodgeDirection,
                DurationSeconds = combatRules.DodgeDurationSeconds,
                InvulnerableSeconds = combatRules.DodgeInvulnerableSeconds,
            };
            combat.Events.Publish(in evt);
        }

        bool CanCancelIntoDodge()
        {
            return action.Phase == ActionPhase.Recovery && action.RecoveryFraction + 1e-9 >= combatRules.DodgeCancelRecoveryFraction;
        }

        void TrySkill(CombatSystem combat, HeroCommand command, int index)
        {
            var slot = GetSlot(index);
            if (slot == null || slot.IsEmpty)
            {
                buffer.Consume();
                Deny(combat, command, DenyReason.EmptySlot);
                return;
            }
            if (!slot.Unlocked)
            {
                buffer.Consume();
                Deny(combat, command, DenyReason.Locked);
                return;
            }
            if (Dodge.IsDodging || drinking != null) return; // espera no buffer
            if (kit != null && IsGuarding)
            {
                buffer.Consume(); // docs/18, 1.3: enquanto defende, o herói não ataca; o pedido não fica esperando
                return;
            }
            var cancelsRecovery = false;
            if (action.IsActive)
            {
                if (kit == null || !CanCancelBasicRecovery()) return; // espera no buffer
                cancelsRecovery = true; // docs/18, 1.3: Q/E/R na metade final da recuperação do golpe básico cancela e zera o combo
            }
            if (!rules.CanAct(self.Stats)) return;
            if (kit != null && tick < guardLowerUntil) return; // espera: acabou de baixar a defesa
            if (!slot.Cooldown.IsReady)
            {
                buffer.Consume();
                Deny(combat, command, DenyReason.Cooldown);
                return;
            }
            var skill = slot.Skill;
            var cost = rules.GetEffectiveCost(self.Stats, skill);
            if (!combat.TrySpendResource(self, cost))
            {
                buffer.Consume();
                Deny(combat, command, DenyReason.NoResource);
                return;
            }

            buffer.Consume();
            if (cancelsRecovery) EndAction(combat);
            if (kit != null) CancelBasicForSkill(combat);
            BeginAction(combat, slot, 0.0, 1.0, BasicActionKind.None);
        }

        /// <summary>Começa uma ação: recarga, mira travada, fases do core e o primeiro passo (fases de duração zero resolvem no mesmo passo).</summary>
        void BeginAction(CombatSystem combat, SkillSlot slot, double creditSeconds, double chargeFract, BasicActionKind kind)
        {
            var skill = slot.Skill;
            currentSlot = slot;
            basicKind = kind;
            chargeFraction = chargeFract;
            slot.Cooldown.Start(rules.GetEffectiveCooldown(self.Stats, skill));
            castDirection = (AimPoint - self.Position).NormalizedOr(self.Forward);
            self.Forward = castDirection;
            hitThisSwing.Clear();
            if (skill.Behavior.GroundTargeted) groundCenter = AreaCenter(skill); // o círculo da Chuva fica onde o cursor estava ao começar
            var timing = rules.GetActionTiming(self.Stats, skill);
            action.Begin(in timing);
            // Crédito de preparação (docs/18, 1.2): o tempo apertado antes de soltar o clique desconta da preparação, até light_windup_credit_max dela.
            var credit = kind == BasicActionKind.Light && kit != null
                ? Math.Max(0.0, Math.Min(creditSeconds, kit.LightWindupCreditMax * timing.Windup))
                : 0.0;
            if (credit > 0.0) action.Tick(credit); // menor que a preparação: não cruza fase
            PublishPhase(combat, ActionPhase.Windup, timing.Windup - credit);

            var events = action.Tick(0.0);
            HandleActionEvents(combat, events);
        }

        void TryPotion(CombatSystem combat, HeroCommand command, int index)
        {
            var slot = GetPotion(index);
            if (slot == null)
            {
                buffer.Consume();
                Deny(combat, command, DenyReason.EmptySlot);
                return;
            }
            if (action.IsActive || Dodge.IsDodging || drinking != null) return; // espera no buffer
            // Trava global, cargas e gasto da carga: o core (shatter_potions_use).
            var status = belt.TryUse(index, self.Stats);
            if (status == PotionUseStatus.LockedOut) return; // espera no buffer
            if (status != PotionUseStatus.Ok)
            {
                buffer.Consume();
                Deny(combat, command, status == PotionUseStatus.NoCharges ? DenyReason.PotionEmpty : DenyReason.EmptySlot); // RF-19: não faz nada e avisa
                return;
            }
            buffer.Consume();
            drinking = slot;
            drinkRemaining = slot.Potion.UseTime;
            var evt = new PotionUsedEvent { Owner = self, Potion = slot.Potion, Applied = false };
            combat.Events.Publish(in evt);
            if (drinkRemaining <= 1e-9) FinishDrinking(combat);
        }

        void FinishDrinking(CombatSystem combat)
        {
            var slot = drinking;
            drinking = null;
            if (slot == null) return;
            var gained = combat.ApplyPotion(self, slot.Potion);
            var evt = new PotionUsedEvent { Owner = self, Potion = slot.Potion, Applied = true, LifeGained = gained };
            combat.Events.Publish(in evt);
        }

        void HandleActionEvents(CombatSystem combat, ActionTimelineEvents events)
        {
            var skill = currentSlot?.Skill;
            if (skill == null) return;

            if ((events & ActionTimelineEvents.ImpactStarted) != 0)
            {
                PublishPhase(combat, ActionPhase.Impact, action.Timing.Impact);
                ApplySelfEffects(combat, skill);
                switch (skill.Shape)
                {
                    case SkillShape.Melee:
                    case SkillShape.Cone:
                        HitCone(combat, skill);
                        break;
                    case SkillShape.Area:
                        // Área no cursor (Chuva): o círculo foi travado ao começar e o golpe cai no fim do impacto (o "impact" do CSV é o atraso até acertar).
                        if (!skill.Behavior.GroundTargeted) HitArea(combat, skill);
                        break;
                    case SkillShape.Dash:
                        var impact = Math.Max(1e-3, action.Timing.Impact);
                        if (skill.Behavior.DashBackShot)
                        {
                            // Salto para trás com tiro: pula o alcance inteiro para longe da mira e atira no pico.
                            dashDirection = -castDirection;
                            dashSpeed = (float)(WorldUnits.ToMeters(skill.RangeUu) / impact);
                        }
                        else
                        {
                            var distance = Math.Min(WorldUnits.ToMeters(skill.RangeUu), PlanarVector.Distance(AimPoint, self.Position));
                            dashDirection = castDirection;
                            dashSpeed = (float)(distance / impact);
                        }
                        break;
                    case SkillShape.Projectile:
                        SpawnProjectiles(combat, skill);
                        break;
                }
            }

            if ((events & ActionTimelineEvents.ImpactEnded) != 0)
            {
                if (skill.Shape == SkillShape.Dash)
                {
                    if (skill.Behavior.DashBackShot) SpawnDashShot(combat, skill); // tiro no pico do salto
                    else HitAroundSelf(combat, skill); // Investida: dano na chegada (RF-13)
                }
                else if (skill.Shape == SkillShape.Area && skill.Behavior.GroundTargeted) HitArea(combat, skill, groundCenter);
                PublishPhase(combat, ActionPhase.Recovery, action.Timing.Recovery);
            }

            if ((events & ActionTimelineEvents.Finished) != 0) EndAction(combat, true);
        }

        void HitCone(CombatSystem combat, SkillInfo skill)
        {
            var range = WorldUnits.ToMeters(skill.RangeUu);
            var half = (float)(skill.ConeAngleDegrees * 0.5);
            var targets = combat.Combatants;
            for (var i = 0; i < targets.Count; i++)
            {
                var target = targets[i];
                if (!IsValidTarget(target)) continue;
                if (!ShapeQuery.InCone(self.Position, castDirection, range, half, target.Position, target.RadiusMeters)) continue;
                Strike(combat, target, skill, self.Position);
            }
        }

        /// <summary>Centro de uma área no cursor limitado ao alcance da habilidade (a Chuva cai até <c>range</c> do herói; área com alcance 0 fica em quem usa).</summary>
        PlanarVector AreaCenter(SkillInfo skill)
        {
            return self.Position + (AimPoint - self.Position).ClampMagnitude(WorldUnits.ToMeters(skill.RangeUu));
        }

        void HitArea(CombatSystem combat, SkillInfo skill) => HitArea(combat, skill, AreaCenter(skill));

        void HitArea(CombatSystem combat, SkillInfo skill, PlanarVector center)
        {
            var radius = WorldUnits.ToMeters(skill.RadiusUu);
            var targets = combat.Combatants;
            for (var i = 0; i < targets.Count; i++)
            {
                var target = targets[i];
                if (!IsValidTarget(target)) continue;
                if (!ShapeQuery.InCircle(center, radius, target.Position, target.RadiusMeters)) continue;
                Strike(combat, target, skill, center);
            }
        }

        void HitAroundSelf(CombatSystem combat, SkillInfo skill)
        {
            var radius = WorldUnits.ToMeters(skill.RadiusUu);
            var targets = combat.Combatants;
            for (var i = 0; i < targets.Count; i++)
            {
                var target = targets[i];
                if (!IsValidTarget(target)) continue;
                if (!ShapeQuery.InCircle(self.Position, radius + self.RadiusMeters, target.Position, target.RadiusMeters)) continue;
                Strike(combat, target, skill, self.Position);
            }
        }

        void SpawnProjectiles(CombatSystem combat, SkillInfo skill)
        {
            var speed = WorldUnits.ToMeters(skill.ProjectileSpeedUu);
            var range = WorldUnits.ToMeters(skill.RangeUu);
            var radius = ProjectileSystem.BodyRadiusMeters(skill);
            var count = Math.Max(1, skill.Projectiles);
            // Leque (Behavior.Fan): N projéteis espalhados em ConeAngle graus em torno da mira; sem leque, saem juntos na mira.
            var fan = skill.Behavior.Fan && count > 1;
            for (var i = 0; i < count; i++)
            {
                var direction = fan ? Rotated(castDirection, (float)(-skill.ConeAngleDegrees * 0.5 + skill.ConeAngleDegrees * i / (count - 1))) : castDirection;
                combat.Projectiles.Spawn(combat, self, skill, self.Position, direction, speed, range, radius, basicKind == BasicActionKind.Heavy, chargeFraction);
            }
        }

        // Tiro do pico do salto (Behavior.DashBackShot): alcance dash_shot_range do core, na direção da mira.
        void SpawnDashShot(CombatSystem combat, SkillInfo skill)
        {
            var speed = WorldUnits.ToMeters(skill.ProjectileSpeedUu);
            var range = WorldUnits.ToMeters(combatRules.DashShotRangeUu);
            combat.Projectiles.Spawn(combat, self, skill, self.Position, castDirection, speed, range, ProjectileSystem.BodyRadiusMeters(skill), basicKind == BasicActionKind.Heavy, chargeFraction);
        }

        static PlanarVector Rotated(PlanarVector v, float degrees)
        {
            var r = degrees * (float)(Math.PI / 180.0);
            var c = (float)Math.Cos(r);
            var s = (float)Math.Sin(r);
            return new PlanarVector(v.X * c + v.Z * s, -v.X * s + v.Z * c);
        }

        bool IsValidTarget(Combatant target)
        {
            return target != null && !target.IsDead && CombatSystem.AreHostile(self, target) && !hitThisSwing.Contains(target.Id);
        }

        void Strike(CombatSystem combat, Combatant target, SkillInfo skill, PlanarVector origin)
        {
            hitThisSwing.Add(target.Id); // RF-16: no máximo 1 acerto por golpe em cada alvo
            combat.ApplySkillHit(self, target, skill, origin, basicKind == BasicActionKind.Heavy, chargeFraction);
        }

        void ApplySelfEffects(CombatSystem combat, SkillInfo skill)
        {
            if (self.Effects == null) return;
            var effects = skill.SelfEffects;
            for (var i = 0; i < effects.Count; i++) combat.ApplyEffect(self, effects[i], 1.0, self.ContentId);
        }

        void EndAction(CombatSystem combat, bool completed = false)
        {
            var skill = currentSlot?.Skill;
            var endedKind = basicKind;
            action.Cancel();
            currentSlot = null;
            dashSpeed = 0f;
            basicKind = BasicActionKind.None;
            chargeFraction = 0.0;
            if (kit != null) OnActionEnded(combat, endedKind, completed);
            if (skill == null) return;
            var evt = new SkillPhaseEvent { Owner = self, Skill = skill, Phase = ActionPhase.None, PhaseSeconds = 0.0, Direction = castDirection };
            combat.Events.Publish(in evt);
        }

        void PublishPhase(CombatSystem combat, ActionPhase phase, double seconds)
        {
            var evt = new SkillPhaseEvent { Owner = self, Skill = currentSlot?.Skill, Phase = phase, PhaseSeconds = seconds, Direction = castDirection };
            combat.Events.Publish(in evt);
        }

        void Deny(CombatSystem combat, HeroCommand command, DenyReason reason)
        {
            var evt = new ActionDeniedEvent { Owner = self, Command = command, Reason = reason };
            combat.Events.Publish(in evt);
        }
    }
}
