namespace Echoes.Gameplay
{
    /// <summary>
    /// Ator que reage a "interrompa a ação em andamento" (ordem do core ao C#, <c>ActorApplyResult.Interrupted</c>: stun ou stagger
    /// em cima de uma preparação). O <see cref="CombatSystem"/> chama depois de aplicar um efeito.
    /// </summary>
    public interface IInterruptible
    {
        void OnInterrupted(CombatSystem combat);
    }
}
