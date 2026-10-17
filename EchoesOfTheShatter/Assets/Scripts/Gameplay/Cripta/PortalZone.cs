using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Portal da Cripta (entrada, saída após o Guardião). A área de destino (Refúgio do Marco) ainda não existe: o portal devolve o herói
    /// ao checkpoint, como a morte (vida e poções cheias, inimigos mortos reaparecem). TODO(area.refuge): trocar pela troca de cena.
    /// </summary>
    public sealed class PortalZone : MonoBehaviour
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] HeroController hero;
        [SerializeField] string portalId;
        [SerializeField] string targetArea = "area.refuge";
        [SerializeField, Min(0.5f)] float radius = 2f;
        [SerializeField] bool active = true;
        [Tooltip("true = o portal so avisa (PortalUsedEvent) e o AreaTravel troca a cena; false = devolve ao checkpoint (comportamento antigo).")]
        [SerializeField] bool travels;

        bool heroInside;
        bool primed;

        public bool IsActive => active;
        public string PortalId => portalId;
        public bool Travels { get => travels; set => travels = value; }
        public string TargetArea { get => targetArea; set => targetArea = value; }

        public void SetActive(bool value)
        {
            active = value;
            gameObject.SetActive(value);
        }

        void Update()
        {
            if (!active || hero == null || hero.Combatant == null || hero.Combatant.IsDead) return;
            var d = hero.transform.position - transform.position;
            d.y = 0f;
            var inside = d.sqrMagnitude <= radius * radius;
            if (!primed)
            {
                // O heroi pode nascer dentro do portal (entrada da Cripta): so conta quem entra depois.
                primed = true;
                heroInside = inside;
                return;
            }
            if (inside && !heroInside)
            {
                var evt = new PortalUsedEvent { PortalId = portalId, TargetArea = targetArea };
                combatHost?.Events?.Publish(in evt);
                if (!travels) hero.ReturnToCheckpoint();
            }
            heroInside = inside;
        }
    }
}
