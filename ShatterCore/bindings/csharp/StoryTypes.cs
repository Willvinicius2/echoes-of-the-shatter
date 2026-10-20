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

    /// <summary>Uma missao como o core a descreve (<c>quests</c> de <c>shatter_story_state_json</c>). O core so guarda progresso e conclusao; a recompensa e uma chave que o cliente aplica.</summary>
    public sealed class StoryQuestInfo
    {
        public string QuestId = string.Empty;
        public string RegionId = string.Empty;
        public string Giver = string.Empty;
        /// <summary>talk, collect_echo, reach_map_boss ou verdict.</summary>
        public string ObjectiveType = string.Empty;
        public string ObjectiveTarget = string.Empty;
        public int ObjectiveCount = 1;
        public int Progress;
        /// <summary>"locked", "active" ou "done".</summary>
        public string Status = "locked";
        public string Requires = string.Empty;
        /// <summary>unlock.return_marker, reveal.general_weakness, unlock.duel ou verdict_choice.</summary>
        public string Reward = string.Empty;

        public bool IsActive => Status == "active";
        public bool IsDone => Status == "done";

        internal static StoryQuestInfo From(Dictionary<string, object> o)
        {
            return new StoryQuestInfo
            {
                QuestId = MiniJson.Str(o, "quest_id"),
                RegionId = MiniJson.Str(o, "region_id"),
                Giver = MiniJson.Str(o, "giver"),
                ObjectiveType = MiniJson.Str(o, "objective_type"),
                ObjectiveTarget = MiniJson.Str(o, "objective_target"),
                ObjectiveCount = MiniJson.Int(o, "objective_count", 1),
                Progress = MiniJson.Int(o, "progress"),
                Status = MiniJson.Str(o, "status", "locked"),
                Requires = MiniJson.Str(o, "requires"),
                Reward = MiniJson.Str(o, "reward"),
            };
        }
    }

    /// <summary>Progresso da historia no save (<c>shatter_story_state_json</c>): Fome, bonus total, Ecos achados e vereditos tomados.</summary>
    public sealed class StoryState
    {
        public int Hunger;
        public int HungerMax;
        public double StatBonusPct;
        /// <summary>Bonus de cura de pocao da Reliquia do Descanso, em %.</summary>
        public double PotionEffectPct;
        /// <summary>Pontos de elite somados por mapa com Mancha (mapId -> %).</summary>
        public readonly Dictionary<string, double> StainEliteBonusByMap = new Dictionary<string, double>();
        /// <summary>Tabela de loot extra por mapa com Mancha (mapId -> tabela).</summary>
        public readonly Dictionary<string, string> StainLootTableByMap = new Dictionary<string, string>();
        /// <summary>Fome que cada uso de habilidade devorada gasta na corrida (story_rules.csv).</summary>
        public int DevouredHungerCost;
        /// <summary>Golpes devorados do save (grantsSignature skill.devoured.* dos vereditos).</summary>
        public readonly List<string> DevouredSkills = new List<string>();
        /// <summary>Usos de golpe devorado por corrida que a Fome deixa (-1 = sem limite); vai para a expedicao idle.</summary>
        public int IdleDevouredUses;
        public readonly List<string> Echoes = new List<string>();
        public readonly List<StoryVerdictInfo> Verdicts = new List<StoryVerdictInfo>();
        /// <summary>Todas as missoes de quests.csv, na ordem da tabela, com progresso e status.</summary>
        public readonly List<StoryQuestInfo> Quests = new List<StoryQuestInfo>();

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
            state.PotionEffectPct = MiniJson.Num(o, "potion_effect_pct");
            if (o.TryGetValue("stain_elite_bonus_by_map", out var stain))
                foreach (var kv in MiniJson.AsObject(stain)) state.StainEliteBonusByMap[kv.Key] = kv.Value is double d ? d : 0.0;
            state.DevouredHungerCost = MiniJson.Int(o, "devoured_hunger_cost");
            if (o.TryGetValue("stain_loot_table_by_map", out var stainLoot))
                foreach (var kv in MiniJson.AsObject(stainLoot)) if (kv.Value is string table) state.StainLootTableByMap[kv.Key] = table;
            if (o.TryGetValue("devoured_skills", out var devoured))
                foreach (var d in MiniJson.AsArray(devoured)) if (d is string skill) state.DevouredSkills.Add(skill);
            state.IdleDevouredUses = MiniJson.Int(o, "idle_devoured_uses");
            if (o.TryGetValue("echoes", out var echoes))
                foreach (var e in MiniJson.AsArray(echoes)) if (e is string s) state.Echoes.Add(s);
            if (o.TryGetValue("verdicts", out var verdicts))
                foreach (var v in MiniJson.AsArray(verdicts)) state.Verdicts.Add(StoryVerdictInfo.From(MiniJson.AsObject(v), string.Empty));
            if (o.TryGetValue("quests", out var quests))
                foreach (var q in MiniJson.AsArray(quests)) state.Quests.Add(StoryQuestInfo.From(MiniJson.AsObject(q)));
            return state;
        }

        public StoryQuestInfo QuestOf(string questId) => Quests.Find(q => q.QuestId == questId);

        public bool QuestDone(string questId) => QuestOf(questId)?.IsDone ?? false;

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
