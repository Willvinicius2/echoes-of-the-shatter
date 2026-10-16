using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Echoes.Core;
using Echoes.Gameplay;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// Smoke de Play em batch da Cripta: a cena sobe sem erro, o combate roda no passo fixo, inimigos mortos reaparecem ao voltar ao
    /// checkpoint e a porta da arena fecha atras do heroi e reabre quando a luta recomeca (decisoes do dono).
    /// </summary>
    [Category("Cripta")]
    public sealed class CriptaSmokeTests
    {
        const string ScenePath = "Assets/Scenes/Cripta/Cripta.unity";

        [UnityTest]
        public IEnumerator CriptaLoadsRunsRespawnsEnemiesAndClosesTheArenaDoor()
        {
            // A cena esta nos Build Settings (o CriptaBuilder a adiciona): carrega pelo caminho.
            yield return SceneManager.LoadSceneAsync(ScenePath, LoadSceneMode.Single);
            yield return null;
            yield return null;

            var root = Object.FindFirstObjectByType<GameRoot>();
            Assert.IsNotNull(root);
            Assert.IsTrue(root.IsReady, "as regras carregaram");
            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var director = Object.FindFirstObjectByType<EncounterDirector>();
            var arena = Object.FindFirstObjectByType<ArenaController>();
            Assert.IsNotNull(host.Combat);
            Assert.IsNotNull(hero.Combatant);

            // Alguns segundos de jogo: o passo fixo anda e ninguem quebra.
            var start = host.Combat.StepCount;
            yield return new WaitForSeconds(3f);
            Assert.Greater(host.Combat.StepCount, start + 30, "o combate roda no passo fixo");
            Assert.IsFalse(hero.Combatant.IsDead);

            // Inimigo morto reaparece ao voltar ao checkpoint.
            var sentinel = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).First(e => e.EnemyId == "enemy.hollow_sentinel");
            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            for (var i = 0; i < 200 && !sentinel.Combatant.IsDead; i++)
                host.Combat.ApplySkillHit(hero.Combatant, sentinel.Combatant, skill, hero.Combatant.Position);
            Assert.IsTrue(sentinel.Combatant.IsDead, "morreu");
            hero.ReturnToCheckpoint();
            yield return null;
            yield return null;
            Assert.IsTrue(sentinel.gameObject.activeSelf, "reapareceu");
            Assert.IsFalse(sentinel.Combatant.IsDead, "com vida cheia");

            // Arena: entrar no gatilho fecha a porta e acorda o chefe; voltar ao checkpoint reabre e reinicia.
            var phases = new List<ArenaPhase>();
            host.Events.Subscribe<ArenaStateEvent>((in ArenaStateEvent e) => phases.Add(e.Phase));
            var trigger = arena.Trigger;
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(trigger.center.x, 0f, trigger.center.y);
            controller.enabled = true;
            yield return null;
            yield return null;
            Assert.AreEqual(ArenaPhase.Fighting, arena.Phase, "entrou no gatilho");
            var gate = Object.FindObjectsByType<GateBarrier>(FindObjectsSortMode.None).First(g => g.name == "gate.crypt.arena");
            Assert.IsTrue(gate.IsClosed, "a porta fechou atras do heroi");
            yield return new WaitForSeconds(2f);
            Assert.IsNotNull(arena.Boss.Logic.Boss, "o chefe nativo acordou");

            hero.ReturnToCheckpoint();
            yield return null;
            Assert.Contains(ArenaPhase.Waiting, phases, "a luta reiniciou e a porta reabriu");
            yield return null;
            yield return null;
            Assert.AreEqual(ArenaPhase.Fighting, arena.Phase, "o heroi volta ao inicio da arena e a luta recomeca na hora");
            Assert.AreEqual(director.EnemyCount, Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).Length);
        }
    }
}
