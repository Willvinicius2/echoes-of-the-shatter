namespace Echoes.Core
{
    /// <summary>Assinante de um evento do <see cref="EventBus"/>. O evento chega por referência (sem cópia).</summary>
    public delegate void GameEventHandler<T>(in T evt) where T : struct;
}
