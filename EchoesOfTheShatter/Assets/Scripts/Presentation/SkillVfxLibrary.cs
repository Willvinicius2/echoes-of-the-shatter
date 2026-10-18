using System.Collections.Generic;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Lista dos SO_SkillPresentation_* que têm VFX e o orçamento de luzes dos efeitos. Fica em Assets/Resources/Echoes para o
    /// <see cref="SkillVfxPresenter"/> se instalar sozinho em qualquer cena que tenha um <see cref="VfxPool"/> (Refúgio, Cripta, vitrine),
    /// sem editar os builders das cenas. Gerado pelo VfxLibraryBuilder.
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Skill VFX Library", fileName = "SO_SkillVfxLibrary")]
    public sealed class SkillVfxLibrary : ScriptableObject
    {
        public const string ResourcePath = "Echoes/SO_SkillVfxLibrary";

        public List<SkillPresentationSet> sets = new List<SkillPresentationSet>();
        [Tooltip("Luzes de VFX acesas ao mesmo tempo (o FirePool usa as demais; orçamento total ~6).")]
        [Range(0, 4)] public int maxVfxLights = 2;
        [Tooltip("Altura do projétil acima do piso (a mesma do ProjectilePresenter), para a explosão nascer onde o projétil acabou.")]
        public float projectileHeight = 1f;
    }
}
