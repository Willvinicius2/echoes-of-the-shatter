using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>Resultado de <c>shatter_story_apply_verdict</c> (SHATTER_VERDICT_*).</summary>
    public enum VerdictResult { Ok = 0, Unknown = 1, GeneralNotDefeated = 2, AlreadyDecided = 3, SaveFull = 4, Error = 99 }

    /// <summary>Uma opcao de veredito (ou um veredito ja tomado) como o core a descreve. Numeros e ids vem das tabelas de Story/; aqui so leitura.</summary>
    public sealed class StoryVerdictInfo
    {
        public string RegionId = string.Empty;
        public string VerdictId = string.Empty;
        /// <summary>"exorcise" ou "devour".</summary>
        public string Choice = string.Empty;
        public int HungerDelta;
        public double StatBonusPct;
        public string GrantsRelic = string.Empty;
        public string GrantsSignature = string.Empty;
        /// <summary>"purified" ou "stain".</summary>
        public string RegionState = string.Empty;
        /// <summary>Id do estado do Refugio (hub.fortified_village, hub.fortified_garrison).</summary>
        public string HubState = string.Empty;
        public string LastWordsKey = string.Empty;

        public bool IsDevour => Choice == "devour";
        public bool IsExorcise => Choice == "exorcise";

        internal static StoryVerdictInfo From(Dictionary<string, object> o, string regionId)
        {
            return new StoryVerdictInfo
            {
                RegionId = MiniJson.Str(o, "region_id", regionId),
                VerdictId = MiniJson.Str(o, "verdict_id"),
                Choice = MiniJson.Str(o, "choice"),
                HungerDelta = MiniJson.Int(o, "hunger_delta"),
                StatBonusPct = MiniJson.Num(o, "stat_bonus_pct"),
                GrantsRelic = MiniJson.Str(o, "grants_relic"),
                GrantsSignature = MiniJson.Str(o, "grants_signature"),
                RegionState = MiniJson.Str(o, "region_state"),
                HubState = MiniJson.Str(o, "hub_state"),
                LastWordsKey = MiniJson.Str(o, "last_words_key"),
            };
        }
    }

    /// <summary>Progresso da historia no save (<c>shatter_story_state_json</c>): Fome, bonus total, Ecos achados e vereditos tomados.</summary>
    public sealed class StoryState
    {
        public int Hunger;
        public int HungerMax;
        public double StatBonusPct;
        public readonly List<string> Echoes = new List<string>();
        public readonly List<StoryVerdictInfo> Verdicts = new List<StoryVerdictInfo>();

        public static StoryState FromJson(string json)
        {
            var state = new StoryState();
            if (string.IsNullOrEmpty(json)) return state;
            Dictionary<string, object> o;
            try { o = MiniJson.AsObject(MiniJson.Parse(json)); }
            catch (FormatException) { return state; }
            state.Hunger = MiniJson.Int(o, "hunger");
            state.HungerMax = MiniJson.Int(o, "hunger_max");
            state.StatBonusPct = MiniJson.Num(o, "stat_bonus_pct");
            if (o.TryGetValue("echoes", out var echoes))
                foreach (var e in MiniJson.AsArray(echoes)) if (e is string s) state.Echoes.Add(s);
            if (o.TryGetValue("verdicts", out var verdicts))
                foreach (var v in MiniJson.AsArray(verdicts)) state.Verdicts.Add(StoryVerdictInfo.From(MiniJson.AsObject(v), string.Empty));
            return state;
        }

        public bool HasEcho(string echoId) => Echoes.Contains(echoId);

        /// <summary>O veredito tomado nesta regiao, ou null.</summary>
        public StoryVerdictInfo VerdictOf(string regionId) => Verdicts.Find(v => v.RegionId == regionId);

        /// <summary>Estado do Refugio pelo ultimo veredito tomado ("" se nenhum): o Refugio reflete a escolha mais recente.</summary>
        public string HubState => Verdicts.Count > 0 ? Verdicts[Verdicts.Count - 1].HubState : string.Empty;

        public bool HasRelic(string relicId) => Verdicts.Exists(v => v.GrantsRelic == relicId);

        public bool HasSignature(string skillId) => Verdicts.Exists(v => v.GrantsSignature == skillId);
    }

    /// <summary>Uma regiao (<c>shatter_story_region_json</c>): as duas opcoes da tela de veredito (Exorcizar primeiro) e o progresso dos Ecos.</summary>
    public sealed class StoryRegionInfo
    {
        public string RegionId = string.Empty;
        public string MapId = string.Empty;
        public string GeneralId = string.Empty;
        public bool Decided;
        public string VerdictId = string.Empty;
        public int EchoesFound;
        public int EchoesTotal;
        public readonly List<StoryVerdictInfo> Options = new List<StoryVerdictInfo>();

        public static StoryRegionInfo FromJson(string json)
        {
            var info = new StoryRegionInfo();
            if (string.IsNullOrEmpty(json)) return info;
            Dictionary<string, object> o;
            try { o = MiniJson.AsObject(MiniJson.Parse(json)); }
            catch (FormatException) { return info; }
            info.RegionId = MiniJson.Str(o, "region_id");
            info.MapId = MiniJson.Str(o, "map_id");
            info.GeneralId = MiniJson.Str(o, "general_id");
            info.Decided = MiniJson.Bool(o, "decided");
            info.VerdictId = MiniJson.Str(o, "verdict_id");
            info.EchoesFound = MiniJson.Int(o, "echoes_found");
            info.EchoesTotal = MiniJson.Int(o, "echoes_total");
            if (o.TryGetValue("options", out var options))
                foreach (var v in MiniJson.AsArray(options)) info.Options.Add(StoryVerdictInfo.From(MiniJson.AsObject(v), info.RegionId));
            return info;
        }
    }
}
