using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Valores que a máquina de entrada do ataque básico lê (docs/18, seções 1.2 e 4.6): as chaves globais do <c>rules.csv</c>
    /// (<c>combo_window</c>, <c>attack_buffer</c>...) e a linha da classe em <c>basic_kits.csv</c>. O core lê e valida o CSV; o C# só
    /// consome por esta interface. Nenhum número fica no código (CLAUDE.md): quem implementa é o adaptador do core
    /// (<see cref="BasicKitSource"/>) e, nos testes, um valor falso declarado no próprio teste.
    /// Tempos em segundos; a máquina converte para ticks de 1/60 s (arredondando para cima).
    /// </summary>
    public interface IBasicKit
    {
        /// <summary>Tempo depois do fim da recuperação em que um clique ainda continua o combo.</summary>
        double ComboWindow { get; }

        /// <summary>Janela que reabre ao fim da esquiva.</summary>
        double ComboWindowAfterDodge { get; }

        /// <summary>Um clique entra na fila se chegar nos últimos <c>AttackBuffer</c> s da recuperação.</summary>
        double AttackBuffer { get; }

        /// <summary>Segurar o botão esquerdo por este tempo vira carga do ataque forte.</summary>
        double HeavyHoldThreshold { get; }

        /// <summary>Fração (0 a 1) da preparação do golpe leve que o tempo apertado desconta.</summary>
        double LightWindupCreditMax { get; }

        /// <summary>Depois de soltar a defesa o herói não ataca por este tempo.</summary>
        double GuardLowerTime { get; }

        /// <summary>Golpes leves em ordem (1 a 3); o mesmo golpe pode repetir.</summary>
        IReadOnlyList<SkillInfo> LightChain { get; }

        SkillInfo HeavySkill { get; }

        /// <summary>Duração da carga depois do limiar; no fim dela o golpe solta sozinho.</summary>
        double HeavyChargeTime { get; }

        /// <summary>Multiplicador de dano na carga máxima (a carga mínima vale 1).</summary>
        double HeavyMaxMult { get; }

        /// <summary>Efeito reaplicado a cada tick enquanto carrega (vazio = nenhum).</summary>
        string ChargeEffect { get; }

        /// <summary>Efeito reaplicado a cada tick enquanto defende (vazio = nenhum).</summary>
        string GuardEffect { get; }

        /// <summary>Arco da defesa em graus (total, 0 a 360).</summary>
        double GuardArcDegrees { get; }

        /// <summary>Tempo máximo de defesa contínua (0 = ilimitado).</summary>
        double GuardMaxHold { get; }

        /// <summary>Espera depois de soltar (ou de a defesa cair sozinha) para defender de novo.</summary>
        double GuardCooldown { get; }

        /// <summary>Janela da defesa perfeita depois de apertar (0 = sem defesa perfeita).</summary>
        double GuardPerfectWindow { get; }

        /// <summary>Tempo mínimo desde o último aperto para a janela perfeita abrir de novo.</summary>
        double GuardPerfectCooldown { get; }
    }
}
