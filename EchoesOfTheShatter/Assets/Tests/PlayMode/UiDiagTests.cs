using System.Collections;
using System.IO;
using System.Linq;
using System.Text;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using UnityEngine.UIElements;

namespace Echoes.Tests.PlayMode
{
    /// <summary>Diagnostico de UI no Refugio: cada UIDocument montou a arvore no painel e tem tamanho na tela?</summary>
    [Category("UiDiag")]
    public sealed class UiDiagTests
    {
        [UnityTest]
        public IEnumerator EveryUiDocumentHasItsPanelInTheRefuge()
        {
            var dir = Path.Combine(Path.GetTempPath(), "echoes_uidiag_" + System.Guid.NewGuid().ToString("N"));
            GameSession.Use(new SaveService(dir, new FakeGameClock(1_800_000_000)));
            Assert.IsTrue(NativeRulesCore.TryCreate(out var rules, out var reason), reason);
            using (rules)
            {
                rules.LoadContent(ContentPaths.ResolveDataDirectory(string.Empty), new System.Collections.Generic.List<RulesError>());
                GameSession.Save.NewGame(rules, 0, "Ui");
            }
            yield return SceneManager.LoadSceneAsync("Refugio", LoadSceneMode.Single);
            for (var i = 0; i < 10; i++) yield return null;
            var report = new StringBuilder();
            foreach (var doc in Object.FindObjectsByType<UIDocument>(FindObjectsSortMode.None))
            {
                var root = doc.rootVisualElement;
                report.AppendLine($"[UiDiag] {doc.name}: sort={doc.sortingOrder} panel={(root != null && root.panel != null)} children={(root != null ? root.childCount : -1)} bound={(root != null ? root.worldBound.ToString() : "-")} asset={(doc.visualTreeAsset != null ? doc.visualTreeAsset.name : "-")}");
                if (root != null && root.childCount > 0)
                {
                    var first = root.ElementAt(0);
                    report.AppendLine($"[UiDiag]    first={first.name} display={first.resolvedStyle.display} visible={first.resolvedStyle.visibility} bound={first.worldBound}");
                }
            }
            Debug.Log(report.ToString());
            foreach (var doc in Object.FindObjectsByType<UIDocument>(FindObjectsSortMode.None))
            {
                Assert.IsNotNull(doc.panelSettings, doc.name + ": PanelSettings ligado na cena (a referencia saia nula quando o asset era carregado antes de NewScene)");
                Assert.IsNotNull(doc.rootVisualElement.panel, doc.name + ": arvore montada no painel");
            }
        }
    }
}
