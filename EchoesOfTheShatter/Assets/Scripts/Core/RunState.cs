namespace Echoes.Core
{
    /// <summary>
    /// Estado da corrida atual que a UI precisa ler e que ainda nao vem do save: o Fervor (RF-32; +200% XP) fica ativo quando o jogador entra na
    /// Cripta por "Jogar esta rota agora" (S-09) e some ao voltar ao Refugio. O Backend vai passar a gravar o Fervor no save; ate la este valor
    /// e o unico ponto de leitura da HUD (trocar aqui, a HUD nao muda).
    /// </summary>
    public static class RunState
    {
        public static bool FervorActive;

        public static void Reset() => FervorActive = false;
    }
}
