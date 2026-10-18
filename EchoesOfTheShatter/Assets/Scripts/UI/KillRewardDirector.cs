using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// XP por morte no jogo manual (docs/09 seção 14, RF-25): a morte de cada inimigo vira uma chamada ao core (shatter_xp_award_kill) com o elite
    /// sorteado do encontro e o Fervor da corrida; o core soma o XP no save e sobe de nível até o teto da área. O cliente só repassa o que
    /// aconteceu e mostra o resultado (aviso de nível; a HUD lê nível e XP do save). Sem save (cena aberta direto) não faz nada.
    /// </summary>
    public sealed class KillRewardDirector : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;
        bool subscribed;

        /// <summary>Mortes que renderam XP e o XP total concedido nesta visita (testes e telas).</summary>
        public int Kills { get; private set; }
        public double TotalAwarded { get; private set; }
        public XpInfo LastAward { get; private set; }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            if (root == null || root.Events == null) return;
            root.Events.Subscribe<CombatantDiedEvent>(OnDied);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<CombatantDiedEvent>(OnDied);
        }

        void OnDied(in CombatantDiedEvent evt)
        {
            var victim = evt.Target;
            if (victim == null || victim.Team != CombatTeam.Enemy || victim.Enemy == null) return;
            var rules = GameSession.NativeRules(root);
            if (rules == null || GameSession.Save == null || !GameSession.Save.HasSave) return;
            var save = GameSession.Save.Current;
            var award = save.AwardKillXp(rules, 0, ExpeditionConfig.CryptMap, victim.ContentId, victim.Level, victim.Elite.Rolled, victim.Elite.ModifierId, RunState.FervorActive, out var ok);
            if (!ok)
            {
                Debug.LogWarning("[XP] O core recusou o XP de " + victim.ContentId);
                return;
            }
            Kills++;
            TotalAwarded += award.Awarded;
            LastAward = award;
            if (!award.LeveledUp) return;
            ScreenHost.Toast(root.Localization.Get("ui.hud.level_up") + " " + ScreenKit.Fmt(root.Localization, "ui.common.level", ("level", award.Level.ToString())), ToastKind.Banner);
            if (hero != null) hero.RefreshFromSave(); // atributos e habilidades do novo nivel valem na hora (o core recalcula o bloco)
            GameSession.Save.Save(rules); // nivel novo gravado na hora
        }
    }
}
