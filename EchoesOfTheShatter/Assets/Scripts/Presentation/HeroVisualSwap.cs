using Echoes.Core;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Previa visual dos herois: troca o corpo (filho "Body") pelo prefab do heroi escolhido (HeroChoice: -hero ou tela inicial) antes de o
    /// PresentationController achar o Animator. Guerreiro = o que a cena ja tem. Arqueiro e Mago usam o kit de teste do Guerreiro.
    /// </summary>
    [DefaultExecutionOrder(-2000)]
    [DisallowMultipleComponent]
    public sealed class HeroVisualSwap : MonoBehaviour
    {
        [SerializeField] GameObject warrior;
        [SerializeField] GameObject archer;
        [SerializeField] GameObject mage;

        void Awake()
        {
            var prefab = Pick(HeroChoice.Id);
            if (prefab == null) return;
            var body = transform.Find("Body");
            if (body != null && body.name == prefab.name) return;
            if (body != null) DestroyImmediate(body.gameObject);
            var visual = Instantiate(prefab, transform);
            visual.name = "Body";
            visual.transform.localPosition = Vector3.zero;
            visual.transform.localRotation = Quaternion.identity;
        }

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
