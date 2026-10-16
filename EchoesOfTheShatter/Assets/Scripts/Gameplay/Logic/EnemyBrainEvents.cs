using System;

namespace Echoes.Gameplay
{
    /// <summary>O que aconteceu num passo da <see cref="EnemyBrainLogic"/>.</summary>
    [Flags]
    public enum EnemyBrainEvents : byte
    {
        None = 0,
        StateChanged = 1,
        TelegraphStarted = 2,
        AttackImpact = 4,
        AttackEnded = 8,
        Interrupted = 16,
    }
}
