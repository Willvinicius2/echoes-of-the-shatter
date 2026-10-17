using System.Collections;
using System.IO;
using System.Text;
using Echoes.Gameplay;
using Echoes.Presentation;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.SceneManagement;

namespace Echoes.UI
{
    /// <summary>
    /// Modos de captura do player, inertes sem o argumento (nunca rodam no jogo normal):
    /// <c>-record PASTA</c> grava PNGs a 30 fps (Time.captureFramerate) de uma entrada roteirizada na Cripta (andar em círculo e em zigue-zague,
    /// parar, virar, aproximar de um inimigo e atacar 3 vezes) e escreve stats.txt (ressincronizações do corpo).
    /// <c>-closeup ARQUIVO.png</c> tira uma foto de perto do herói; <c>-rimold</c> devolve o rim de borda dura de antes do polimento (comparação).
    /// </summary>
    public sealed class RecordMode : MonoBehaviour, IScriptedInput
    {
        /// <summary>m/s do herói só para o vídeo da corrida; o AnimatorControllerBuilder lê a mesma variável para o limiar da corrida da árvore.</summary>
        public const string DevSpeedVariable = "ECHOES_DEV_HERO_SPEED";

        const int Fps = 30;
        const int MaxFrames = 420;

        string folder;
        string closeup;
        bool rimOld;

        // IScriptedInput
        public Vector2 Move { get; private set; }
        public Vector2 Aim { get; private set; }
        int pressFrame = -10;
        public bool WasPressed(HeroCommand command) => command == HeroCommand.BasicAttack && Time.frameCount == pressFrame;
        public bool IsHeld(HeroCommand command) => false;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            var record = GameFlow.ArgValue("-record");
            var closeupArg = GameFlow.ArgValue("-closeup");
            if (record == null && closeupArg == null) return;
            var go = new GameObject("RecordMode");
            DontDestroyOnLoad(go);
            var mode = go.AddComponent<RecordMode>();
            mode.folder = record;
            mode.closeup = closeupArg;
            mode.rimOld = HasFlag("-rimold");
        }

        static bool HasFlag(string name)
        {
            foreach (var arg in System.Environment.GetCommandLineArgs())
            {
                if (string.Equals(arg, name, System.StringComparison.OrdinalIgnoreCase)) return true;
            }
            return false;
        }

        IEnumerator Start()
        {
            if (SceneManager.GetActiveScene().name != GameFlow.CriptaScene)
            {
                SceneManager.LoadScene(GameFlow.CriptaScene, LoadSceneMode.Single);
                yield return null;
            }
            for (var i = 0; i < 90; i++) yield return null;
            var hero = FindAnyObjectByType<HeroController>();
            var input = FindAnyObjectByType<PlayerInputHandler>();
            if (hero == null || input == null)
            {
                Debug.LogError("[Record] Cripta sem heroi ou sem entrada.");
                Application.Quit(1);
                yield break;
            }
            TestSettings.HeroGodMode = true;
            // Comparacao do pe na corrida: velocidade do heroi em m/s so para o video (variavel de ambiente de desenvolvimento; nao toca o CSV).
            var speedEnv = System.Environment.GetEnvironmentVariable(DevSpeedVariable);
            if (!string.IsNullOrEmpty(speedEnv) && float.TryParse(speedEnv, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var devSpeed) && devSpeed > 0f)
                TestSettings.HeroSpeedOverrideMetersPerSecond = devSpeed;
            input.Script = this;
            if (closeup != null) yield return RunCloseup(hero);
            else yield return RunRecord(hero);
            Application.Quit();
        }

        IEnumerator RunCloseup(HeroController hero)
        {
            if (rimOld)
            {
                foreach (var renderer in hero.GetComponentsInChildren<Renderer>())
                {
                    foreach (var material in renderer.materials)
                    {
                        if (!material.HasProperty("_FresnelStrength")) continue;
                        material.SetFloat("_FresnelStrength", 2.5f);
                        material.SetVector("_FresnelSmoothStepRange", new Vector4(0.2f, 0.05f, 0f, 0f));
                    }
                }
            }
            var follow = FindAnyObjectByType<FollowCamera>();
            if (follow != null) follow.enabled = false;
            var cam = Camera.main;
            for (var i = 0; i < 60; i++) yield return null;
            var t = hero.transform;
            var focus = t.position + Vector3.up * 0.9f;
            cam.transform.position = focus + t.forward * 2.2f + t.right * 1.1f + Vector3.up * 0.5f;
            cam.transform.rotation = Quaternion.LookRotation(focus - cam.transform.position, Vector3.up);
            for (var i = 0; i < 30; i++) yield return null;
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(closeup);
            for (var i = 0; i < 20; i++) yield return null;
            Debug.Log("[Record] closeup: " + closeup + (rimOld ? " (rim antigo)" : ""));
        }

