using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// Kit básico de uma classe (<c>shatter::BasicKitData</c>, basic_kits.csv, docs/18 4.6): o combo de golpes leves, o golpe
    /// forte carregado e a defesa. Os NÚMEROS vêm do core (<c>shatter_basic_kit_get</c>); a máquina de combate básica (índice do
    /// combo, buffer, janelas, carga, cancelamentos) roda no C# (<c>HeroCombatLogic</c>, docs/18 8.1) e só lê estes valores.
    /// O C# não guarda número de balanceamento: chaves globais (janela do combo, limiar de segurar...) estão em
    /// <see cref="CombatRules"/>.
    /// </summary>
    public sealed class BasicKitInfo
    {
        static readonly string[] NoIds = Array.Empty<string>();

        public string ClassId { get; internal set; } = string.Empty;

        /// <summary>Golpes leves em ordem (1 a 3). O mesmo ID pode repetir (Arqueiro e Mago repetem o golpe 1 no golpe 2).</summary>
        public IReadOnlyList<string> LightChain { get; internal set; } = NoIds;

        /// <summary>Golpe forte (carregado ao segurar o botão esquerdo).</summary>
        public string HeavySkill { get; internal set; } = string.Empty;

        /// <summary>Duração da carga em segundos, depois do limiar <see cref="CombatRules.HeavyHoldThresholdSeconds"/>.</summary>
        public double HeavyChargeSeconds { get; internal set; }

        /// <summary>Multiplicador de dano na carga máxima (>= 1). Progresso linear: 1 + (max - 1) * progresso.</summary>
        public double HeavyMaxMultiplier { get; internal set; } = 1.0;

        /// <summary>Efeito de movimento reaplicado a cada tick enquanto carrega.</summary>
        public string ChargeEffect { get; internal set; } = string.Empty;

        /// <summary>
        /// Efeito reaplicado a cada tick enquanto defende (tag <see cref="SkillTags.Guard"/>). O dano recebido só cai se o golpe
        /// vem de dentro do arco: informe <see cref="HitRequest.FromGuardArc"/> ao resolver o golpe.
        /// </summary>
        public string GuardEffect { get; internal set; } = string.Empty;

        /// <summary>Arco TOTAL da defesa em graus (120 = ±60° em torno da mira; 360 = cúpula). A geometria é do C# (ShapeQuery).</summary>
        public double GuardArcDegrees { get; internal set; }

        /// <summary>Tempo máximo da defesa em segundos; 0 = ilimitado.</summary>
        public double GuardMaxHoldSeconds { get; internal set; }

        /// <summary>Espera em segundos depois de soltar a defesa (ou de ela cair sozinha).</summary>
        public double GuardCooldownSeconds { get; internal set; }

        /// <summary>Janela da defesa perfeita em segundos depois de apertar; 0 = sem defesa perfeita.</summary>
        public double GuardPerfectWindowSeconds { get; internal set; }

        /// <summary>Tempo mínimo em segundos desde o último aperto para a janela perfeita abrir de novo.</summary>
        public double GuardPerfectCooldownSeconds { get; internal set; }

        /// <summary>Efeitos aplicados no atacante corpo a corpo pela defesa perfeita.</summary>
        public IReadOnlyList<string> GuardPerfectEffects { get; internal set; } = NoIds;

        /// <summary>Recurso ganho pela defesa perfeita (substitui o <see cref="ClassInfo.ResourceOnBlock"/>).</summary>
        public double GuardPerfectResource { get; internal set; }

        /// <summary>Recurso gasto por ponto de dano evitado; 0 = não gasta (Mago: 1,0 de Mana por ponto).</summary>
        public double GuardDrainPerDamage { get; internal set; }

        public bool HasPerfectGuard => GuardPerfectWindowSeconds > 0.0;
        public bool HasGuardTimeLimit => GuardMaxHoldSeconds > 0.0;
        public bool GuardDrainsResource => GuardDrainPerDamage > 0.0;

        public override string ToString() => ClassId;
    }
}
