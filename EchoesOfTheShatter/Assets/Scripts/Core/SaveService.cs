using System;
using System.IO;
using Echoes.Interop;
using Echoes.Interop.Native;
using UnityEngine;

namespace Echoes.Core
{
    /// <summary>Fonte de horario UTC (segundos Unix). O jogo usa o relogio do sistema; os testes usam um relogio falso.</summary>
    public interface IGameClock
    {
        long NowUtc { get; }
    }

    public sealed class SystemGameClock : IGameClock
    {
        /// <summary>Acelerador de debug (1 h = 10 s no teste): soma segundos ao relogio local. So avanca; o core detecta relogio que volta.</summary>
        public static long DebugOffsetSeconds;

        public long NowUtc => DateTimeOffset.UtcNow.ToUnixTimeSeconds() + DebugOffsetSeconds;
    }

    public sealed class FakeGameClock : IGameClock
    {
        public long Now;

        public FakeGameClock(long now) { Now = now; }

        public long NowUtc => Now;

        public void Advance(long seconds) { Now += seconds; }
    }

    /// <summary>
    /// Configuracoes do save e do fluxo de expedicao, em um lugar facil de mudar (o dono ainda vai decidir): numero de slots, autosave,
    /// heroi ocupado durante a expedicao e o acelerador de debug.
    /// </summary>
    public static class SaveSettings
    {
        /// <summary>Numero de slots de save (1 a 9). Padrao 1. Muda pela variavel ECHOES_SAVE_SLOTS ou pelo PlayerPrefs "echoes.save.slots".</summary>
        public static int SlotCount
        {
            get
            {
                var env = Environment.GetEnvironmentVariable("ECHOES_SAVE_SLOTS");
                if (int.TryParse(env, out var fromEnv)) return Mathf.Clamp(fromEnv, 1, 9);
                return Mathf.Clamp(PlayerPrefs.GetInt("echoes.save.slots", DefaultSlotCount), 1, 9);
            }
            set => PlayerPrefs.SetInt("echoes.save.slots", Mathf.Clamp(value, 1, 9));
        }

        public const int DefaultSlotCount = 1;

        /// <summary>Autosave a cada 5 min (RF-54) alem de ao trocar de area, ao coletar e ao sair.</summary>
        public const float AutosaveSeconds = 300f;

        /// <summary>O heroi fica OCUPADO enquanto a expedicao roda: o portal da Cripta fecha com a fala dlg.ilsa.busy. O dono pode mudar.</summary>
        public static bool HeroBusyDuringExpedition
        {
            get => PlayerPrefs.GetInt("echoes.exp.busy", 1) != 0;
            set => PlayerPrefs.SetInt("echoes.exp.busy", value ? 1 : 0);
        }

        /// <summary>Acelerador de debug da expedicao (F9 = +1 h, F10 = +12 h no Refugio). Ligado no prototipo para o dono testar sem esperar.</summary>
        public static bool DebugAccelerator
        {
            get => PlayerPrefs.GetInt("echoes.debug.accelerator", 1) != 0;
            set => PlayerPrefs.SetInt("echoes.debug.accelerator", value ? 1 : 0);
        }
    }

    public readonly struct SlotInfo
    {
        public readonly int Slot;
        public readonly LoadOutcome Outcome;
        public readonly string CharacterName;
        public readonly int Level, MarkerCharges;
        public readonly bool ExpeditionRunning;
        public readonly int UsedBackup;

        public SlotInfo(int slot, LoadOutcome outcome, string name, int level, int charges, bool running, int usedBackup)
        {
            Slot = slot;
            Outcome = outcome;
            CharacterName = name;
            Level = level;
            MarkerCharges = charges;
            ExpeditionRunning = running;
            UsedBackup = usedBackup;
        }

        public bool Exists => Outcome == LoadOutcome.Ok;
    }