        IEnumerator RunRecord(HeroController hero)
        {
            Directory.CreateDirectory(folder);
            var cam = Camera.main;
            var enemy = NearestEnemy(hero.transform.position);
            if (enemy != null) PlaceHeroAtDistance(hero, enemy.transform.position, 11f);
            for (var i = 0; i < 30; i++) yield return null; // assenta o corpo no novo lugar

            HeroController.DeviationFrames = 0;
            HeroController.ResyncCount = 0;
            Time.captureFramerate = Fps;
            var attacksDone = 0;
            var nextAttackFrame = -1;
            var idleAfter = 0;
            var f = 0;
            for (; f < MaxFrames; f++)
            {
                var heroPos = hero.transform.position;
                var aimWorld = heroPos + new Vector3(3f, 0f, 0f);
                var seconds = f / (float)Fps;
                if (seconds < 3f)
                {
                    var a = seconds / 3f * Mathf.PI * 2f; // círculo, mouse fixo à direita do herói
                    Move = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                }
                else if (seconds < 5.5f)
                {
                    var leg = Mathf.FloorToInt((seconds - 3f) / 0.5f); // zigue-zague
                    Move = new Vector2(leg % 2 == 0 ? 1f : -1f, 0.7f).normalized;
                }
                else if (seconds < 6.3f)
                {
                    Move = Vector2.zero; // parado: o mouse gira em volta e o corpo não vira
                    aimWorld = heroPos + new Vector3(Mathf.Cos(seconds * 6f), 0f, Mathf.Sin(seconds * 6f)) * 3f;
                }
                else if (seconds < 6.8f) Move = new Vector2(-1f, 0f); // virar
                else if (enemy != null && enemy.Combatant != null && !enemy.Combatant.IsDead)
                {
                    var toEnemy = enemy.transform.position - heroPos;
                    toEnemy.y = 0f;
                    aimWorld = enemy.transform.position;
                    if (toEnemy.magnitude > 2.0f && attacksDone == 0 && nextAttackFrame < 0)
                        Move = ScreenDirection(cam, toEnemy.normalized);
                    else
                    {
                        Move = Vector2.zero;
                        if (nextAttackFrame < 0) nextAttackFrame = f + 3;
                        if (f == nextAttackFrame && attacksDone < 3)
                        {
                            pressFrame = Time.frameCount + 1;
                            attacksDone++;
                            nextAttackFrame = f + 14;
                        }
                        if (attacksDone >= 3 && ++idleAfter > 45) break;
                    }
                }
                else Move = Vector2.zero;

                var screen = cam.WorldToScreenPoint(aimWorld);
                Aim = new Vector2(screen.x, screen.y);

                yield return new WaitForEndOfFrame();
                var texture = ScreenCapture.CaptureScreenshotAsTexture();
                File.WriteAllBytes(Path.Combine(folder, $"frame_{f:D5}.png"), texture.EncodeToPNG());
                Destroy(texture);
            }
            Time.captureFramerate = 0;
            var text = new StringBuilder();
            text.AppendLine($"frames={f}");
            text.AppendLine($"seconds={f / (float)Fps:F2}");
            text.AppendLine($"attacks={attacksDone}");
            text.AppendLine($"deviationFrames(>1mm)={HeroController.DeviationFrames}");
            text.AppendLine($"resyncs={HeroController.ResyncCount}");
            File.WriteAllText(Path.Combine(folder, "stats.txt"), text.ToString());
            Debug.Log("[Record] gravado em " + folder + "\n" + text);
        }

        static EnemyController NearestEnemy(Vector3 from)
        {
            EnemyController best = null;
            var bestDistance = float.MaxValue;
            foreach (var enemy in FindObjectsByType<EnemyController>(FindObjectsSortMode.None))
            {
                if (enemy.Combatant == null || enemy.Combatant.IsBoss) continue;
                var d = (enemy.transform.position - from).sqrMagnitude;
                if (d < bestDistance)
                {
                    best = enemy;
                    bestDistance = d;
                }
            }
            return best;
        }

        // Escolhe, em volta do inimigo, um ponto andável a "distance" m com linha livre até ele e leva o herói para lá.
        static void PlaceHeroAtDistance(HeroController hero, Vector3 enemyPosition, float distance)
        {
            for (var step = 0; step < 16; step++)
            {
                var angle = step * Mathf.PI * 2f / 16f;
                var candidate = enemyPosition + new Vector3(Mathf.Cos(angle), 0f, Mathf.Sin(angle)) * distance;
                if (!NavMesh.SamplePosition(candidate, out var hit, 1.5f, NavMesh.AllAreas)) continue;
                if (NavMesh.Raycast(hit.position, enemyPosition, out _, NavMesh.AllAreas)) continue;
                var controller = hero.GetComponent<CharacterController>();
                controller.enabled = false;
                hero.transform.position = hit.position;
                controller.enabled = true;
                return;
            }
            Debug.LogWarning("[Record] Sem ponto livre a " + distance + " m do inimigo; o herói fica onde está.");
        }

        // Direção do mundo para entrada de tela (x direita, y para cima) pela base da câmera, o inverso do HeroController.CameraRelative.
        static Vector2 ScreenDirection(Camera cam, Vector3 worldDirection)
        {
            var forward = Vector3.ProjectOnPlane(cam.transform.forward, Vector3.up).normalized;
            var right = Vector3.ProjectOnPlane(cam.transform.right, Vector3.up).normalized;
            return new Vector2(Vector3.Dot(worldDirection, right), Vector3.Dot(worldDirection, forward));
        }
    }
}
