using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using Echoes.Interop;
using Echoes.Interop.Native;

namespace Echoes.Core
{
    /// <summary>Uma regra de IA da expedicao (formato do core): condicao, parametro, acao e referencia (poção ou habilidade).</summary>
    public sealed class AiRuleDef
    {
        public string Condition = "always";
        public double Param;
        public string Action = "use_skill";
        public string RefId = string.Empty;

        public AiRuleDef() { }

        public AiRuleDef(string condition, double param, string action, string refId)
        {
            Condition = condition;
            Param = param;
            Action = action;
            RefId = refId;
        }

        public string ToJson() =>
            "{\"condition\":" + MiniJson.Quote(Condition) + ",\"param\":" + Param.ToString("R", CultureInfo.InvariantCulture) + ",\"action\":" + MiniJson.Quote(Action) + ",\"ref_id\":" + MiniJson.Quote(RefId) + "}";
    }

    /// <summary>Configuracao da expedicao montada na tela da Ilsa: rota, objetivo, regras de IA e duracao em horas.</summary>
    public sealed class ExpeditionConfig
    {
        public const string CryptMap = "map.act1.crypt";

        public string MapId = CryptMap;
        public string Objective = "xp";
        public int Hours = 1;
        public readonly List<AiRuleDef> Rules = new List<AiRuleDef>();

        /// <summary>Regras padrao do protocolo (docs/16): pocao abaixo de 35% de vida, Fenda de Pedra se houver 3 ou mais, depois o golpe basico.</summary>
        public static ExpeditionConfig Default()
        {
            var config = new ExpeditionConfig();
            config.Rules.Add(new AiRuleDef("life_below", 0.35, "use_potion", string.Empty));
            config.Rules.Add(new AiRuleDef("enemies_at_least", 3, "use_skill", "skill.warrior.stone_rift"));
            config.Rules.Add(new AiRuleDef("always", 0, "use_skill", "skill.warrior.iron_cut"));
            return config;
        }

        /// <summary>Parametros de inicio (sem "seed" nem "start_utc": proibidos, o core deriva pela chamada _trusted).</summary>
        public string ToParamsJson(int characterIndex = 0)
        {
            var sb = new StringBuilder(256);
            sb.Append("{\"character_index\":").Append(characterIndex).Append(",\"map_id\":").Append(MiniJson.Quote(MapId));
            sb.Append(",\"objective\":").Append(MiniJson.Quote(Objective)).Append(",\"rules\":[");
            for (var i = 0; i < Rules.Count; i++) sb.Append(i > 0 ? "," : string.Empty).Append(Rules[i].ToJson());
            sb.Append("],\"duration_hours\":").Append(Hours).Append('}');
            return sb.ToString();
        }
    }

    public enum ExpeditionPhase { None, Running, ReadyToCollect, Collected }

    public readonly struct ExpeditionState
    {
        public readonly ExpeditionPhase Phase;
        public readonly long SecondsLeft;
        public readonly double EffectiveSeconds;

        public ExpeditionState(ExpeditionPhase phase, long secondsLeft, double effectiveSeconds)
        {
            Phase = phase;
            SecondsLeft = secondsLeft;
            EffectiveSeconds = effectiveSeconds;
        }
    }

    /// <summary>O relatorio do Tico (seis campos, RF-44) lido do ExpeditionResult que o core devolve.</summary>
    public sealed class ExpeditionReport
    {
        public string Stop = string.Empty;
        public double EffectiveSeconds, Xp;
        public int Encounters, Kills, PotionsUsed, Rares, ItemCount, CommonCount, MagicCount, RareCount;
        public long Gold;
        public string TipKey = string.Empty;
        public bool IsEstimate;

