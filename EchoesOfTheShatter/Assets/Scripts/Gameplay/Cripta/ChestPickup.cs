using Echoes.Core;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Baú da Cripta (docs/14 5.2): abre com a ação Interagir quando o herói está perto. Quem rola o loot é o core (a UI escuta
    /// <see cref="ChestOpenedEvent"/> e chama OpenChest, que também marca o baú como aberto no estado do mundo do save). Baú já aberto no save
    /// aparece aberto e não abre de novo (nem depois de checkpoint ou de sair e voltar).
    /// </summary>
    public sealed class ChestPickup : MonoBehaviour, IInteractable
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] HeroController hero;
        [SerializeField] string chestId;
        [SerializeField] string lootTableId;
        [SerializeField, Min(0.5f)] float radius = 1.8f;
        [Tooltip("Visual do baú fechado e do aberto (alterna ao abrir).")]
        [SerializeField] GameObject closedVisual;
        [SerializeField] GameObject openedVisual;

        public bool IsOpen { get; private set; }
        public string ChestId => chestId;
        public string LootTableId => lootTableId;

        public bool CanInteract => !IsOpen && hero != null && hero.Combatant != null && !hero.Combatant.IsDead;
        public string PromptKey => "ui.interact.open_chest";
        public Vector3 Position => transform.position;
        public float Reach => radius;

        void Start()
        {
            IsOpen = OpenInSave();
            Show(IsOpen);
        }

        // Estado do mundo no save (o core guarda por ID de objeto): sem save (cena aberta direto) o baú começa fechado.
        bool OpenInSave()
        {
            var save = GameSession.Save;
            return save != null && save.HasSave && !string.IsNullOrEmpty(chestId) && save.Current.IsWorldObjectOpen(ExpeditionConfig.CryptMap, chestId);
        }

        public void Interact()
        {
            if (!CanInteract) return;
            var d = hero.transform.position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude > radius * radius) return;
            IsOpen = true;
            Show(true);
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            var evt = new ChestOpenedEvent { ChestId = chestId, LootTableId = lootTableId, Position = transform.position };
            combatHost?.Events?.Publish(in evt);
        }

        void Show(bool opened)
        {
            if (closedVisual != null) closedVisual.SetActive(!opened);
            if (openedVisual != null) openedVisual.SetActive(opened);
        }
    }
}
