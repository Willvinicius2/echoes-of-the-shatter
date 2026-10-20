using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    // Core da Cripta (API C 1.7; docs/09 secao 14): estado do mundo, baus, encontros sorteados, XP por morte e Fervor.
    // Tudo e regra do core: estes tipos so carregam o que ele devolveu.

    /// <summary>Estado de uma area no save: objetos abertos (baus, parede secreta, atalho) por ID e visitas ja comecadas.</summary>
    public sealed class WorldAreaInfo
    {
        public string MapId = string.Empty;
        public int Visits;
        public readonly List<string> Opened = new List<string>();

        public bool IsOpen(string objectId) => Opened.Contains(objectId);

        public static WorldAreaInfo FromJson(string json)
        {
            var info = new WorldAreaInfo();
            if (string.IsNullOrEmpty(json)) return info;
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            info.MapId = MiniJson.Str(o, "map_id");
            info.Visits = MiniJson.Int(o, "visits");
            foreach (var v in MiniJson.AsArray(o.TryGetValue("opened", out var list) ? list : null))
                if (v is string id) info.Opened.Add(id);
            return info;
        }
    }

    /// <summary>Mapa: nivel de monstro, tabela de loot da area, encontros na ordem do CSV e baus com a tabela de cada um.</summary>
    public sealed class MapInfo
    {
        public string MapId = string.Empty;
        public int MonsterLevel, Tier;
        public string AreaLootTable = string.Empty, BossEncounter = string.Empty;
        public readonly List<string> Encounters = new List<string>();
        public readonly List<KeyValuePair<string, string>> Chests = new List<KeyValuePair<string, string>>();   // id -> tabela

        public static MapInfo FromJson(string json)
        {
            var info = new MapInfo();
            if (string.IsNullOrEmpty(json)) return info;
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            info.MapId = MiniJson.Str(o, "map_id");
            info.MonsterLevel = MiniJson.Int(o, "monster_level");
            info.Tier = MiniJson.Int(o, "tier");
            info.AreaLootTable = MiniJson.Str(o, "area_loot_table");
            info.BossEncounter = MiniJson.Str(o, "boss_encounter");
            foreach (var v in MiniJson.AsArray(o.TryGetValue("encounters", out var encs) ? encs : null))
                if (v is string id) info.Encounters.Add(id);
            foreach (var c in MiniJson.AsArray(o.TryGetValue("chests", out var chests) ? chests : null))
            {
                var co = MiniJson.AsObject(c);
                info.Chests.Add(new KeyValuePair<string, string>(MiniJson.Str(co, "id"), MiniJson.Str(co, "loot_table")));
            }
            return info;
        }
    }

    /// <summary>Um espaco do encontro sorteado: virou elite? Com qual modificador?</summary>
    public readonly struct RolledSlotInfo
    {
        public readonly bool Elite;
        public readonly string ModifierId;

        public RolledSlotInfo(bool elite, string modifierId)
        {
            Elite = elite;
            ModifierId = modifierId ?? string.Empty;
        }
    }

    /// <summary>Um grupo do encontro: quantos nasceram (<see cref="Count"/>) e o que cada espaco virou. Um grupo de n usa os n primeiros espacos do layout.</summary>
    public sealed class RolledGroupInfo
    {
        public string EnemyId = string.Empty;
        public readonly List<RolledSlotInfo> Slots = new List<RolledSlotInfo>();
        public int Count => Slots.Count;
    }

    /// <summary>Encontro da visita (determinístico pela semente da visita: o mesmo encontro dá a mesma formacao, tambem depois de um checkpoint).</summary>
    public sealed class RolledEncounterInfo
    {
        public string EncounterId = string.Empty;
        public bool IsBoss;
        public readonly List<RolledGroupInfo> Groups = new List<RolledGroupInfo>();

        public static RolledEncounterInfo FromJson(string json)
        {
            var info = new RolledEncounterInfo();
            if (string.IsNullOrEmpty(json)) return info;
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            info.EncounterId = MiniJson.Str(o, "encounter_id");
            info.IsBoss = MiniJson.Bool(o, "is_boss");
            foreach (var g in MiniJson.AsArray(o.TryGetValue("groups", out var groups) ? groups : null))
            {
                var go = MiniJson.AsObject(g);
                var group = new RolledGroupInfo { EnemyId = MiniJson.Str(go, "enemy_id") };
                foreach (var s in MiniJson.AsArray(go.TryGetValue("slots", out var slots) ? slots : null))
                {
                    var so = MiniJson.AsObject(s);
                    group.Slots.Add(new RolledSlotInfo(MiniJson.Int(so, "elite") != 0, MiniJson.Str(so, "modifier_id")));
                }
                info.Groups.Add(group);
            }
            return info;
        }
    }

    /// <summary>Resultado de abrir um bau (<c>SHATTER_CHEST_*</c>).</summary>
    public enum ChestOpenResult { Opened = 0, AlreadyOpen = 1, NoTable = 2, Error = 99 }

    /// <summary>XP e nivel do personagem (<c>shatter_xp_info</c>). O heroi usa <see cref="Level"/>, o do save.</summary>
    public readonly struct XpInfo
    {
        /// <summary>XP concedido nesta chamada, ja com o Fervor (0 no getter).</summary>
        public readonly double Awarded;
        public readonly double XpInLevel, XpToNext;
        public readonly int LevelBefore, Level, LevelCap;

        public XpInfo(double awarded, double xpInLevel, double xpToNext, int levelBefore, int level, int levelCap)
        {
            Awarded = awarded;
            XpInLevel = xpInLevel;
            XpToNext = xpToNext;
            LevelBefore = levelBefore;
            Level = level;
            LevelCap = levelCap;
        }

        public bool LeveledUp => Level > LevelBefore;
        public bool AtCap => Level >= LevelCap;
    }

    /// <summary>Fervor do jogo manual (rules.csv) para a HUD: multiplicadores e bonus (mult - 1: XP +200% = 2,0).</summary>
    public readonly struct FervorInfo
    {
        public readonly double XpMult, GoldMatMult, RareMult, XpBonus, GoldMatBonus, RareBonus;

        public FervorInfo(double xpMult, double goldMatMult, double rareMult, double xpBonus, double goldMatBonus, double rareBonus)
        {
            XpMult = xpMult;
            GoldMatMult = goldMatMult;
            RareMult = rareMult;
            XpBonus = xpBonus;
            GoldMatBonus = goldMatBonus;
            RareBonus = rareBonus;
        }
    }
}
