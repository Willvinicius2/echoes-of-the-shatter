using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Text;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Modo de medicao de quadro do player (-perf arquivo.txt): na Cripta, o heroi (vida de teste) entra na arena do Guardiao e, com o chefe lutando,
    /// grava o tempo de quadro de 10 s com o VSync como esta nas opcoes e de mais 10 s com VSync desligado (custo real). Registra media, p95, p99,
    /// maximo e FPS medio no arquivo e no log, e sai. Inerte sem o argumento; nunca roda no jogo normal.
    /// </summary>
    public sealed class FramePerfRunner : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] float windowSeconds = 10f;

        void Start()
        {
            var path = GameFlow.ArgValue("-perf");
            if (path != null) StartCoroutine(Run(path));
        }

        IEnumerator Run(string path)
        {
            yield return new WaitForSecondsRealtime(3f);
            var hero = FindAnyObjectByType<HeroController>();
            var arena = FindAnyObjectByType<ArenaController>();
            if (hero == null || arena == null)
            {
                Debug.LogError("[Perf] Cripta incompleta.");
                Application.Quit(1);
                yield break;
            }
            TestSettings.HeroGodMode = true;
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y);
            controller.enabled = true;
            yield return new WaitForSecondsRealtime(5f); // a porta fecha e o chefe comeca a lutar

            var report = new StringBuilder();
            var shippedVsync = QualitySettings.vSyncCount;
            var target = Application.targetFrameRate;
            report.AppendLine($"Cena: {UnityEngine.SceneManagement.SceneManager.GetActiveScene().name}; GPU: {SystemInfo.graphicsDeviceName}; CPU: {SystemInfo.processorType} x{SystemInfo.processorCount}; resolucao {Screen.width}x{Screen.height}");
            yield return Measure(report, $"como entregue (vSyncCount={shippedVsync}, targetFrameRate={target})");
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = -1;
            yield return Measure(report, "VSync desligado (custo real)");
            QualitySettings.vSyncCount = shippedVsync;
            Application.targetFrameRate = target;

            try { File.WriteAllText(path, report.ToString(), Encoding.UTF8); } catch (Exception e) { Debug.LogWarning("[Perf] Nao gravou " + path + ": " + e.Message); }
            Debug.Log("[Perf]\n" + report);
            yield return new WaitForSecondsRealtime(0.5f);
            Application.Quit();
        }

        IEnumerator Measure(StringBuilder report, string label)
        {
            yield return null;
            var samples = new float[20000];
            var n = 0;
            var elapsed = 0f;
            var lights = FindAnyObjectByType<Echoes.Presentation.FirePool>();
            var maxLights = 0;
            while (elapsed < windowSeconds && n < samples.Length)
            {
                yield return null;
                var dt = Time.unscaledDeltaTime;
                samples[n++] = dt * 1000f;
                elapsed += dt;
                if (lights != null) maxLights = Mathf.Max(maxLights, lights.ActiveLightCount);
            }
            Array.Sort(samples, 0, n);
            double sum = 0;
            for (var i = 0; i < n; i++) sum += samples[i];
            var mean = sum / Math.Max(1, n);
            float P(double q) => samples[Mathf.Clamp((int)Math.Ceiling(q * n) - 1, 0, n - 1)];
            var line = string.Format(CultureInfo.InvariantCulture,
                "{0}: {1} quadros em {2:F1} s; media {3:F2} ms ({4:F0} FPS); mediana {5:F2} ms; p95 {6:F2} ms; p99 {7:F2} ms; max {8:F2} ms; luzes de fogo ativas (max) {9}",
                label, n, elapsed, mean, 1000.0 / mean, P(0.5), P(0.95), P(0.99), samples[n - 1], maxLights);
            report.AppendLine(line);
            Debug.Log("[Perf] " + line);
        }
    }
}
