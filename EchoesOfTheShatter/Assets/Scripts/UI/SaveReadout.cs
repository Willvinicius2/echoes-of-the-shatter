using System.Collections.Generic;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;

namespace Echoes.UI
{
    /// <summary>
    /// Leitura do save para a HUD e o inventario: nivel, XP, Ouro, Lascas e Cargas do Marco. So le (o ganho de XP e o Ouro sao do core/Backend);
    /// nada aqui calcula regra. Moedas vem do bloco <c>currencies</c> do JSON do save (ids de loot_entries.csv).
    /// </summary>
    public static class SaveReadout
    {
        public const string GoldId = "currency.gold";
        public const string ShardsId = "material.shards";

        public readonly struct Snapshot
        {
            public readonly bool Valid;
            public readonly int Level, Charges;
            public readonly double Xp;
            public readonly long Gold, Shards;

            public Snapshot(int level, double xp, long gold, long shards, int charges)
            {
                Valid = true;
                Level = level;
                Xp = xp;
                Gold = gold;
                Shards = shards;
                Charges = charges;
            }
        }

        public static Snapshot Read()
        {
            var service = GameSession.Save;
            if (service == null || !service.HasSave || GameSession.SaveBusy) return default;
            var save = service.Current;
            var character = MiniJson.AsObject(MiniJson.Parse(save.CharacterJson(0)));
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
            return new Snapshot(MiniJson.Int(character, "level", 1), MiniJson.Num(character, "xp"), gold, shards, save.Summary.MarkerCharges);
        }
    }
}
