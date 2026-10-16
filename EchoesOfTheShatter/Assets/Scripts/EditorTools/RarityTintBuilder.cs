using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Gera o SO_RarityTint a partir dos tokens <c>art3d.rarity_tint</c> do docs/03_design_tokens.json (nenhum valor copiado a mão).
    /// Menu: Echoes ▸ Criar SO_RarityTint (idempotente: atualiza o asset pelo mesmo caminho).
    /// </summary>
    public static class RarityTintBuilder
    {
        public const string AssetPath = "Assets/Data/Presentation/SO_RarityTint.asset";

        public static string TokensPath => Path.GetFullPath(Path.Combine(Application.dataPath, "../../docs/03_design_tokens.json"));

        [MenuItem("Echoes/Criar SO_RarityTint")]
        public static RarityTintAsset CreateOrUpdate()
        {
            SandboxBuilder.EnsureDir(SandboxBuilder.DataDir);
            var asset = SandboxBuilder.LoadOrCreate<RarityTintAsset>(AssetPath);
            Fill(asset, ReadTokens());
            EditorUtility.SetDirty(asset);
            AssetDatabase.SaveAssets();
            return asset;
        }

        public static Dictionary<string, object> ReadTokens()
        {
            var root = MiniJson.Parse(File.ReadAllText(TokensPath)) as Dictionary<string, object>;
            var art = root["art3d"] as Dictionary<string, object>;
            return art["rarity_tint"] as Dictionary<string, object>;
        }

        public static void Fill(RarityTintAsset asset, Dictionary<string, object> tokens)
        {
            asset.normal = Entry(tokens, "normal");
            asset.magic = Entry(tokens, "magic");
            asset.rare = Entry(tokens, "rare");
            asset.unique = Entry(tokens, "unique");
        }

        static RarityTintAsset.Entry Entry(Dictionary<string, object> tokens, string key)
        {
            var o = (Dictionary<string, object>)tokens[key];
            var e = new RarityTintAsset.Entry
            {
                tintColor = HexColor(o, "tint_color", UnityEngine.Color.white),
                tintStrength = Num(o, "tint_strength", 0f),
                tintDesat = Num(o, "tint_desat", 0f),
                tintGain = Num(o, "tint_gain", 1f),
                rimTint = HexColor(o, "rim_tint", UnityEngine.Color.white),
                rimTintMix = Num(o, "rim_tint_mix", 0f),
                rimIntensity = Num(o, "rim_intensity", 0.5f),
                accentEmissive = Num(o, "accent_emissive", 0f),
                accentColor = HexColor(o, "accent_color", UnityEngine.Color.white),
            };
            if (key == "unique")
            {
                e.pulse = true;
                e.pulsePeriodSeconds = Num(o, "pulse_ms", 2400f) / 1000f;
                e.pulseVariation = Num(o, "pulse_variation", 0.2f);
            }
            return e;
        }

        static float Num(Dictionary<string, object> o, string key, float fallback)
        {
            return o.TryGetValue(key, out var v) && v is double d ? (float)d : fallback;
        }

        static Color HexColor(Dictionary<string, object> o, string key, Color fallback)
        {
            if (o.TryGetValue(key, out var v) && v is string hex && ColorUtility.TryParseHtmlString(hex, out var c)) return c;
            return fallback;
        }
    }
}
