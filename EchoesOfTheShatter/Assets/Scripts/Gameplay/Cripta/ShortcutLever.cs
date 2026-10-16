using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Alavanca do atalho A (docs/14 seção 5.3): só existe do lado da Sala da Linha de Tiro. O herói chegando perto abre o portão
    /// para sempre; do lado do Átrio o portão fica fechado.
    /// </summary>
    public sealed class ShortcutLever : MonoBehaviour
    {
        [SerializeField] HeroController hero;
        [SerializeField] GateBarrier gate;
        [SerializeField, Min(0.5f)] float radius = 2f;

        public bool Used { get; private set; }

        void Update()
        {
            if (Used || hero == null || gate == null || hero.Combatant == null || hero.Combatant.IsDead) return;
            var d = hero.transform.position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude > radius * radius) return;
            Used = true;
            gate.Open();
        }
    }
}
