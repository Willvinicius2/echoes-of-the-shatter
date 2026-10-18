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
    /// toca isso na camada Upper (tronco e braços) enquanto as pernas da camada Base seguem andando. Kit, cena e Animator são os reais (basic_kits.csv do core).
    /// </summary>
    [Category("Animation")]
    public sealed class BasicKitPlayTests
    {
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
                pressFrame = Time.frameCount + 1; // o Update do heroi vê o aperto no quadro seguinte
            }

            public void Release(HeroCommand command) => held.Remove(command);
            public bool WasPressed(HeroCommand command) => pressFrame == Time.frameCount && pressedThisFrame.Contains(command);
            public bool IsHeld(HeroCommand command) => held.Contains(command);
        }

        const string ScenePath = "Assets/Scenes/Cripta/Cripta.unity";

        [UnityTest]
        public IEnumerator GuardAndChargeUseTheUpperLayerWhileTheLegsKeepWalking()
        {
            try
            {
                yield return SceneManager.LoadSceneAsync(ScenePath, LoadSceneMode.Single);
                yield return null;
                yield return null;
                var hero = Object.FindFirstObjectByType<HeroController>();
                Assert.IsTrue(hero.Logic.HasKit, "o Guerreiro tem kit no core (basic_kits.csv)");
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
                Assert.IsTrue(animator.GetCurrentAnimatorStateInfo(0).IsName("AimLocomotion"), "defendendo, as pernas usam o blend 2D da mira (AimLocomotion) e seguem andando");
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
                    sawBasic |= animator.GetCurrentAnimatorStateInfo(action).IsName("HeavyRelease");
                }
                Assert.IsTrue(sawBasic, "o golpe forte (Melee_2H_Attack_Slice a partir de holdAt) soltou na camada Action");
                Assert.IsTrue(animator.GetCurrentAnimatorStateInfo(upper).IsName("Empty"));
            }
            finally
            {
                var hero = Object.FindFirstObjectByType<HeroController>();
                if (hero != null) hero.InputHandler.Script = null;
            }
        }
    }
}
