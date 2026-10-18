using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Salvamentos da Cripta (docs/16, F-07 e F-08): ao passar num checkpoint, ao abrir a parede secreta ou o atalho e logo depois de morrer (o heroi volta ao checkpoint). A regra de
    /// encher pocoes e do core (CheckpointZone / Revive); aqui so se grava. Em testes sem save carregado nao faz nada.
    /// </summary>
    public sealed class CriptaSaveHooks : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;
        bool subscribed;

        /// <summary>Quantos salvamentos esta classe pediu (testes).</summary>
        public int SaveCount { get; private set; }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            if (root != null && root.Events != null)
            {
                root.Events.Subscribe<CheckpointReachedEvent>(OnCheckpoint);
                root.Events.Subscribe<SecretOpenedEvent>(OnSecret);
                root.Events.Subscribe<ShortcutOpenedEvent>(OnShortcut);
                subscribed = true;
            }
            if (hero != null) hero.Respawned += OnRespawned;
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null)
            {
                root.Events.Unsubscribe<CheckpointReachedEvent>(OnCheckpoint);
                root.Events.Unsubscribe<SecretOpenedEvent>(OnSecret);
                root.Events.Unsubscribe<ShortcutOpenedEvent>(OnShortcut);
            }
            if (hero != null) hero.Respawned -= OnRespawned;
        }

        void OnCheckpoint(in CheckpointReachedEvent evt) => SaveNow();

        void OnRespawned() => SaveNow();

        // Parede secreta e atalho abertos: o estado do mundo ja esta no save em memoria (SetWorldObjectOpen); aqui vai para o disco.
        void OnSecret(in SecretOpenedEvent evt) => SaveNow();

        void OnShortcut(in ShortcutOpenedEvent evt) => SaveNow();

        void SaveNow()
        {
            var rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) return;
            if (GameSession.Save.Save(rules)) SaveCount++;
        }
    }
}
