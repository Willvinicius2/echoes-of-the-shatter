namespace Echoes.Interop
{
    /// <summary>
    /// Resultado de aplicar um efeito pelo <c>shatter_actor</c> (stun e Guarda Quebrada, docs/13 item 3). Os campos
    /// <see cref="Interrupted"/> e <see cref="RemoveBarrier"/> sao ORDENS do core ao C# (cancelar o telegraph em andamento,
    /// zerar a barreira/escudo do alvo). Vazio no stub.
    /// </summary>
    public struct ActorApplyResult
    {
        public bool Applied;
        public bool Stunned;
        public bool StunBlocked;
        public bool Interrupted;
        public bool Staggered;
        public bool RemoveBarrier;
        public double StunSeconds;
        public double StaggerSeconds;
        public int GuardBreakStacks;
    }
}