    /// <summary>
    /// Save e load ponta a ponta pelo core (shatter_save_*): N slots (setting), gravacao segura com backups, autosave e o aviso de backup.
    /// Um slot = um arquivo <c>slot_N</c> em <c>Application.persistentDataPath/saves</c> (o core cuida de .tmp, checksum e 3 backups).
    /// </summary>
    public sealed class SaveService : IDisposable
    {
        public SaveService(string directory, IGameClock clock)
        {
            Directory = directory;
            Clock = clock;
        }

        public string Directory { get; }
        public IGameClock Clock { get; set; }
        public SaveGame Current { get; private set; }
        public int CurrentSlot { get; private set; } = -1;
        public bool HasSave => Current != null;

        /// <summary>O slot foi lido de um backup (o principal estava invalido): a tela avisa com ui.save.backup_loaded.</summary>
        public event Action<int, int> LoadedFromBackup;

        public string SlotPath(int slot) => Path.Combine(Directory, "slot_" + (slot + 1));

        public SlotInfo Peek(NativeRulesCore rules, int slot)
        {
            var outcome = SaveGame.Read(rules, SlotPath(slot), out var save, out var backup, out _);
            if (outcome != LoadOutcome.Ok) return new SlotInfo(slot, outcome, string.Empty, 0, 0, false, 0);
            using (save)
            {
                var character = MiniJson.AsObject(MiniJson.Parse(save.CharacterJson(0)));
                var summary = save.Summary;
                return new SlotInfo(slot, outcome, MiniJson.Str(character, "name"), MiniJson.Int(character, "level", 1), summary.MarkerCharges, summary.HasRunningExpedition, backup);
            }
        }

        public LoadOutcome Load(NativeRulesCore rules, int slot)
        {
            var outcome = SaveGame.Read(rules, SlotPath(slot), out var save, out var backup, out var error);
            if (outcome != LoadOutcome.Ok)
            {
                if (outcome != LoadOutcome.NotFound) Debug.LogWarning($"[Save] Slot {slot + 1}: {outcome} ({error})");
                return outcome;
            }
            Replace(save, slot);
            if (backup > 0)
            {
                Debug.LogWarning($"[Save] Slot {slot + 1} lido do backup {backup}.");
                LoadedFromBackup?.Invoke(slot, backup);
            }
            // Descanso diario: +4 cargas por dia UTC (sem acumular), aplicado ao abrir.
            var now = SaveGame.ResolveNow(rules, new ClockInput(Clock.NowUtc, Current.Summary.LastSeenUtc));
            Current.ApplyDailyRest(rules, now);
            return LoadOutcome.Ok;
        }

        /// <summary>Cria um jogo novo no slot (substitui o save em memoria) e grava.</summary>
        public bool NewGame(NativeRulesCore rules, int slot, string name)
        {
            var save = SaveGame.NewGame(rules, string.IsNullOrWhiteSpace(name) ? "Guerreiro" : name.Trim(), Clock.NowUtc, out var error);
            if (save == null)
            {
                Debug.LogError("[Save] Novo jogo falhou: " + error);
                return false;
            }
            Replace(save, slot);
            return Save(rules);
        }

        /// <summary>Grava o save atual (last_seen pelo relogio confiavel, depois a gravacao segura do core).</summary>
        public bool Save(NativeRulesCore rules)
        {
            if (Current == null || CurrentSlot < 0) return false;
            System.IO.Directory.CreateDirectory(Directory);
            var now = SaveGame.ResolveNow(rules, new ClockInput(Clock.NowUtc, Current.Summary.LastSeenUtc));
            Current.TouchLastSeen(now);
            if (Current.Write(SlotPath(CurrentSlot), out var error)) return true;
            Debug.LogError("[Save] Gravacao falhou: " + error);
            return false;
        }

        public void Delete(int slot)
        {
            if (slot == CurrentSlot) Close();
            SaveGame.DeleteSlotFiles(SlotPath(slot));
        }

        public void Close()
        {
            Current?.Dispose();
            Current = null;
            CurrentSlot = -1;
        }

        void Replace(SaveGame save, int slot)
        {
            Current?.Dispose();
            Current = save;
            CurrentSlot = slot;
        }

        public void Dispose() => Close();
    }
}