        public static ExpeditionReport Parse(string json)
        {
            var o = MiniJson.AsObject(MiniJson.Parse(json));
            var report = new ExpeditionReport
            {
                Stop = MiniJson.Str(o, "stop"),
                EffectiveSeconds = MiniJson.Num(o, "effective_seconds"),
                Encounters = MiniJson.Int(o, "encounters_cleared"),
                Kills = MiniJson.Int(o, "kills"),
                PotionsUsed = MiniJson.Int(o, "potions_used"),
                Xp = MiniJson.Num(o, "xp_gained"),
                Rares = MiniJson.Int(o, "rares_dropped"),
                IsEstimate = MiniJson.Str(o, "calibration") == "manual_estimate",
            };
            foreach (var item in MiniJson.AsArray(o.TryGetValue("items", out var items) ? items : null))
            {
                var rarity = MiniJson.Str(MiniJson.AsObject(item), "rarity");
                report.ItemCount++;
                if (rarity == "rare") report.RareCount++;
                else if (rarity == "magic") report.MagicCount++;
                else report.CommonCount++;
            }
            foreach (var stack in MiniJson.AsArray(o.TryGetValue("stacks", out var stacks) ? stacks : null))
            {
                var s = MiniJson.AsObject(stack);
                if (MiniJson.Str(s, "id") == "currency.gold") report.Gold += (long)MiniJson.Num(s, "amount");
            }
            var tips = MiniJson.AsArray(o.TryGetValue("tip_keys", out var t) ? t : null);
            if (tips.Count > 0 && tips[0] is string key) report.TipKey = key;
            return report;
        }

        /// <summary>Chave de Loc do motivo da parada (report.stop.*).</summary>
        public string StopKey
        {
            get
            {
                switch (Stop)
                {
                    case "duration_reached": return "report.stop.duration_done";
                    case "clock_rollback": return "report.stop.clock_back";
                    case "content_mismatch": return "report.stop.content_mismatch";
                    case "incompatible_build": return "report.stop.content_mismatch";
                    default: return Stop == "retreat" ? "report.stop.low_life" : "report.stop.duration_done";
                }
            }
        }
    }

    /// <summary>
    /// Expedicao idle ponta a ponta (docs/16, F-11 a F-13) so com as chamadas _trusted e o relogio confiavel: configurar (previsao e conferencia),
    /// iniciar, consultar o estado, coletar uma vez so e gravar. O heroi fica ocupado enquanto ela roda (setting).
    /// </summary>
    public sealed class ExpeditionService
    {
        readonly SaveService saves;

        public ExpeditionService(SaveService saves)
        {
            this.saves = saves;
        }

        SaveGame Save => saves.Current;

        ClockInput Clock => new ClockInput(saves.Clock.NowUtc, Save != null ? Save.Summary.LastSeenUtc : 0);

        /// <summary>Verdadeiro se o heroi esta em rota (expedicao Running) e o setting HeroBusyDuringExpedition esta ligado.</summary>
        public bool IsHeroBusy => SaveSettings.HeroBusyDuringExpedition && Save != null && Save.Summary.HasRunningExpedition;

        public StartCheck Check(NativeRulesCore rules, ExpeditionConfig config, out string blockers)
        {
            if (Save == null)
            {
                blockers = string.Empty;
                return StartCheck.Error;
            }
            return Save.CheckExpedition(rules, config.ToParamsJson(), out blockers);
        }

        /// <summary>Previsao em faixa com o selo de calibracao (RF-40): monta o pedido do snapshot atual e pede ao core.</summary>
        public bool Preview(NativeRulesCore rules, ExpeditionConfig config, out ForecastBands bands)
        {
            bands = default;
            if (Save == null) return false;
            var character = Save.CharacterJson(0);
            var version = rules.ContentVersion;
            var rulesJson = new StringBuilder("[");
            for (var i = 0; i < config.Rules.Count; i++) rulesJson.Append(i > 0 ? "," : string.Empty).Append(config.Rules[i].ToJson());
            rulesJson.Append(']');
            var request = "{\"snapshot\":{\"character\":" + character + ",\"content_version\":" + version + "},\"map_id\":" + MiniJson.Quote(config.MapId) +
                          ",\"objective\":" + MiniJson.Quote(config.Objective) + ",\"rules\":" + rulesJson + ",\"seed\":\"1\",\"start_utc\":0,\"duration_hours\":" + config.Hours +
                          ",\"effective_seconds\":" + (config.Hours * 3600) + ",\"content_version\":" + version + "}";
            return SaveGame.Forecast(rules, request, 64, out bands, out _);
        }

