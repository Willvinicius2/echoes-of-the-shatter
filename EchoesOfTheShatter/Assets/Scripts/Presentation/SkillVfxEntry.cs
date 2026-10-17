using System;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>Onde um <see cref="VfxSpec"/> nasce.</summary>
    public enum VfxPlace : byte
    {
        /// <summary>No Transform âncora do dono (<see cref="VfxSpec.anchor"/>); com <see cref="VfxSpec.follow"/> acompanha o osso.</summary>
        Anchor = 0,
        /// <summary>Nos pés do dono (raiz do objeto, no piso).</summary>
        OwnerFeet = 1,
        /// <summary>No ponto mirado no chão, limitado ao alcance da habilidade (Chuva de Flechas).</summary>
        AimGround = 2,
        /// <summary>No alvo atingido (golpe) ou no fim do projétil (explosão).</summary>
        Target = 3,
    }

    /// <summary>
    /// Um efeito a tocar em pool (<see cref="VfxPool"/>). Dado de apresentação: tamanho, duração e âncora ficam aqui (SO_SkillPresentation_*),
    /// nunca no código. <see cref="authoredRadiusMeters"/> liga o tamanho ao alcance real da habilidade: o efeito não mente sobre a área.
    /// </summary>
    [Serializable]
    public sealed class VfxSpec
    {
        public GameObject prefab;
        public VfxPlace place = VfxPlace.Anchor;
        [Tooltip("Transform âncora (weapon_tip, staff_crystal, bow_nock, shield_face, chest, root_feet...). Vazio = raiz do dono.")]
        public string anchor = string.Empty;
        [Tooltip("Segundos até devolver ao pool (cobre a vida das partículas).")]
        [Min(0f)] public float seconds = 1f;
        [Tooltip("Acompanha o Transform âncora enquanto durar.")]
        public bool follow;
        [Tooltip("Gira o efeito para a direção do golpe; senão fica na rotação do mundo.")]
        public bool alignToDirection = true;
        [Tooltip("Altura acima do ponto, em metros.")]
        public float yOffset;
        [Tooltip("Multiplicador de tamanho.")]
        [Min(0.01f)] public float scale = 1f;
        [Tooltip("Raio com que o prefab foi feito (m). Maior que 0: o tamanho vira (raio da habilidade / este valor).")]
        [Min(0f)] public float authoredRadiusMeters;
        [Tooltip("Estica o comprimento (Z) até o alcance da habilidade (feixe do Raio Arcano).")]
        public bool lengthFromRange;
        [Tooltip("Segundos de duração do efeito até o último golpe visual (queda das flechas). Maior que 0: o efeito começa em (PhaseSeconds da fase - este valor) e termina junto do fim da fase, então acompanha o tempo do impacto vindo dos dados.")]
        [Min(0f)] public float endsWithPhaseAfter;

        public bool IsSet => prefab != null;
    }

    /// <summary>
    /// VFX de uma habilidade (ou de um estado do kit, com ID virtual <c>&lt;classe&gt;#guard</c>, <c>#perfect</c>, <c>#guard_break</c>).
    /// Lido pelo <see cref="SkillVfxPresenter"/>, que reage aos eventos do core; guardado em <see cref="SkillPresentationSet.vfx"/>,
    /// separado das entradas de animação (<see cref="SkillPresentationEntry"/>), que outro builder regenera.
    /// </summary>
    [Serializable]
    public sealed class SkillVfxEntry
    {
        [Tooltip("ID de conteúdo (skill.mage.fireball) ou virtual (class.warrior#guard).")]
        public string skillId = string.Empty;

        [Header("Fases (SkillPhaseEvent)")]
        [Tooltip("Preparação: brilho de lançamento na mão. Acaba na fase seguinte.")]
        public VfxSpec[] windupFx = Array.Empty<VfxSpec>();
        [Tooltip("Início do impacto: clarão de saída, nova no chão, chuva.")]
        public VfxSpec[] releaseFx = Array.Empty<VfxSpec>();

        [Header("Carga do golpe forte (BasicInputEvent)")]
        public VfxSpec[] chargeFx = Array.Empty<VfxSpec>();
        public VfxSpec[] chargeFullFx = Array.Empty<VfxSpec>();

        [Header("Rastro da arma (golpe corpo a corpo)")]
        public VfxSpec trail = new VfxSpec();
        [Tooltip("Âncora do cabo (lado da mão) e da ponta da fita do rastro.")]
        public string trailBase = "weapon_base";
        public string trailTip = "weapon_tip";
        [Tooltip("Largura da fita em relação ao comprimento da arma (o 3º golpe do combo é mais largo).")]
        [Min(0.1f)] public float trailWidth = 1f;
        [Tooltip("Segundos em que a fita continua a ser desenhada a partir do início do impacto (o resto é o apagar da cauda).")]
        [Min(0.02f)] public float trailEmitSeconds = 0.2f;

        [Header("Projétil (ProjectileEvent)")]
        [Tooltip("Visual do projétil em voo (substitui o do ProjectilePresenter).")]
        public GameObject projectile;
        [Min(0.01f)] public float projectileScale = 1f;
        [Tooltip("Âncora de onde o projétil sai (staff_crystal, bow_nock...): a magia sai da mão e converge para a trajetória do core.")]
        public string launchAnchor = string.Empty;
        [Tooltip("Metros de voo até o visual alinhar com a trajetória lógica.")]
        [Min(0f)] public float launchBlendMeters = 1.5f;
        [Tooltip("Segundos em que o rastro do projétil continua depois que ele acaba.")]
        [Min(0f)] public float lingerSeconds = 0.25f;
        [Tooltip("Fim do projétil que acertou alguém: explosão.")]
        public VfxSpec[] endFx = Array.Empty<VfxSpec>();
        [Tooltip("Fim do projétil que não acertou ninguém (alcance esgotado).")]
        public VfxSpec[] missFx = Array.Empty<VfxSpec>();

        [Header("Acerto (HitEvent)")]
        public VfxSpec[] hitFx = Array.Empty<VfxSpec>();
        [Tooltip("Golpe pesado (hitstop): se vazio usa hitFx.")]
        public VfxSpec[] hitHeavyFx = Array.Empty<VfxSpec>();
    }
}
