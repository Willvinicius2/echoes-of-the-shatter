using System;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Na Cripta: vencer o Guardiao grava o dominio da area e as cargas (RecordAreaRun, RF-35 e RF-50) e salva antes de qualquer outra coisa (RF-55).
    /// Sem save carregado (cena aberta direto no editor) nao faz nada.
    /// </summary>
    public sealed class RunRecorder : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        bool subscribed;
        bool recorded;

        /// <summary>O ultimo loot do Guardiao (JSON do core) e o resultado da conquista (testes e telas).</summary>
        public static string LastLootJson { get; private set; }
        public static AreaRunReward LastReward { get; private set; }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (root == null || root.Events == null) return;
            root.Events.Subscribe<ArenaStateEvent>(OnArena);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<ArenaStateEvent>(OnArena);
        }

        void OnArena(in ArenaStateEvent evt)
        {
            if (evt.Phase != ArenaPhase.Won || recorded) return;
            var rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) return;
            recorded = true;
            ScreenHost.Toast(root.Localization.Get("ui.boss.defeated") + " - " + root.Localization.Get("ui.boss.marker_installed"), ToastKind.Banner);
            var save = GameSession.Save;
            var reward = save.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, true, true);
            save.Save(rules); // RF-55: dominio e contador gravados ANTES de entregar o item
            // Loot do Guardiao pelo core (1a vitoria: Unico garantido; depois 20%, garantido na 5a sem Unico). O contador avanca no save.
            var seed = (ulong)(save.Clock.NowUtc * 2654435761L) ^ 0x9E3779B97F4A7C15UL;
            var json = save.Current.RollBossLoot(rules, 0, "enemy.crypt_guardian", 3, seed, out var error);
            if (string.IsNullOrEmpty(json))
            {
                Debug.LogError("[Boss] Loot do Guardiao falhou: " + error);
            }
            else
            {
                save.Save(rules); // o contador do chefe ja esta no disco antes do item entrar
                // TODO(inventario): sem inventario o item vai para o Bau compartilhado (stash do save); falta o item cair no chao com feixe e a Mochila.
                if (!save.Current.AddLoot(json, out error)) Debug.LogError("[Boss] AddLoot falhou: " + error);
                save.Save(rules);
                LastLootJson = json;
                if (json.Contains("\"rarity\":\"unique\"")) ScreenHost.Toast(root.Localization.Get("ui.item.picked").Replace("{item}", "Unico") + " (Bau)", ToastKind.Item);
            }
            LastReward = reward;
            if (reward.ChargesGained > 0) ScreenHost.Toast("+" + reward.ChargesGained + " " + root.Localization.Get("ui.hud.charges"), ToastKind.Charges);
        }
    }
}
