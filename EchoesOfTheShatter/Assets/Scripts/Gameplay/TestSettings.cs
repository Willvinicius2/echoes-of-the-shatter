namespace Echoes.Gameplay
{
    /// <summary>Ajustes SO de teste (PlayMode e depuracao): nunca vem do CSV de balanceamento e fica desligado no jogo normal.</summary>
    public static class TestSettings
    {
        /// <summary>O heroi nao morre (a vida volta ao maximo todo quadro): para vencer o Guardiao de verdade nos testes.</summary>
        public static bool HeroGodMode;

        /// <summary>Os inimigos nao morrem (a vida volta ao maximo todo quadro): so para os roteiros de combate do modo de gravacao (-record -scenario).</summary>
        public static bool EnemyGodMode;

        /// <summary>
        /// Velocidade do herói em m/s no lugar da do core (0 = desligado): só para comparar o pé na corrida em vídeo (RecordMode, variável de ambiente de
        /// desenvolvimento ECHOES_DEV_HERO_SPEED). Nunca toca o CSV e nunca liga no jogo normal.
        /// </summary>
        public static float HeroSpeedOverrideMetersPerSecond;
    }
}
