using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using Echoes.Presentation;
using Echoes.UI;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// Loot e inventario no Play: matar inimigos da Cripta rola o drop pelo core, o item cai no chao e andar por cima pega, abrir o inventario (com o
    /// boneco), equipar muda o equipamento, o visual do boneco e o bloco de atributos do heroi, desequipar deixa a posicao nua, e o save grava tudo.
    /// </summary>
    [Category("Inventario")]
    public sealed class InventoryPlayTests
    {
        const long T0 = 1_800_000_000;
        string dir;

        [SetUp]
        public void SetUp()
        {
            dir = Path.Combine(Path.GetTempPath(), "echoes_invplay_" + System.Guid.NewGuid().ToString("N"));
            GameSession.Use(new SaveService(dir, new FakeGameClock(T0)));
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                Assert.AreEqual(RulesStatus.Ok, rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new List<RulesError>()));
                Assert.IsTrue(GameSession.Save.NewGame(rules, 0, "Playtest"));
            }
        }

        [TearDown]
        public void TearDown()
        {
            GameSession.Reset();
            Time.timeScale = 1f;
            TestSettings.HeroGodMode = false;
            if (Directory.Exists(dir)) Directory.Delete(dir, true);
        }

        [UnityTest]
        public IEnumerator KillDropPickupEquipChangesTheVisualAndSavesEverything()
        {
            yield return SceneManager.LoadSceneAsync("Cripta", LoadSceneMode.Single);
            yield return null;
            yield return null;

            var root = Object.FindFirstObjectByType<GameRoot>();
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var director = Object.FindFirstObjectByType<GroundLootDirector>();
            var inventory = Object.FindFirstObjectByType<InventoryController>();
            var rules = GameSession.NativeRules(root);
            Assert.IsNotNull(director);
            Assert.IsNotNull(inventory);
            Assert.IsNotNull(rules);
            TestSettings.HeroGodMode = true;
            // O XP por morte subiria o nivel do save no meio do teste e o bloco de atributos do heroi (montado no nivel da entrada) deixaria de bater com a
            // comparacao do core: aqui o assunto e o inventario, entao o diretor de XP fica de fora.
            var xpDirector = Object.FindFirstObjectByType<KillRewardDirector>();
            if (xpDirector != null) Object.DestroyImmediate(xpDirector); // imediato: as mortes do teste acontecem neste mesmo quadro
            var save = GameSession.Save.Current;
            Assert.IsNotNull(hero.Combatant.Weapon, "arma do heroi vinda do save (espada de ferro)");

            // Matar: o core rola o drop de cada inimigo; Ouro e Lascas entram no save, itens ficam no chao.
            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            var enemies = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Where(e => e.EnemyId != "enemy.crypt_guardian").ToList();
            var killed = 0;
            foreach (var enemy in enemies)
            {
                for (var i = 0; i < 300 && !enemy.Combatant.IsDead; i++) host.Combat.ApplySkillHit(hero.Combatant, enemy.Combatant, skill, hero.Combatant.Position);
                if (enemy.Combatant.IsDead) killed++;
            }
            Assert.Greater(killed, 10, "inimigos mortos");
            yield return null;
            var json = save.ToJson();
            var droppedSomething = director.GroundCount > 0 || save.Inventory(rules, 0).BackpackUsed > 0 || json.Contains("\"amount\":");
            Assert.IsTrue(droppedSomething, "a morte rolou drop pelo core (item no chao ou Ouro/Lascas no save)");

            // Item garantido para o resto do teste: a tabela do Guardiao (Magico/Raro) cai no chao junto do heroi.
            var armorUid = 0UL;
            for (var attempt = 0; attempt < 60 && armorUid == 0UL; attempt++)
            {
                director.DropTable("loot.crypt.guardian", 3, hero.transform.position + new Vector3(0f, 0f, 6f));
                foreach (var g in save.GroundItems())
                {
                    var info = rules.FindItemBase(g.BaseId);
                    if (info != null && info.Slot == "head" && g.Rarity != ItemRarity.Normal) armorUid = g.Uid;
                }
            }
            Assert.AreNotEqual(0UL, armorUid, "um elmo Magico ou melhor caiu");
            Assert.IsTrue(director.Views.TryGetValue(armorUid, out var view), "o item aparece no chao (marcador, feixe e rotulo)");
            Assert.IsNotNull(view.GetComponentInChildren<TextMesh>(), "rotulo de Magico ou melhor");

            // Andar por cima pega (1,2 m): o core manda para a Mochila.
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(view.transform.position.x, 0f, view.transform.position.z);
            controller.enabled = true;
            yield return null;
            yield return null;
            Assert.IsFalse(director.Views.ContainsKey(armorUid), "pegou ao andar por cima");
            Assert.IsTrue(save.ListItems(0, ItemContainer.Backpack).Any(i => i.Uid == armorUid), "na Mochila");
            Assert.IsFalse(save.GroundItems().Any(i => i.Uid == armorUid), "fora do chao");

            // Inventario: abre com o boneco, seleciona e equipa.
            var lifeBefore = hero.Combatant.Stats.Get(StatId.Life);
            var armorBefore = hero.Combatant.Stats.Get(StatId.Armor);
            inventory.Show();
            Assert.IsTrue(InventoryController.IsOpen);
            Assert.AreEqual(0f, Time.timeScale, "pausa enquanto aberto");
            yield return new WaitForSecondsRealtime(0.3f);
            Assert.IsNotNull(inventory.Doll, "boneco modular");
            Assert.IsTrue(inventory.Doll.HasModularParts);
            Assert.IsTrue(inventory.SelectUid(armorUid));
            var compare = save.Compare(rules, 0, armorUid);
            Assert.IsTrue(inventory.EquipSelected());
            Assert.AreEqual(armorUid, save.Equipment(0)[ItemSlots.IndexOf("head")].Uid, "equipado");

            // atributos do heroi so mudam pelo que o core comparou; o visual vem do conjunto do core
            foreach (var delta in compare.Deltas)
            {
                if (delta.Stat == "life") Assert.AreEqual(delta.Change, hero.Combatant.Stats.Get(StatId.Life) - lifeBefore, 1e-6);
                if (delta.Stat == "armor") Assert.AreEqual(delta.Change, hero.Combatant.Stats.Get(StatId.Armor) - armorBefore, 1e-6);
            }
            var modular = hero.GetComponentInChildren<ModularCharacter>();
            var equippedItem = save.Equipment(0)[ItemSlots.IndexOf("head")];
            Assert.IsTrue(modular.IsEquipped(HeroPartSlot.Head));
            Assert.AreEqual(rules.ItemVisualSetId(equippedItem.BaseId, equippedItem.UniqueId), modular.Equipped(HeroPartSlot.Head).visualSetId, "conjunto visual pelo core");

            // Desequipar: a posicao fica nua no heroi e no boneco.
            inventory.SelectItem(equippedItem, "slot:" + ItemSlots.IndexOf("head"));
            Assert.IsTrue(inventory.UnequipSelected());
            Assert.IsNull(save.Equipment(0)[ItemSlots.IndexOf("head")]);
            Assert.IsFalse(modular.IsEquipped(HeroPartSlot.Head), "elmo fora: corpo base nu");
            yield return null;
            var dollModular = inventory.Doll.Doll.GetComponentInChildren<ModularCharacter>();
            Assert.IsFalse(dollModular.IsEquipped(HeroPartSlot.Head), "o boneco acompanha");

            // Volta a equipar e fecha: salvou no disco.
            Assert.IsTrue(inventory.SelectUid(armorUid));
            Assert.IsTrue(inventory.EquipSelected());
            inventory.Close();
            Assert.IsFalse(InventoryController.IsOpen);
            Assert.AreEqual(1f, Time.timeScale);
            Assert.Greater(Directory.GetFiles(dir, "slot_1*").Length, 0, "save gravado");
            GameSession.Save.Close();
            Assert.AreEqual(LoadOutcome.Ok, GameSession.Save.Load(rules, 0));
            Assert.AreEqual(armorUid, GameSession.Save.Current.Equipment(0)[ItemSlots.IndexOf("head")].Uid, "equipamento mantido ao carregar");
        }

        [UnityTest]
        public IEnumerator GroundIsClearedWhenLeavingTheCrypt()
        {
            yield return SceneManager.LoadSceneAsync("Cripta", LoadSceneMode.Single);
            yield return null;
            var root = Object.FindFirstObjectByType<GameRoot>();
            var director = Object.FindFirstObjectByType<GroundLootDirector>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var save = GameSession.Save.Current;
            Assert.Greater(director.DropTable("loot.crypt.guardian", 3, hero.transform.position + new Vector3(10f, 0f, 10f)), 0);
            Assert.IsNotEmpty(save.GroundItems());
            yield return SceneManager.LoadSceneAsync("Refugio", LoadSceneMode.Single);
            yield return null;
            Assert.IsEmpty(save.GroundItems(), "o chao nao atravessa a troca de cena");
        }
    }
}
