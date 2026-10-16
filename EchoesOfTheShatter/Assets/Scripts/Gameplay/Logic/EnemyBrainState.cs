namespace Echoes.Gameplay
{
    /// <summary>Estados da IA base (RF-20): parado → perseguir → telegraph → atacar → recuperar.</summary>
    public enum EnemyBrainState : byte
    {
        Idle = 0,
        Chase = 1,
        Telegraph = 2,
        Attack = 3,
        Recover = 4,
        Dead = 5,
    }
}
