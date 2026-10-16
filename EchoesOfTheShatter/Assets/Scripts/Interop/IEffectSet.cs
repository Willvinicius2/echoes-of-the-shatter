using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// Efeitos ativos de UMA entidade (handle <c>shatter_effects</c> da API C). Os modificadores dos
    /// efeitos entram e saem do <see cref="IStatBlock"/> do alvo pelo próprio motor.
    /// </summary>
    public interface IEffectSet : IDisposable
    {
        /// <summary>
        /// Aplica um efeito de conteúdo (ex.: <c>effect.stun</c>). Devolve false se o alvo é imune,
        /// se a recarga interna bloqueou ou se o ID não existe.
        /// </summary>
        bool Apply(string effectId, double magnitude, string sourceId);

        /// <summary>Avança <paramref name="dt"/> segundos (sempre o passo fixo) e acrescenta os eventos à lista.</summary>
        void Tick(double dt, List<EffectTickEvent> outEvents);

        /// <summary>Resultado do ultimo <see cref="Apply"/> (ordens do core: interromper o telegraph, zerar a barreira). Default no stub.</summary>
        ActorApplyResult LastApply { get; }

        /// <summary>Liga o chefe desta entidade: stun e Guarda Quebrada passam a ser aplicados por ele (escudo, imunidade, stagger).</summary>
        void BindBoss(IBossController boss);

        int StackCount(string effectId);

        int ActiveCount { get; }

        /// <summary>Remove todos os efeitos (morte, reinício da luta).</summary>
        void Clear();
    }
}
