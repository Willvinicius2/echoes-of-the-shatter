using Echoes.Core;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Alavanca do atalho A (docs/14 seção 5.3): só existe do lado da Sala da Linha de Tiro. O herói usa a ação Interagir perto dela e o portão
    /// abre para sempre: o estado vai para o save pelo ID do portão (shortcut.crypt.a) e o atalho continua aberto depois de checkpoint, de sair
    /// e voltar. Do lado do Átrio o portão fica fechado.
    /// </summary>
    public sealed class ShortcutLever : MonoBehaviour, IInteractable
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] HeroController hero;
        [SerializeField] GateBarrier gate;
        [SerializeField] string shortcutId;
        [SerializeField, Min(0.5f)] float radius = 2f;

        bool restored;

        public bool Used { get; private set; }
        public string ShortcutId => shortcutId;

        public bool CanInteract => !Used && hero != null && gate != null && hero.Combatant != null && !hero.Combatant.IsDead;
        public string PromptKey => "ui.interact.pull_lever";
        public Vector3 Position => transform.position;
        public float Reach => radius;

        void Update()
        {
            if (restored) return;
            restored = true;
            var save = GameSession.Save;
            if (save != null && save.HasSave && !string.IsNullOrEmpty(shortcutId) && save.Current.IsWorldObjectOpen(ExpeditionConfig.CryptMap, shortcutId))
            {
                Used = true;
                gate?.Open();
            }
        }

        public void Interact()
        {
            if (!CanInteract) return;
            var d = hero.transform.position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude > radius * radius) return;
            Used = true;
            gate.Open();
            var save = GameSession.Save;
            if (save != null && save.HasSave && !string.IsNullOrEmpty(shortcutId)) save.Current.SetWorldObjectOpen(ExpeditionConfig.CryptMap, shortcutId, true);
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            var evt = new ShortcutOpenedEvent { ShortcutId = shortcutId };
            combatHost?.Events?.Publish(in evt);
        }
    }
}
