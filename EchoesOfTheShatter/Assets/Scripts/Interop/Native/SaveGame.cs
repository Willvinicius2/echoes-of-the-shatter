using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace Echoes.Interop.Native
{
    public enum LoadOutcome { Ok = 0, NotFound, VersionMismatch, AllCorrupt, IoError, Failed }

    public enum StartCheck { Ok = 0, MapNotConquered, NotEnoughCharges, AnotherRunning, InvalidDuration, TooManyRules, IdleIncompatible, UnknownContent, Error = 99 }

    public enum CollectStatus { Collected = 0, Already = 1, NotFinished = 2, Error = 99 }

    public enum Calibration { None = 0, ManualEstimate = 1, BotParity = 2 }

    /// <summary>Entradas do relogio confiavel (docs/04, secao 9): relogio local, Steam (se houver) e o ultimo visto do save.</summary>
    public readonly struct ClockInput
    {
        public readonly long LocalNowUtc, SteamNowUtc, LastSeenUtc;
        public readonly bool HasSteam;

        public ClockInput(long localNowUtc, long lastSeenUtc, long steamNowUtc = 0, bool hasSteam = false)
        {
            LocalNowUtc = localNowUtc;
            LastSeenUtc = lastSeenUtc;
            SteamNowUtc = steamNowUtc;
            HasSteam = hasSteam;
        }
    }

    public readonly struct TrustedNow
    {
        public readonly long Now;
        public readonly bool UsedSteam, RollbackDetected;

        public TrustedNow(long now, bool usedSteam, bool rollbackDetected)
        {
            Now = now;
            UsedSteam = usedSteam;
            RollbackDetected = rollbackDetected;
        }
    }

    public readonly struct SaveSummary
    {
        public readonly long LastSeenUtc, LastRestDay;
        public readonly uint ContentVersion;
        public readonly int SaveVersion, CharacterCount, MarkerCharges, ExpeditionSlots, ExpeditionCount, RunningExpedition;

        internal SaveSummary(in ShatterSaveSummary s)
        {
            LastSeenUtc = s.last_seen_utc;
            LastRestDay = s.last_rest_day;
            ContentVersion = s.content_version;
            SaveVersion = s.save_version;
            CharacterCount = s.character_count;
            MarkerCharges = s.marker_charges;
            ExpeditionSlots = s.expedition_slots;
            ExpeditionCount = s.expedition_count;
            RunningExpedition = s.running_expedition;
        }

        public bool HasRunningExpedition => RunningExpedition >= 0;
    }

    public readonly struct ForecastBands
    {
        public readonly double XpP10, XpP50, XpP90, GoldP10, GoldP50, GoldP90, RetreatProbability;
        public readonly Calibration Calibration;

        internal ForecastBands(in ShatterForecastBandsEx f)
        {
            XpP10 = f.baseValue.xp_p10;
            XpP50 = f.baseValue.xp_p50;
            XpP90 = f.baseValue.xp_p90;
            GoldP10 = f.baseValue.gold_p10;
            GoldP50 = f.baseValue.gold_p50;
            GoldP90 = f.baseValue.gold_p90;
            RetreatProbability = f.baseValue.retreat_probability;
            Calibration = (Calibration)f.calibration;
        }
    }

    public readonly struct AreaRunReward
    {
        public readonly int ChargesGained;
        public readonly bool NewConquest;

        public AreaRunReward(int chargesGained, bool newConquest)
        {
            ChargesGained = chargesGained;
            NewConquest = newConquest;
        }
    }

    /// <summary>
    /// O save em memoria (shatter_save). Tudo passa pelo core: ler (com backups), gravar com seguranca, descanso diario, conquista de area,
    /// expedicao (so as chamadas _trusted: inicio com o relogio confiavel e coleta recalculada pelo core) e coleta uma vez so.
    /// Main thread. Cada chamada recebe as regras (o banco de conteudo) da cena atual.
    /// </summary>
    public sealed unsafe class SaveGame : IDisposable
    {
        const string FormatTag = "echoes-of-the-shatter-save";
        readonly SaveHandle handle;

        SaveGame(SaveHandle handle)
        {
            this.handle = handle;
        }

        public void Dispose() => handle.Dispose();

        IntPtr Raw => handle.DangerousGetHandle();

        // ------------------------------------------------------------------------------ criar, ler, gravar

        /// <summary>Novo jogo: um Guerreiro nivel 1 com o kit inicial (6 pecas Comuns vset.starter, pocoes cheias, 0 Ouro, 0 cargas).</summary>
        public static SaveGame NewGame(NativeRulesCore rules, string name, long nowUtc, out string error)
        {
            var save = FromData(rules, BuildNewGameData(rules.ContentVersion, name, nowUtc, false), out error);
            if (save == null) save = FromData(rules, BuildNewGameData(rules.ContentVersion, name, nowUtc, true), out error);
            return save;
        }

        static SaveGame FromData(NativeRulesCore rules, string dataJson, out string error)
        {
            var saveVersion = CurrentSaveVersion();
            var sha = BitConverter.ToString(SHA256.Create().ComputeHash(Encoding.UTF8.GetBytes(dataJson))).Replace("-", string.Empty).ToLowerInvariant();
            var envelope = "{\"format\":\"" + FormatTag + "\",\"save_version\":" + saveVersion + ",\"sha256\":\"" + sha + "\",\"data\":" + dataJson + "}";
            return FromJson(envelope, out error);
        }

        static int CurrentSaveVersion()
        {
            IntPtr raw;
            if (ShatterNative.shatter_save_create(&raw) != 0) return 2;
            try
            {
                ShatterSaveSummary summary;
                return ShatterNative.shatter_save_summary_get(raw, &summary) == 0 ? summary.save_version : 2;
            }
            finally
            {
                ShatterNative.shatter_save_destroy(raw);
            }
        }

        /// <summary>Os dados do jogo novo no formato "data" do save (compacto, para o checksum do core bater).</summary>
        public static string BuildNewGameData(uint contentVersion, string name, long nowUtc, bool asciiName)
        {
            var quoted = asciiName ? MiniJson.QuoteAscii(name) : MiniJson.Quote(name);
            string Item(int uid, string baseId) => "{\"uid\":\"" + uid + "\",\"base_id\":\"" + baseId + "\",\"rarity\":\"normal\",\"item_level\":1,\"unique_id\":\"\",\"affixes\":[],\"has_inscription\":false}";
            var sb = new StringBuilder(2048);
            sb.Append("{\"save_version\":").Append(CurrentSaveVersion()).Append(",\"content_version\":").Append(contentVersion);
            sb.Append(",\"characters\":[{\"name\":").Append(quoted).Append(",\"class_id\":\"class.warrior\",\"spec_id\":\"\",\"level\":1,\"xp\":0,\"passives\":[]");
            sb.Append(",\"skills\":[");
            var skills = new[] { "skill.warrior.iron_cut", "skill.warrior.charge", "skill.warrior.stone_rift", "skill.warrior.shield_bash" };
            for (var i = 0; i < skills.Length; i++) sb.Append(i > 0 ? "," : string.Empty).Append("{\"skill_id\":\"").Append(skills[i]).Append("\",\"rank\":1,\"sigils\":[]}");
            sb.Append("],\"skill_bar\":[");
            for (var i = 0; i < 6; i++) sb.Append(i > 0 ? "," : string.Empty).Append(i < skills.Length ? "\"" + skills[i] + "\"" : "\"\"");
            sb.Append("],\"equipment\":{");
            sb.Append("\"main_hand\":").Append(Item(1, "item_base.iron_sword"));
            sb.Append(",\"off_hand\":null,\"head\":").Append(Item(2, "item_base.iron_helm"));
            sb.Append(",\"body\":").Append(Item(3, "item_base.leather_vest"));
            sb.Append(",\"hands\":").Append(Item(4, "item_base.leather_gloves"));
            sb.Append(",\"feet\":").Append(Item(5, "item_base.worn_boots"));
            sb.Append(",\"amulet\":null,\"ring\":null,\"ring2\":null,\"belt\":null,\"legs\":").Append(Item(6, "item_base.worn_trousers")).Append('}');
            sb.Append(",\"conquered_maps\":[],\"highest_tier_cleared\":0");
            sb.Append(",\"potion_slots\":[{\"potion_id\":\"potion.life\",\"charges\":3,\"recharge_remaining\":0},{\"potion_id\":\"potion.ward\",\"charges\":2,\"recharge_remaining\":0}]");
            sb.Append(",\"boss_progress\":[],\"play_time_seconds\":0}]");
            sb.Append(",\"stash\":[],\"currencies\":[],\"marker_charges\":0,\"last_rest_day\":0,\"last_seen_utc\":").Append(nowUtc);
            sb.Append(",\"next_item_uid\":\"7\",\"expedition_slots\":1,\"expeditions\":[],\"codex_seen_uniques\":[],\"books_seen\":[]}");
            return sb.ToString();
        }

        /// <summary>Arquivo completo (envelope) para o core ler: confere o checksum e migra (v1 para v2).</summary>
        public static SaveGame FromJson(string json, out string error)
        {
            var bytes = Encoding.UTF8.GetBytes(json);
            IntPtr raw = IntPtr.Zero;
            int loadStatus;
            ShatterError err = default;
            int status;
            fixed (byte* p = bytes) status = ShatterNative.shatter_save_from_json(p, (nuint)bytes.Length, &raw, &loadStatus, &err);
            if (status != 0 || raw == IntPtr.Zero)
            {
                error = $"status {status}, load {loadStatus}: {NativeBuffers.ErrorMessage(ref err)}";
                return null;
            }
            error = string.Empty;
            return new SaveGame(new SaveHandle(raw));
        }

        /// <summary>
        /// Le o slot (<paramref name="basePath"/> sem extensao): o principal ou o backup mais recente valido. <paramref name="usedBackup"/> &gt; 0
        /// = a tela deve avisar (LoadedFromBackup). VersionMismatch deixa o arquivo intacto. AllCorrupt: nunca sobrescreva sem confirmar.
        /// </summary>
        public static LoadOutcome Read(NativeRulesCore rules, string basePath, out SaveGame save, out int usedBackup, out string error)
        {
            save = null;
            usedBackup = 0;
            error = string.Empty;
            var path = NativeBuffers.Utf8(basePath);
            IntPtr raw = IntPtr.Zero;
            ShatterLoadReport report = default;
            ShatterError err = default;
            int status;
            fixed (byte* p = path) status = ShatterNative.shatter_save_read(rules.DbPointer, p, (nuint)path.Length, &raw, &report, &err);
            if (status == 0 && raw != IntPtr.Zero)
            {
                save = new SaveGame(new SaveHandle(raw));
                usedBackup = report.used_backup;
                return LoadOutcome.Ok;
            }
            error = NativeBuffers.ErrorMessage(ref err);
            switch (status)
            {
                case 7: return LoadOutcome.NotFound;
                case 6: return LoadOutcome.VersionMismatch;
                case 3: return LoadOutcome.AllCorrupt;
                case 5: return LoadOutcome.IoError;
                default: return LoadOutcome.Failed;
            }
        }

        /// <summary>Gravacao segura do core (.tmp conferido, 3 backups rotativos, rename). Devolve false com a mensagem em <paramref name="error"/>.</summary>
        public bool Write(string basePath, out string error)
        {
            var path = NativeBuffers.Utf8(basePath);
            ShatterError err = default;
            int status;
            fixed (byte* p = path) status = ShatterNative.shatter_save_write(Raw, p, (nuint)path.Length, &err);
            error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
            return status == 0;
        }

        public string ToJson(bool pretty = false)
        {
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) => ShatterNative.shatter_save_to_json(save, (byte)(pretty ? 1 : 0), o, cap, needed), out var text, 8192);
            return status == 0 ? text : string.Empty;
        }

        public SaveSummary Summary
        {
            get
            {
                ShatterSaveSummary s;
                ShatterNative.shatter_save_summary_get(Raw, &s);
                return new SaveSummary(in s);
            }
        }

        /// <summary>Personagem <paramref name="index"/> no formato CharacterState do save (JSON).</summary>
        public string CharacterJson(int index)
        {
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) => ShatterNative.shatter_save_character_json(save, (nuint)index, o, cap, needed), out var text, 4096);
            return status == 0 ? text : string.Empty;
        }

        // ------------------------------------------------------------------------------ relogio

        /// <summary>Relogio confiavel: o core escolhe entre local e Steam e detecta relogio que voltou.</summary>
        public static TrustedNow ResolveNow(NativeRulesCore rules, in ClockInput input)
        {
            var raw = new ShatterClockInput { local_now_utc = input.LocalNowUtc, steam_now_utc = input.SteamNowUtc, last_seen_utc = input.LastSeenUtc, has_steam_time = (byte)(input.HasSteam ? 1 : 0) };
            ShatterRules r;
            ShatterNative.shatter_db_rules(rules.DbPointer, &r);
            ShatterTrustedNow now;
            ShatterNative.shatter_clock_resolve_now(&raw, &r, &now);
            return new TrustedNow(now.now, now.used_steam != 0, now.rollback_detected != 0);
        }

        public void TouchLastSeen(in TrustedNow now)
        {
            var raw = new ShatterTrustedNow { now = now.Now, used_steam = (byte)(now.UsedSteam ? 1 : 0), rollback_detected = (byte)(now.RollbackDetected ? 1 : 0) };
            ShatterNative.shatter_save_touch_last_seen(Raw, &raw);
        }

        /// <summary>Descanso diario (+4 cargas por dia UTC, sem acumular). Devolve as cargas depois.</summary>
        public int ApplyDailyRest(NativeRulesCore rules, in TrustedNow now)
        {
            var raw = new ShatterTrustedNow { now = now.Now, used_steam = (byte)(now.UsedSteam ? 1 : 0), rollback_detected = (byte)(now.RollbackDetected ? 1 : 0) };
            int charges;
            ShatterNative.shatter_save_apply_daily_rest(rules.DbPointer, Raw, &raw, &charges);
            return charges;
        }

        // ------------------------------------------------------------------------------ area

        /// <summary>Fim de uma corrida manual numa area: cargas e dominio (RF-35, RF-50).</summary>
        public AreaRunReward RecordAreaRun(NativeRulesCore rules, int characterIndex, string mapId, bool reachedEnd, bool bossDefeated)
        {
            var id = NativeBuffers.Utf8(mapId);
            ShatterAreaRunReward reward = default;
            fixed (byte* p = id) ShatterNative.shatter_save_record_area_run(rules.DbPointer, Raw, (nuint)characterIndex, p, (nuint)id.Length, (byte)(reachedEnd ? 1 : 0), (byte)(bossDefeated ? 1 : 0), &reward);
            return new AreaRunReward(reward.charges_gained, reward.new_conquest != 0);
        }

        // ------------------------------------------------------------------------------ expedicao (so as chamadas _trusted)

        /// <summary>Confere os parametros sem mudar o save. <paramref name="blockers"/> = JSON com os IDs que bloqueiam (RF-43).</summary>
        public StartCheck CheckExpedition(NativeRulesCore rules, string paramsJson, out string blockers)
        {
            var bytes = Encoding.UTF8.GetBytes(paramsJson);
            var buffer = new byte[256];
            for (var attempt = 0; attempt < 3; attempt++)
            {
                int check = 0;
                nuint needed = 0;
                ShatterError err = default;
                int status;
                fixed (byte* p = bytes)
                fixed (byte* o = buffer)
                    status = ShatterNative.shatter_expedition_check(rules.DbPointer, Raw, p, (nuint)bytes.Length, &check, o, (nuint)buffer.Length, &needed, &err);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, (int)needed)];
                    continue;
                }
                blockers = status == 0 ? Encoding.UTF8.GetString(buffer, 0, (int)needed) : string.Empty;
                return status == 0 ? (StartCheck)check : StartCheck.Error;
            }
            blockers = string.Empty;
            return StartCheck.Error;
        }

        /// <summary>Inicia a expedicao: start_utc vem do relogio confiavel e a seed e derivada pelo core (os campos "seed" e "start_utc" sao proibidos).</summary>
        public StartCheck StartExpedition(NativeRulesCore rules, string paramsJson, in TrustedNow now, out string error)
        {
            var bytes = Encoding.UTF8.GetBytes(paramsJson);
            var raw = new ShatterTrustedNow { now = now.Now, used_steam = (byte)(now.UsedSteam ? 1 : 0), rollback_detected = (byte)(now.RollbackDetected ? 1 : 0) };
            int check = 0;
            ShatterError err = default;
            int status;
            fixed (byte* p = bytes) status = ShatterNative.shatter_save_start_expedition_trusted(rules.DbPointer, Raw, p, (nuint)bytes.Length, &raw, &check, &err);
            error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
            return status == 0 ? (StartCheck)check : StartCheck.Error;
        }

        /// <summary>
        /// Coleta: o core recalcula o resultado pelo pedido salvo e pelo relogio confiavel (nada vem do chamador). NotFinished nao muda nada;
        /// Already = ja coletada (uma vez so, RF-55); Collected = itens, pilhas e XP entram no save (grave em seguida). <paramref name="resultJson"/>
        /// = ExpeditionResult em JSON.
        /// </summary>
        public CollectStatus CollectExpedition(NativeRulesCore rules, int index, in ClockInput clock, out string resultJson, out string error)
        {
            var raw = new ShatterClockInput { local_now_utc = clock.LocalNowUtc, steam_now_utc = clock.SteamNowUtc, last_seen_utc = clock.LastSeenUtc, has_steam_time = (byte)(clock.HasSteam ? 1 : 0) };
            var buffer = new byte[16384];
            for (var attempt = 0; attempt < 3; attempt++)
            {
                var collect = 0;
                nuint needed = 0;
                ShatterError err = default;
                int status;
                fixed (byte* o = buffer)
                    status = ShatterNative.shatter_save_collect_expedition_trusted(rules.DbPointer, Raw, (nuint)index, &raw, 0u, &collect, o, (nuint)buffer.Length, &needed, &err);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, (int)needed)];
                    continue;
                }
                resultJson = status == 0 ? Encoding.UTF8.GetString(buffer, 0, (int)needed) : string.Empty;
                error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
                return status == 0 ? (CollectStatus)collect : CollectStatus.Error;
            }
            resultJson = string.Empty;
            error = "buffer";
            return CollectStatus.Error;
        }

        /// <summary>
        /// Pedido de simulacao da expedicao <paramref name="index"/> (JSON do snapshot, regras, inicio e duracao) e a janela offline pelo relogio:
        /// <paramref name="finished"/> = a duracao acabou; <paramref name="effectiveSeconds"/> = o tempo contado (pode ser menor se o relogio voltou).
        /// </summary>
        public bool ExpeditionRequest(NativeRulesCore rules, int index, in ClockInput clock, out string requestJson, out bool finished, out double effectiveSeconds)
        {
            var raw = new ShatterClockInput { local_now_utc = clock.LocalNowUtc, steam_now_utc = clock.SteamNowUtc, last_seen_utc = clock.LastSeenUtc, has_steam_time = (byte)(clock.HasSteam ? 1 : 0) };
            var buffer = new byte[4096];
            for (var attempt = 0; attempt < 3; attempt++)
            {
                ShatterOfflineWindow window = default;
                nuint needed = 0;
                ShatterError err = default;
                int status;
                fixed (byte* o = buffer)
                    status = ShatterNative.shatter_save_expedition_request(rules.DbPointer, Raw, (nuint)index, &raw, &window, o, (nuint)buffer.Length, &needed, &err);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, (int)needed)];
                    continue;
                }
                requestJson = status == 0 ? Encoding.UTF8.GetString(buffer, 0, (int)needed) : string.Empty;
                finished = window.finished != 0;
                effectiveSeconds = window.effective_seconds;
                return status == 0;
            }
            requestJson = string.Empty;
            finished = false;
            effectiveSeconds = 0;
            return false;
        }

        /// <summary>Previsao em faixa (RF-40) a partir de um pedido de expedicao em JSON; o selo vem em <see cref="ForecastBands.Calibration"/>.</summary>
        public static bool Forecast(NativeRulesCore rules, string requestJson, int samples, out ForecastBands bands, out string error)
        {
            var bytes = Encoding.UTF8.GetBytes(requestJson);
            ShatterForecastBandsEx result = default;
            ShatterError err = default;
            int status;
            fixed (byte* p = bytes) status = ShatterNative.shatter_expedition_forecast_ex(rules.DbPointer, p, (nuint)bytes.Length, 1UL, samples, &result, &err);
            bands = status == 0 ? new ForecastBands(in result) : default;
            error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
            return status == 0;
        }

        // ------------------------------------------------------------------------------ arquivos do slot

        /// <summary>Apaga o principal e os backups de um slot (so por acao explicita do jogador).</summary>
        public static void DeleteSlotFiles(string basePath)
        {
            var dir = Path.GetDirectoryName(basePath);
            var prefix = Path.GetFileName(basePath);
            if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return;
            foreach (var file in Directory.GetFiles(dir, prefix + "*")) File.Delete(file);
        }
    }

    public sealed partial class NativeRulesCore
    {
        /// <summary>O ponteiro do banco de conteudo para a camada de save (o dono continua sendo este objeto).</summary>
        internal IntPtr DbPointer => RequireDb().DangerousGetHandle();
    }
}
