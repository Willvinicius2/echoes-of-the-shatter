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
    public sealed class HeroCombatLogic : ICombatActor
    {
        public const int SlotCount = 6;

        readonly Combatant self;
        readonly IRulesCore rules;
        readonly CombatRules combatRules;
        readonly SkillSlot[] slots = new SkillSlot[SlotCount];
        readonly List<PotionSlot> potions = new List<PotionSlot>(2);
        readonly ActionTimeline action = new ActionTimeline();
        readonly InputBuffer buffer;
        readonly CooldownTimer potionLockout = new CooldownTimer();
        readonly List<int> hitThisSwing = new List<int>(8);

        SkillSlot currentSlot;
        PlanarVector castDirection = PlanarVector.Forward;
        PlanarVector dodgeDirection = PlanarVector.Forward;
        float dodgeSpeed;
        float dashSpeed;
        PotionSlot drinking;
        double drinkRemaining;

        public HeroCombatLogic(Combatant self, IRulesCore rules, IReadOnlyList<string> skillBarIds)
        {
            this.self = self ?? throw new ArgumentNullException(nameof(self));
            this.rules = rules ?? throw new ArgumentNullException(nameof(rules));
            combatRules = rules.Combat;
            buffer = new InputBuffer(combatRules.InputBufferSeconds);
            Dodge = new DodgeLogic(combatRules.DodgeMaxCharges, combatRules.DodgeRechargeSeconds,
                combatRules.DodgeDurationSeconds, combatRules.DodgeInvulnerableSeconds);

            for (var i = 0; i < SlotCount; i++)
            {
                var id = skillBarIds != null && i < skillBarIds.Count ? skillBarIds[i] : null;
                var skill = string.IsNullOrEmpty(id) ? null : rules.FindSkill(id);
                var unlocked = skill != null && self.Level >= skill.UnlockLevel;
                slots[i] = new SkillSlot(i, skill, unlocked);
            }

            var potionInfos = rules.Potions;
            for (var i = 0; i < potionInfos.Count; i++) potions.Add(new PotionSlot(potionInfos[i]));
        }

        public Combatant Self => self;
        public DodgeLogic Dodge { get; }
        public ActionTimeline Action => action;
        public SkillInfo CurrentSkill => currentSlot?.Skill;
        public bool IsCasting => action.IsActive;
        public bool IsDrinking => drinking != null;
        public PotionSlot DrinkingPotion => drinking;
        public double PotionLockoutRemaining => potionLockout.Remaining;
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
        public float WalkSpeed => self.Class != null
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

        /// <summary>Velocidade no plano para este quadro (m/s). O HeroController move o CharacterController com ela.</summary>
        public PlanarVector CurrentVelocity()
        {
            if (self.IsDead || self.Hitstop.IsActive) return PlanarVector.Zero;
            if (Dodge.IsDodging) return dodgeDirection * dodgeSpeed;
            if (action.IsActive)
            {
                if (currentSlot?.Skill != null && currentSlot.Skill.Shape == SkillShape.Dash && action.Phase == ActionPhase.Impact)
                    return castDirection * dashSpeed;
                return PlanarVector.Zero;
            }
            if (!rules.CanMove(self.Stats)) return PlanarVector.Zero;
            var speed = WalkSpeed;
            if (drinking != null) speed *= (float)drinking.Potion.MoveSpeedWhileUsing;
            return MoveInput.ClampMagnitude(1f) * speed;
        }

        /// <summary>Para onde o modelo olha neste quadro.</summary>
        public PlanarVector FacingDirection()
        {
            if (Dodge.IsDodging) return dodgeDirection;
            if (action.IsActive) return castDirection;
            return (AimPoint - self.Position).NormalizedOr(self.Forward);
        }

        public void FixedTick(CombatSystem combat, double dt)
        {
            for (var i = 0; i < SlotCount; i++)
            {
                var slot = slots[i];
                slot.Cooldown.Tick(dt);
                if (slot.Skill != null) slot.EffectiveCost = rules.GetEffectiveCost(self.Stats, slot.Skill);
            }
            Dodge.Tick(dt);
            for (var i = 0; i < potions.Count; i++) potions[i].Charges.Tick(dt);
            potionLockout.Tick(dt);
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

            TryRunBufferedCommand(combat);
            self.IsInvulnerable = Dodge.IsInvulnerable;
            if (!action.IsActive) self.Forward = FacingDirection();
        }

        public void FrozenTick(CombatSystem combat, double dt)
        {
            // Hitstop: nada avança (timers congelados). A velocidade sai zero em CurrentVelocity.
        }

        public void OnIncomingHitAvoided(CombatSystem combat, Combatant attacker)
        {
            if (!Dodge.IsDodging || Dodge.PerfectGranted) return;
            Dodge.PerfectGranted = true;
            combat.GainResource(self, combatRules.DodgePerfectResource);
        }

        public void OnKilled(CombatSystem combat, Combatant victim)
        {
            // docs/13, item 2: matar elite dá +1 carga na poção com menos cargas (empate: a de tecla menor).
            if (victim == null || !victim.IsElite) return;
            PotionSlot best = null;
            for (var i = 0; i < potions.Count; i++)
            {
                var p = potions[i];
                if (p.Potion.EliteKillRefillCharges <= 0 || p.Charges.IsFull) continue;
                if (best == null || p.Charges.Charges < best.Charges.Charges) best = p;
            }
            best?.Charges.AddCharges(best.Potion.EliteKillRefillCharges);
        }

        public void OnDeath(CombatSystem combat)
        {
            if (action.IsActive) EndAction(combat);
            Dodge.Stop();
            drinking = null;
            buffer.Consume();
            self.IsInvulnerable = false;
        }

        public void OnRevive(CombatSystem combat)
        {
            // docs/13, item 2: poções enchem no checkpoint e no reinício da luta.
            for (var i = 0; i < potions.Count; i++) potions[i].Charges.Refill();
            for (var i = 0; i < SlotCount; i++) slots[i].Cooldown.Reset();
            Dodge.Refill();
            potionLockout.Reset();
            buffer.Consume();
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
            if (Dodge.Charges.IsEmpty)
            {
                buffer.Consume();
                Deny(combat, HeroCommand.Dodge, DenyReason.NoDodgeCharges);
                return;
            }
            if (combatRules.DodgeResourceCost > 0.0 && !combat.TrySpendResource(self, combatRules.DodgeResourceCost))
            {
                buffer.Consume();
                Deny(combat, HeroCommand.Dodge, DenyReason.NoResource);
                return;
            }
            if (action.IsActive) EndAction(combat);
            Dodge.TryStart();
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
            if (action.IsActive || Dodge.IsDodging || drinking != null) return; // espera no buffer
            if (!rules.CanAct(self.Stats)) return;
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
            currentSlot = slot;
            slot.Cooldown.Start(rules.GetEffectiveCooldown(self.Stats, skill));
            castDirection = (AimPoint - self.Position).NormalizedOr(self.Forward);
            self.Forward = castDirection;
            hitThisSwing.Clear();
            var timing = rules.GetActionTiming(self.Stats, skill);
            action.Begin(in timing);
            PublishPhase(combat, ActionPhase.Windup, timing.Windup);

            // Fases de duração zero (dados) resolvem no mesmo passo.
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
            if (action.IsActive || Dodge.IsDodging || drinking != null || !potionLockout.IsReady) return; // espera no buffer
            if (!slot.Charges.TryConsume())
            {
                buffer.Consume();
                Deny(combat, command, DenyReason.PotionEmpty); // RF-19: não faz nada e avisa
                return;
            }
            buffer.Consume();
            potionLockout.Start(combatRules.PotionLockoutSeconds);
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
                ApplySelfEffects(skill);
                switch (skill.Shape)
                {
                    case SkillShape.Melee:
                    case SkillShape.Cone:
                        HitCone(combat, skill);
                        break;
                    case SkillShape.Area:
                        HitArea(combat, skill);
                        break;
                    case SkillShape.Dash:
                        var distance = Math.Min(WorldUnits.ToMeters(skill.RangeUu), PlanarVector.Distance(AimPoint, self.Position));
                        var impact = Math.Max(1e-3, action.Timing.Impact);
                        dashSpeed = (float)(distance / impact);
                        break;
                    case SkillShape.Projectile:
                        SpawnProjectiles(combat, skill);
                        break;
                }
            }

            if ((events & ActionTimelineEvents.ImpactEnded) != 0)
            {
                if (skill.Shape == SkillShape.Dash) HitAroundSelf(combat, skill); // Investida: dano na chegada (RF-13)
                PublishPhase(combat, ActionPhase.Recovery, action.Timing.Recovery);
            }

            if ((events & ActionTimelineEvents.Finished) != 0) EndAction(combat);
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

        void HitArea(CombatSystem combat, SkillInfo skill)
        {
            var range = WorldUnits.ToMeters(skill.RangeUu);
            var toAim = AimPoint - self.Position;
            var center = self.Position + toAim.ClampMagnitude(range);
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
            var radius = WorldUnits.ToMeters(skill.RadiusUu);
            var count = Math.Max(1, skill.Projectiles);
            for (var i = 0; i < count; i++)
                combat.Projectiles.Spawn(combat, self, skill, self.Position, castDirection, speed, range, radius);
        }

        bool IsValidTarget(Combatant target)
        {
            return target != null && !target.IsDead && CombatSystem.AreHostile(self, target) && !hitThisSwing.Contains(target.Id);
        }

        void Strike(CombatSystem combat, Combatant target, SkillInfo skill, PlanarVector origin)
        {
            hitThisSwing.Add(target.Id); // RF-16: no máximo 1 acerto por golpe em cada alvo
            combat.ApplySkillHit(self, target, skill, origin);
        }

        void ApplySelfEffects(SkillInfo skill)
        {
            if (self.Effects == null) return;
            var effects = skill.SelfEffects;
            for (var i = 0; i < effects.Count; i++) self.Effects.Apply(effects[i], 1.0, self.ContentId);
        }

        void EndAction(CombatSystem combat)
        {
            var skill = currentSlot?.Skill;
            action.Cancel();
            currentSlot = null;
            dashSpeed = 0f;
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
