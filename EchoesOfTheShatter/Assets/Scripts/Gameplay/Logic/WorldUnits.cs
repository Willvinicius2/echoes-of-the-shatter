namespace Echoes.Gameplay
{
    /// <summary>
    /// Conversão de unidades. Os CSV usam uu (1 uu = 1 cm, herança do plano em Unreal; docs/tecnico/06_dados.md);
    /// o mundo Unity usa metros (1 unidade = 1 m; docs/tecnico/04_arquitetura.md, seção 3.1). Não é balanceamento.
    /// </summary>
    public static class WorldUnits
    {
        public const double MetersPerUu = 0.01;

        public static float ToMeters(double uu) => (float)(uu * MetersPerUu);
    }
}
