namespace Echoes.Gameplay
{
    /// <summary>Projétil criado ou encerrado. A posição corrente fica em <see cref="ProjectileSystem"/>.</summary>
    public struct ProjectileEvent
    {
        public int ProjectileId;
        public bool Spawned;
        public Combatant Owner;
        public PlanarVector Position;
        public PlanarVector Direction;
        /// <summary>No fim de um projétil que explode: raio da explosão em metros, centrada em <see cref="Position"/> (0 = sem explosão).</summary>
        public float ExplosionRadiusMeters;
    }
}
