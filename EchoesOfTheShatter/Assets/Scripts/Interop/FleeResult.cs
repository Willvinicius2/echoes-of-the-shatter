namespace Echoes.Interop
{
    /// <summary>
    /// Um passo da fuga do inimigo, decidido pelo core (<c>shatter_actor_flee_step</c>, API 1.3; enemy_ai.csv). O C# so move e anima.
    /// <see cref="Started"/> manda cancelar o telegraph e o golpe em curso. Vazio (nunca foge) no stub.
    /// </summary>
    public struct FleeResult
    {
        public double Remaining;
        public bool Fleeing;
        public bool Started;
        public bool Ended;
        public bool CanFlee;
    }
}