        /// <summary>Inicia pelo relogio confiavel e grava. Devolve o resultado da conferencia (Ok = iniciou).</summary>
        public StartCheck Start(NativeRulesCore rules, ExpeditionConfig config)
        {
            if (Save == null) return StartCheck.Error;
            var now = SaveGame.ResolveNow(rules, Clock);
            var check = Save.StartExpedition(rules, config.ToParamsJson(), now, out _);
            if (check == StartCheck.Ok) saves.Save(rules);
            return check;
        }

        public ExpeditionState State(NativeRulesCore rules)
        {
            if (Save == null) return new ExpeditionState(ExpeditionPhase.None, 0, 0);
            var summary = Save.Summary;
            if (!summary.HasRunningExpedition)
                return new ExpeditionState(summary.ExpeditionCount > 0 ? ExpeditionPhase.Collected : ExpeditionPhase.None, 0, 0);
            if (!Save.ExpeditionRequest(rules, summary.RunningExpedition, Clock, out var request, out var finished, out var effective))
                return new ExpeditionState(ExpeditionPhase.None, 0, 0);
            if (finished) return new ExpeditionState(ExpeditionPhase.ReadyToCollect, 0, effective);
            var o = MiniJson.AsObject(MiniJson.Parse(request));
            var end = (long)MiniJson.Num(o, "start_utc") + (long)MiniJson.Int(o, "duration_hours") * 3600;
            return new ExpeditionState(ExpeditionPhase.Running, Math.Max(0, end - saves.Clock.NowUtc), effective);
        }

        /// <summary>
        /// Coleta uma vez so (RF-55): o core recalcula o resultado e entrega itens, pilhas e XP no save; depois grava. NotFinished/Already nao mudam nada.
        /// </summary>
        public CollectStatus Collect(NativeRulesCore rules, out ExpeditionReport report)
        {
            report = null;
            if (Save == null) return CollectStatus.Error;
            var summary = Save.Summary;
            if (!summary.HasRunningExpedition) return CollectStatus.Already;
            var status = Save.CollectExpedition(rules, summary.RunningExpedition, Clock, out var json, out _);
            if (status == CollectStatus.Collected)
            {
                report = ExpeditionReport.Parse(json);
                saves.Save(rules);
            }
            return status;
        }
    }

    /// <summary>
    /// A sessao de jogo entre cenas: o servico de save, o de expedicao e o relogio. Estatico porque o GameRoot (regras) e recriado a cada cena,
    /// mas o save em memoria e o slot atual atravessam as trocas de cena.
    /// </summary>
    public static class GameSession
    {
        static SaveService save;
        static ExpeditionService expedition;

        public static SaveService Save => save ?? (save = new SaveService(System.IO.Path.Combine(UnityEngine.Application.persistentDataPath, "saves"), new SystemGameClock()));

        public static ExpeditionService Expedition => expedition ?? (expedition = new ExpeditionService(Save));

        /// <summary>Troca o servico de save (testes: pasta temporaria e relogio falso).</summary>
        public static void Use(SaveService service)
        {
            save?.Dispose();
            save = service;
            expedition = new ExpeditionService(service);
        }

        public static void Reset()
        {
            save?.Dispose();
            save = null;
            expedition = null;
        }

        /// <summary>O motor nativo da cena atual, ou null se o jogo caiu no stub (sem save nem expedicao).</summary>
        public static NativeRulesCore NativeRules(GameRoot root) => root != null && root.Rules != null ? root.Rules.Core as NativeRulesCore : null;
    }
}
