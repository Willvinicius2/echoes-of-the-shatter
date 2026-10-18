using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Usa o Frasco de Recarga (tecla G, remapeavel) no cinto vivo do heroi: o core restaura 1 carga da pocao com menos cargas, gasta 1 frasco do save
    /// e recusa na arena do Guardiao e na expedicao (contexto). O cliente so repassa o contexto e mostra o resultado (docs/16 11.2; docs/09 secao 13).
    /// </summary>
    public sealed class FlaskUser : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;
        [SerializeField] ArenaController arena;
        PlayerInputHandler input;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            if (arena == null) arena = FindAnyObjectByType<ArenaController>();
            input = FindAnyObjectByType<PlayerInputHandler>();
        }

        void Update()
        {
            if (input == null || !input.IsReady || !input.FlaskPressed) return;
            Use();
        }

        /// <summary>Contexto do frasco: a arena em luta bloqueia (o core recusa); fora dela, corrida normal.</summary>
        public FlaskContext CurrentContext => arena != null && arena.Phase == ArenaPhase.Fighting ? FlaskContext.Arena : FlaskContext.Run;

        public FlaskOutcome Use()
        {
            var rules = GameSession.NativeRules(root);
            if (rules == null || hero == null || hero.Logic == null || !GameSession.Save.HasSave) return FlaskOutcome.Failed;
            var outcome = GameSession.Save.Current.UseRefillFlask(rules, hero.Logic.Belt, CurrentContext);
            var loc = root.Localization;
            if (outcome.Ok)
            {
                GameSession.Save.Save(rules);
                ScreenHost.Toast(ScreenKit.Fmt(loc, "ui.vendor.flask_used", ("n", outcome.FlasksLeft.ToString())), ToastKind.Item);
            }
            else ScreenHost.Toast(loc.Get(ErrorKey(outcome.Result)), ToastKind.Error);
            return outcome;
        }

        public static string ErrorKey(FlaskResult result)
        {
            switch (result)
            {
                case FlaskResult.ArenaLocked: return "ui.vendor.err.flask_arena";
                case FlaskResult.IdleForbidden: return "ui.vendor.err.flask_idle";
                case FlaskResult.NoFlask: return "ui.vendor.err.flask_none";
                case FlaskResult.PotionsFull: return "ui.vendor.err.potions_full";
                case FlaskResult.LockedOut: return "ui.vendor.err.locked";
                default: return "ui.vendor.err.not_found";
            }
        }
    }
}
