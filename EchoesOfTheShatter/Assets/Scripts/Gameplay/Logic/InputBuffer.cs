namespace Echoes.Gameplay
{
    /// <summary>
    /// Guarda o último comando pedido por uma janela curta (docs/13, item 1: buffer de 0,10 s), para a
    /// ação sair assim que a atual terminar. O pedido mais novo substitui o anterior.
    /// </summary>
    public sealed class InputBuffer
    {
        HeroCommand pending = HeroCommand.None;
        double age;

        public InputBuffer(double windowSeconds)
        {
            WindowSeconds = windowSeconds;
        }

        public double WindowSeconds { get; }
        public bool HasPending => pending != HeroCommand.None;
        public HeroCommand Pending => pending;

        public void Push(HeroCommand command)
        {
            if (command == HeroCommand.None) return;
            pending = command;
            age = 0.0;
        }

        public void Consume()
        {
            pending = HeroCommand.None;
            age = 0.0;
        }

        /// <summary>Envelhece o pedido; descarta quando passa da janela.</summary>
        public void Tick(double dt)
        {
            if (pending == HeroCommand.None) return;
            age += dt;
            if (age > WindowSeconds + 1e-9) Consume();
        }
    }
}
