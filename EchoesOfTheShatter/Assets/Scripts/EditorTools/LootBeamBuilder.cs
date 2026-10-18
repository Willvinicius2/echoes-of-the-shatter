using System.Collections.Generic;
using System.IO;
using Echoes.Interop;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Gera o SO_LootBeam (Assets/Data/Presentation) dos tokens do docs/03 (<c>color.rarity.*</c> e <c>juice.loot_beam.*</c>) e os materiais do feixe
    /// (aditivo, sem sombra). Valores de apresentacao: nenhum numero de balanceamento. Idempotente.
    /// </summary>
    public static class LootBeamBuilder
    {
        public const string AssetPath = "Assets/Data/Presentation/SO_LootBeam.asset";

        public static LootBeamSettings CreateOrUpdate()
        {
            SandboxBuilder.EnsureDir(SandboxBuilder.DataDir);
            var so = AssetDatabase.LoadAssetAtPath<LootBeamSettings>(AssetPath);
            if (so == null)
            {
                so = ScriptableObject.CreateInstance<LootBeamSettings>();
                AssetDatabase.CreateAsset(so, AssetPath);
            }
            var tokensPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../../docs/arte/03_design_tokens.json"));
            var root = Echoes.Interop.MiniJson.AsObject(Echoes.Interop.MiniJson.Parse(File.ReadAllText(tokensPath)));
            var colors = Echoes.Interop.MiniJson.AsObject(Echoes.Interop.MiniJson.AsObject(root["color"])["rarity"]);
            var beams = Echoes.Interop.MiniJson.AsObject(Echoes.Interop.MiniJson.AsObject(root["juice"])["loot_beam"]);
            so.magic = Tier(colors, beams, "magic");
            so.rare = Tier(colors, beams, "rare");
            so.unique = Tier(colors, beams, "unique");
            so.beamMaterial = AdditiveMaterial("M_LootBeam", null);
            so.glowMaterial = AdditiveMaterial("M_LootGlow", SceneryBuilder.EnsureFlameMaterial().GetTexture("_BaseMap") as Texture2D);
            so.markerMaterial = MarkerMaterial();
            EditorUtility.SetDirty(so);
            AssetDatabase.SaveAssets();
            return AssetDatabase.LoadAssetAtPath<LootBeamSettings>(AssetPath);
        }

        static LootBeamSettings.Tier Tier(Dictionary<string, object> colors, Dictionary<string, object> beams, string name)
        {
            ColorUtility.TryParseHtmlString(Echoes.Interop.MiniJson.Str(colors, name, "#FFFFFF"), out var color);
            var o = Echoes.Interop.MiniJson.AsObject(beams.TryGetValue(name, out var v) ? v : null);
            return new LootBeamSettings.Tier
            {
                color = color,
                radiusMeters = (float)Echoes.Interop.MiniJson.Num(o, "radius_cm") / 100f,
                heightMeters = (float)Echoes.Interop.MiniJson.Num(o, "height_cm") / 100f,
                glowRadiusMeters = (float)Echoes.Interop.MiniJson.Num(o, "glow_radius_cm") / 100f,
                pulseSeconds = (float)Echoes.Interop.MiniJson.Num(o, "pulse_ms") / 1000f,
            };
        }

        static Material AdditiveMaterial(string name, Texture2D texture)
        {
            SandboxBuilder.EnsureDir(EnvironmentKit.MaterialDir);
            var path = $"{EnvironmentKit.MaterialDir}/{name}.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            if (texture != null) mat.SetTexture("_BaseMap", texture);
            mat.SetColor("_BaseColor", Color.white);
            mat.SetFloat("_Surface", 1f);
            mat.SetFloat("_Blend", 2f);
            mat.SetFloat("_SrcBlend", 5f);
            mat.SetFloat("_DstBlend", 1f);
            mat.SetFloat("_ZWrite", 0f);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)RenderQueue.Transparent;
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static Material MarkerMaterial()
        {
            var path = EnvironmentKit.MaterialDir + "/M_LootMarker.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", new Color(0.85f, 0.82f, 0.78f));
            mat.SetFloat("_Smoothness", 0.2f);
            EditorUtility.SetDirty(mat);
            return mat;
        }
    }
}
