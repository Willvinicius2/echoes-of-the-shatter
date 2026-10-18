using UnityEngine;

namespace Echoes.UI
{
    /// <summary>Ponto de interacao do Refugio (Ilsa, Tico, Vendedor, Encantador ou o Bau compartilhado; S-04): o RefugeController mostra a dica e abre a conversa ao apertar F perto.</summary>
    public sealed class InteractableNpc : MonoBehaviour
    {
        public const string Ilsa = "ilsa";
        public const string Tico = "tico";
        public const string Vendor = "vendor";
        public const string Enchanter = "enchanter";
        public const string Stash = "stash";

        public string npcId = Ilsa;
        public float radius = 2.8f;
    }
}
