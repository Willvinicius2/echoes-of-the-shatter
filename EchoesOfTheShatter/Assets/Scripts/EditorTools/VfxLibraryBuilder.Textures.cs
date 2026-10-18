using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Texturas de efeito geradas por código (determinísticas, sem arte externa): máscaras em alfa sobre branco, usadas com cor de vértice e
    /// cor do material (HDR). Escritas como PNG em Assets/Art/VFX/Textures.
    /// </summary>
    public static partial class VfxLibraryBuilder
    {
        public const string TextureDir = "Assets/Art/VFX/Textures";

        static float Smooth(float a, float b, float x)
        {
            var t = Mathf.Clamp01((x - a) / (b - a));
            return t * t * (3f - 2f * t);
        }

        // Ruído de valor periódico (tileável) com fbm, para fumaça, chama e hexágonos.
        static float Hash(int x, int y, int seed)
        {
            unchecked
            {
                var h = x * 374761393 + y * 668265263 + seed * 1274126177;
                h = (h ^ (h >> 13)) * 1274126177;
                h ^= h >> 16;
                return (h & 0xFFFFFF) / (float)0xFFFFFF;
            }
        }

        static float ValueNoise(float x, float y, int period, int seed)
        {
            var xi = Mathf.FloorToInt(x);
            var yi = Mathf.FloorToInt(y);
            var fx = x - xi;
            var fy = y - yi;
            fx = fx * fx * (3f - 2f * fx);
            fy = fy * fy * (3f - 2f * fy);
            float V(int ix, int iy) => Hash(((ix % period) + period) % period, ((iy % period) + period) % period, seed);
            var a = Mathf.Lerp(V(xi, yi), V(xi + 1, yi), fx);
            var b = Mathf.Lerp(V(xi, yi + 1), V(xi + 1, yi + 1), fx);
            return Mathf.Lerp(a, b, fy);
        }

        static float Fbm(float u, float v, int baseCells, int seed)
        {
            var sum = 0f;
            var amp = 0.5f;
            var cells = baseCells;
            for (var o = 0; o < 4; o++)
            {
                sum += amp * ValueNoise(u * cells, v * cells, cells, seed + o);
                amp *= 0.5f;
                cells *= 2;
            }
            return sum;
        }

        static Texture2D GenerateTexture(string name, int width, int height, Func<float, float, Color> pixel, bool srgb = true, TextureWrapMode wrap = TextureWrapMode.Clamp)
        {
            var path = $"{TextureDir}/{name}.png";
            var tex = new Texture2D(width, height, TextureFormat.RGBA32, false);
            var pixels = new Color32[width * height];
            for (var y = 0; y < height; y++)
            {
                for (var x = 0; x < width; x++)
                {
                    pixels[y * width + x] = pixel((x + 0.5f) / width, (y + 0.5f) / height);
                }
            }
            tex.SetPixels32(pixels);
            File.WriteAllBytes(path, tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = TextureImporterType.Default;
            importer.sRGBTexture = srgb;
            importer.alphaSource = TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = false;
            importer.mipmapEnabled = true;
            importer.wrapMode = wrap;
            importer.filterMode = FilterMode.Bilinear;
            importer.maxTextureSize = 512;
            importer.textureCompression = TextureImporterCompression.Uncompressed; // pequenas: sem blocos nos degradês do fogo
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static Color White(float a) => new Color(1f, 1f, 1f, Mathf.Clamp01(a));

        static Texture2D TexSoft() => GenerateTexture("T_VFX_Soft", 128, 128, (u, v) =>
        {
            var r = Mathf.Sqrt((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 2f;
            return White(Mathf.Pow(1f - Smooth(0f, 1f, r), 1.7f));
        });

        static Texture2D TexCore() => GenerateTexture("T_VFX_Core", 128, 128, (u, v) =>
        {
            var r = Mathf.Sqrt((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 2f;
            return White(Mathf.Exp(-r * r * 9f) * (1f - Smooth(0.85f, 1f, r)));
        });

        // Anel fino e nítido (borda do círculo de marcação, onda de choque).
        static Texture2D TexRing() => GenerateTexture("T_VFX_Ring", 256, 256, (u, v) =>
        {
            var r = Mathf.Sqrt((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 2f;
            var edge = 1f - Smooth(0f, 0.05f, Mathf.Abs(r - 0.93f));
            var inner = 0.1f * Smooth(0.2f, 0.93f, r) * (1f - Smooth(0.93f, 0.97f, r));
            return White(edge + inner);
        });

        // Anel largo com brilho forte na borda de fora e cauda para dentro (onda que se espalha).
        static Texture2D TexRingSoft() => GenerateTexture("T_VFX_RingSoft", 256, 256, (u, v) =>
        {
            var r = Mathf.Sqrt((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 2f;
            var outer = 1f - Smooth(0.9f, 1f, r);
            var body = Mathf.Pow(Smooth(0.35f, 0.92f, r), 2.2f);
            return White(outer * body);
        });

        static Texture2D TexStar4() => GenerateTexture("T_VFX_Star4", 128, 128, (u, v) =>
        {
            var x = Mathf.Abs(u - 0.5f) * 2f;
            var y = Mathf.Abs(v - 0.5f) * 2f;
            var a = Mathf.Exp(-x * 26f) * Mathf.Exp(-y * 2.4f) + Mathf.Exp(-y * 26f) * Mathf.Exp(-x * 2.4f);
            var core = Mathf.Exp(-(x * x + y * y) * 40f);
            return White(Mathf.Max(a, core));
        });

        static Texture2D TexStar6() => GenerateTexture("T_VFX_Star6", 256, 256, (u, v) =>
        {
            var x = (u - 0.5f) * 2f;
            var y = (v - 0.5f) * 2f;
            var a = 0f;
            for (var k = 0; k < 3; k++)
            {
                var ang = k * Mathf.PI / 3f;
                var along = x * Mathf.Cos(ang) + y * Mathf.Sin(ang);
                var across = -x * Mathf.Sin(ang) + y * Mathf.Cos(ang);
                a = Mathf.Max(a, Mathf.Exp(-Mathf.Abs(across) * 34f) * Mathf.Exp(-Mathf.Abs(along) * 1.8f));
            }
            var core = Mathf.Exp(-(x * x + y * y) * 30f);
            return White(Mathf.Max(a, core) * (1f - Smooth(0.85f, 1f, Mathf.Sqrt(x * x + y * y))));
        });

        // Faísca esticada: capsula horizontal brilhante no meio.
        static Texture2D TexStreak() => GenerateTexture("T_VFX_Streak", 128, 32, (u, v) =>
        {
            var across = 1f - Mathf.Abs(v - 0.5f) * 2f;
            var along = Mathf.Sin(u * Mathf.PI);
            return White(Mathf.Pow(across, 2.2f) * Mathf.Pow(along, 0.8f));
        });

        // Fumaça: fbm mascarado por queda radial.
        static Texture2D TexSmoke() => GenerateTexture("T_VFX_Smoke", 128, 128, (u, v) =>
        {
            var r = Mathf.Sqrt((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 2f;
            var n = Fbm(u, v, 4, 11);
            var a = Mathf.Clamp01((n * 1.7f - 0.35f) * (1f - Smooth(0.35f, 1f, r)));
            return White(a);
        }, true, TextureWrapMode.Clamp);

        // Chama: gota com a ponta para cima (v), borda desfeita por ruído.
        static Texture2D TexFlame() => GenerateTexture("T_VFX_Flame", 128, 128, (u, v) =>
        {
            var x = (u - 0.5f) * 2f;
            var halfWidth = 0.62f * Mathf.Pow(Mathf.Clamp01(1f - v), 0.75f) * (0.55f + 0.45f * Smooth(0f, 0.25f, v));
            var wobble = (Fbm(u, v, 4, 21) - 0.5f) * 0.45f * v;
            var d = Mathf.Abs(x + wobble) / Mathf.Max(0.0001f, halfWidth);
            var body = 1f - Smooth(0.45f, 1f, d);
            var tip = 1f - Smooth(0.78f, 1f, v);
            var heat = Mathf.Lerp(0.55f, 1f, 1f - v);
            return White(body * tip * heat);
        });

        // Atlas 2 x 2 de nuvens de fogo/fumaça: 4 variações suaves (borda irregular por ruído com deformação, miolo mais denso). Cada partícula
        // sorteia uma célula (TextureSheetAnimation), então a explosão não repete a mesma mancha. Substitui a gota de chama de borda dura.
        static Texture2D TexFirePuff() => GenerateTexture("T_VFX_FirePuff", 256, 256, (u, v) =>
        {
            var cx = u < 0.5f ? 0 : 1;
            var cy = v < 0.5f ? 0 : 1;
            var lu = (u - 0.5f * cx) * 2f;
            var lv = (v - 0.5f * cy) * 2f;
            var seed = 100 + cx * 7 + cy * 13;
            var x = (lu - 0.5f) * 2f;
            var y = (lv - 0.5f) * 2f;
            var r = Mathf.Sqrt(x * x + y * y);
            var n = Fbm(lu, lv, 3, seed) - 0.5f;
            var w = Fbm(lu + 0.37f, lv + 0.61f, 2, seed + 9) - 0.5f;
            var rr = r + n * 0.9f + w * 0.35f;
            var body = Mathf.Pow(1f - Smooth(0.12f, 0.95f, rr), 1.2f);
            var edge = 1f - Smooth(0.8f, 1f, r);
            return White(body * edge);
        });

        // Faixa do arco de lâmina: u corre pelo arco, v vai do raio de dentro (0) ao de fora (1). Borda de fora nítida e brilhante, corpo que
        // esmaece para dentro com listras de movimento: lê como "corte", não como setor de círculo cheio.
        static Texture2D TexSwipe() => GenerateTexture("T_VFX_Swipe", 128, 64, (u, v) =>
        {
            var rim = Mathf.Exp(-Mathf.Pow((v - 0.92f) / 0.045f, 2f));
            var body = Mathf.Pow(Smooth(0.2f, 0.93f, v), 2.6f) * (1f - Smooth(0.95f, 1f, v));
            var streak = 0.78f + 0.22f * ValueNoise(u * 18f, v * 2f, 18, 77);
            return White(Mathf.Clamp01((body * 0.7f + rim) * streak));
        });

        // Placa do rastro da lâmina: u = vida (1 recente), v = 0 cabo, 1 ponta. A ponta é viva e a cauda esfumaça em listras de movimento.
        static Texture2D TexSlash(string name, bool gold) => GenerateTexture(name, 256, 64, (u, v) =>
        {
            var tipBias = Mathf.Pow(Smooth(0f, 1f, v), 1.35f);
            var edge = Smooth(0f, 0.12f, v) * (1f - Smooth(0.96f, 1f, v));
            var streaks = 0.75f + 0.25f * ValueNoise(u * 24f, v * 3f, 24, 31);
            var life = Smooth(0f, 0.2f, u);
            var a = tipBias * edge * streaks * life;
            if (gold) a = Mathf.Max(a, Mathf.Exp(-Mathf.Abs(v - 0.9f) * 38f) * life);
            return White(a);
        });

        static Texture2D TexScorch() => GenerateTexture("T_VFX_Scorch", 256, 256, (u, v) =>
        {
            var x = (u - 0.5f) * 2f;
            var y = (v - 0.5f) * 2f;
            var r = Mathf.Sqrt(x * x + y * y);
            var ang = Mathf.Atan2(y, x);
            var ragged = 0.62f + 0.22f * ValueNoise((Mathf.Cos(ang) + 1f) * 3f, (Mathf.Sin(ang) + 1f) * 3f, 8, 41) + 0.12f * (Fbm(u, v, 6, 43) - 0.5f);
            var body = 1f - Smooth(ragged - 0.2f, ragged, r);
            var crack = Fbm(u * 1.2f, v * 1.2f, 8, 47);
            var a = body * Mathf.Lerp(0.55f, 0.95f, crack);
            return new Color(0.06f, 0.04f, 0.035f, Mathf.Clamp01(a));
        });

        // Malha de hexágonos tileável (4 repetições): a técnica clássica dos dois centros por célula retangular 1 x sqrt(3).
        static Texture2D TexHex() => GenerateTexture("T_VFX_Hex", 256, 256, (u, v) =>
        {
            const float s3 = 1.7320508f;
            var px = u * 4f;
            var py = v * 4f * s3;
            var ax = Mathf.Repeat(px, 1f) - 0.5f;
            var ay = Mathf.Repeat(py, s3) - s3 * 0.5f;
            var bx = Mathf.Repeat(px - 0.5f, 1f) - 0.5f;
            var by = Mathf.Repeat(py - s3 * 0.5f, s3) - s3 * 0.5f;
            var gx = ax * ax + ay * ay < bx * bx + by * by ? ax : bx;
            var gy = ax * ax + ay * ay < bx * bx + by * by ? ay : by;
            var qx = Mathf.Abs(gx);
            var qy = Mathf.Abs(gy);
            var c = Mathf.Max(qx * 0.5f + qy * 0.8660254f, qx); // distância hexagonal ao centro (0,5 na borda)
            var line = 1f - Smooth(0f, 0.07f, 0.5f - c);
            var fill = 0.10f * Fbm(u, v, 4, 51);
            return White(line + fill);
        }, true, TextureWrapMode.Repeat);

        static Texture2D TexBeam() => GenerateTexture("T_VFX_Beam", 64, 128, (u, v) =>
        {
            // u atravessa a largura (gauss), v corre pelo comprimento (leve tremor).
            var across = Mathf.Exp(-Mathf.Pow((u - 0.5f) * 2f, 2f) * 5f);
            var flicker = 0.85f + 0.15f * ValueNoise(v * 12f, u * 2f, 12, 61);
            var ends = Smooth(0f, 0.04f, v) * (1f - Smooth(0.9f, 1f, v));
            return White(across * flicker * ends);
        });

        static Texture2D TexRune() => GenerateTexture("T_VFX_Rune", 256, 256, (u, v) =>
        {
            var x = (u - 0.5f) * 2f;
            var y = (v - 0.5f) * 2f;
            var r = Mathf.Sqrt(x * x + y * y);
            var ang = Mathf.Atan2(y, x);
            var outer = 1f - Smooth(0f, 0.035f, Mathf.Abs(r - 0.94f));
            var inner = 0.65f * (1f - Smooth(0f, 0.025f, Mathf.Abs(r - 0.78f)));
            // 12 marcas entre os dois anéis
            var tick = Mathf.Pow(Mathf.Max(0f, Mathf.Cos(ang * 12f)), 24f) * Smooth(0.78f, 0.82f, r) * (1f - Smooth(0.9f, 0.94f, r));
            var disc = 0.07f * (1f - Smooth(0.5f, 0.94f, r));
            return White(outer + inner + tick * 0.8f + disc);
        });

        // Fita de rastro: u corre pelo comprimento (uniforme), v atravessa a largura (gauss).
        static Texture2D TexTrail() => GenerateTexture("T_VFX_Trail", 64, 32, (u, v) =>
        {
            var across = Mathf.Exp(-Mathf.Pow((v - 0.5f) * 2f, 2f) * 3.2f);
            return White(across);
        });

        static Texture2D TexNoise() => GenerateTexture("T_VFX_Noise", 128, 128, (u, v) => White(Fbm(u, v, 4, 71)), true, TextureWrapMode.Repeat);

        static Texture2D TexSpark() => GenerateTexture("T_VFX_Spark", 64, 64, (u, v) =>
        {
            var r = Mathf.Sqrt((u - 0.5f) * (u - 0.5f) + (v - 0.5f) * (v - 0.5f)) * 2f;
            return White(Mathf.Exp(-r * r * 14f));
        });
    }
}
