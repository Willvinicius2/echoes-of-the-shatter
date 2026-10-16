using System;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Máquina de estados base dos inimigos (RF-20; docs/04_arquitetura.md, seção 10.4):
    /// Idle → Chase (alvo dentro do aggro) → Telegraph (alvo no alcance do ataque escolhido) →
    /// Attack (impacto) → Recover → Chase/Idle. Atordoado durante o telegraph = interrompido
    /// (vai para Recover). Pura e determinística: a escolha do ataque vem de <see cref="IAttackSelector"/>.
    /// Estados próprios de cada família (cercar, fugir, recuar) entram como extensões depois que a
    /// tabela enemy_ai.csv existir (docs/13, item 6).
    /// </summary>
    public sealed class EnemyBrainLogic
    {
        const double Epsilon = 1e-9;

        readonly EnemyAttackProfile[] attacks;
        readonly IAttackSelector selector;

        public EnemyBrainLogic(float aggroRangeMeters, EnemyAttackProfile[] attacks, IAttackSelector selector)
        {
            AggroRangeMeters = aggroRangeMeters;
            this.attacks = attacks ?? Array.Empty<EnemyAttackProfile>();
            this.selector = selector;
            CurrentAttack = -1;
        }

        public float AggroRangeMeters { get; }
        public EnemyBrainState State { get; private set; }
        public EnemyBrainState PreviousState { get; private set; }
        public double StateElapsed { get; private set; }
        public int CurrentAttack { get; private set; }
        public int AttackCount => attacks.Length;

        public bool WantsToMove => State == EnemyBrainState.Chase;

        /// <summary>A direção fica travada do início do telegraph ao fim do impacto (docs/13, item 4.2).</summary>
        public bool CanRotate => State == EnemyBrainState.Idle || State == EnemyBrainState.Chase || State == EnemyBrainState.Recover;

        public EnemyAttackProfile CurrentProfile => CurrentAttack >= 0 && CurrentAttack < attacks.Length ? attacks[CurrentAttack] : default;

        public EnemyBrainEvents Tick(double dt, in EnemyBrainInput input)
        {
            if (State == EnemyBrainState.Dead) return EnemyBrainEvents.None;
            StateElapsed += dt;
            var events = EnemyBrainEvents.None;

            switch (State)
            {
                case EnemyBrainState.Idle:
                    if (input.HasTarget && input.DistanceToTarget <= AggroRangeMeters)
                    {
                        EnsureAttackChosen();
                        events |= Enter(EnemyBrainState.Chase, 0.0);
                    }
                    break;

                case EnemyBrainState.Chase:
                    if (!input.HasTarget)
                    {
                        events |= Enter(EnemyBrainState.Idle, 0.0);
                        break;
                    }
                    EnsureAttackChosen();
                    if (CurrentAttack >= 0 && input.CanAct && !input.HoldFire && input.DistanceToTarget <= CurrentProfile.RangeMeters)
                    {
                        events |= Enter(EnemyBrainState.Telegraph, 0.0) | EnemyBrainEvents.TelegraphStarted;
                        events |= AdvanceZeroLength();
                    }
                    break;

                case EnemyBrainState.Telegraph:
                    if (!input.CanAct)
                    {
                        events |= Enter(EnemyBrainState.Recover, 0.0) | EnemyBrainEvents.Interrupted;
                        break;
                    }
                    if (StateElapsed + Epsilon >= CurrentProfile.Windup)
                    {
                        events |= Enter(EnemyBrainState.Attack, StateElapsed - CurrentProfile.Windup) | EnemyBrainEvents.AttackImpact;
                        events |= AdvanceZeroLength();
                    }
                    break;

                case EnemyBrainState.Attack:
                    if (StateElapsed + Epsilon >= CurrentProfile.Impact)
                    {
                        events |= Enter(EnemyBrainState.Recover, StateElapsed - CurrentProfile.Impact) | EnemyBrainEvents.AttackEnded;
                    }
                    break;

                case EnemyBrainState.Recover:
                    var recovery = CurrentAttack >= 0 ? CurrentProfile.Recovery : 0.0;
                    if (StateElapsed + Epsilon >= recovery && input.CanAct)
                    {
                        CurrentAttack = selector != null && attacks.Length > 0 ? selector.SelectAttack() : (attacks.Length > 0 ? 0 : -1);
                        events |= Enter(input.HasTarget ? EnemyBrainState.Chase : EnemyBrainState.Idle, 0.0);
                    }
                    break;
            }
            return events;
        }

        /// <summary>Morte: para tudo. Um telegraph em andamento é encerrado por quem chama.</summary>
        /// <summary>Ordem do core (stun/stagger): cancela o telegraph em andamento. Devolve os eventos (Interrupted) ou None.</summary>
        public EnemyBrainEvents Interrupt()
        {
            if (State != EnemyBrainState.Telegraph) return EnemyBrainEvents.None;
            return Enter(EnemyBrainState.Recover, 0.0) | EnemyBrainEvents.Interrupted;
        }

        public void Kill()
        {
            PreviousState = State;
            State = EnemyBrainState.Dead;
            StateElapsed = 0.0;
        }

        public void Reset()
        {
            PreviousState = State;
            State = EnemyBrainState.Idle;
            StateElapsed = 0.0;
            CurrentAttack = -1;
        }

        void EnsureAttackChosen()
        {
            if (CurrentAttack >= 0 || attacks.Length == 0) return;
            CurrentAttack = selector != null ? selector.SelectAttack() : 0;
            if (CurrentAttack < 0 || CurrentAttack >= attacks.Length) CurrentAttack = 0;
        }

        EnemyBrainEvents Enter(EnemyBrainState next, double carry)
        {
            PreviousState = State;
            State = next;
            StateElapsed = carry > 0.0 ? carry : 0.0;
            return EnemyBrainEvents.StateChanged;
        }

        // Telegraph ou impacto de duração zero passam no mesmo passo (dados com windup 0).
        EnemyBrainEvents AdvanceZeroLength()
        {
            var events = EnemyBrainEvents.None;
            if (State == EnemyBrainState.Telegraph && CurrentProfile.Windup <= Epsilon)
                events |= Enter(EnemyBrainState.Attack, StateElapsed) | EnemyBrainEvents.AttackImpact;
            if (State == EnemyBrainState.Attack && CurrentProfile.Impact <= Epsilon)
                events |= Enter(EnemyBrainState.Recover, StateElapsed) | EnemyBrainEvents.AttackEnded;
            return events;
        }
    }
}
