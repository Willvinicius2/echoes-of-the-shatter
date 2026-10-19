namespace Echoes.Gameplay
{
    /// <summary>
    /// Trava de Fome das habilidades devoradas (docs/design/21). A lógica do herói pergunta antes de gastar o recurso e avisa depois do gasto;
    /// o número do custo e o limite vêm do core (story_rules.csv), a implementação só guarda a conta da corrida.
    /// </summary>
    public interface IHungerGate
    {
        /// <summary>true se a habilidade não é devorada ou ainda há Fome sobrando para ela.</summary>
        bool CanCast(string skillId);

        /// <summary>A habilidade foi usada: gasta a Fome dela (nada para habilidades comuns).</summary>
        void Spent(string skillId);
    }
}
