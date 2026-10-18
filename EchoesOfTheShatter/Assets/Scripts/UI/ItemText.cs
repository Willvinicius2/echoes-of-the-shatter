using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Textos de item para tooltip e etiqueta no chao. O nome sai dos padroes <c>item.pattern.*</c> do Loc com o genero (e o numero) da base e a forma
    /// flexionada do prefixo (<c>.name</c>, <c>.name_f</c>, <c>.name_mp</c>, <c>.name_fp</c>); nunca se concatena frase aqui. Os numeros (dano, DPS,
    /// afixos, deltas, preco) vem do core; este codigo so formata. Cores da raridade: docs/03 secao 2.3.
    /// </summary>
    public static class ItemText
    {
        public static readonly Color NormalColor = new Color(0.851f, 0.824f, 0.784f);   // #D9D2C8
        public static readonly Color MagicColor = new Color(0.435f, 0.659f, 1f);        // #6FA8FF
        public static readonly Color RareColor = new Color(1f, 0.824f, 0.29f);          // #FFD24A
        public static readonly Color UniqueColor = new Color(1f, 0.541f, 0.18f);        // #FF8A2E

        public static Color RarityColor(ItemRarity rarity)
        {
            switch (rarity)
            {
                case ItemRarity.Magic: return MagicColor;
                case ItemRarity.Rare: return RareColor;
                case ItemRarity.Unique: return UniqueColor;
                default: return NormalColor;
            }
        }

        public static string RarityKey(ItemRarity rarity) => "rarity." + rarity.ToString().ToLowerInvariant() + ".name";

        /// <summary>Atributos mostrados como porcentagem quando o valor e fracao (chance de critico, resistencias); o resto e numero.</summary>
        static bool IsFractionStat(string stat) => stat == "crit_chance" || stat == "block_chance" || stat == "evasion_chance" || stat.StartsWith("resist", StringComparison.Ordinal);

        // ------------------------------------------------------------------------------------------------ nome

        sealed class AffixData
        {
            public bool Prefix;
            public string Stat = string.Empty;
            public string ModKind = "flat";
        }

        static AffixData LookupAffix(NativeRulesCore rules, string affixId)
        {
            var data = new AffixData();
            var json = rules != null ? rules.ContentJson(affixId) : null;
            if (string.IsNullOrEmpty(json)) return data;
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            data.Prefix = MiniJson.Str(o, "kind") == "prefix";
            data.Stat = MiniJson.Str(o, "stat");
            data.ModKind = MiniJson.Str(o, "mod_kind", "flat");
            return data;
        }

        /// <summary>Nome do item: Unico pelo nome proprio; Comum pela base; Magico/Raro pelo padrao com prefixo e sufixo e a concordancia da base.</summary>
        public static string Name(LocalizationService loc, NativeRulesCore rules, ItemInstanceInfo item)
        {
            if (item == null) return string.Empty;
            if (item.IsUnique && !string.IsNullOrEmpty(item.UniqueId) && loc.TryGet(item.UniqueId + ".name", out var unique)) return unique;
            var baseKey = item.BaseId + ".name";
            var baseName = loc.Get(baseKey);
            var info = rules?.FindItemBase(item.BaseId);
            var gender = info != null ? info.GrammaticalGender : string.Empty;
            var plural = loc.ContextOf(baseKey).IndexOf("plural", StringComparison.OrdinalIgnoreCase) >= 0;
            string prefix = null, suffix = null;
            foreach (var affix in item.Affixes)
            {
                var data = LookupAffix(rules, affix.AffixId);
                if (data.Prefix && prefix == null) prefix = Inflect(loc, affix.AffixId, gender, plural);
                else if (!data.Prefix && suffix == null) suffix = Inflect(loc, affix.AffixId, gender, plural);
            }
            var pattern = prefix != null && suffix != null ? "item.pattern.prefix_suffix"
                : prefix != null ? "item.pattern.prefix_only"
                : suffix != null ? "item.pattern.suffix_only"
                : "item.pattern.plain";
            return loc.Get(pattern).Replace("{base}", baseName).Replace("{prefix}", prefix ?? string.Empty).Replace("{suffix}", suffix ?? string.Empty).Trim();
        }

        /// <summary>Forma do afixo para o genero e o numero da base: .name (m), .name_f, .name_mp, .name_fp; sufixos sao invariaveis (so .name).</summary>
        static string Inflect(LocalizationService loc, string affixId, string gender, bool plural)
        {
            var form = plural ? (gender == "f" ? "_fp" : "_mp") : (gender == "f" ? "_f" : string.Empty);
            var key = affixId + ".name" + form;
            return loc.TryGet(key, out var text) ? text : loc.Get(affixId + ".name");
        }

        // ------------------------------------------------------------------------------------------------ linhas

        public static string StatName(LocalizationService loc, string stat) => loc.TryGet("stat." + stat + ".name", out var name) ? name : stat;

        /// <summary>Um modificador como linha: "+12 vida", "+8% dano", "+2% chance de critico".</summary>
        public static string ModLine(LocalizationService loc, string stat, string modKind, double value)
        {
            var percent = modKind == "increased" || modKind == "more" || IsFractionStat(stat);
            var shown = percent ? value * 100.0 : value;
            var text = (shown >= 0 ? "+" : "-") + Math.Abs(shown).ToString(Math.Abs(shown - Math.Round(shown)) < 0.005 ? "0" : "0.#", CultureInfo.InvariantCulture) + (percent ? "%" : string.Empty);
            return loc.Get("ui.item.mod").Replace("{value}", text).Replace("{stat}", StatName(loc, stat));
        }

        /// <summary>Linhas do tooltip na ordem do docs/16 S-06: propriedades da base, afixos, efeito do Unico, nivel.</summary>
        public static List<(string text, Color color)> BodyLines(LocalizationService loc, NativeRulesCore rules, ItemInstanceInfo item, bool includeAffixes = true)
        {
            var lines = new List<(string, Color)>();
            var info = rules?.FindItemBase(item.BaseId);
            if (info != null && info.IsWeapon)
            {
                var damage = info.WeaponDamage.Physical + info.WeaponDamage.Fire + info.WeaponDamage.Cold + info.WeaponDamage.Lightning;
                lines.Add((loc.Get("ui.item.weapon_damage").Replace("{value}", damage.ToString("0.#", CultureInfo.InvariantCulture)), ScreenKit.Text));
                lines.Add((loc.Get("ui.item.attack_time").Replace("{value}", info.AttackTime.ToString("0.0#", CultureInfo.InvariantCulture)), ScreenKit.Text));
            }
            var baseJson = rules != null ? rules.ContentJson(item.BaseId) : null;
            if (!string.IsNullOrEmpty(baseJson))
            {
                var o = MiniJson.AsObject(MiniJson.Parse(baseJson));
                foreach (var m in MiniJson.AsArray(o.TryGetValue("implicit_mods", out var mods) ? mods : null))
                {
                    var mo = MiniJson.AsObject(m);
                    lines.Add((ModLine(loc, MiniJson.Str(mo, "stat"), MiniJson.Str(mo, "kind"), MiniJson.Num(mo, "value")), ScreenKit.Text));
                }
            }
            foreach (var affix in item.Affixes)
            {
                if (!includeAffixes) break; // o Encantador mostra os afixos em linhas proprias (valor, barra e passos)
                var data = LookupAffix(rules, affix.AffixId);
                lines.Add((ModLine(loc, data.Stat, data.ModKind, affix.Value), MagicColor));
            }
            if (item.IsUnique && !string.IsNullOrEmpty(item.UniqueId))
            {
                var uniqueJson = rules != null ? rules.ContentJson(item.UniqueId) : null;
                if (!string.IsNullOrEmpty(uniqueJson))
                {
                    var o = MiniJson.AsObject(MiniJson.Parse(uniqueJson));
                    foreach (var m in MiniJson.AsArray(o.TryGetValue("fixed_mods", out var mods) ? mods : null))
                    {
                        var mo = MiniJson.AsObject(m);
                        var value = MiniJson.Num(mo, "value");
                        lines.Add((ModLine(loc, MiniJson.Str(mo, "stat"), MiniJson.Str(mo, "kind"), value), value < 0 ? ScreenKit.Bad : UniqueColor));
                    }
                }
                if (loc.TryGet(item.UniqueId + ".desc", out var desc)) lines.Add((desc, UniqueColor));
                if (loc.TryGet(item.UniqueId + ".flavor", out var flavor)) lines.Add((flavor, ScreenKit.Muted));
            }
            lines.Add((loc.Get("ui.item.level").Replace("{level}", item.ItemLevel.ToString(CultureInfo.InvariantCulture)), ScreenKit.Muted));
            return lines;
        }

        /// <summary>"Raro · Espada": a raridade em texto (nunca so cor) e a posicao do item.</summary>
        public static string RarityLine(LocalizationService loc, NativeRulesCore rules, ItemInstanceInfo item)
        {
            var info = rules?.FindItemBase(item.BaseId);
            var slot = info != null ? loc.Get("slot." + info.Slot + ".name") : string.Empty;
            var feminine = info != null && info.GrammaticalGender == "f";
            var rarityKey = RarityKey(item.Rarity);
            var rarity = feminine && loc.TryGet(rarityKey.Replace(".name", ".name_f"), out var f) ? f : loc.Get(rarityKey);
            return loc.Get("ui.item.rarity_line").Replace("{rarity}", rarity).Replace("{slot}", slot);
        }

        /// <summary>Linhas da comparacao: cada atributo que muda com a seta (verde melhora, vermelho piora), do core.</summary>
        public static List<(string text, Color color)> CompareLines(LocalizationService loc, ItemComparison comparison)
        {
            var lines = new List<(string, Color)>();
            if (comparison == null || comparison.Result != InvResult.Ok) return lines;
            if (comparison.IsWeapon)
            {
                var up = comparison.WeaponDpsAfter >= comparison.WeaponDpsBefore;
                var text = loc.Get("ui.item.weapon_dps").Replace("{value}", comparison.WeaponDpsBefore.ToString("0.#", CultureInfo.InvariantCulture) + " → " + comparison.WeaponDpsAfter.ToString("0.#", CultureInfo.InvariantCulture));
                if (Math.Abs(comparison.WeaponDpsAfter - comparison.WeaponDpsBefore) > 1e-6) lines.Add(((up ? "▲ " : "▼ ") + text, up ? ScreenKit.Good : ScreenKit.Bad));
            }
            foreach (var d in comparison.Deltas)
            {
                var up = d.Change >= 0;
                var fraction = IsFractionStat(d.Stat);
                string F(double v) => fraction ? (v * 100.0).ToString("0.#", CultureInfo.InvariantCulture) + "%" : v.ToString("0.##", CultureInfo.InvariantCulture);
                var text = loc.Get("ui.item.stat_delta").Replace("{stat}", StatName(loc, d.Stat)).Replace("{before}", F(d.Before)).Replace("{after}", F(d.After));
                lines.Add(((up ? "▲ " : "▼ ") + text, up ? ScreenKit.Good : ScreenKit.Bad));
            }
            return lines;
        }

        /// <summary>Resumo para o slot: +1 melhora, -1 piora, 0 neutro (so informacao do core: DPS da arma ou a soma dos deltas).</summary>
        public static int CompareVerdict(ItemComparison comparison)
        {
            if (comparison == null || comparison.Result != InvResult.Ok) return 0;
            if (comparison.IsWeapon) return Math.Sign(Math.Round(comparison.WeaponDpsAfter - comparison.WeaponDpsBefore, 4));
            var score = 0.0;
            foreach (var d in comparison.Deltas) score += d.Change;
            return Math.Sign(Math.Round(score, 4));
        }

        /// <summary>Valor de atributo do painel: fracao vira porcentagem (critico, resistencias); o resto, numero com ate 2 casas.</summary>
        public static string StatValue(string stat, double value)
        {
            return IsFractionStat(stat)
                ? (value * 100.0).ToString("0.#", CultureInfo.InvariantCulture) + "%"
                : value.ToString("0.##", CultureInfo.InvariantCulture);
        }

        /// <summary>Abreviacao do item para o quadrado do slot (so quando a base nao tem icone em UiArt): iniciais da base.</summary>
        public static string Glyph(LocalizationService loc, ItemInstanceInfo item)
        {
            var name = loc.Get(item.BaseId + ".name");
            var sb = new StringBuilder();
            foreach (var word in name.Split(' '))
            {
                if (word.Length == 0 || word == "de" || word == "do" || word == "da" || word == "of") continue;
                sb.Append(char.ToUpperInvariant(word[0]));
                if (sb.Length >= 2) break;
            }
            return sb.ToString();
        }
    }
}
