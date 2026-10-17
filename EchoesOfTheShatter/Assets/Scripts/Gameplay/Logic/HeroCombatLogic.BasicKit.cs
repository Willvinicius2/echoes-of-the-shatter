using System;
using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>Que tipo de ação do kit básico está em andamento (docs/18): golpe leve do combo ou golpe forte solto da carga.</summary>
    public enum BasicActionKind : byte
    {
        None = 0,
        Light = 1,
        Heavy = 2,
    }

    /// <summary>
    /// Máquina de entrada do ataque básico (docs/18, seções 1.3 e 1.4; decisão 8.1: fica no C#, no passo fixo de 60 Hz). Cuida de: clique ou
    /// segurar do botão esquerdo (decidido ao soltar, com crédito de preparação), janela do combo e fila de clique, carga do golpe forte com
    /// soltura automática no máximo, defesa segurada no botão direito e os cancelamentos. Tudo em ticks inteiros de 1/60 s; os valores vêm de
    /// <see cref="IBasicKit"/> (core). Sem kit (<see cref="HasKit"/> falso) nada daqui roda e vale a entrada antiga.
    /// </summary>
    public sealed partial class HeroCombatLogic : IHeroGuardian
    {
        /// <summary>Botão direito do mouse = defesa (índice 1 da barra: o mesmo <see cref="HeroCommand"/> do espaço 1).</summary>
        public const HeroCommand GuardButton = HeroCommand.Skill1;

        enum PressState : byte
        {
            Idle,
            /// <summary>Apertou e ainda não decidiu entre clique e segurar.</summary>
            Pending,
            Charging,
            /// <summary>O aperto já virou ação (ou foi cancelado): ignorar até soltar.</summary>
            Spent,
        }

        struct ButtonEdge
        {
            public HeroCommand Button;
            public bool Down;
            public long Stamp;
        }

        const int EdgeCapacity = 16;
        const double Eps = 1e-9;

        IBasicKit kit;
        SkillSlot[] chainSlots;
        SkillSlot heavySlot;
        double step = 1.0 / 60.0;
        long tick;
        readonly ButtonEdge[] edges = new ButtonEdge[EdgeCapacity];
        int edgeCount;

        PressState left;
        long leftPressStamp;
        int pendingIndex;
        bool queuedLight;
        long queuedHeldTicks;
        double chargeProgress;

        int comboIndex;
        long comboWindowEnd = long.MaxValue;

        bool guardWanted;
        bool guarding;
        bool guardPerfectEligible;
        long guardPressStamp;
        long lastGuardPressStamp = long.MinValue / 2;
        long guardEnterTick;
        long guardPerfectUntil;
        long guardCooldownUntil;
        long guardLowerUntil;
        bool wasDodging;

        /// <summary>Há um kit básico (combo, carga e defesa) ligado a este herói.</summary>
        public bool HasKit => kit != null;

        public IBasicKit Kit => kit;

        /// <summary>Contador de ticks da lógica (1/60 s cada); a máquina de entrada mede tudo nele.</summary>
        public long TickCount => tick;

        public bool IsCharging => left == PressState.Charging;

        /// <summary>Progresso da carga, de 0 (limiar) a 1 (máximo); 0 fora da carga.</summary>
        public double ChargeProgress => left == PressState.Charging ? chargeProgress : 0.0;

        public bool IsGuarding => guarding;

        /// <summary>Defendendo ou carregando: o corpo encara a mira e as pernas andam (camada de tronco e braços na apresentação).</summary>
        public bool IsAiming => kit != null && (guarding || left == PressState.Charging);

        /// <summary>Dentro da janela da defesa perfeita (primeiros <c>guardPerfectWindow</c> s depois de levantar a defesa).</summary>
        public bool GuardPerfectOpen => guarding && tick < guardPerfectUntil;

        public double GuardArcDegrees => kit != null ? kit.GuardArcDegrees : 0.0;

        /// <summary>Índice do próximo golpe leve do combo (0 = primeiro).</summary>
        public int ComboIndex => comboIndex;

        public bool IsComboWindowOpen => comboIndex > 0;

        public SkillInfo HeavySkill => heavySlot != null ? heavySlot.Skill : null;

        public bool IsMoving => CurrentVelocity().SqrMagnitude > 1e-6f;
        public double GuardPerfectResource => kit != null ? kit.GuardPerfectResource : 0.0;
        public IReadOnlyList<string> GuardPerfectEffects => kit != null ? kit.GuardPerfectEffects : System.Array.Empty<string>();
        public double GuardDrainPerDamage => kit != null ? kit.GuardDrainPerDamage : 0.0;

        /// <summary>
        /// O golpe vindo de <paramref name="attackerPosition"/> bate dentro do arco da defesa? (docs/18, 8.1: o C# tem a geometria e diz ao core
        /// a cada golpe recebido.) Falso se não está defendendo.
        /// </summary>
        public bool GuardCovers(PlanarVector attackerPosition)
        {
            if (!guarding || kit == null) return false;
            var arc = kit.GuardArcDegrees;
            if (arc >= 359.99) return true;
            if (arc <= 0.0) return false;
            var facing = (AimPoint - self.Position).NormalizedOr(self.Forward);
            var toAttacker = (attackerPosition - self.Position).NormalizedOr(facing);
            var cos = PlanarVector.Dot(facing, toAttacker);
            return cos + 1e-6 >= Math.Cos(arc * 0.5 * Math.PI / 180.0);
        }

        /// <summary>
        /// Botão esquerdo (<see cref="HeroCommand.BasicAttack"/>) ou direito (<see cref="GuardButton"/>) apertado. O instante fica marcado no tick
        /// atual; a decisão acontece no próximo passo fixo. Sem kit, vira o <see cref="Press"/> antigo.
        /// </summary>
        public void ButtonDown(HeroCommand button) => PushEdge(button, true);

        /// <summary>Botão soltado (só vale com kit).</summary>
        public void ButtonUp(HeroCommand button) => PushEdge(button, false);

        void PushEdge(HeroCommand button, bool down)
        {
            if (kit == null)
            {
                if (down) Press(button);
                return;
            }
            if (button != HeroCommand.BasicAttack && button != GuardButton) return;
            if (edgeCount == EdgeCapacity)
            {
                Array.Copy(edges, 1, edges, 0, EdgeCapacity - 1);
                edgeCount--;
            }
            edges[edgeCount++] = new ButtonEdge { Button = button, Down = down, Stamp = tick };
        }

        void InitBasicKit(IBasicKit basicKit)
        {
            kit = basicKit;
            step = Math.Max(1e-6, combatRules.FixedStep);
            if (kit == null) return;
            var chain = kit.LightChain;
            if (chain == null || chain.Count == 0) throw new ArgumentException("O kit básico precisa de pelo menos 1 golpe leve.", nameof(basicKit));
            chainSlots = new SkillSlot[chain.Count];
            for (var i = 0; i < chain.Count; i++)
            {
                var skill = chain[i];
                chainSlots[i] = new SkillSlot(100 + i, skill, skill != null && self.Level >= skill.UnlockLevel);
            }
            var heavy = kit.HeavySkill;
            heavySlot = heavy != null ? new SkillSlot(110, heavy, self.Level >= heavy.UnlockLevel) : null;
        }

        long Ticks(double seconds)
        {
            return seconds <= 0.0 ? 0L : (long)Math.Ceiling(seconds / step - 1e-6);
        }

        void TickBasicKit(CombatSystem combat)
        {
            var dodging = Dodge.IsDodging;
            if (wasDodging && !dodging) OnDodgeEnded();
            wasDodging = dodging;

            if (self.IsDead)
            {
                edgeCount = 0;
                return;
            }
            if (!rules.CanAct(self.Stats))
            {
                // Atordoamento: cancela tudo e zera o combo (docs/18, 1.3).
                edgeCount = 0;
                CancelAllBasic(combat);
                return;
            }
            if (comboIndex > 0 && tick > comboWindowEnd) ResetCombo(combat);

            for (var i = 0; i < edgeCount; i++)
            {
                var edge = edges[i];
                if (edge.Button == HeroCommand.BasicAttack)
                {
                    if (edge.Down) OnLeftDown(edge.Stamp);
                    else OnLeftUp(combat, edge.Stamp);
                }
                else if (edge.Down) OnGuardPress(edge.Stamp);
                else OnGuardRelease(combat);
            }
            edgeCount = 0;

            UpdateGuard(combat);
            UpdateLeft(combat);
        }

        // ---------------------------------------------------------------------------------------------- botão esquerdo

        bool CanBeginBasicNow()
        {
            return !self.IsDead && !action.IsActive && !Dodge.IsDodging && drinking == null && !guarding
                && tick >= guardLowerUntil && rules.CanAct(self.Stats);
        }

        bool HeavyAvailable => heavySlot != null && heavySlot.Unlocked;

        bool HeavyAffordable()
        {
            return rules.GetEffectiveCost(self.Stats, heavySlot.Skill) <= self.Resource + Eps;
        }

        void OnLeftDown(long stamp)
        {
            if (left != PressState.Idle) return;
            if (drinking != null || Dodge.IsDodging || guarding || guardWanted) return;
            if (action.IsActive)
            {
                // Preparação e impacto: compromisso do golpe, o clique é ignorado. Recuperação: só nos últimos attack_buffer s (docs/18, 1.3).
                if (action.Phase != ActionPhase.Recovery) return;
                if (action.Timing.Recovery - action.PhaseElapsed > kit.AttackBuffer + Eps) return;
            }
            left = PressState.Pending;
            leftPressStamp = stamp;
            pendingIndex = comboIndex;
        }

        void OnLeftUp(CombatSystem combat, long stamp)
        {
            var held = stamp - leftPressStamp;
            switch (left)
            {
                case PressState.Pending:
                    if (HeavyAvailable && held >= Ticks(kit.HeavyHoldThreshold) && CanBeginBasicNow() && HeavyAffordable())
                    {
                        BeginCharge(combat);
                        ReleaseHeavy(combat, held);
                    }
                    else
                    {
                        queuedLight = true;
                        queuedHeldTicks = held;
                    }
                    break;
                case PressState.Charging:
                    ReleaseHeavy(combat, held);
                    break;
            }
            left = PressState.Idle;
        }

        void UpdateLeft(CombatSystem combat)
        {
            if (left == PressState.Pending && tick - leftPressStamp >= Ticks(kit.HeavyHoldThreshold) && CanBeginBasicNow())
            {
                if (HeavyAvailable && HeavyAffordable()) BeginCharge(combat);
                else
                {
                    // Sem recurso para o forte (ou sem forte): o botão vira golpe leve, nada de carga vazia (docs/18, 1.4).
                    queuedLight = true;
                    queuedHeldTicks = tick - leftPressStamp;
                    left = PressState.Spent;
                }
            }
            if (left == PressState.Charging) UpdateCharge(combat);
            if (queuedLight && CanBeginBasicNow())
            {
                queuedLight = false;
                StartLight(combat, queuedHeldTicks);
            }
        }

        void BeginCharge(CombatSystem combat)
        {
            left = PressState.Charging;
            chargeProgress = 0.0;
            PublishBasic(combat, BasicInputKind.ChargeStarted, heavySlot.Skill, 0.0);
        }

        void UpdateCharge(CombatSystem combat)
        {
            var held = tick - leftPressStamp;
            var chargeTicks = Math.Max(1L, Ticks(kit.HeavyChargeTime));
            var progress = (held - Ticks(kit.HeavyHoldThreshold)) / (double)chargeTicks;
            chargeProgress = progress < 0.0 ? 0.0 : progress > 1.0 ? 1.0 : progress;
            ApplyKitEffect(combat, kit.ChargeEffect);
            if (chargeProgress < 1.0 - Eps) return;
            // Máximo da carga: solta sozinho (decisão do orquestrador); segurar no máximo não rende nada.
            PublishBasic(combat, BasicInputKind.ChargeFull, heavySlot.Skill, 1.0);
            ReleaseHeavy(combat, held);
            left = PressState.Spent;
        }

        void ReleaseHeavy(CombatSystem combat, long heldTicks)
        {
            var chargeTicks = Math.Max(1L, Ticks(kit.HeavyChargeTime));
            var progress = (heldTicks - Ticks(kit.HeavyHoldThreshold)) / (double)chargeTicks;
            progress = progress < 0.0 ? 0.0 : progress > 1.0 ? 1.0 : progress;
            chargeProgress = 0.0;
            if (!CanBeginBasicNow())
            {
                PublishBasic(combat, BasicInputKind.ChargeCancelled, heavySlot.Skill, progress);
                return;
            }
            // Custo cobrado ao soltar (docs/18, 1.4).
            if (!combat.TrySpendResource(self, rules.GetEffectiveCost(self.Stats, heavySlot.Skill)))
            {
                PublishBasic(combat, BasicInputKind.ChargeCancelled, heavySlot.Skill, progress);
                Deny(combat, HeroCommand.BasicAttack, DenyReason.NoResource);
                return;
            }
            ResetCombo(combat);
            var mult = 1.0 + (kit.HeavyMaxMult - 1.0) * progress;
            PublishBasic(combat, BasicInputKind.HeavyReleased, heavySlot.Skill, mult);
            BeginAction(combat, heavySlot, 0.0, mult, BasicActionKind.Heavy);
        }

        void StartLight(CombatSystem combat, long heldTicks)
        {
            var index = pendingIndex >= 0 && pendingIndex < chainSlots.Length ? pendingIndex : 0;
            var slot = chainSlots[index];
            if (slot.IsEmpty || !slot.Unlocked)
            {
                index = 0;
                slot = chainSlots[0];
                if (slot.IsEmpty || !slot.Unlocked) return;
            }
            if (!combat.TrySpendResource(self, rules.GetEffectiveCost(self.Stats, slot.Skill)))
            {
                Deny(combat, HeroCommand.BasicAttack, DenyReason.NoResource);
                ResetCombo(combat);
                return;
            }
            comboIndex = index + 1 < chainSlots.Length ? index + 1 : 0;
            comboWindowEnd = long.MaxValue; // a janela só conta depois do fim da recuperação (OnActionEnded)
            BeginAction(combat, slot, heldTicks * step, 1.0, BasicActionKind.Light);
        }

        void DropPendingLeft()
        {
            queuedLight = false;
            if (left == PressState.Pending) left = PressState.Spent;
        }

        void CancelCharge(CombatSystem combat)
        {
            if (left != PressState.Charging) return;
            left = PressState.Spent;
            var progress = chargeProgress;
            chargeProgress = 0.0;
            PublishBasic(combat, BasicInputKind.ChargeCancelled, heavySlot != null ? heavySlot.Skill : null, progress);
        }

        // ---------------------------------------------------------------------------------------------- combo

        void ResetCombo(CombatSystem combat)
        {
            comboWindowEnd = long.MaxValue;
            if (comboIndex == 0) return;
            comboIndex = 0;
            PublishBasic(combat, BasicInputKind.ComboReset, null, 0.0);
        }

        bool CanCancelBasicRecovery()
        {
            return basicKind != BasicActionKind.None && action.Phase == ActionPhase.Recovery
                && action.RecoveryFraction + Eps >= combatRules.DodgeCancelRecoveryFraction;
        }

        void OnActionEnded(CombatSystem combat, BasicActionKind kind, bool completed)
        {
            if (kind != BasicActionKind.Light || !completed) return;
            if (comboIndex > 0) comboWindowEnd = tick + Ticks(kit.ComboWindow);
        }

        void OnDodgeCommitted(CombatSystem combat)
        {
            guardWanted = false;
            if (guarding) ExitGuard(combat, false);
            CancelCharge(combat);
            DropPendingLeft();
            // O combo guarda o índice; a janela só volta a contar no fim da esquiva.
            if (comboIndex > 0) comboWindowEnd = long.MaxValue;
        }

        void OnDodgeEnded()
        {
            if (comboIndex > 0) comboWindowEnd = tick + Ticks(kit.ComboWindowAfterDodge);
        }

        void CancelBasicForSkill(CombatSystem combat)
        {
            guardWanted = false;
            CancelCharge(combat);
            DropPendingLeft();
            ResetCombo(combat);
        }

        void CancelAllBasic(CombatSystem combat)
        {
            guardWanted = false;
            CancelCharge(combat);
            if (guarding) ExitGuard(combat, false);
            queuedLight = false;
            left = PressState.Idle;
            ResetCombo(combat);
        }

        // ---------------------------------------------------------------------------------------------- defesa

        void OnGuardPress(long stamp)
        {
            if (self.IsDead || drinking != null || Dodge.IsDodging) return;
            if (tick < guardCooldownUntil) return;
            if (action.IsActive && action.Phase != ActionPhase.Recovery) return; // compromisso do golpe
            guardPerfectEligible = kit.GuardPerfectWindow > 0.0 && stamp - lastGuardPressStamp >= Ticks(kit.GuardPerfectCooldown);
            lastGuardPressStamp = stamp;
            guardPressStamp = stamp;
            guardWanted = true;
        }

        void OnGuardRelease(CombatSystem combat)
        {
            guardWanted = false;
            if (guarding) ExitGuard(combat, false);
        }

        void UpdateGuard(CombatSystem combat)
        {
            if (guardWanted && !guarding) TryEnterGuard(combat);
            if (!guarding) return;
            ApplyKitEffect(combat, kit.GuardEffect);
            // Defesa que gasta recurso (Mago): sem Mana a barreira estilhaça e cai.
            if (kit.GuardDrainPerDamage > 0.0 && self.Resource <= Eps)
            {
                ExitGuard(combat, true);
                return;
            }
            if (kit.GuardMaxHold > 0.0 && tick - guardEnterTick >= Ticks(kit.GuardMaxHold)) ExitGuard(combat, true);
        }

        void TryEnterGuard(CombatSystem combat)
        {
            if (drinking != null || Dodge.IsDodging) return; // espera
            if (action.IsActive)
            {
                if (action.Phase != ActionPhase.Recovery)
                {
                    guardWanted = false;
                    return;
                }
                if (!CanCancelBasicRecovery()) return; // espera o fim da recuperação (ou a metade final, no golpe básico)
                EndAction(combat);
            }
            CancelCharge(combat);
            DropPendingLeft();
            ResetCombo(combat);
            guarding = true;
            guardEnterTick = tick;
            guardPerfectUntil = guardPerfectEligible ? tick + Ticks(kit.GuardPerfectWindow) : 0L;
            PublishBasic(combat, BasicInputKind.GuardUp, null, 0.0);
        }

        void ExitGuard(CombatSystem combat, bool auto)
        {
            guarding = false;
            guardPerfectUntil = 0L;
            guardCooldownUntil = tick + Ticks(kit.GuardCooldown);
            guardLowerUntil = tick + Ticks(kit.GuardLowerTime);
            if (auto) guardWanted = false; // caiu sozinha: precisa apertar de novo
            PublishBasic(combat, auto ? BasicInputKind.GuardBroke : BasicInputKind.GuardDown, null, 0.0);
        }

        // ---------------------------------------------------------------------------------------------- apoio

        void ApplyKitEffect(CombatSystem combat, string effectId)
        {
            if (string.IsNullOrEmpty(effectId) || self.Effects == null) return;
            combat.ApplyEffect(self, effectId, 1.0, self.ContentId);
        }

        void PublishBasic(CombatSystem combat, BasicInputKind kind, SkillInfo skill, double value)
        {
            var evt = new BasicInputEvent { Owner = self, Kind = kind, Skill = skill, Value = value };
            combat.Events.Publish(in evt);
        }
    }
}
