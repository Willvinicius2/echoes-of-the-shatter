using System.Collections;
using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Modo de captura do player (-bossshot arquivo.png): na Cripta, o heroi (vida de teste) entra na arena, golpeia o Guardiao de tras do escudo
    /// e a tela e salva com a barra do chefe visivel. Inerte sem o argumento. Nunca roda no jogo normal.
    /// </summary>
    public sealed class BossShotRunner : MonoBehaviour
    {
        [SerializeField] GameRoot root;

        void Start()
        {
            if (GameFlow.ArgValue("-bossshot") != null) StartCoroutine(Run(GameFlow.ArgValue("-bossshot")));
        }

        IEnumerator Run(string path)
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            yield return new WaitForSecondsRealtime(3f);
            var host = FindAnyObjectByType<CombatSystemHost>();
            var hero = FindAnyObjectByType<HeroController>();
            var arena = FindAnyObjectByType<ArenaController>();
            if (host == null || hero == null || arena == null)
            {
                Debug.LogError("[BossShot] Cripta incompleta.");
                yield break;
            }
            TestSettings.HeroGodMode = true;
            var controller = hero.GetComponent<CharacterController>();
            controller.enabled = false;
            hero.transform.position = new Vector3(arena.Trigger.center.x, 0f, arena.Trigger.center.y);
            controller.enabled = true;
            yield return new WaitForSecondsRealtime(3f);
            var skill = host.Rules.FindSkill("skill.warrior.iron_cut");
            var boss = arena.Boss;
            for (var i = 0; i < 4 && boss != null && !boss.Combatant.IsDead; i++)
            {
                var info = boss.Logic.Boss.Info;
                var p = boss.Combatant.Position;
                var behind = new PlanarVector(p.X - (float)info.FacingX * 3f, p.Z - (float)info.FacingZ * 3f);
                host.Combat.ApplySkillHit(hero.Combatant, boss.Combatant, skill, behind);
                yield return new WaitForSecondsRealtime(0.5f);
            }
            var bar = ScreenHost.Current != null ? ScreenHost.Current.Root.Q<VisualElement>("boss-bar") : null;
            Debug.Log("[BossShot] fase=" + arena.Phase + ", barra=" + (bar != null ? bar.style.display.value.ToString() : "ausente") + ", vida=" + boss.Combatant.Life + "/" + boss.Combatant.MaxLife);
            yield return new WaitForSecondsRealtime(0.5f);
            ScreenCapture.CaptureScreenshot(path);
            yield return new WaitForSecondsRealtime(1.5f);
            Debug.Log("[BossShot] captura pedida: " + path);
        }
    }
}
