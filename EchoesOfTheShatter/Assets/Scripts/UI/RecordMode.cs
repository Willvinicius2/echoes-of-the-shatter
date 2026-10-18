using System;
using System.Collections;
using System.Collections.Generic;
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
    /// <c>-scenario warrior|archer|mage</c> (com <c>-record PASTA</c> e <c>-hero</c> da classe) roda um roteiro de combate perto de inimigos que não morrem
    /// (docs/18: combo, forte carregado, defesa, defesa perfeita, esquiva retomando o combo; leque, tiro carregado e Chuva; dardos, orbe, Bola de Fogo e Nova)
    /// e junta os quadros num MP4 com o ffmpeg (<c>-videoname NOME</c>). Sem <c>-scenario</c> grava a locomoção (corrida em círculo e zigue-zague).
    /// </summary>
    public sealed class RecordMode : MonoBehaviour, IScriptedInput
    {
        /// <summary>m/s do herói só para o vídeo da corrida; o AnimatorControllerBuilder lê a mesma variável para o limiar da corrida da árvore.</summary>
        public const string DevSpeedVariable = "ECHOES_DEV_HERO_SPEED";

        const int Fps = 30;
        const int MaxFrames = 420;

        string folder;
        string closeup;
        string scenario;
        string videoName;
        bool rimOld;

        // IScriptedInput
        public Vector2 Move { get; private set; }
        public Vector2 Aim { get; private set; }
        int pressFrame = -10;
        readonly Dictionary<HeroCommand, int> pressedAt = new Dictionary<HeroCommand, int>();
        readonly HashSet<HeroCommand> held = new HashSet<HeroCommand>();
        public bool WasPressed(HeroCommand command) => (command == HeroCommand.BasicAttack && Time.frameCount == pressFrame)
            || (pressedAt.TryGetValue(command, out var frame) && frame == Time.frameCount);
        public bool IsHeld(HeroCommand command) => held.Contains(command);

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
            mode.scenario = GameFlow.ArgValue("-scenario");
            mode.videoName = GameFlow.ArgValue("-videoname");
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
            ApplyCameraDistance();
            if (closeup != null) yield return RunCloseup(hero);
            else if (!string.IsNullOrEmpty(scenario) && !string.Equals(scenario, "run", StringComparison.OrdinalIgnoreCase)) yield return RunScenario(hero, scenario.ToLowerInvariant());
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
            var shot = Grab();
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(closeup)));
            File.WriteAllBytes(closeup, shot.EncodeToPNG());
            Destroy(shot);
            Debug.Log("[Record] closeup: " + closeup + (rimOld ? " (rim antigo)" : ""));
        }

        IEnumerator RunRecord(HeroController hero)
        {
            Directory.CreateDirectory(folder);
            var cam = Camera.main;
            var enemy = NearestEnemy(hero.transform.position);
            if (enemy != null) PlaceHeroAtDistance(hero, enemy.transform.position, 11f);
            SnapCamera(hero);
            for (var i = 0; i < 30; i++) yield return null; // assenta o corpo no novo lugar
            SnapCamera(hero);
            traceHero = hero;

            HeroController.DeviationFrames = 0;
            HeroController.ResyncCount = 0;
            Time.captureFramerate = Fps;
            var attacksDone = 0;
            var nextAttackFrame = -1;
            var idleAfter = 0;
            var f = 0;
            var runSeconds = ArgInt("-runseconds", 0);
            var runFrames = runSeconds > 0 ? Mathf.Min(MaxFrames, runSeconds * Fps) : MaxFrames;
            for (; f < runFrames; f++)
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
                SaveFrame(f);
            }
            Time.captureFramerate = 0;
            var text = new StringBuilder();
            text.AppendLine($"frames={f}");
            text.AppendLine($"seconds={f / (float)Fps:F2}");
            text.AppendLine($"attacks={attacksDone}");
            text.AppendLine($"deviationFrames(>1mm)={HeroController.DeviationFrames}");
            text.AppendLine($"resyncs={HeroController.ResyncCount}");
            File.WriteAllText(Path.Combine(folder, "stats.txt"), text.ToString());
            File.WriteAllText(Path.Combine(folder, "trace.csv"), trace.ToString());
            if (!string.IsNullOrEmpty(videoName)) Encode(Path.Combine(folder, videoName + ".mp4"));
            Debug.Log("[Record] gravado em " + folder + "\n" + text);
        }

        // ============================================================================================ roteiros de combate (docs/18)

        int frame;
        bool perfectArmed;
        float perfectAt;

        // Entrada: apertar (por 'frames' quadros), segurar e soltar. O PumpButton do herói vê o aperto no quadro seguinte.
        void Hold(HeroCommand command)
        {
            held.Add(command);
            pressedAt[command] = Time.frameCount + 1;
        }

        void Release(HeroCommand command) => held.Remove(command);

        Func<bool> Frames(int count)
        {
            var end = frame + Mathf.Max(1, count);
            return () => frame >= end;
        }

        Func<bool> Sec(float seconds) => Frames(Mathf.RoundToInt(seconds * Fps));

        static Func<bool> Until(Func<bool> condition) => condition;

        void Tap(HeroCommand command)
        {
            Hold(command);
            tapRelease.Add((command, frame + 3));
        }

        readonly List<(HeroCommand command, int frame)> tapRelease = new List<(HeroCommand, int)>();

        // Anda ate ficar a 'range' m do inimigo mais proximo (o golpe recebido empurra; o roteiro de defesa precisa dele ao alcance).
        float approachRange;

        IEnumerator<Func<bool>> Approach(HeroController hero, float range)
        {
            approachRange = range;
            var deadline = Time.time + 3f;
            yield return Until(() =>
            {
                var near = NearestEnemy(hero.transform.position);
                return near == null || Vector3.Distance(near.transform.position, hero.transform.position) <= range + 0.15f || Time.time > deadline;
            });
            approachRange = 0f;
            yield return Frames(4);
        }

        IEnumerator<Func<bool>> Strike(HeroController hero)
        {
            // Um golpe: toca o botão, espera começar e acabar. Dá o tempo de a janela do combo (combo_window) continuar aberta.
            Tap(HeroCommand.BasicAttack);
            yield return Until(() => hero.Logic.IsCasting);
            yield return Until(() => !hero.Logic.IsCasting);
        }

        IEnumerator<Func<bool>> Charge(HeroController hero, float seconds)
        {
            Hold(HeroCommand.BasicAttack);
            yield return Sec(seconds);
            Release(HeroCommand.BasicAttack);
            yield return Frames(2);
            yield return Until(() => !hero.Logic.IsCasting);
        }

        IEnumerator<Func<bool>> Cast(HeroController hero, HeroCommand slot)
        {
            Tap(slot);
            yield return Until(() => hero.Logic.IsCasting);
            yield return Until(() => !hero.Logic.IsCasting);
        }

        IEnumerator<Func<bool>> ScenarioSteps(HeroController hero, string name)
        {
            var logic = hero.Logic;
            yield return Sec(1.0f);
            switch (name)
            {
                case "warrior":
                    for (var i = 0; i < 3; i++)
                    {
                        var s = Strike(hero);
                        while (s.MoveNext()) yield return s.Current;
                    }
                    yield return Sec(0.8f);
                    var heavy = Charge(hero, 1.5f); // carga cheia: solta sozinho em 1,25 s
                    while (heavy.MoveNext()) yield return heavy.Current;
                    yield return Sec(0.6f);
                    var close1 = Approach(hero, 1.5f);
                    while (close1.MoveNext()) yield return close1.Current;
                    Hold(HeroCombatLogic.GuardButton); // defesa recebendo golpe
                    yield return Sec(3.0f);
                    Release(HeroCombatLogic.GuardButton);
                    yield return Sec(0.6f);
                    var close2 = Approach(hero, 1.5f);
                    while (close2.MoveNext()) yield return close2.Current;
                    perfectArmed = true; // defesa perfeita: aperta perto do impacto do telegraph do inimigo
                    var perfectDeadline = Time.time + 6f; // o inimigo pode demorar a atacar; nao trava o roteiro
                    yield return Until(() => (Time.time >= perfectAt && perfectAt > 0f) || Time.time > perfectDeadline);
                    Hold(HeroCombatLogic.GuardButton);
                    yield return Sec(0.8f);
                    Release(HeroCombatLogic.GuardButton);
                    perfectArmed = false;
                    yield return Sec(0.8f);
                    // esquiva retomando o combo: golpe 1, esquiva na metade final da recuperação, golpe 2 dentro da janela
                    Tap(HeroCommand.BasicAttack);
                    yield return Until(() => logic.IsCasting);
                    yield return Until(() => logic.Action.Phase == ActionPhase.Recovery && logic.Action.RecoveryFraction >= 0.5);
                    Tap(HeroCommand.Dodge);
                    yield return Until(() => logic.Dodge.IsDodging);
                    yield return Until(() => !logic.Dodge.IsDodging);
                    yield return Sec(0.1f);
                    var resumed = Strike(hero);
                    while (resumed.MoveNext()) yield return resumed.Current;
                    break;
                case "archer":
                    for (var i = 0; i < 3; i++) // Disparo Reto, Disparo Reto, Flechas em Leque
                    {
                        var s = Strike(hero);
                        while (s.MoveNext()) yield return s.Current;
                    }
                    yield return Sec(0.8f);
                    var piercing = Charge(hero, 1.4f);
                    while (piercing.MoveNext()) yield return piercing.Current;
                    yield return Sec(0.6f);
                    var rain = Cast(hero, HeroCommand.Skill3); // E: Chuva de Flechas
                    while (rain.MoveNext()) yield return rain.Current;
                    break;
                case "mage":
                    for (var i = 0; i < 3; i++) // Dardo, Dardo, Orbe
                    {
                        var s = Strike(hero);
                        while (s.MoveNext()) yield return s.Current;
                    }
                    yield return Sec(0.8f);
                    var fireball = Charge(hero, 1.6f);
                    while (fireball.MoveNext()) yield return fireball.Current;
                    yield return Sec(0.6f);
                    var nova = Cast(hero, HeroCommand.Skill2); // Q: Nova de Gelo
                    while (nova.MoveNext()) yield return nova.Current;
                    break;
                default:
                    Debug.LogWarning("[Record] Roteiro desconhecido: " + name);
                    break;
            }
            yield return Sec(1.2f);
        }

        IEnumerator RunScenario(HeroController hero, string name)
        {
            Directory.CreateDirectory(folder);
            var cam = Camera.main;
            TestSettings.EnemyGodMode = true;
            var host = FindAnyObjectByType<CombatSystemHost>();
            host.Events.Subscribe<SkillPhaseEvent>(OnPhase);
            var first = NearestEnemy(hero.transform.position);
            if (first != null) PlaceHeroAtDistance(hero, first.transform.position, name == "warrior" ? 1.5f : 5f);
            SnapCamera(hero);
            for (var i = 0; i < 30; i++) yield return null;
            SnapCamera(hero);
            traceHero = hero;
            if (!hero.Logic.HasKit) Debug.LogError("[Record] O herói não tem kit básico (o roteiro precisa do core nativo).");

            Time.captureFramerate = Fps;
            var script = ScenarioSteps(hero, name);
            Func<bool> wait = null;
            var done = false;
            var tail = 0;
            for (frame = 0; frame < ScenarioMaxFrames; frame++)
            {
                for (var i = tapRelease.Count - 1; i >= 0; i--)
                {
                    if (frame < tapRelease[i].frame) continue;
                    Release(tapRelease[i].command);
                    tapRelease.RemoveAt(i);
                }
                if (!done && (wait == null || wait()))
                {
                    if (script.MoveNext()) wait = script.Current;
                    else done = true;
                }
                if (done && ++tail > 15) break;

                var target = NearestEnemy(hero.transform.position);
                var aimWorld = target != null ? target.transform.position : hero.transform.position + hero.transform.forward * 3f;
                var screen = cam.WorldToScreenPoint(aimWorld);
                Aim = new Vector2(screen.x, screen.y);
                Move = Vector2.zero;
                if (approachRange > 0f && target != null)
                {
                    var toTarget = target.transform.position - hero.transform.position;
                    toTarget.y = 0f;
                    if (toTarget.magnitude > approachRange) Move = ScreenDirection(cam, toTarget.normalized);
                }

                yield return new WaitForEndOfFrame();
                SaveFrame(frame);
            }
            Time.captureFramerate = 0;
            host.Events.Unsubscribe<SkillPhaseEvent>(OnPhase);
            File.WriteAllText(Path.Combine(folder, "trace.csv"), trace.ToString());
            var heroId = Echoes.Core.HeroChoice.Id;
            var file = (string.IsNullOrEmpty(videoName) ? name + "_" + heroId : videoName) + ".mp4";
            Encode(Path.Combine(folder, file));
            Debug.Log("[Record] roteiro " + name + ": " + frame + " quadros, " + file);
        }

        void OnPhase(in SkillPhaseEvent evt)
        {
            // Armar a defesa perfeita: o telegraph do inimigo (preparação) termina no impacto; o aperto cai 0,1 s antes (janela de 0,2 s).
            if (!perfectArmed || evt.Owner == null || evt.Owner.Team != CombatTeam.Enemy || evt.Phase != ActionPhase.Windup || evt.PhaseSeconds < 0.3) return;
            perfectAt = Time.time + (float)evt.PhaseSeconds - 0.1f;
        }

        const int ScenarioMaxFrames = 900;

        // trace.csv: uma linha por quadro (posicao, velocidade, giro, fase do core, estado/clipes por camada do Animator) para medir deslize, giro e transicoes.
        readonly StringBuilder trace = new StringBuilder("frame,t,x,z,speed_mps,yaw_deg,turn_dps,combo,casting,phase,skill,charging,guarding,dodging,animSpeed,enemyDist,L0,L0w,L1,L1w,L2,L2w\n");
        Vector3 tracePos;
        float traceYaw;
        bool traceFirst = true;
        HeroController traceHero;

        void TraceRow(int index)
        {
            var hero = traceHero;
            if (hero == null) return;
            var dt = 1f / Fps;
            var pos = hero.transform.position;
            var yaw = hero.transform.eulerAngles.y;
            var speed = traceFirst ? 0f : new Vector2(pos.x - tracePos.x, pos.z - tracePos.z).magnitude / dt;
            var turn = traceFirst ? 0f : Mathf.DeltaAngle(traceYaw, yaw) / dt;
            tracePos = pos;
            traceYaw = yaw;
            traceFirst = false;
            var logic = hero.Logic;
            var near = NearestEnemy(pos);
            var animator = hero.GetComponentInChildren<Animator>();
            string Layer(int layer, out float weight)
            {
                weight = 0f;
                if (animator == null || layer >= animator.layerCount) return "";
                var infos = animator.GetCurrentAnimatorClipInfo(layer);
                if (infos.Length == 0) return "-";
                var best = infos[0];
                foreach (var info in infos) if (info.weight > best.weight) best = info;
                weight = best.weight;
                return best.clip.name;
            }
            var l0 = Layer(0, out var w0);
            var l1 = Layer(1, out var w1);
            var l2 = Layer(2, out var w2);
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            trace.Append(index).Append(',').Append((index * dt).ToString("F3", inv)).Append(',').Append(pos.x.ToString("F3", inv)).Append(',').Append(pos.z.ToString("F3", inv))
                .Append(',').Append(speed.ToString("F2", inv)).Append(',').Append(yaw.ToString("F1", inv)).Append(',').Append(turn.ToString("F0", inv))
                .Append(',').Append(logic.ComboIndex).Append(',').Append(logic.IsCasting ? 1 : 0).Append(',').Append(logic.Action.Phase)
                .Append(',').Append(logic.CurrentSkill != null ? logic.CurrentSkill.Id : "").Append(',').Append(logic.IsCharging ? 1 : 0).Append(',').Append(logic.IsGuarding ? 1 : 0)
                .Append(',').Append(logic.Dodge.IsDodging ? 1 : 0).Append(',').Append(animator != null ? animator.speed.ToString("F2", inv) : "").Append(',').Append(near != null ? Vector3.Distance(near.transform.position, pos).ToString("F1", inv) : "")
                .Append(',').Append(l0).Append(',').Append(w0.ToString("F2", inv)).Append(',').Append(l1).Append(',').Append(w1.ToString("F2", inv)).Append(',').Append(l2).Append(',').Append(w2.ToString("F2", inv)).Append('\n');
        }

        void SaveFrame(int index)
        {
            TraceRow(index);
            var texture = Grab();
            File.WriteAllBytes(Path.Combine(folder, $"frame_{index:D5}.png"), texture.EncodeToPNG());
            Destroy(texture);
        }

        // Sem janela (o dono nao pode ver nada na tela): a camera principal desenha num RenderTexture e o quadro sai por ReadPixels, nao por captura de tela.
        // Funciona em -batchmode (sem -nographics). Tamanho: -recwidth/-recheight (padrao 1280x720).
        RenderTexture captureTarget;

        Texture2D Grab()
        {
            var cam = Camera.main;
            if (captureTarget == null)
            {
                var width = Mathf.Max(64, ArgInt("-recwidth", 1280));
                var height = Mathf.Max(64, ArgInt("-recheight", 720));
                captureTarget = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32) { name = "RecordTarget" };
                captureTarget.Create();
            }
            var previous = cam.targetTexture;
            cam.targetTexture = captureTarget;
            cam.aspect = captureTarget.width / (float)captureTarget.height;
            cam.Render();
            var texture = new Texture2D(captureTarget.width, captureTarget.height, TextureFormat.RGB24, false);
            var active = RenderTexture.active;
            RenderTexture.active = captureTarget;
            texture.ReadPixels(new Rect(0, 0, captureTarget.width, captureTarget.height), 0, 0);
            texture.Apply(false);
            RenderTexture.active = active;
            cam.targetTexture = previous;
            cam.ResetAspect();
            return texture;
        }

        // -camdist METROS: aproxima a camera so para o video (o padrao do jogo, 56 m, deixa o heroi minusculo para revisar a animacao). Nao toca o asset.
        static void ApplyCameraDistance()
        {
            var value = GameFlow.ArgValue("-camdist");
            if (value == null || !float.TryParse(value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var meters) || meters <= 0f) return;
            var cam = Camera.main;
            if (cam == null) return;
            var tuner = FindAnyObjectByType<CameraDistanceTuner>();
            if (tuner != null) tuner.enabled = false;
            cam.transform.localPosition = new Vector3(0f, 0f, -meters);
            // -campitch GRAUS: inclinacao da camera (so para revisar a pose; o jogo usa o pitch do asset).
            var pitchArg = GameFlow.ArgValue("-campitch");
            var follow = FindAnyObjectByType<FollowCamera>();
            if (follow != null && pitchArg != null && float.TryParse(pitchArg, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var pitch))
                follow.transform.rotation = Quaternion.Euler(pitch, follow.transform.eulerAngles.y, 0f);
            Debug.Log("[Record] camera a " + meters + " m");
        }

        // Depois do teleporte do roteiro a camera nao deve "voar" ate o heroi dentro do video.
        static void SnapCamera(HeroController hero)
        {
            var follow = FindAnyObjectByType<FollowCamera>();
            if (follow != null) follow.SetTarget(hero.transform, true);
        }

        static int ArgInt(string name, int fallback)
        {
            var value = GameFlow.ArgValue(name);
            return value != null && int.TryParse(value, out var parsed) ? parsed : fallback;
        }

        // Junta os quadros num MP4 (ffmpeg no PATH) e apaga os PNG se deu certo.
        void Encode(string output)
        {
            try
            {
                var info = new System.Diagnostics.ProcessStartInfo("ffmpeg", $"-y -loglevel error -framerate {Fps} -i \"{Path.Combine(folder, "frame_%05d.png")}\" -c:v libx264 -pix_fmt yuv420p -crf 20 \"{output}\"")
                {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                };
                using (var process = System.Diagnostics.Process.Start(info))
                {
                    process.WaitForExit();
                    if (process.ExitCode == 0 && File.Exists(output))
                    {
                        foreach (var png in Directory.GetFiles(folder, "frame_*.png")) File.Delete(png);
                    }
                    else Debug.LogWarning("[Record] ffmpeg saiu com " + process.ExitCode + "; os PNG ficam em " + folder);
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning("[Record] Sem ffmpeg (" + e.Message + "); os PNG ficam em " + folder);
            }
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
