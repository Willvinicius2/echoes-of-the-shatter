namespace Echoes.Gameplay
{
    /// <summary>
    /// Comandos de combate do herói. Os índices 0..5 são os espaços da barra (botão esquerdo, botão
    /// direito, Q, E, R, F); as teclas reais vêm das ações nomeadas do Echoes.inputactions.
    /// </summary>
    public enum HeroCommand : sbyte
    {
        None = -1,
        BasicAttack = 0,
        Skill1 = 1,
        Skill2 = 2,
        Skill3 = 3,
        Skill4 = 4,
        Skill5 = 5,
        Dodge = 6,
        Potion1 = 7,
        Potion2 = 8,
    }
}
