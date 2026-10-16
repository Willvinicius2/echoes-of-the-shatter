using System;
using System.Collections.Generic;
using Echoes.Core;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Combate em passo fixo (RF-11; docs/04_arquitetura.md, seções 6.2 e 10.4). Único lugar que chama
    /// o golpe do motor de regras (<see cref="ApplySkillHit"/>) e aplica o resultado. Guarda os fluxos
    /// de RNG da sessão (Combat e Events, derivados do runSeed). Classe pura: sem UnityEngine, chamada
    /// pelo <c>CombatSystemHost</c> a cada quadro. Sem alocação por passo.
    /// </summary>
    public sealed class CombatSystem
    {
        readonly List<Combatant> combatants = new List<Combatant>();
        readonly List<EffectTickEvent> effectEvents = new List<EffectTickEvent>();
        RngState combatRng;
        RngState eventsRng;
        int nextId = 1;
        int nextTelegraphId = 1;

        public CombatSystem(IRulesCore rules, EventBus events, ulong runSeed, CombatFeelValues feel, int maxStepsPerFrame)
        {
            Rules = rules ?? throw new ArgumentNullException(nameof(rules));
            Events = events ?? throw new ArgumentNullException(nameof(events));
            Feel = feel ?? new CombatFeelValues();
            RunSeed = runSeed;
            combatRng = rules.CreateRng(runSeed, RngStream.Combat, 0);
            eventsRng = rules.CreateRng(runSeed, RngStream.Events, 0);
            Clock = new FixedStepAccumulator(rules.Combat.FixedStep, Math.Max(1, maxStepsPerFrame));
            Projectiles = new ProjectileSystem();
        }

        public IRulesCore Rules { get; }
        public EventBus Events { get; }
        public CombatFeelValues Feel { get; }
        public ulong RunSeed { get; }
        public FixedStepAccumulator Clock { get; }
        public ProjectileSystem Projectiles { get; }

        /// <summary>Tempo de combate acumulado em passos fixos (segundos).</summary>
        public double Time { get; private set; }
        public long StepCount { get; private set; }

        public IReadOnlyList<Combatant> Combatants => combatants;

        /// <summary>O herói (primeiro registrado do time Hero), ou null.</summary>
        public Combatant Hero { get; private set; }

        public void Register(Combatant combatant, ICombatActor actor)
        {
            if (combatant == null) throw new ArgumentNullException(nameof(combatant));
            if (combatant.IsRegistered) return;
            combatant.Id = nextId++;
            combatant.Actor = actor;
            combatant.IsRegistered = true;
            combatant.SetVitals(Rules.CreateVitals(combatant.Stats, combatant.Class));
            combatants.Add(combatant);
            if (combatant.Team == CombatTeam.Hero && Hero == null) Hero = combatant;
        }

        public void Unregister(Combatant combatant)
        {
            if (combatant == null || !combatant.IsRegistered) return;
            combatant.IsRegistered = false;
            combatants.Remove(combatant);
            if (ReferenceEquals(Hero, combatant)) Hero = null;
        }

        /// <summary>Tempo real do quadro → N passos fixos. Devolve quantos passos rodou.</summary>
        public int Tick(double deltaTime)
        {
            var steps = Clock.Advance(deltaTime);
            for (var i = 0; i < steps; i++) Step(Clock.Step);
            return steps;
        }

        /// <summary>Um passo fixo. Público para testes e ferramentas.</summary>
        public void Step(double dt)
        {
            Time += dt;
            StepCount++;
            var count = combatants.Count;
            for (var i = 0; i < count && i < combatants.Count; i++)
            {
                var c = combatants[i];
                if (c.IsDead) continue;
                if (c.SecondsSinceCombat < double.MaxValue) c.SecondsSinceCombat += dt;

                if (c.Hitstop.IsActive)
                {
                    c.Hitstop.Tick(dt);
                    c.Actor?.FrozenTick(this, dt);
                    continue;
                }

                if (c.Effects != null)
                {
                    effectEvents.Clear();
                    c.Effects.Tick(dt, effectEvents);
                    for (var e = 0; e < effectEvents.Count && !c.IsDead; e++)
                    {
                        if (!effectEvents[e].Expired) ApplyDamageOverTime(c, effectEvents[e]);
                    }
                    if (c.IsDead) continue;
                }

                Rules.TickVitals(ref c.vitals, c.Stats, c.Class, dt, IsInCombat(c));
                c.Actor?.FixedTick(this, dt);
            }
            Projectiles.Step(this, dt);
        }

        public bool IsInCombat(Combatant c) => c.SecondsSinceCombat < Rules.Combat.OutOfCombatSeconds;

        public static bool AreHostile(Combatant a, Combatant b) => a != null && b != null && a.Team != b.Team;

        /// <summary>
        /// Resolve UM golpe de <paramref name="skill"/> de <paramref name="attacker"/> em <paramref name="target"/>:
        /// monta o pedido, chama o motor de regras, aplica vida/barreira, efeitos ao acertar, recurso,
        /// hitstop e knockback, e publica os eventos. Devolve true se o golpe acertou (não evadido).
        /// Quem chama garante "no máximo 1 vez por golpe por alvo" (RF-16).
        /// </summary>
        public bool ApplySkillHit(Combatant attacker, Combatant target, SkillInfo skill, PlanarVector hitOrigin)
        {
            if (attacker == null || target == null || skill == null) return false;
            if (target.IsDead || ReferenceEquals(attacker, target) || !target.IsRegistered) return false;

            attacker.SecondsSinceCombat = 0.0;
            target.SecondsSinceCombat = 0.0;

            if (target.IsInvulnerable)
            {
                var avoided = new HitAvoidedEvent { Attacker = attacker, Target = target, Skill = skill };
                Events.Publish(in avoided);
                target.Actor?.OnIncomingHitAvoided(this, attacker);
                return false;
            }

            var request = new HitRequest
            {
                Attacker = attacker.Stats,
                Defender = target.Stats,
                SkillTags = skill.Tags,
                BaseDamage = Rules.GetSkillBaseDamage(skill, attacker.Weapon),
                Coefficient = skill.Coefficient(1),
                IsDamageOverTime = false,
                CanBeBlocked = true,
                DefenderLife = target.vitals.Life,
                DefenderBarrier = target.vitals.Barrier,
            };
            var result = Rules.ResolveHit(in request, ref combatRng);
            target.vitals.Life = result.DefenderLifeAfter;
            target.vitals.Barrier = result.DefenderBarrierAfter;

            var heavy = Feel.IsHeavy(skill.Id);
            if (result.Landed)
            {
                var onHit = skill.OnHitEffects;
                if (target.Effects != null)
                {
                    for (var i = 0; i < onHit.Count; i++) target.Effects.Apply(onHit[i], 1.0, attacker.ContentId);
                }
                if (attacker.Class != null)
                    Rules.GainResource(ref attacker.vitals, attacker.Stats, attacker.Class.ResourceOnHit);

                var hitstop = Feel.HitstopFor(result.Critical, heavy, attacker.IsBoss, target.Team == CombatTeam.Hero);
                if (hitstop > 0.0)
                {
                    attacker.Hitstop.Trigger(hitstop);
                    target.Hitstop.Trigger(hitstop);
                }

                if (target.Team == CombatTeam.Enemy && !result.Killed)
                {
                    var distance = Feel.KnockbackFor(target);
                    if (distance > 0f)
                        target.StartKnockback((target.Position - hitOrigin).NormalizedOr(attacker.Forward), distance, Feel.KnockbackSeconds);
                }
            }

            var hit = new HitEvent
            {
                Attacker = attacker,
                Target = target,
                Skill = skill,
                Result = result,
                IsHeavy = heavy,
                IsDamageOverTime = false,
                Position = target.Position,
            };
            Events.Publish(in hit);

            if (result.Killed) HandleDeath(target, attacker);
            return result.Landed;
        }

        /// <summary>Recurso ganho fora do golpe (esquiva perfeita).</summary>
        public void GainResource(Combatant combatant, double amount)
        {
            if (combatant == null || combatant.IsDead) return;
            Rules.GainResource(ref combatant.vitals, combatant.Stats, amount);
        }

        public bool TrySpendResource(Combatant combatant, double amount)
        {
            return combatant != null && Rules.TrySpendResource(ref combatant.vitals, amount);
        }

        /// <summary>Aplica o resultado de uma poção calculado pelo motor de regras.</summary>
        public double ApplyPotion(Combatant combatant, PotionInfo potion)
        {
            if (combatant == null || combatant.IsDead || potion == null) return 0.0;
            var outcome = Rules.ResolvePotion(potion, combatant.Stats, in combatant.vitals);
            combatant.vitals.Life = outcome.LifeAfter;
            combatant.vitals.Barrier = outcome.BarrierAfter;
            combatant.vitals.BarrierSecondsLeft = outcome.BarrierSeconds;
            return outcome.LifeGained;
        }

        /// <summary>Volta à vida cheia (checkpoint ou reinício da luta, RF-18).</summary>
        public void Revive(Combatant combatant)
        {
            if (combatant == null || !combatant.IsRegistered) return;
            combatant.Effects?.Clear();
            combatant.Hitstop.Clear();
            combatant.IsInvulnerable = false;
            combatant.SecondsSinceCombat = double.MaxValue;
            combatant.SetVitals(Rules.CreateVitals(combatant.Stats, combatant.Class));
            combatant.Actor?.OnRevive(this);
            var evt = new CombatantRevivedEvent { Target = combatant };
            Events.Publish(in evt);
        }

        /// <summary>Próximo ataque do inimigo, sorteado no fluxo de eventos.</summary>
        public int PickAttack(EnemyInfo enemy) => Rules.PickAttack(ref eventsRng, enemy);

        public int NextTelegraphId() => nextTelegraphId++;

        void ApplyDamageOverTime(Combatant target, in EffectTickEvent tick)
        {
            var request = new HitRequest
            {
                Attacker = target.Stats, // DoT do stub não escala com o atacante (nenhum DoT no protótipo)
                Defender = target.Stats,
                SkillTags = tick.Tags,
                BaseDamage = tick.Damage,
                Coefficient = 1.0,
                IsDamageOverTime = true,
                CanBeBlocked = false,
                DefenderLife = target.vitals.Life,
                DefenderBarrier = target.vitals.Barrier,
            };
            var result = Rules.ResolveHit(in request, ref combatRng);
            target.vitals.Life = result.DefenderLifeAfter;
            target.vitals.Barrier = result.DefenderBarrierAfter;
            var hit = new HitEvent { Target = target, Result = result, IsDamageOverTime = true, Position = target.Position };
            Events.Publish(in hit);
            if (result.Killed) HandleDeath(target, null);
        }

        void HandleDeath(Combatant victim, Combatant killer)
        {
            victim.Effects?.Clear();
            victim.IsInvulnerable = false;
            victim.Hitstop.Clear();
            victim.Actor?.OnDeath(this);
            var died = new CombatantDiedEvent { Target = victim, Killer = killer };
            Events.Publish(in died);
            killer?.Actor?.OnKilled(this, victim);
        }
    }
}
