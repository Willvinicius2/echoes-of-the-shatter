using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>PROVISÓRIO (stub). Conversões de texto do CSV (nomes iguais aos do core e do _enums.json).</summary>
    internal static class StubParse
    {
        static readonly Dictionary<string, StatId> Stats = new Dictionary<string, StatId>(StringComparer.Ordinal)
        {
            { "life", StatId.Life },
            { "life_regen", StatId.LifeRegen },
            { "resource", StatId.Resource },
            { "resource_regen", StatId.ResourceRegen },
            { "armor", StatId.Armor },
            { "evasion_chance", StatId.EvasionChance },
            { "block_chance", StatId.BlockChance },
            { "resist_fire", StatId.ResistFire },
            { "resist_cold", StatId.ResistCold },
            { "resist_lightning", StatId.ResistLightning },
            { "damage", StatId.Damage },
            { "attack_speed", StatId.AttackSpeed },
            { "cast_speed", StatId.CastSpeed },
            { "crit_chance", StatId.CritChance },
            { "crit_multiplier", StatId.CritMultiplier },
            { "move_speed", StatId.MoveSpeed },
            { "cooldown_recovery", StatId.CooldownRecovery },
            { "area_of_effect", StatId.AreaOfEffect },
            { "projectile_count", StatId.ProjectileCount },
            { "damage_taken", StatId.DamageTaken },
            { "potion_effect", StatId.PotionEffect },
        };

        static readonly Dictionary<string, SkillTags> Tags = new Dictionary<string, SkillTags>(StringComparer.Ordinal)
        {
            { "attack", SkillTags.Attack },
            { "spell", SkillTags.Spell },
            { "melee", SkillTags.Melee },
            { "projectile", SkillTags.Projectile },
            { "area", SkillTags.Area },
            { "fire", SkillTags.Fire },
            { "cold", SkillTags.Cold },
            { "lightning", SkillTags.Lightning },
            { "physical", SkillTags.Physical },
        };

        static readonly Dictionary<string, SkillShape> Shapes = new Dictionary<string, SkillShape>(StringComparer.Ordinal)
        {
            { "melee", SkillShape.Melee },
            { "cone", SkillShape.Cone },
            { "projectile", SkillShape.Projectile },
            { "area", SkillShape.Area },
            { "dash", SkillShape.Dash },
            { "self", SkillShape.Self },
            { "channel", SkillShape.Channel },
            { "trap", SkillShape.Trap },
        };

        public static bool TryStat(string text, out StatId stat) => Stats.TryGetValue(text, out stat);

        public static bool TryShape(string text, out SkillShape shape) => Shapes.TryGetValue(text, out shape);

        /// <summary>Lista de tags separadas por <paramref name="separator"/> ("attack|melee" ou "melee+attack").</summary>
        public static bool TryTags(string text, char separator, out SkillTags tags)
        {
            tags = SkillTags.None;
            if (string.IsNullOrEmpty(text)) return true;
            var parts = text.Split(separator);
            for (var i = 0; i < parts.Length; i++)
            {
                if (!Tags.TryGetValue(parts[i], out var tag)) return false;
                tags |= tag;
            }
            return true;
        }

        public static SkillTags TagOf(DamageType type)
        {
            switch (type)
            {
                case DamageType.Physical: return SkillTags.Physical;
                case DamageType.Fire: return SkillTags.Fire;
                case DamageType.Cold: return SkillTags.Cold;
                case DamageType.Lightning: return SkillTags.Lightning;
                default: return SkillTags.None;
            }
        }

        public static string[] SplitList(string text)
        {
            if (string.IsNullOrEmpty(text)) return Array.Empty<string>();
            return text.Split('|');
        }

        /// <summary>
        /// Lista de modificadores <c>stat:kind:valor[:tag+tag]</c> separados por '|' (docs/06_dados.md, seção 1).
        /// </summary>
        public static bool TryModifiers(string text, string source, List<StubModifier> into, out string error)
        {
            error = string.Empty;
            if (string.IsNullOrEmpty(text)) return true;
            var entries = text.Split('|');
            for (var i = 0; i < entries.Length; i++)
            {
                var parts = entries[i].Split(':');
                if (parts.Length < 3 || parts.Length > 4)
                {
                    error = $"modifier '{entries[i]}' must be stat:kind:value[:tag+tag]";
                    return false;
                }
                if (!TryStat(parts[0], out var stat))
                {
                    error = $"unknown stat '{parts[0]}'";
                    return false;
                }
                StubModKind kind;
                switch (parts[1])
                {
                    case "flat": kind = StubModKind.Flat; break;
                    case "increased": kind = StubModKind.Increased; break;
                    case "more": kind = StubModKind.More; break;
                    default:
                        error = $"unknown modifier kind '{parts[1]}'";
                        return false;
                }
                if (!StubCsvTable.TryParseDouble(parts[2], out var value))
                {
                    error = $"modifier value '{parts[2]}' is not a number";
                    return false;
                }
                var required = SkillTags.None;
                if (parts.Length == 4 && !TryTags(parts[3], '+', out required))
                {
                    error = $"unknown tag in '{parts[3]}'";
                    return false;
                }
                into.Add(new StubModifier { Stat = stat, Kind = kind, Value = value, RequiredTags = required, Source = source });
            }
            return true;
        }

        /// <summary>Atributos de inimigo <c>stat:base:porNível</c> separados por '|'.</summary>
        public static bool TryStatGrowth(string text, List<StubStatGrowth> into, out string error)
        {
            error = string.Empty;
            if (string.IsNullOrEmpty(text)) return true;
            var entries = text.Split('|');
            for (var i = 0; i < entries.Length; i++)
            {
                var parts = entries[i].Split(':');
                if (parts.Length != 3 || !TryStat(parts[0], out var stat)
                    || !StubCsvTable.TryParseDouble(parts[1], out var baseValue)
                    || !StubCsvTable.TryParseDouble(parts[2], out var perLevel))
                {
                    error = $"stat growth '{entries[i]}' must be stat:base:perLevel";
                    return false;
                }
                into.Add(new StubStatGrowth { Stat = stat, Base = baseValue, PerLevel = perLevel });
            }
            return true;
        }

        public static bool IsValidContentId(string id)
        {
            if (string.IsNullOrEmpty(id) || id[0] == '.' || id[id.Length - 1] == '.') return false;
            var sawDot = false;
            var prev = '\0';
            for (var i = 0; i < id.Length; i++)
            {
                var c = id[i];
                var ok = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '.';
                if (!ok) return false;
                if (c == '.')
                {
                    if (prev == '.') return false;
                    sawDot = true;
                }
                prev = c;
            }
            return sawDot;
        }
    }
}
