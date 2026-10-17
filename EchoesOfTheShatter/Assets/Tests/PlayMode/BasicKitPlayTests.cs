using System.Collections;
using System.Collections.Generic;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// Máquina de entrada do ataque básico (docs/18) ligada à cena da Cripta: o botão direito levanta a defesa e o esquerdo segurado carrega, e a apresentação
    /// toca isso na camada Upper (tronco e braços) enquanto as pernas da camada Base seguem andando. Os valores do kit são FALSOS e só existem aqui (o core
    /// ainda não expõe basic_kits.csv); a cena e o Animator são os reais.
    /// </summary>
    [Category("Animation")]
    public sealed class BasicKitPlayTests
    {
        sealed class TestKit : IBasicKit
        {
            public TestKit(IRulesCore rules)
            {
                var cut = rules.FindSkill("skill.warrior.iron_cut");
                LightChain = new[] { cut, cut, cut };
                HeavySkill = cut;
            }

            public double ComboWindow => 0.4;
            public double ComboWindowAfterDodge => 0.3;
            public double AttackBuffer => 0.15;
            public double HeavyHoldThreshold => 0.35;
            public double LightWindupCreditMax => 0.7;
            public double GuardLowerTime => 0.1;
            public IReadOnlyList<SkillInfo> LightChain { get; }
            public SkillInfo HeavySkill { get; }
            public double HeavyChargeTime => 0.9;
            public double HeavyMaxMult => 2.0;
            public string ChargeEffect => string.Empty;
            public string GuardEffect => string.Empty;
            public double GuardArcDegrees => 120.0;
            public double GuardMaxHold => 0.0;
            public double GuardCooldown => 0.25;
            public double GuardPerfectWindow => 0.2;
            public double GuardPerfectCooldown => 0.8;
        }

        /// <summary>Entrada roteirizada: andar para cima e segurar botões.</summary>
        sealed class Buttons : IScriptedInput
        {
            public Vector2 Move { get; set; }
            public Vector2 Aim => Vector2.zero;
            readonly HashSet<HeroCommand> held = new HashSet<HeroCommand>();
            readonly HashSet<HeroCommand> pressedThisFrame = new HashSet<HeroCommand>();
            int pressFrame = -1;

            public void Hold(HeroCommand command)
            {
                held.Add(command);
                pressedThisFrame.Add(command);
                pressFrame = Time.frameCount;
            }

            public void Release(HeroCommand command) => held.Remove(command);
            public bool WasPressed(HeroCommand command) => pressFrame == Time.frameCount && pressedThisFrame.Contains(command);
            public bool IsHeld(HeroCommand command) => held.Contains(command);
        }

        const string ScenePath = "Assets/Scenes/Cripta/Cripta.unity";

        [UnityTest]
        public IEnumerator GuardAndChargeUseTheUpperLayerWhileTheLegsKeepWalking()
        {
            BasicKitSource.TestFactory = (rules, classId) => new TestKit(rules);
            try
            {
                yield return SceneManager.LoadSceneAsync(ScenePath, LoadSceneMode.Single);
                yield return null;
                yield return null;
                var hero = Object.FindFirstObjectByType<HeroController>();
                Assert.IsTrue(hero.Logic.HasKit, "a cena pegou o kit da fábrica de teste");
                var animator = hero.GetComponentInChildren<Animator>();
                var upper = animator.GetLayerIndex("Upper");
                var action = animator.GetLayerIndex("Action");
                var input = new Buttons { Move = Vector2.up };
                hero.InputHandler.Script = input;

                // Botão direito segurado + andar: defesa na camada Upper, pernas (Base) em Locomotion com Speed > 0.
                input.Hold(HeroCombatLogic.GuardButton);
                var sawRaise = false;
                var maxSpeed = 0f;
                for (var t = 0f; t < 0.7f; t += Time.deltaTime)
                {
                    yield return null;
                    sawRaise |= animator.GetCurrentAnimatorStateInfo(upper).IsName("GuardRaise") || animator.GetCurrentAnimatorStateInfo(upper).IsName("GuardHold");
                    maxSpeed = Mathf.Max(maxSpeed, animator.GetFloat("Speed"));
                }
                Assert.IsTrue(hero.Logic.IsGuarding);
                Assert.IsTrue(sawRaise, "a defesa tocou na camada Upper");
                Assert.Greater(maxSpeed, 0.5f, "as pernas andam enquanto defende");
                Assert.IsTrue(animator.GetCurrentAnimatorStateInfo(0).IsName("Locomotion"));
                Assert.IsTrue(animator.GetCurrentAnimatorStateInfo(action).IsName("Empty"), "a defesa não ocupa a camada Action");

                input.Release(HeroCombatLogic.GuardButton);
                for (var t = 0f; t < 0.5f; t += Time.deltaTime) yield return null;
                Assert.IsFalse(hero.Logic.IsGuarding);
                Assert.IsTrue(animator.GetCurrentAnimatorStateInfo(upper).IsName("Empty"), "baixou a defesa: a camada Upper volta ao repouso");

                // Botão esquerdo segurado: carga na camada Upper; soltar manda o golpe para a camada Action.
                input.Hold(HeroCommand.BasicAttack);
                var sawCharge = false;
                for (var t = 0f; t < 0.7f; t += Time.deltaTime)
                {
                    yield return null;
                    sawCharge |= animator.GetCurrentAnimatorStateInfo(upper).IsName("ChargeHold");
                }
                Assert.IsTrue(hero.Logic.IsCharging, "passou do limiar de segurar");
                Assert.IsTrue(sawCharge, "carregar tocou na camada Upper");
                input.Release(HeroCommand.BasicAttack);
                var sawBasic = false;
                for (var t = 0f; t < 0.8f; t += Time.deltaTime)
                {
                    yield return null;
                    sawBasic |= animator.GetCurrentAnimatorStateInfo(action).IsName("Basic");
                }
                Assert.IsTrue(sawBasic, "o golpe forte soltou na camada Action");
                Assert.IsTrue(animator.GetCurrentAnimatorStateInfo(upper).IsName("Empty"));
            }
            finally
            {
                BasicKitSource.TestFactory = null;
                var hero = Object.FindFirstObjectByType<HeroController>();
                if (hero != null) hero.InputHandler.Script = null;
            }
        }
    }
}
