using UnityEngine;

namespace Echoes.UI
{
    /// <summary>Ponto de interacao do Refugio (Ilsa ou Tico): o RefugeController mostra a dica e abre a conversa ao apertar F perto.</summary>
    public sealed class InteractableNpc : MonoBehaviour
    {
        public const string Ilsa = "ilsa";
        public const string Tico = "tico";

        public string npcId = Ilsa;
        public float radius = 2.8f;
    }
}
