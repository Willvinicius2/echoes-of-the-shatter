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
        [SerializeField] GameObject village;
        [SerializeField] GameObject garrison;

        public void Apply(string hubState)
        {
            var (showVillage, showGarrison) = HubStateRule.Visible(hubState);
            if (village != null) village.SetActive(showVillage);
            if (garrison != null) garrison.SetActive(showGarrison);
        }
    }
}

namespace Echoes.UI
{
    /// <summary>Regra pura de quais grupos do Refúgio ficam ligados (separada do MonoBehaviour para testar sem a Unity).</summary>
    public static class HubStateRule
    {
        public const string VillageState = "hub.fortified_village";
        public const string GarrisonState = "hub.fortified_garrison";

        public static (bool village, bool garrison) Visible(string hubState) =>
            (hubState == VillageState, hubState == GarrisonState);
    }
}
