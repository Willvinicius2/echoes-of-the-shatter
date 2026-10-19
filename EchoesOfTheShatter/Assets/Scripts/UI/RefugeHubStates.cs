using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Visual do Refúgio por estado (hub_state do core): vila fortificada (Exorcizar) ou guarnição (Devorar). Os dois grupos de cenário ficam
    /// prontos e desligados na cena (montados pelo RefugioBuilder com o kit pintado); o StoryDirector liga o do veredito ao abrir o Refúgio.
    /// Sem veredito (ou estado desconhecido), os dois ficam desligados e o Refúgio fica como era.
    /// </summary>
    public sealed class RefugeHubStates : MonoBehaviour
    {
        public const string VillageState = "hub.fortified_village";
        public const string GarrisonState = "hub.fortified_garrison";

        [SerializeField] GameObject village;
        [SerializeField] GameObject garrison;

        /// <summary>Quais grupos ficam ligados para o estado dado (vila, guarnição).</summary>
        public static (bool village, bool garrison) Visible(string hubState) =>
            (hubState == VillageState, hubState == GarrisonState);

        public void Apply(string hubState)
        {
            var (showVillage, showGarrison) = Visible(hubState);
            if (village != null) village.SetActive(showVillage);
            if (garrison != null) garrison.SetActive(showGarrison);
        }
    }
}
