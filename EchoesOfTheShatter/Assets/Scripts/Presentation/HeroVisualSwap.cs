using Echoes.Core;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Previa visual dos herois: troca o corpo (filho "Body") pelo prefab do heroi escolhido (HeroChoice: -hero ou tela inicial) antes de o
    /// PresentationController achar o Animator. Guerreiro = o que a cena ja tem. Arqueiro e Mago trazem o proprio controller (AC_Archer, AC_Mage) e conjunto.
    /// </summary>
    [DefaultExecutionOrder(-2000)]
    [DisallowMultipleComponent]
    public sealed class HeroVisualSwap : MonoBehaviour
    {
        [SerializeField] GameObject warrior;
        [SerializeField] GameObject archer;
        [SerializeField] GameObject mage;
        [Tooltip("Conjuntos de apresentação do Arqueiro e do Mago (AC_Archer e AC_Mage): o PresentationController da raiz passa a usá-los.")]
        [SerializeField] SkillPresentationSet archerSkillSet;
        [SerializeField] SkillPresentationSet mageSkillSet;

        void Awake()
        {
            var prefab = Pick(HeroChoice.Id);
            if (prefab == null) return;
            var set = HeroChoice.Id == "archer" ? archerSkillSet : mageSkillSet;
            if (set != null && TryGetComponent<PresentationController>(out var presentation)) presentation.UseSkillSet(set);
            var body = transform.Find("Body");
            if (body != null && body.name == prefab.name) return;
            if (body != null) DestroyImmediate(body.gameObject);
            var visual = Instantiate(prefab, transform);
            visual.name = "Body";
            visual.transform.localPosition = Vector3.zero;
            visual.transform.localRotation = Quaternion.identity;
        }

        /// <summary>O prefab do heroi escolhido (Guerreiro por padrao): o boneco do inventario usa o mesmo.</summary>
        public GameObject CurrentPrefab => Pick(HeroChoice.Id) ?? warrior;

        public GameObject Pick(string id)
        {
            switch (id)
            {
                case "archer": return archer;
                case "mage": return mage;
                default: return null; // warrior: ja esta na cena
            }
        }
    }
}
