namespace Echoes.Gameplay
{
    /// <summary>
    /// O save sobe de nível por mais de um caminho (morte na Cripta, coleta de expedição no Refúgio, XP de missão). O herói em cena confere o nível
    /// do save e refaz o bloco quando ficou para trás (<see cref="HeroController"/>); esta é a comparação, sem Unity para poder ser testada.
    /// </summary>
    public static class HeroLevelSync
    {
        /// <summary>O nível do herói em cena difere do nível do save. Save sem nível (leitura falhou, 0) não manda refazer.</summary>
        public static bool NeedsRefresh(int heroLevel, int saveLevel) => saveLevel >= 1 && saveLevel != heroLevel;
    }
}
