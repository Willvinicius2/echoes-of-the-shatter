using System.Collections;
using System.IO;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Echoes.Tests.PlayMode
{
    /// <summary>
    /// A vitrine de VFX pelo caminho real (SkillPhaseEvent, ProjectileSystem, ApplySkillHit, presenters do jogo): a Bola de Fogo, a flecha e o
    /// golpe do Guerreiro tocam efeitos, ficam dentro do orcamento de luzes e geram os quadros.
    /// </summary>
    [Category("Vfx")]
    public sealed class VfxShowcasePlayTests
    {
        const string ScenePath = "Assets/Scenes/Sandbox/VfxShowcase.unity";

        [UnityTest]
        public IEnumerator SkillsPlayTheirEffectsThroughTheRealPath()
        {
#if UNITY_EDITOR
            yield return UnityEditor.SceneManagement.EditorSceneManager.LoadSceneAsyncInPlayMode(ScenePath, new LoadSceneParameters(LoadSceneMode.Single));
#else
            yield return SceneManager.LoadSceneAsync("VfxShowcase", LoadSceneMode.Single);
#endif
            yield return null;
            var show = Object.FindFirstObjectByType<VfxShowcase>();
            Assert.IsNotNull(show, "cena da vitrine");
            var folder = Path.Combine(Path.GetTempPath(), "echoes_vfxshow_test_" + System.Guid.NewGuid().ToString("N"));
            try
            {
                yield return show.RunScript(folder, "mago_bola_de_fogo,arqueiro_disparo_reto,guerreiro_corte_de_ferro", "perto");
                Assert.IsNull(show.Failure, show.Failure);
                foreach (var id in new[] { "mago_bola_de_fogo_perto", "arqueiro_disparo_reto_perto", "guerreiro_corte_de_ferro_perto" })
                {
                    var frames = Path.Combine(folder, "frames", id);
                    Assert.IsTrue(Directory.Exists(frames), id + ": pasta de quadros");
                    Assert.Greater(Directory.GetFiles(frames, "*.jpg").Length, 20, id + ": quadros gravados");
                }
                var marks = File.ReadAllText(Path.Combine(folder, "marks.txt"));
                StringAssert.Contains("mago_bola_de_fogo_perto\texplosao", marks, "a bola de fogo explodiu onde acabou");
                StringAssert.Contains("arqueiro_disparo_reto_perto\tacerto", marks, "a flecha acertou o boneco");
                StringAssert.Contains("guerreiro_corte_de_ferro_perto\tacerto", marks, "o golpe acertou");
                Assert.LessOrEqual(show.PeakLights, 2, "orcamento de luzes de VFX");
            }
            finally
            {
                Time.captureFramerate = 0;
                if (Directory.Exists(folder)) Directory.Delete(folder, true);
            }
        }
    }
}
