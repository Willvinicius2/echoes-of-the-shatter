namespace Echoes.Gameplay
{
    /// <summary>Percepção da IA num passo.</summary>
    public struct EnemyBrainInput
    {
        /// <summary>Há alvo vivo para perseguir.</summary>
        public bool HasTarget;
        /// <summary>Distância até a borda do alvo, em metros.</summary>
        public float DistanceToTarget;
        /// <summary>false quando atordoado (interrompe o telegraph; docs/13, item 3).</summary>
        public bool CanAct;
    }
}
