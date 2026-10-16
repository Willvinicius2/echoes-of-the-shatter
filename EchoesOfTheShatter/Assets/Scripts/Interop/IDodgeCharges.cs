using System;

namespace Echoes.Interop
{
    public enum DodgeStartStatus { Ok = 0, NoCharges = 1, Active = 2, NotEnoughResource = 3 }

    /// <summary>
    /// Cargas e invulnerabilidade da esquiva (<c>shatter_dodge_*</c>; docs/13 item 1): recarga em série, janela de i-frames,
    /// recurso da esquiva perfeita. O deslocamento (direção, distância) é posição, do cliente.
    /// </summary>
    public interface IDodgeCharges : IDisposable
    {
        int Charges { get; }
        int MaxCharges { get; }
        bool IsFull { get; }
        bool IsEmpty { get; }

        /// <summary>Esquiva em andamento (dura <see cref="CombatRules.DodgeDurationSeconds"/>).</summary>
        bool IsDodging { get; }

        /// <summary>Segundos desde o início da esquiva em andamento.</summary>
        double Elapsed { get; }

        /// <summary>0 a 1: quanto da próxima carga já recarregou (0 se cheia).</summary>
        double RechargeFraction { get; }

        /// <summary>Invulnerável de 0 (inclusive) até <c>dodge_iframes</c> (exclusive).</summary>
        bool IsInvulnerable { get; }

        /// <summary>Recurso da esquiva perfeita se um golpe chegou durante os i-frames (senão 0).</summary>
        double PerfectReward { get; }

        void Tick(double dt);

        /// <summary>Começa a esquiva; só com Ok gasta a carga. <paramref name="resourceAvailable"/> é o recurso atual (custo <c>dodge_cost_resource</c>).</summary>
        DodgeStartStatus TryStart(double resourceAvailable);

        /// <summary>Volta ao estado inicial (cargas cheias, sem esquiva em andamento): morte, checkpoint, reinício.</summary>
        void Reset();
    }
}
