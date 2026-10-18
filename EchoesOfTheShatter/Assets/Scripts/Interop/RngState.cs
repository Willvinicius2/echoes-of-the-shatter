namespace Echoes.Interop
{
    /// <summary>
    /// Estado de um gerador PCG32 (2 <c>ulong</c>), guardado pelo C# e passado por referência
    /// ao motor de regras (docs/tecnico/04_arquitetura.md, seção 6.2). Blittable; o layout é o do
    /// <c>Pcg32</c> do rng.h (state, inc).
    /// </summary>
    public struct RngState
    {
        public ulong State;
        public ulong Increment;
    }
}
