using System.Collections.Generic;
using Echoes.Interop;
using UnityEngine;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Números de dano numa única camada de tela cheia, com Labels em pool (64; tokens
    /// juice.damage_number), posicionados por <see cref="RuntimePanelUtils.CameraTransformWorldToPanel"/>
    /// (docs/tecnico/04_arquitetura.md, seção 3.11). Sobe 40 px em 700 ms e some nos últimos 200 ms; crítico
    /// pulsa a 120% por 120 ms. Golpes no mesmo alvo dentro de 100 ms somam num número.
    /// </summary>
    [UxmlElement]
    public partial class DamageNumberLayer : VisualElement
    {
        public const string UssClass = "damage-layer";
        public const string NumberClass = "damage-number";

        sealed class Entry
        {
            public Label Label;
            public object Target;
            public Vector3 World;
            public float Age;
            public float Jitter;
            public double Amount;
            public DamageNumberKind Kind;
            public bool Active;
        }

        static readonly string[] KindClasses =
        {
            "damage-number--normal", "damage-number--crit", "damage-number--taken", "damage-number--heal", "damage-number--muted",
        };

        static readonly string[] TypeClasses =
        {
            "damage-number--physical", "damage-number--fire", "damage-number--cold", "damage-number--lightning",
        };

        readonly List<Entry> entries = new List<Entry>(64);

        public int PoolSize { get; set; } = 64;
        public float RisePixels { get; set; } = 40f;
        public float LifeSeconds { get; set; } = 0.7f;
        public float FadeSeconds { get; set; } = 0.2f;
        public float CritHoldSeconds { get; set; } = 0.12f;
        public float CritScale { get; set; } = 1.2f;
        public float MergeWindowSeconds { get; set; } = 0.1f;
        public float CritJitterPixels { get; set; } = 24f;

        public DamageNumberLayer()
        {
            AddToClassList(UssClass);
            pickingMode = PickingMode.Ignore;
        }

        /// <summary>Mostra (ou soma) um número sobre <paramref name="world"/>. <paramref name="text"/> já vem formatado.</summary>
        public void Show(object target, Vector3 world, double amount, string text, DamageNumberKind kind, DamageType type)
        {
            EnsurePool();
            Entry entry = null;
            if (target != null && kind != DamageNumberKind.Muted)
            {
                for (var i = 0; i < entries.Count; i++)
                {
                    var e = entries[i];
                    if (e.Active && ReferenceEquals(e.Target, target) && e.Kind == kind && e.Age <= MergeWindowSeconds)
                    {
                        entry = e;
                        break;
                    }
                }
            }

            if (entry == null)
            {
                entry = Acquire();
                entry.Target = target;
                entry.Amount = 0.0;
                entry.Age = 0f;
                entry.Kind = kind;
                entry.Jitter = kind == DamageNumberKind.Critical ? Random.Range(-CritJitterPixels, CritJitterPixels) : 0f;
                for (var i = 0; i < KindClasses.Length; i++) entry.Label.EnableInClassList(KindClasses[i], i == (int)kind);
            }
            for (var i = 0; i < TypeClasses.Length; i++) entry.Label.EnableInClassList(TypeClasses[i], i == (int)type);
            entry.World = world;
            entry.Amount += amount;
            entry.Label.text = text;
            entry.Active = true;
            entry.Label.style.display = DisplayStyle.Flex;
        }

        /// <summary>Soma acumulada do número que está sendo mesclado (para reformatar o texto).</summary>
        public double PendingAmount(object target, DamageNumberKind kind)
        {
            for (var i = 0; i < entries.Count; i++)
            {
                var e = entries[i];
                if (e.Active && ReferenceEquals(e.Target, target) && e.Kind == kind && e.Age <= MergeWindowSeconds) return e.Amount;
            }
            return 0.0;
        }

        /// <summary>Avança a animação e reposiciona. Chamado pela tela uma vez por quadro.</summary>
        public void Tick(float deltaTime, Camera camera)
        {
            if (panel == null || camera == null) return;
            for (var i = 0; i < entries.Count; i++)
            {
                var e = entries[i];
                if (!e.Active) continue;
                e.Age += deltaTime;
                if (e.Age >= LifeSeconds)
                {
                    e.Active = false;
                    e.Target = null;
                    e.Label.style.display = DisplayStyle.None;
                    continue;
                }

                var p = RuntimePanelUtils.CameraTransformWorldToPanel(panel, e.World, camera);
                var hold = e.Kind == DamageNumberKind.Critical ? CritHoldSeconds : 0f;
                var riseT = Mathf.Clamp01((e.Age - hold) / Mathf.Max(0.01f, LifeSeconds - hold));
                var rise = RisePixels * (1f - (1f - riseT) * (1f - riseT) * (1f - riseT)); // ease-out cúbico
                var scale = e.Kind == DamageNumberKind.Critical && e.Age < hold ? CritScale : 1f;
                var fadeStart = LifeSeconds - FadeSeconds;
                var alpha = e.Age > fadeStart ? Mathf.Clamp01((LifeSeconds - e.Age) / FadeSeconds) : 1f;

                var style = e.Label.style;
                style.left = p.x + e.Jitter;
                style.top = p.y - rise;
                style.opacity = alpha;
                style.scale = new StyleScale(new Scale(new Vector3(scale, scale, 1f)));
            }
        }

        void EnsurePool()
        {
            if (entries.Count > 0) return;
            for (var i = 0; i < PoolSize; i++)
            {
                var label = new Label { pickingMode = PickingMode.Ignore };
                label.AddToClassList(NumberClass);
                label.style.display = DisplayStyle.None;
                Add(label);
                entries.Add(new Entry { Label = label });
            }
        }

        Entry Acquire()
        {
            Entry oldest = null;
            for (var i = 0; i < entries.Count; i++)
            {
                var e = entries[i];
                if (!e.Active) return e;
                if (oldest == null || e.Age > oldest.Age) oldest = e;
            }
            return oldest; // pool cheio: reaproveita o mais velho
        }
    }
}
