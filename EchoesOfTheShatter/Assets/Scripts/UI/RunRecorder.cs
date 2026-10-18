using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Na Cripta: vencer o Guardiao grava o dominio da area e as cargas (RecordAreaRun, RF-35 e RF-50) e salva antes de qualquer outra coisa (RF-55).
    /// "Chegou ao fim" vem da arena (o heroi cruzou o gatilho nesta corrida), nao de um valor fixo; a seed do loot e a da corrida (GameRoot.RunSeed,
    /// reproduzivel com fixedRunSeed), nao o relogio. A vitoria ganha a faixa S-13. Sem save carregado (cena aberta direto no editor) nao faz nada.
    /// </summary>
    public sealed class RunRecorder : MonoBehaviour
    {
        /// <summary>Segundos da faixa de vitoria (S-13: banner por 3 s).</summary>
        public const float VictoryBannerSeconds = 3f;

        [SerializeField] GameRoot root;
        [SerializeField] ArenaController arena;
        bool subscribed;
        bool recorded;

        /// <summary>O ultimo loot do Guardiao (JSON do core) e o resultado da conquista (testes e telas).</summary>
        public static string LastLootJson { get; private set; }
        public static AreaRunReward LastReward { get; private set; }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (arena == null) arena = FindAnyObjectByType<ArenaController>();
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
            var loc = root.Localization;
            ScreenHost.Banner(loc.Get("ui.boss.defeated"), loc.Get("ui.boss.marker_installed"), VictoryBannerSeconds);
            var save = GameSession.Save;
            // RF-50: o dominio exige ter chegado a arena E vencido o chefe na mesma corrida; sem arena na cena (teste) so o chefe vencido conta.
            var reachedEnd = arena == null || arena.EverTriggered;
            var reward = save.Current.RecordAreaRun(rules, 0, ExpeditionConfig.CryptMap, reachedEnd, true);
            save.Save(rules); // RF-55: dominio e contador gravados ANTES de entregar o item
            // Loot do Guardiao pelo core (1a vitoria: Unico garantido; depois 20%, garantido na 5a sem Unico). O contador avanca no save.
            var json = save.Current.RollBossLoot(rules, 0, "enemy.crypt_guardian", 3, root.RunSeed, out var error);
            if (string.IsNullOrEmpty(json))
            {
                Debug.LogError("[Boss] Loot do Guardiao falhou: " + error);
            }
            else
            {
                save.Save(rules); // o contador do chefe ja esta no disco antes do item entrar
                // O Unico cai NO CHAO (feixe de raridade) pelo core; pegar manda para a Mochila (ou o Bau se estiver cheia). O chao nao e salvo:
                // o contador do chefe ja esta gravado acima (RF-55). Sem diretor de loot na cena (teste), vai direto para o Bau.
                var director = FindAnyObjectByType<GroundLootDirector>();
                var bossObject = arena != null ? arena.Boss : null;
                var where = bossObject != null ? bossObject.transform.position : Vector3.zero;
                where.y = 0f;
                if (director == null || !director.DropBossLoot(json, where))
                {
                    if (!save.Current.AddLoot(json, out error)) Debug.LogError("[Boss] AddLoot falhou: " + error);
                    save.Save(rules);
                    var unique = FindUnique(ItemInstanceInfo.ListFromJson(json));
                    if (unique != null) ScreenHost.Toast(ScreenKit.Fmt(loc, "ui.item.pick_stash", ("item", ItemText.Name(loc, rules, unique))), ToastKind.Item);
                }
                LastLootJson = json;
            }
            LastReward = reward;
            if (reward.ChargesGained > 0) ScreenHost.Toast("+" + reward.ChargesGained + " " + loc.Get("ui.hud.charges"), ToastKind.Charges);
        }

        static ItemInstanceInfo FindUnique(List<ItemInstanceInfo> items)
        {
            foreach (var item in items) if (item.IsUnique) return item;
            return null;
        }
    }
}
