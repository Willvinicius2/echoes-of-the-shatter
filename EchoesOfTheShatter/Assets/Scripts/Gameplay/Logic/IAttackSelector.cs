namespace Echoes.Gameplay
{
    /// <summary>Escolhe o próximo ataque (índice). No jogo, sorteio ponderado no fluxo de eventos do RNG.</summary>
    public interface IAttackSelector
    {
        int SelectAttack();
    }
}
