using System;

namespace Echoes.Gameplay
{
    /// <summary>O que aconteceu num avanço da <see cref="ActionTimeline"/> (pode ser mais de um no mesmo passo).</summary>
    [Flags]
    public enum ActionTimelineEvents : byte
    {
        None = 0,
        ImpactStarted = 1,
        ImpactEnded = 2,
        Finished = 4,
    }
}
