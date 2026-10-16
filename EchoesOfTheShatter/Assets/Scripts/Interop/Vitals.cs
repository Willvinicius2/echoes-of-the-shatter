namespace Echoes.Interop
{
    /// <summary>
    /// Valores correntes de uma entidade: vida, recurso e barreira. O C# guarda; quem altera é
    /// sempre o motor de regras (golpe, poção, regeneração) por meio do <see cref="IRulesCore"/>.
    /// </summary>
    public struct Vitals
    {
        public double Life;
        public double Resource;
        public double Barrier;
        /// <summary>Segundos que faltam para a barreira temporária (poção de Resguardo) acabar; 0 = sem prazo.</summary>
        public double BarrierSecondsLeft;
    }
}
