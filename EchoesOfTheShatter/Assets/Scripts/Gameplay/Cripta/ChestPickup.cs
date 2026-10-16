using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>Baú da Cripta: abre uma vez quando o herói chega perto e publica <see cref="ChestOpenedEvent"/> com a tabela de loot.</summary>
    public sealed class ChestPickup : MonoBehaviour
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

        void Start()
        {
            Show(false);
        }

        void Update()
        {
            if (IsOpen || hero == null || hero.Combatant == null || hero.Combatant.IsDead) return;
            var d = hero.transform.position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude > radius * radius) return;
            IsOpen = true;
            Show(true);
            var evt = new ChestOpenedEvent { ChestId = chestId, LootTableId = lootTableId };
            combatHost?.Events?.Publish(in evt);
        }

        void Show(bool opened)
        {
            if (closedVisual != null) closedVisual.SetActive(!opened);
            if (openedVisual != null) openedVisual.SetActive(opened);
        }
    }
}
