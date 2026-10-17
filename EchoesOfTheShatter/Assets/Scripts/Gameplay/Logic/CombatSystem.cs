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
    public sealed class CombatSystem : IDisposable
    {
        /// <summary>
        /// Índice do fluxo Events reservado à escolha de ataque da IA. Os índices baixos são das salas
        /// (eventos de área, docs/04 seção 6.2); este fica longe deles para um não deslocar o outro.
        /// </summary>
        public const ulong AiAttackStreamIndex = 1UL << 62;

        /// <summary>Índice do fluxo Events reservado ao sorteio de elite (modificador; consome sempre 1 número).</summary>
        public const ulong EliteStreamIndex = (1UL << 62) + 1UL;

        readonly List<Combatant> combatants = new List<Combatant>();
        readonly List<string> orderKeys = new List<string>();
        readonly List<EffectTickEvent> effectEvents = new List<EffectTickEvent>();
        readonly IStatBlock neutralSource;
        RngState combatRng;
        RngState aiRng;
        RngState eliteRng;
        int nextId = 1;
        int nextTelegraphId = 1;

        public CombatSystem(IRulesCore rules, EventBus events, ulong runSeed, CombatFeelValues feel, int maxStepsPerFrame)
        {
            Rules = rules ?? throw new ArgumentNullException(nameof(rules));
            Events = events ?? throw new ArgumentNullException(nameof(events));
            Feel = feel ?? new CombatFeelValues();
            RunSeed = runSeed;
            combatRng = rules.CreateRng(runSeed, RngStream.Combat, 0);
            aiRng = rules.CreateRng(runSeed, RngStream.Events, AiAttackStreamIndex);
            eliteRng = rules.CreateRng(runSeed, RngStream.Events, EliteStreamIndex);
            neutralSource = rules.CreateEmptyStats();
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
            Register(combatant, actor, null);
        }

        /// <summary>
        /// Registra no combate. A ordem de passo (e de consumo do RNG) é: heróis antes de inimigos, depois
        /// <paramref name="orderKey"/> em ordem ordinal (a cena passa o caminho na hierarquia), depois a ordem
        /// de registro. Assim a mesma cena e a mesma seed repetem a luta, seja qual for a ordem dos Start.
        /// </summary>
        public void Register(Combatant combatant, ICombatActor actor, string orderKey)
        {
            if (combatant == null) throw new ArgumentNullException(nameof(combatant));
            if (combatant.IsRegistered) return;
            combatant.Id = nextId++;
            combatant.Actor = actor;
            combatant.IsRegistered = true;
            combatant.SetVitals(Rules.CreateVitals(combatant.Stats, combatant.Class));
            if (combatant.InitialBarrier > 0.0) combatant.vitals.Barrier = combatant.InitialBarrier; // elite: barreira inicial do core

            var index = combatants.Count;
            for (var i = 0; i < combatants.Count; i++)
            {
                if (ComesBefore(combatant.Team, orderKey, combatants[i].Team, orderKeys[i])) { index = i; break; }
            }
            combatants.Insert(index, combatant);
            orderKeys.Insert(index, orderKey);
            RefreshHero();
        }

        public void Unregister(Combatant combatant)
        {
            if (combatant == null || !combatant.IsRegistered) return;
            combatant.IsRegistered = false;
            var index = combatants.IndexOf(combatant);
            if (index >= 0)
            {
                combatants.RemoveAt(index);
                orderKeys.RemoveAt(index);
            }
            RefreshHero();
        }

        static bool ComesBefore(CombatTeam team, string key, CombatTeam otherTeam, string otherKey)
        {
            if (team != otherTeam) return team < otherTeam;
            if (key == null) return false;          // sem chave: no fim do time, em ordem de registro
            if (otherKey == null) return true;
            return string.CompareOrdinal(key, otherKey) < 0;
        }

        void RefreshHero()
        {
            Hero = null;
            for (var i = 0; i < combatants.Count; i++)
            {
                if (combatants[i].Team != CombatTeam.Hero) continue;
                Hero = combatants[i];
                break;
            }
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
                // Posição só avança aqui, em passos de 1/60 s (A-04): o resultado não depende do FPS.
                c.PreviousPosition = c.Position;
                var knockback = c.ConsumeKnockback((float)dt);
                if (!knockback.IsZero) c.Position += knockback;
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
        /// <paramref name="damageMultiplier"/>: multiplicador do golpe forte carregado (docs/18, seção 1.4: 1 + (heavyMaxMult - 1) * carga),
        /// vindo da máquina de entrada; 1 em todo outro golpe. Entra como fator do coeficiente da habilidade.
        /// </summary>
        public bool ApplySkillHit(Combatant attacker, Combatant target, SkillInfo skill, PlanarVector hitOrigin, double damageMultiplier = 1.0)
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
                Coefficient = skill.Coefficient(1) * damageMultiplier,
                IsDamageOverTime = false,
                CanBeBlocked = true,
                DefenderLife = target.vitals.Life,
                DefenderBarrier = target.vitals.Barrier,
            };
            var result = Rules.ResolveHit(in request, ref combatRng);
            if (target.Boss != null)
            {
                // O chefe guarda a própria vida: escudo frontal (ângulo pela posição do atacante), rugido e limiar de fase são do core.
                var boss = target.Boss.ApplyDamage(result.LifeLost, target.Position.X, target.Position.Z, hitOrigin.X, hitOrigin.Z);
                if (boss.ShieldBlocked || boss.Invulnerable)
                {
                    var blocked = new ShieldBlockedEvent { Attacker = attacker, Target = target, Skill = skill, Invulnerable = boss.Invulnerable };
                    Events.Publish(in blocked);
                    return false; // 0 de dano, sem Ímpeto, sem empurrão, sem efeitos
                }
                result.LifeLost = boss.Applied;
                result.DefenderLifeAfter = boss.LifeAfter;
                result.Killed = boss.Killed;
            }
            target.vitals.Life = result.DefenderLifeAfter;
            target.vitals.Barrier = result.DefenderBarrierAfter;

            var heavy = Feel.IsHeavy(skill.Id);
            if (result.Landed)
            {
                var onHit = skill.OnHitEffects;
                for (var i = 0; i < onHit.Count; i++) ApplyEffect(target, onHit[i], 1.0, attacker.ContentId);
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

        /// <summary>
        /// Aplica um efeito pelo core (stun e Guarda Quebrada passam pelo actor/chefe) e cumpre as ordens que ele devolve:
        /// interromper a preparação em andamento e zerar a barreira (<see cref="ActorApplyResult"/>).
        /// </summary>
        public bool ApplyEffect(Combatant target, string effectId, double magnitude, string sourceId)
        {
            if (target == null || target.Effects == null || target.IsDead) return false;
            var applied = target.Effects.Apply(effectId, magnitude, sourceId);
            var result = target.Effects.LastApply;
            if (result.RemoveBarrier)
            {
                target.vitals.Barrier = 0.0;
                target.vitals.BarrierSecondsLeft = 0.0;
            }
            if (result.Interrupted) (target.Actor as IInterruptible)?.OnInterrupted(this);
            return applied;
        }

        /// <summary>Sorteia o modificador de elite no fluxo de eventos (consome sempre 1 número do fluxo).</summary>
        public EliteProfile RollElite() => Rules.RollElite(ref eliteRng);

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

        /// <summary>Libera o handle próprio (fonte neutra de DoT). As entidades são dos seus donos.</summary>
        public void Dispose()
        {
            neutralSource.Dispose();
        }

        /// <summary>Próximo ataque do inimigo, sorteado no fluxo Events reservado à IA.</summary>
        public int PickAttack(EnemyInfo enemy) => Rules.PickAttack(ref aiRng, enemy);

        public int NextTelegraphId() => nextTelegraphId++;

        void ApplyDamageOverTime(Combatant target, in EffectTickEvent tick)
        {
            var request = new HitRequest
            {
                Attacker = neutralSource, // fonte neutra: os mods de dano da vítima não escalam o DoT
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
