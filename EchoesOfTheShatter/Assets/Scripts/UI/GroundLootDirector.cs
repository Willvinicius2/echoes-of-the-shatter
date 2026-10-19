using System.Collections.Generic;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Loot no chao da Cripta (docs/16 4.2 e 4.7). Ao morrer um inimigo, o CORE rola o drop da tabela dele (shatter_save_drop_loot): Ouro e Lascas entram
    /// direto no save e cada item aparece no chao com o feixe da raridade (docs/03 2.3). Pegar e andar por cima (1,2 m) ou usar Interact (ate 3 m):
    /// o core decide o destino (Mochila; Mochila cheia e Unico: Bau; senao o item fica no chao e avisa Mochila cheia). O Unico do Guardiao cai no
    /// chao por shatter_save_ground_add_loot depois de o contador ser gravado (RF-55). O chao nao e salvo: ao sair da Cripta, limpa.
    /// </summary>
    public sealed class GroundLootDirector : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] HeroController hero;
        [SerializeField] LootBeamSettings beam;

        readonly Dictionary<ulong, GroundItemView> views = new Dictionary<ulong, GroundItemView>();
        readonly List<ulong> scratch = new List<ulong>();
        PlayerInputHandler input;
        int raresDropped;
        float nextFullToast;
        bool subscribed;
        ulong seedState;

        public int GroundCount => views.Count;
        public IReadOnlyDictionary<ulong, GroundItemView> Views => views;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (hero == null) hero = FindAnyObjectByType<HeroController>();
            input = FindAnyObjectByType<PlayerInputHandler>();
            if (root != null && root.Events != null)
            {
                root.Events.Subscribe<CombatantDiedEvent>(OnDied);
                root.Events.Subscribe<ChestOpenedEvent>(OnChest);
                root.Events.Subscribe<EncounterClearedEvent>(OnEncounterCleared);
                subscribed = true;
            }
            if (GameSession.Save != null && GameSession.Save.HasSave) GameSession.Save.Current.GroundClear(); // chao vazio ao entrar
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null)
            {
                root.Events.Unsubscribe<CombatantDiedEvent>(OnDied);
                root.Events.Unsubscribe<ChestOpenedEvent>(OnChest);
                root.Events.Unsubscribe<EncounterClearedEvent>(OnEncounterCleared);
            }
            if (GameSession.Save != null && GameSession.Save.HasSave) GameSession.Save.Current.GroundClear(); // saiu da Cripta: o chao some
        }

        ulong NextSeed()
        {
            if (seedState == 0) seedState = (ulong)(GameSession.Save.Clock.NowUtc * 2654435761L) ^ 0xA5A5C3C37E37A1B5UL;
            return seedState;
        }

        void OnDied(in CombatantDiedEvent evt)
        {
            var victim = evt.Target;
            if (victim == null || victim.Team != CombatTeam.Enemy || victim.Enemy == null) return;
            if (victim.ContentId == "enemy.crypt_guardian") return; // o chefe entrega o loot dele pelo RunRecorder
            var rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) return;
            var enemy = victim.Enemy;
            var table = victim.IsElite && !string.IsNullOrEmpty(enemy.EliteLootTableId) ? enemy.EliteLootTableId : enemy.LootTableId;
            if (string.IsNullOrEmpty(table)) return;
            var json = GameSession.Save.Current.DropLoot(rules, table, victim.Level, raresDropped, -1, NextSeed(), out var error);
            if (string.IsNullOrEmpty(json))
            {
                Debug.LogWarning("[Loot] drop falhou: " + error);
                return;
            }
            var origin = new Vector3(victim.Position.X, 0f, victim.Position.Z);
            SpawnViews(ItemInstanceInfo.ListFromJson(json), origin);
        }

        // Nivel de monstro da area (maps.csv, pelo core): o drop de bau e de encontro usa o nivel da area.
        int AreaLevel(Echoes.Interop.Native.NativeRulesCore rules)
        {
            var info = Echoes.Interop.Native.SaveGame.MapInfoOf(rules, ExpeditionConfig.CryptMap);
            return info.MonsterLevel > 0 ? info.MonsterLevel : 1;
        }

        /// <summary>Baú aberto (Interagir): o core rola a tabela do baú, marca o baú como aberto no estado do mundo e o save é gravado; os itens caem no chão.</summary>
        void OnChest(in ChestOpenedEvent evt)
        {
            var rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) return;
            var json = GameSession.Save.Current.OpenChest(rules, ExpeditionConfig.CryptMap, evt.ChestId, AreaLevel(rules), raresDropped, -1, NextSeed(), out var result, out var error);
            if (result == ChestOpenResult.Error) Debug.LogWarning("[Loot] bau " + evt.ChestId + ": " + error);
            GameSession.Save.Save(rules); // o bau aberto (estado do mundo) e o Ouro e as Lascas vao para o disco
            if (result != ChestOpenResult.Opened || string.IsNullOrEmpty(json)) return;
            SpawnViews(ItemInstanceInfo.ListFromJson(json), evt.Position + Vector3.up * 0f);
        }

        /// <summary>Encontro limpo: o core rola a tabela da área (Ouro, Lascas e itens baixos), uma vez por encontro na visita.</summary>
        void OnEncounterCleared(in EncounterClearedEvent evt)
        {
            var rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) return;
            var json = GameSession.Save.Current.EncounterClearLoot(rules, ExpeditionConfig.CryptMap, AreaLevel(rules), raresDropped, -1, NextSeed(), out var error);
            if (string.IsNullOrEmpty(json))
            {
                if (!string.IsNullOrEmpty(error)) Debug.LogWarning("[Loot] loot do encontro " + evt.EncounterId + ": " + error);
                return;
            }
            SpawnViews(ItemInstanceInfo.ListFromJson(json), evt.Position);
            DropStainLoot(rules, evt.Position);
        }

        /// <summary>Mancha (veredito Devorar): o encontro limpo rola também a tabela extra da área, nomeada pelo core (<c>stain_loot_table_by_map</c>).</summary>
        void DropStainLoot(Echoes.Interop.Native.NativeRulesCore rules, Vector3 origin)
        {
            // O StoryDirector da cena ja tem a tabela aberta; sem ele (cena de teste), le direto do core.
            var director = StoryDirector.Current;
            var state = director != null && director.IsLoaded ? director.CurrentState() : Echoes.Gameplay.DevouredKit.ReadState(root, rules, GameSession.Save.Current);
            if (state == null || !state.StainLootTableByMap.TryGetValue(ExpeditionConfig.CryptMap, out var table) || string.IsNullOrEmpty(table)) return;
            var json = GameSession.Save.Current.DropLoot(rules, table, AreaLevel(rules), raresDropped, -1, NextSeed(), out var error);
            if (string.IsNullOrEmpty(json))
            {
                if (!string.IsNullOrEmpty(error)) Debug.LogWarning("[Loot] loot da Mancha: " + error);
                return;
            }
            SpawnViews(ItemInstanceInfo.ListFromJson(json), origin);
        }

        /// <summary>Loot do Guardiao (JSON do core, com o Unico): grave o save ANTES (RF-55); aqui o item cai no chao.</summary>
        public bool DropBossLoot(string lootJson, Vector3 origin)
        {
            if (!GameSession.Save.HasSave) return false;
            if (!GameSession.Save.Current.GroundAddLoot(lootJson, out var error))
            {
                Debug.LogError("[Loot] ground_add_loot falhou: " + error);
                return false;
            }
            SpawnViews(ItemInstanceInfo.ListFromJson(lootJson), origin);
            return true;
        }

        /// <summary>Teste: poe no chao o loot de uma tabela como se um inimigo tivesse morrido em <paramref name="origin"/>.</summary>
        public int DropTable(string table, int level, Vector3 origin)
        {
            var rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) return 0;
            var json = GameSession.Save.Current.DropLoot(rules, table, level, raresDropped, -1, NextSeed(), out var error);
            if (string.IsNullOrEmpty(json)) { Debug.LogWarning("[Loot] drop falhou: " + error); return 0; }
            var items = ItemInstanceInfo.ListFromJson(json);
            SpawnViews(items, origin);
            return items.Count;
        }

        void SpawnViews(List<ItemInstanceInfo> items, Vector3 origin)
        {
            var rules = GameSession.NativeRules(root);
            for (var i = 0; i < items.Count; i++)
            {
                var item = items[i];
                if (item.Rarity == ItemRarity.Rare || item.Rarity == ItemRarity.Unique) raresDropped++;
                var angle = (i * 137.5f + item.Uid % 90UL) * Mathf.Deg2Rad;
                var offset = new Vector3(Mathf.Cos(angle), 0f, Mathf.Sin(angle)) * (0.9f + 0.35f * i);
                var go = new GameObject("GroundItem_" + item.Uid);
                go.transform.position = origin + offset;
                var view = go.AddComponent<GroundItemView>();
                view.Setup(item.Uid, (int)item.Rarity, ItemText.Name(root.Localization, rules, item), beam);
                views[item.Uid] = view;
            }
        }

        void Update()
        {
            if (views.Count == 0 || hero == null || !GameSession.Save.HasSave) return;
            if (RefugeController.AnyScreenOpen || InventoryController.IsOpen) return;
            var interact = input != null && input.IsReady && input.InteractPressed;
            var p = hero.transform.position;
            scratch.Clear();
            foreach (var pair in views)
            {
                var d = pair.Value.transform.position - p;
                d.y = 0f;
                var distance = d.magnitude;
                if (distance <= beam.pickupRadiusMeters || (interact && distance <= beam.interactRadiusMeters)) scratch.Add(pair.Key);
            }
            for (var i = 0; i < scratch.Count; i++) TryPickup(scratch[i]);
        }

        void TryPickup(ulong uid)
        {
            var rules = GameSession.NativeRules(root);
            var save = GameSession.Save.Current;
            var item = FindOnGround(save, uid);
            var dest = save.Pickup(rules, 0, uid);
            switch (dest)
            {
                case PickupDest.Backpack:
                    Remove(uid);
                    ScreenHost.Toast(ScreenKit.Fmt(root.Localization, "ui.item.picked", ("item", NameOf(rules, item, uid))), ToastKind.Item);
                    break;
                case PickupDest.Stash:
                    Remove(uid);
                    ScreenHost.Toast(ScreenKit.Fmt(root.Localization, "ui.item.pick_stash", ("item", NameOf(rules, item, uid))), ToastKind.Item);
                    break;
                case PickupDest.Full:
                    if (Time.unscaledTime >= nextFullToast)
                    {
                        nextFullToast = Time.unscaledTime + 2.5f;
                        ScreenHost.Toast(root.Localization.Get("ui.item.pick_full"), ToastKind.Error);
                    }
                    break;
                default:
                    Remove(uid);
                    break;
            }
            if (dest == PickupDest.Backpack || dest == PickupDest.Stash) GameSession.Save.Save(rules);
        }

        static ItemInstanceInfo FindOnGround(SaveGame save, ulong uid)
        {
            foreach (var item in save.GroundItems()) if (item.Uid == uid) return item;
            return null;
        }

        string NameOf(NativeRulesCore rules, ItemInstanceInfo item, ulong uid) => item != null ? ItemText.Name(root.Localization, rules, item) : uid.ToString();

        void Remove(ulong uid)
        {
            if (views.TryGetValue(uid, out var view))
            {
                if (view != null) Destroy(view.gameObject);
                views.Remove(uid);
            }
        }
    }
}
