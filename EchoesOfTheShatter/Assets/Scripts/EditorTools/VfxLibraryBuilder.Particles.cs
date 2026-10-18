using System;
using System.Collections.Generic;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.EditorTools
{
    /// <summary>Pequena DSL para montar Particle Systems por código (um "layer" = um sistema), cores em gradiente e curvas.</summary>
    public static partial class VfxLibraryBuilder
    {
        // ------------------------------------------------------------------------------------------------ paleta (docs/03 seção 2.4)

        static Color Hex(string html)
        {
            ColorUtility.TryParseHtmlString(html, out var color);
            return color;
        }

        static readonly Color FireCore = Hex("#FFE2B0"), FireMid = Hex("#F2642C"), FireEdge = Hex("#B8361A");
        static readonly Color IceCore = Hex("#D8F6FF"), IceMid = Hex("#4FA8E8"), IceEdge = Hex("#2B4F92");
        static readonly Color BoltCore = Hex("#F2F6FF"), BoltMid = Hex("#7FA8FF"), BoltEdge = Hex("#3A4FB8");
        static readonly Color AcidCore = Hex("#E6FF8A"), AcidMid = Hex("#8FD43A"), AcidEdge = Hex("#3E7A1E");
        static readonly Color ShadowCore = Hex("#F0D0FF"), ShadowMid = Hex("#9A4BD6"), ShadowEdge = Hex("#3E1766");
        static readonly Color GoldCore = Hex("#FFF2A8"), GoldMid = Hex("#F2B23A"), GoldEdge = Hex("#8F5A12");
        static readonly Color PhysCore = Color.white, PhysMid = Hex("#E8E0D4"), PhysEdge = Hex("#8A7F78");
        static readonly Color SparkYellow = Hex("#FFE066"), ChargeGold = Hex("#FCD58A");
        // Ameaça (docs/03 seção 2.4): núcleo menos branco, borda quase preta e a faixa vermelha.
        static readonly Color ThreatShadowCore = Hex("#E58AD8"), ThreatShadowMid = Hex("#8C3A9E"), ThreatShadowEdge = Hex("#2A0F3A"), ThreatRed = Hex("#E0301E");

        static Gradient Ramp(Color core, Color mid, Color edge, float peak = 1f, float fadeIn = 0.08f, float holdUntil = 0.55f)
        {
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(core, 0f), new GradientColorKey(mid, 0.4f), new GradientColorKey(edge, 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(peak, fadeIn), new GradientAlphaKey(peak * 0.75f, holdUntil), new GradientAlphaKey(0f, 1f) });
            return g;
        }

        static Gradient Flat(Color color, float peak = 1f, float fadeIn = 0.1f, float fadeOutStart = 0.6f)
        {
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(color, 0f), new GradientColorKey(color, 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(peak, fadeIn), new GradientAlphaKey(peak, fadeOutStart), new GradientAlphaKey(0f, 1f) });
            return g;
        }

        // Cor estática com o alfa cheio já no início (partículas de um disparo só, sem fade-in).
        static Gradient Snap(Color core, Color edge, float peak = 1f, float fadeStart = 0.35f)
        {
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(core, 0f), new GradientColorKey(edge, 1f) },
                new[] { new GradientAlphaKey(peak, 0f), new GradientAlphaKey(peak, fadeStart), new GradientAlphaKey(0f, 1f) });
            return g;
        }

        static AnimationCurve Curve(params float[] timeValuePairs)
        {
            var keys = new Keyframe[timeValuePairs.Length / 2];
            for (var i = 0; i < keys.Length; i++) keys[i] = new Keyframe(timeValuePairs[i * 2], timeValuePairs[i * 2 + 1]);
            var curve = new AnimationCurve(keys);
            for (var i = 0; i < keys.Length; i++) curve.SmoothTangents(i, 0f);
            return curve;
        }

        static Vector2 R(float a) => new Vector2(a, a);
        static Vector2 R(float a, float b) => new Vector2(a, b);

        sealed class Layer
        {
            public string Name = "Layer";
            public Material Mat;
            public float Duration = 1f;
            public bool Loop;
            public float Delay;
            public bool World;
            public Vector2 Life = R(1f);
            public Vector2 Speed = R(0f);
            public Vector2 Size = R(0.2f);
            public Vector2 StartRotation = R(0f);   // graus
            public float RotationSpeed;             // graus por segundo (aleatório +/-)
            public float Gravity;
            public float Drag;
            public int Max = 64;
            public Gradient Grad;
            public AnimationCurve SizeCurve;
            public float Rate;
            public (float time, int min, int max)[] Bursts;
            public ParticleSystemShapeType Shape = ParticleSystemShapeType.Sphere;
            public float Radius = 0.01f;
            public float RadiusThickness = 1f;
            public float Angle = 25f;
            public float Arc = 360f;
            public Vector3 Position;
            public Vector3 ShapeRotation;
            public Vector3 ShapeScale = Vector3.one;
            public bool RandomDirection;
            public ParticleSystemRenderMode Render = ParticleSystemRenderMode.Billboard;
            public float LengthScale = 2f;
            public float VelocityScale;
            public Mesh Mesh;
            public bool AlignToVelocity;
            public int SortingFudge;
            public float NoiseStrength;
            public float NoiseFrequency = 0.8f;
            public Vector3 StartRotation3DMin, StartRotation3DMax;
            public bool UseRotation3D;
            [Tooltip("Atlas N x N: cada partícula sorteia uma célula (sem animar).")]
            public int SheetTiles;

            public ParticleSystem Build(Transform parent)
            {
                var go = new GameObject(Name);
                go.transform.SetParent(parent, false);
                var ps = go.AddComponent<ParticleSystem>();
                ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);

                var main = ps.main;
                main.playOnAwake = false;
                main.duration = Duration;
                main.loop = Loop;
                main.startDelay = Delay;
                main.simulationSpace = World ? ParticleSystemSimulationSpace.World : ParticleSystemSimulationSpace.Local;
                main.scalingMode = ParticleSystemScalingMode.Hierarchy;
                main.startLifetime = new ParticleSystem.MinMaxCurve(Life.x, Life.y);
                main.startSpeed = new ParticleSystem.MinMaxCurve(Speed.x, Speed.y);
                main.startSize = new ParticleSystem.MinMaxCurve(Size.x, Size.y);
                if (UseRotation3D)
                {
                    main.startRotation3D = true;
                    main.startRotationX = new ParticleSystem.MinMaxCurve(StartRotation3DMin.x * Mathf.Deg2Rad, StartRotation3DMax.x * Mathf.Deg2Rad);
                    main.startRotationY = new ParticleSystem.MinMaxCurve(StartRotation3DMin.y * Mathf.Deg2Rad, StartRotation3DMax.y * Mathf.Deg2Rad);
                    main.startRotationZ = new ParticleSystem.MinMaxCurve(StartRotation3DMin.z * Mathf.Deg2Rad, StartRotation3DMax.z * Mathf.Deg2Rad);
                }
                else
                {
                    main.startRotation = new ParticleSystem.MinMaxCurve(StartRotation.x * Mathf.Deg2Rad, StartRotation.y * Mathf.Deg2Rad);
                }
                main.startColor = Color.white;
                main.gravityModifier = Gravity;
                main.maxParticles = Max;

                var emission = ps.emission;
                emission.enabled = true;
                emission.rateOverTime = Rate;
                if (Bursts != null)
                {
                    var bursts = new ParticleSystem.Burst[Bursts.Length];
                    for (var i = 0; i < Bursts.Length; i++) bursts[i] = new ParticleSystem.Burst(Bursts[i].time, (short)Bursts[i].min, (short)Bursts[i].max);
                    emission.SetBursts(bursts);
                }

                var shape = ps.shape;
                shape.enabled = true;
                shape.shapeType = Shape;
                shape.radius = Radius;
                shape.radiusThickness = RadiusThickness;
                shape.angle = Angle;
                shape.arc = Arc;
                shape.position = Position;
                shape.rotation = ShapeRotation;
                shape.scale = ShapeScale;
                shape.randomDirectionAmount = RandomDirection ? 1f : 0f;

                if (Grad != null)
                {
                    var col = ps.colorOverLifetime;
                    col.enabled = true;
                    col.color = Grad;
                }
                if (SizeCurve != null)
                {
                    var size = ps.sizeOverLifetime;
                    size.enabled = true;
                    size.size = new ParticleSystem.MinMaxCurve(1f, SizeCurve);
                }
                if (RotationSpeed != 0f)
                {
                    var rot = ps.rotationOverLifetime;
                    rot.enabled = true;
                    rot.z = new ParticleSystem.MinMaxCurve(-RotationSpeed * Mathf.Deg2Rad, RotationSpeed * Mathf.Deg2Rad);
                }
                if (Drag > 0f)
                {
                    var limit = ps.limitVelocityOverLifetime;
                    limit.enabled = true;
                    limit.dampen = 0f;
                    limit.limit = 1000f;
                    limit.drag = Drag;
                }
                if (NoiseStrength > 0f)
                {
                    var noise = ps.noise;
                    noise.enabled = true;
                    noise.strength = NoiseStrength;
                    noise.frequency = NoiseFrequency;
                    noise.quality = ParticleSystemNoiseQuality.Low;
                }

                if (SheetTiles > 1)
                {
                    var sheet = ps.textureSheetAnimation;
                    sheet.enabled = true;
                    sheet.mode = ParticleSystemAnimationMode.Grid;
                    sheet.numTilesX = SheetTiles;
                    sheet.numTilesY = SheetTiles;
                    sheet.animation = ParticleSystemAnimationType.WholeSheet;
                    sheet.frameOverTime = new ParticleSystem.MinMaxCurve(0f);
                    sheet.startFrame = new ParticleSystem.MinMaxCurve(0f, 0.999f);
                    sheet.cycleCount = 1;
                }

                var renderer = go.GetComponent<ParticleSystemRenderer>();
                renderer.renderMode = Render;
                renderer.lengthScale = LengthScale;
                renderer.velocityScale = VelocityScale;
                renderer.sharedMaterial = Mat;
                renderer.shadowCastingMode = ShadowCastingMode.Off;
                renderer.receiveShadows = false;
                renderer.lightProbeUsage = LightProbeUsage.Off;
                renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
                renderer.sortingFudge = SortingFudge;
                renderer.maxParticleSize = 5f;
                if (Render == ParticleSystemRenderMode.Mesh)
                {
                    renderer.mesh = Mesh;
                    renderer.alignment = AlignToVelocity ? ParticleSystemRenderSpace.Velocity : ParticleSystemRenderSpace.Local;
                    renderer.enableGPUInstancing = true;
                }
                return ps;
            }
        }

        // ------------------------------------------------------------------------------------------------ peças soltas

        static GameObject Child(GameObject parent, string name, Vector3 localPosition)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent.transform, false);
            go.transform.localPosition = localPosition;
            return go;
        }

        static void AddLight(GameObject go, Color color, float range, float peak, float seconds, AnimationCurve curve, float flicker)
        {
            var light = go.AddComponent<Light>();
            light.type = LightType.Point;
            light.color = color;
            light.range = range;
            light.intensity = 0f;
            light.shadows = LightShadows.None;
            light.renderMode = LightRenderMode.ForcePixel;
            var vfx = go.AddComponent<VfxLight>();
            vfx.Configure(peak, seconds, curve, flicker);
        }

        static TrailRenderer AddTrail(GameObject go, Material mat, float seconds, float widthStart, Gradient color)
        {
            var trail = go.AddComponent<TrailRenderer>();
            trail.sharedMaterial = mat;
            trail.time = seconds;
            trail.widthCurve = Curve(0f, 1f, 1f, 0f);
            trail.widthMultiplier = widthStart;
            trail.colorGradient = color;
            trail.alignment = LineAlignment.View;
            trail.textureMode = LineTextureMode.Stretch;
            trail.minVertexDistance = 0.05f;
            trail.numCapVertices = 2;
            trail.shadowCastingMode = ShadowCastingMode.Off;
            trail.receiveShadows = false;
            return trail;
        }

        static Gradient TrailGradient(Color head, Color tail, float alpha)
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(head, 0f), new GradientColorKey(tail, 1f) },
                new[] { new GradientAlphaKey(alpha, 0f), new GradientAlphaKey(0f, 1f) });
            return g;
        }

        static GameObject MeshObject(GameObject parent, string name, Mesh mesh, Material mat, Vector3 localPosition, Vector3 localScale)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent.transform, false);
            go.transform.localPosition = localPosition;
            go.transform.localScale = localScale;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.AddComponent<MeshRenderer>();
            renderer.sharedMaterial = mat;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.lightProbeUsage = LightProbeUsage.Off;
            return go;
        }

        static GameObject SavePrefab(string name, Action<GameObject> build)
        {
            var path = $"{PrefabDir}/{name}.prefab";
            var root = new GameObject(name);
            try
            {
                build(root);
                return PrefabUtility.SaveAsPrefabAsset(root, path);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }
    }
}
