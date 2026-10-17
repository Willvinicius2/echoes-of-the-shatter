using System.Collections;
using System.IO;
using System.Text;
using Echoes.Gameplay;
using Echoes.Presentation;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Echoes.UI
{
    /// <summary>
    /// Modo de captura do PLAYER (-shots pasta): a tela inicial entra sozinha (implica -autostart) e, em runtime, com a camera do jogo a 56 m, grava
    /// runtime_refugio.png, runtime_cripta_entrada.png, runtime_cripta_encontro.png (sala da Patrulha B) e runtime_cripta_arena.png (Guardiao),
    /// mais runtime_heroi_perto.png (camera de perto, para ver a armadura modular equipada) e registra no log as pecas vestidas. Cada etapa tem
    /// timeout e um "[Shots] etapa: ..." no log; se travar, loga onde parou e sai com erro. Inerte sem o argumento; nunca roda no jogo normal.
    /// </summary>
    public sealed class RuntimeShotsRunner : MonoBehaviour
    {
        const float StageTimeout = 40f;
        string stage = "inicio";
        string folder;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            var path = GameFlow.ArgValue("-shots");
            if (string.IsNullOrEmpty(path)) return;
            var go = new GameObject("RuntimeShotsRunner");
            DontDestroyOnLoad(go);
            go.AddComponent<RuntimeShotsRunner>().folder = path;
        }

        void Start()
        {
            Directory.CreateDirectory(folder);
            StartCoroutine(Run());
            StartCoroutine(Watchdog());
        }

        void Stage(string name)
        {
            stage = name;
            Debug.Log("[Shots] etapa: " + name + " (cena " + SceneManager.GetActiveScene().name + ")");
        }

        IEnumerator Watchdog()
        {
            yield return new WaitForSecondsRealtime(180f);
            Debug.LogError("[Shots] TIMEOUT geral: parou na etapa '" + stage + "'");
            Application.Quit(1);
        }

        IEnumerator WaitScene(string scene)
        {
            var t = 0f;
            while (SceneManager.GetActiveScene().name != scene && t < StageTimeout)
            {
                t += Time.unscaledDeltaTime;
                yield return null;
            }
            if (SceneManager.GetActiveScene().name != scene)
            {
                Debug.LogError("[Shots] parou na etapa '" + stage + "': a cena " + scene + " nao carregou em " + StageTimeout + " s (cena atual " + SceneManager.GetActiveScene().name + ")");
                Application.Quit(1);
                yield break;
            }
            yield return new WaitForSecondsRealtime(2.5f);
        }

        IEnumerator Shoot(string file)
        {
            yield return new WaitForEndOfFrame();
            var path = Path.Combine(folder, file);
            ScreenCapture.CaptureScreenshot(path);
            yield return new WaitForSecondsRealtime(1.2f);
            Debug.Log("[Shots] capturada: " + path + " (" + (File.Exists(path) ? new FileInfo(path).Length + " bytes" : "AUSENTE") + ")");
        }

        static void Teleport(HeroController hero, Vector3 position)
        {
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = position;
            controller.enabled = true;
        }

        IEnumerator Run()
        {
            Stage("aguardando o Refugio (tela inicial -> novo jogo automatico)");
            yield return WaitScene(GameFlow.RefugeScene);
            var hero = FindAnyObjectByType<HeroController>();
            if (hero == null) { Debug.LogError("[Shots] sem heroi no Refugio"); Application.Quit(1); yield break; }
            TestSettings.HeroGodMode = true;
            Stage("captura do Refugio");
            yield return Shoot("runtime_refugio.png");

            Stage("heroi de perto");
            LogEquipment(hero);
            var follow = FindAnyObjectByType<FollowCamera>();
            var cam = Camera.main;
            if (follow != null && cam != null)
            {
                follow.enabled = false;
                var p = hero.transform.position;
                var toFront = hero.transform.forward;
                cam.transform.position = p + toFront * 3.2f + Vector3.up * 1.5f;
                cam.transform.LookAt(p + Vector3.up * 1.0f);
                cam.fieldOfView = 30f;
                yield return new WaitForSecondsRealtime(0.5f);
                yield return Shoot("runtime_heroi_perto.png");
                cam.transform.position = p - toFront * 3.2f + Vector3.up * 1.5f;
                cam.transform.LookAt(p + Vector3.up * 1.0f);
                yield return new WaitForSecondsRealtime(0.3f);
                yield return Shoot("runtime_heroi_perto_costas.png");
                follow.enabled = true;
            }

            Stage("indo para a Cripta");
            GameFlow.StartGame();
            yield return null;
            yield return WaitScene(GameFlow.CriptaScene);
            hero = FindAnyObjectByType<HeroController>();
            if (hero == null) { Debug.LogError("[Shots] sem heroi na Cripta"); Application.Quit(1); yield break; }
            TestSettings.HeroGodMode = true;
            Stage("captura da entrada da Cripta");
            yield return Shoot("runtime_cripta_entrada.png");

            Stage("sala com encontro (Patrulha B)");
            EnemyController target = null;
            foreach (var e in FindObjectsByType<EnemyController>(FindObjectsSortMode.None))
            {
                if (e.EnemyId == "enemy.hollow_sentinel" && e.transform.parent != null && e.transform.parent.name == "enc.crypt.patrol_b") { target = e; break; }
            }
            if (target == null) { Debug.LogError("[Shots] encontro enc.crypt.patrol_b nao encontrado"); Application.Quit(1); yield break; }
            Teleport(hero, target.transform.position + new Vector3(8f, 0f, 0f));
            yield return new WaitForSecondsRealtime(1.8f);
            yield return Shoot("runtime_cripta_encontro.png");

            Stage("arena do Guardiao");
            var arena = FindAnyObjectByType<ArenaController>();
            if (arena == null) { Debug.LogError("[Shots] sem ArenaController"); Application.Quit(1); yield break; }
            Teleport(hero, new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y));
            yield return new WaitForSecondsRealtime(4f);
            yield return Shoot("runtime_cripta_arena.png");

            Stage("fim");
            Debug.Log("[Shots] concluido em " + folder);
            Application.Quit();
        }

        static void LogEquipment(HeroController hero)
        {
            var modular = hero.GetComponentInChildren<ModularCharacter>();
            if (modular == null) { Debug.LogWarning("[Shots] heroi sem ModularCharacter"); return; }
            var sb = new StringBuilder("[Shots] pecas vestidas:");
            for (var i = 0; i < 5; i++)
            {
                var slot = (HeroPartSlot)i;
                var part = modular.Equipped(slot);
                sb.Append(' ').Append(slot).Append('=').Append(part != null ? part.name : "(nenhuma)");
            }
            Debug.Log(sb.ToString());
        }
    }
}
