namespace Echoes.Gameplay
{
    /// <summary>
    /// Comportamento de uma entidade no passo fixo (herói ou inimigo). Chamado só pelo
    /// <see cref="CombatSystem"/>, na ordem de registro (determinística).
    /// </summary>
    public interface ICombatActor
    {
        /// <summary>Passo normal (entidade viva e fora de hitstop).</summary>
        void FixedTick(CombatSystem combat, double dt);

        /// <summary>Passo em hitstop: timers parados; só o que precisa saber que está congelada.</summary>
        void FrozenTick(CombatSystem combat, double dt);

        /// <summary>Um golpe teria acertado esta entidade, mas ela estava invulnerável (esquiva).</summary>
        void OnIncomingHitAvoided(CombatSystem combat, Combatant attacker);

        void OnKilled(CombatSystem combat, Combatant victim);

        void OnDeath(CombatSystem combat);

        void OnRevive(CombatSystem combat);
    }
}
