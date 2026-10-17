using System.Collections.Generic;
using System.IO;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Barra de vida do chefe no topo da tela durante a luta da arena: nome, vida, marcas das fases (de boss_phases.csv: lifeThreshold de cada fase),
    /// a fase atual e o aviso "Guarda quebrada!" enquanto o escudo esta caido. So le o estado do core (BossInfo) e os eventos do chefe; nunca decide regra.
    /// </summary>
    [RequireComponent(typeof(ScreenHost))]
    public sealed class BossBarView : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [SerializeField] ArenaController arena;

        VisualElement panel, fill, markers;
        Label nameLabel, phaseLabel, guardLabel;
        bool built;
        readonly List<float> thresholds = new List<float>();
        bool subscribed;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (arena == null) arena = FindAnyObjectByType<ArenaController>();
            LoadThresholds();
            if (root != null && root.Events != null)
            {
                root.Events.Subscribe<BossStateEvent>(OnBossState);
                subscribed = true;
            }
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<BossStateEvent>(OnBossState);
        }

        // Marcas das fases: lifeThreshold das fases 2 em diante (boss_phases.csv, fonte da verdade).
        void LoadThresholds()
        {
            thresholds.Clear();
            var path = Path.Combine(ContentPaths.ResolveDataDirectory(string.Empty), "boss_phases.csv");
            if (!File.Exists(path)) return;
            var records = CsvReader.Parse(File.ReadAllText(path));
            for (var i = 1; i < records.Count; i++)
            {
                var f = records[i].Fields;
                if (f.Length > 2 && f[0] == "enemy.crypt_guardian" && f[1] != "1" && float.TryParse(f[2], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var t)) thresholds.Add(t);
            }
        }

        void OnBossState(in BossStateEvent evt)
        {
            if (!ReferenceEquals(arena != null && arena.Boss != null ? arena.Boss.Combatant : null, evt.Owner) || root == null) return;
            if (evt.Kind == BossEventKind.PhaseStart) ScreenHost.Toast(ScreenKit.Fmt(root.Localization, "ui.boss.phase_change", ("n", evt.Phase.ToString())));
            else if (evt.Kind == BossEventKind.ShieldDown) ScreenHost.Toast(root.Localization.Get("ui.boss.shield_down"));
            else if (evt.Kind == BossEventKind.SummonSpawn) ScreenHost.Toast(root.Localization.Get("ui.boss.summon_sentinels"));
        }

        void Build()
        {
            var host = ScreenHost.Current;
            if (host == null || host.Root == null) return;
            built = true;
            panel = new VisualElement { name = "boss-bar" };
            panel.style.position = Position.Absolute;
            panel.style.top = 90;
            panel.style.alignSelf = Align.Center;
            panel.style.left = new Length(25, LengthUnit.Percent);
            panel.style.right = new Length(25, LengthUnit.Percent);
            panel.style.display = DisplayStyle.None;
            panel.pickingMode = PickingMode.Ignore;
            var top = ScreenKit.Row(panel);
            nameLabel = ScreenKit.Line(top, root.Localization.Get("enemy.crypt_guardian.name"), 24, ScreenKit.Gold, true);
            phaseLabel = ScreenKit.Line(top, string.Empty, 20, ScreenKit.Muted);
            var track = new VisualElement();
            track.style.height = 18;
            track.style.backgroundColor = new Color(0.07f, 0.05f, 0.08f, 0.92f);
            track.style.borderTopWidth = track.style.borderBottomWidth = track.style.borderLeftWidth = track.style.borderRightWidth = 1;
            var edge = new Color(0.6f, 0.45f, 0.2f, 1f);
            track.style.borderTopColor = edge;
            track.style.borderBottomColor = edge;
            track.style.borderLeftColor = edge;
            track.style.borderRightColor = edge;
            fill = new VisualElement();
            fill.style.height = new Length(100, LengthUnit.Percent);
            fill.style.backgroundColor = new Color(0.72f, 0.16f, 0.14f, 1f);
            track.Add(fill);
            markers = new VisualElement();
            markers.style.position = Position.Absolute;
            markers.style.left = 0;
            markers.style.right = 0;
            markers.style.top = 0;
            markers.style.bottom = 0;
            markers.pickingMode = PickingMode.Ignore;
            foreach (var t in thresholds)
            {
                var mark = new VisualElement();
                mark.style.position = Position.Absolute;
                mark.style.left = new Length(t * 100f, LengthUnit.Percent);
                mark.style.width = 2;
                mark.style.top = 0;
                mark.style.bottom = 0;
                mark.style.backgroundColor = ScreenKit.Gold;
                markers.Add(mark);
            }
            track.Add(markers);
            panel.Add(track);
            guardLabel = ScreenKit.Line(panel, root.Localization.Get("ui.hud.guard_broken"), 22, ScreenKit.Bad, true);
            guardLabel.style.unityTextAlign = TextAnchor.MiddleCenter;
            guardLabel.style.display = DisplayStyle.None;
            host.Root.Add(panel);
        }

        void Update()
        {
            if (root == null || arena == null) return;
            if (!built) Build();
            if (!built) return;
            var boss = arena.Boss;
            var fighting = arena.Phase == ArenaPhase.Fighting && boss != null && boss.Combatant != null && !boss.Combatant.IsDead;
            panel.style.display = fighting ? DisplayStyle.Flex : DisplayStyle.None;
            if (!fighting) return;
            var maxLife = boss.Combatant.MaxLife;
            fill.style.width = new Length(maxLife > 0 ? (float)(boss.Combatant.Life / maxLife) * 100f : 0f, LengthUnit.Percent);
            var info = boss.Logic != null && boss.Logic.Boss != null ? boss.Logic.Boss.Info : default;
            phaseLabel.text = ScreenKit.Fmt(root.Localization, "ui.boss.phase_change", ("n", Mathf.Max(1, info.Phase).ToString()));
            guardLabel.style.display = info.ShieldDownRemaining > 0.0 || info.StaggerRemaining > 0.0 ? DisplayStyle.Flex : DisplayStyle.None;
        }
    }
}
