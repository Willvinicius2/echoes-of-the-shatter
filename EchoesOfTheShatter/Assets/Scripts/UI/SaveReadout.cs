using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;

namespace Echoes.UI
{
    /// <summary>
    /// Leitura do save para a HUD e o inventario: nivel, XP, Ouro, Lascas e Cargas do Marco. So le (XP, nivel e Ouro sao do core); nada aqui calcula
    /// regra. Nivel e XP vem de <c>shatter_character_progress</c> (nivel do save, XP dentro do nivel e o total do nivel); moedas, do bloco
    /// <c>currencies</c> do JSON do save (ids de loot_entries.csv).
    /// </summary>
    public static class SaveReadout
    {
        public const string GoldId = "currency.gold";
        public const string ShardsId = "material.shards";

        public readonly struct Snapshot
        {
            public readonly bool Valid;
            public readonly int Level, Charges;
            /// <summary>XP dentro do nivel atual e o XP que o nivel pede (0 no teto de nivel da area).</summary>
            public readonly double XpInLevel, XpToNext;
            public readonly long Gold, Shards;
            /// <summary>Frascos de Recarga que o jogador leva e o maximo (vendor_stock.csv, carryCap).</summary>
            public readonly int Flasks, FlaskCap;

            public Snapshot(int level, double xpInLevel, double xpToNext, long gold, long shards, int charges, int flasks = 0, int flaskCap = 0)
            {
                Valid = true;
                Level = level;
                XpInLevel = xpInLevel;
                XpToNext = xpToNext;
                Gold = gold;
                Shards = shards;
                Charges = charges;
                Flasks = flasks;
                FlaskCap = flaskCap;
            }

            /// <summary>Fracao da barra de XP (0 a 1); no teto de nivel a barra fica cheia.</summary>
            public float XpFraction => XpToNext > 0.0 ? (float)System.Math.Max(0.0, System.Math.Min(1.0, XpInLevel / XpToNext)) : 1f;
        }

        /// <param name="rules">Motor nativo (nivel e XP vem dele); null cai no JSON do save.</param>
        /// <param name="mapId">Area do teto de nivel (vazio = teto maximo).</param>
        public static Snapshot Read(NativeRulesCore rules = null, string mapId = "")
        {
            var service = GameSession.Save;
            if (service == null || !service.HasSave || GameSession.SaveBusy) return default;
            var save = service.Current;
            int level;
            double inLevel, toNext;
            if (rules != null)
            {
                var progress = save.CharacterProgress(rules, 0, mapId);
                level = progress.Level >= 1 ? progress.Level : 1;
                inLevel = progress.XpInLevel;
                toNext = progress.XpToNext;
            }
            else
            {
                var character = MiniJson.AsObject(MiniJson.Parse(save.CharacterJson(0)));
                level = MiniJson.Int(character, "level", 1);
                inLevel = MiniJson.Num(character, "xp");
                toNext = 0.0;
            }
            long gold = 0, shards = 0;
            var envelope = MiniJson.AsObject(MiniJson.Parse(save.ToJson()));
            var data = envelope.TryGetValue("data", out var inner) ? MiniJson.AsObject(inner) : envelope; // o save vem num envelope {format, data}
            foreach (var entry in MiniJson.AsArray(data.TryGetValue("currencies", out var list) ? list : null))
            {
                var o = MiniJson.AsObject(entry);
                var id = MiniJson.Str(o, "id");
                var amount = (long)MiniJson.Num(o, "amount");
                if (id == GoldId) gold += amount;
                else if (id == ShardsId) shards += amount;
            }
            var flasks = 0;
            var flaskCap = 0;
            if (rules != null)
            {
                var stock = save.VendorStock(rules).Find(x => x.RefId == SaveGame.RefillFlaskId);
                flasks = stock.Owned;
                flaskCap = stock.CarryCap;
            }
            return new Snapshot(level, inLevel, toNext, gold, shards, save.Summary.MarkerCharges, flasks, flaskCap);
        }
    }
}
