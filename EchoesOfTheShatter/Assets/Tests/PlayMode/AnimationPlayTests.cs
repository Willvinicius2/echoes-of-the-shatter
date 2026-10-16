using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Echoes.Gameplay;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// Smoke de Play da animacao (KayKit): o heroi anda e ataca, e o Animator passa por Locomotion (com Speed), pela camada Action no
    /// estado Basic e, na Sentinela atingida, pela camada Hit no estado Hit. Os eventos do combate e o movimento e que mexem no
    /// Animator (o PresentationController); o controller nunca decide regra.
    /// </summary>
    [Category("Animation")]
    public sealed class AnimationPlayTests
    {
        const string ScenePath = "Assets/Scenes/Cripta/Cripta.unity";

        [UnityTest]
        public IEnumerator HeroWalksAttacksAndTheSentinelFlinchesInTheAnimator()
        {
            yield return SceneManager.LoadSceneAsync(ScenePath, LoadSceneMode.Single);
            yield return null;
            yield return null;

            var host = Object.FindFirstObjectByType<CombatSystemHost>();
            var hero = Object.FindFirstObjectByType<HeroController>();
            var heroAnimator = hero.GetComponentInChildren<Animator>();
            Assert.IsNotNull(heroAnimator);
            Assert.AreEqual("AC_Warrior", heroAnimator.runtimeAnimatorController.name);
            var action = heroAnimator.GetLayerIndex("Action");
            var hitLayer = heroAnimator.GetLayerIndex("Hit");
            Assert.AreEqual(1, action);
            Assert.AreEqual(2, hitLayer);

            // Andar: o corpo do heroi anda (CharacterController, como no jogo); o PresentationController alimenta Speed com o deslocamento real.
            var controller = hero.GetComponent<CharacterController>();
            var maxSpeed = 0f;
            var locomotion = false;
            for (var t = 0f; t < 0.8f; t += Time.deltaTime)
            {
                controller.Move(hero.transform.forward * (5f * Time.deltaTime));
                yield return null;
                maxSpeed = Mathf.Max(maxSpeed, heroAnimator.GetFloat("Speed"));
                locomotion |= heroAnimator.GetCurrentAnimatorStateInfo(0).IsName("Locomotion");
            }
            Assert.IsTrue(locomotion, "camada Base em Locomotion");
            Assert.Greater(maxSpeed, 1f, "o heroi andou: Speed alimenta o blend Idle/Walk/Run");

            // Atacar: golpe basico pelo core; a camada Action passa pelo estado Basic.
            for (var t = 0f; t < 1f && !hero.Logic.IsReadyForAction; t += Time.deltaTime) yield return null;
            hero.Logic.Press(HeroCommand.BasicAttack);
            var sawBasic = false;
            for (var t = 0f; t < 1.2f; t += Time.deltaTime)
            {
                yield return null;
                sawBasic |= heroAnimator.GetCurrentAnimatorStateInfo(action).IsName("Basic");
            }
            Assert.IsTrue(sawBasic, "a camada Action tocou Basic");

            // A Sentinela atingida toca Hit na camada Hit.
            var sentinel = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None).First(e => e.EnemyId == "enemy.hollow_sentinel");
            var enemyAnimator = sentinel.GetComponentInChildren<Animator>();
            Assert.AreEqual("AC_EnemyHumanoid", enemyAnimator.runtimeAnimatorController.name);
            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            host.Combat.ApplySkillHit(hero.Combatant, sentinel.Combatant, skill, hero.Combatant.Position);
            var sawHit = false;
            for (var t = 0f; t < 0.6f; t += Time.deltaTime)
            {
                yield return null;
                sawHit |= enemyAnimator.GetCurrentAnimatorStateInfo(enemyAnimator.GetLayerIndex("Hit")).IsName("Hit");
            }
            Assert.IsTrue(sawHit, "a camada Hit tocou Hit na Sentinela");
        }
    }
}
