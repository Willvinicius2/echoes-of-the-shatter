namespace Echoes.Gameplay
{
    /// <summary>
    /// Início ou fim do telegraph de um ataque inimigo. Alcance e ângulo são os da consulta real,
    /// para o aviso não mentir. <see cref="ShowOnGround"/> segue o <c>telegraphed</c> do enemy_attacks.csv.
    /// </summary>
    public struct TelegraphEvent
    {
        public int TelegraphId;
        public bool Started;
        public Combatant Owner;
        public TelegraphShape Shape;
        public PlanarVector Origin;
        public PlanarVector Direction;
        public float RangeMeters;
        public float HalfAngleDegrees;
        public float WidthMeters;
        public double DurationSeconds;
        public bool ShowOnGround;
    }
}
