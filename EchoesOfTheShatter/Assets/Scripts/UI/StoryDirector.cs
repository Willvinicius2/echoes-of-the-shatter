using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// A historia da Regiao 1 no cliente (docs/design/21 e 22): Ecos da Queda na Cripta, tela de veredito depois de vencer o Guardiao, Fome na HUD e o
    /// estado do Refugio (vila fortificada ou guarnicao) conforme a escolha. Toda regra (Ecos, veredito irreversivel, Fome, bonus) e do core
    /// (<see cref="StoryDb"/> / <see cref="SaveGame"/>); aqui so chamadas, UI e a ligacao com a cena. Nasce sozinho nas cenas Cripta e Refugio (nao
    /// precisa estar na cena) e fica desligado sem save carregado ou sem a pasta Story/.
    /// </summary>
    public sealed class StoryDirector : MonoBehaviour
    {
        public const string RegionId = "region.r1.crypt";

        /// <summary>Onde cada Eco aparece na Cripta (docs/tecnico/14, salas fora da rota principal), na ordem de echoes.csv da regiao. Sobra de Ecos sem ponto: sem brilho.</summary>
        static readonly Vector3[] CryptEchoSpots =
        {
            new Vector3(30f, 0.9f, 5f),    // r01, canto da Sala da Patrulha A
            new Vector3(-14f, 0.9f, 64f),  // r05, Sala da Linha de Tiro
            new Vector3(48f, 0.9f, 104f),  // r07, Sala da Elite Veloz
        };

        static readonly Color VillageTint = new Color(0.55f, 0.85f, 0.5f, 1f);
        static readonly Color GarrisonTint = new Color(0.95f, 0.5f, 0.35f, 1f);
        const float HubTintAmount = 0.2f;
        const float VerdictDelaySeconds = 3.2f;
        const float PostVerdictBannerSeconds = 3.5f;

        sealed class EchoRow
        {
            public string Id;
            public readonly List<string> RevealsSkills = new List<string>();
        }

        public static StoryDirector Current { get; private set; }

        /// <summary>A tela de veredito esta aberta (pausa e inventario esperam).</summary>
        public static bool VerdictOpen { get; private set; }

        GameRoot root;
        NativeRulesCore rules;
        StoryDb db;
        ScreenHost host;
        HeroController hero;
        VerdictScreen verdictScreen;
        VisualElement hungerBox;
        Label hungerLabel;
        bool subscribed;
        bool verdictQueued;
        bool applying;
        readonly List<EchoRow> echoRows = new List<EchoRow>();
        readonly Dictionary<string, EchoPickup> pickups = new Dictionary<string, EchoPickup>();

        public bool IsLoaded => db != null;
        public StoryDb Db => db;

        LocalizationService Loc => root.Localization;
        SaveGame Save => GameSession.Save.Current;

        // ------------------------------------------------------------------------------------------------ ciclo de vida

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Install()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
            SceneManager.sceneLoaded += OnSceneLoaded;
        }

        static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            if (scene.name != GameFlow.CriptaScene && scene.name != GameFlow.RefugeScene) return;
            if (FindAnyObjectByType<StoryDirector>() != null) return;
            new GameObject("StoryDirector").AddComponent<StoryDirector>();
        }

        void Awake()
        {
            Current = this;
            root = FindAnyObjectByType<GameRoot>();
            rules = GameSession.NativeRules(root);
            if (rules == null || !GameSession.Save.HasSave) { enabled = false; return; }
            var directory = Path.Combine(root.Rules.DataDirectory, "Story");
            db = StoryDb.Load(rules, directory, out var error);
            if (db == null)
            {
                Debug.LogWarning("[Story] Historia desligada: " + error);
                enabled = false;
                return;
            }
            LoadEchoRows(directory);
            // O bonus tem de estar no save ANTES de o heroi montar os atributos (HeroController.Start).
            Save.ApplyStoryState(Save.ReadStory(db));
        }

        void Start()
        {
            if (db == null) return;
            host = ScreenHost.Current;
            hero = FindAnyObjectByType<HeroController>();
            BuildHud();
            RefreshHud();
            var state = Save.ReadStory(db);
            if (state.StatBonusPct > 0.0 && hero != null) hero.RefreshFromSave();

            if (SceneManager.GetActiveScene().name == GameFlow.CriptaScene) StartCrypt(state);
            else StartRefuge(state);
        }

        void OnDestroy()
        {
            if (Current == this) Current = null;
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<ArenaStateEvent>(OnArena);
            if (VerdictOpen)
            {
                VerdictOpen = false;
                Time.timeScale = 1f;
            }
            db?.Dispose();
            db = null;
        }

        // ------------------------------------------------------------------------------------------------ Cripta

        void StartCrypt(StoryState state)
        {
            if (root.Events != null)
            {
                root.Events.Subscribe<ArenaStateEvent>(OnArena);
                subscribed = true;
            }
            SpawnEchoes(state);
            var verdict = state.VerdictOf(RegionId);
            if (verdict != null) ShowRegionState(verdict);
        }

        void SpawnEchoes(StoryState state)
        {
            for (var i = 0; i < echoRows.Count && i < CryptEchoSpots.Length; i++)
            {
                var echo = echoRows[i];
                if (state.HasEcho(echo.Id)) continue;
                pickups[echo.Id] = EchoPickup.Spawn(this, echo.Id, CryptEchoSpots[i]);
            }
        }

        /// <summary>Recolhe um Eco: o core registra (ou recusa), o save e gravado e o jogador e avisado. false = nao registrou.</summary>
        public bool CollectEcho(string echoId)
        {
            if (db == null || !Save.StoryRecordEcho(db, echoId, out var isNew)) return false;
            if (!isNew) return true;
            GameSession.Save.Save(rules);
            ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.story.echo_found", ("name", Loc.Get(echoId + ".name"))), ToastKind.Item);
            var echo = echoRows.Find(e => e.Id == echoId);
            if (echo != null)
            {
                foreach (var skill in echo.RevealsSkills)
                {
                    if (Save.StorySkillRevealed(db, RegionId, skill))
                    {
                        ScreenHost.Toast(Loc.Get("ui.story.echo_skill_revealed"), ToastKind.Banner);
                        break;
                    }
                }
            }
            return true;
        }

        void OnArena(in ArenaStateEvent evt)
        {
            if (evt.Phase != ArenaPhase.Won || verdictQueued) return;
            verdictQueued = true;
            // O RunRecorder grava a vitoria sobre o General no save no mesmo evento; o veredito espera isso (o core recusa sem o General vencido).
            StartCoroutine(OpenVerdictAfterDelay());
        }

        IEnumerator OpenVerdictAfterDelay()
        {
            var region = Save.ReadStoryRegion(db, RegionId);
            if (region.RegionId.Length == 0 || region.Decided || region.Options.Count < 2) yield break;
            ScreenHost.Banner(Loc.Get("dlg.guardian.kneel"), null, VerdictDelaySeconds - 0.2f);
            yield return new WaitForSecondsRealtime(VerdictDelaySeconds);
            OpenVerdict(region);
        }

        void OpenVerdict(StoryRegionInfo region)
        {
            if (host == null || host.Root == null) host = ScreenHost.Current;
            if (host == null) return;
            VerdictOpen = true;
            applying = false;
            Time.timeScale = 0f;
            verdictScreen = new VerdictScreen(host.Root, Loc, region, OnVerdictChosen);
            verdictScreen.Show();
        }

        void CloseVerdict()
        {
            verdictScreen?.Close();
            verdictScreen = null;
            if (VerdictOpen) Time.timeScale = 1f;
            VerdictOpen = false;
        }

        void OnVerdictChosen(StoryVerdictInfo option)
        {
            if (applying || db == null) return;
            applying = true;
            var result = Save.StoryApplyVerdict(db, option.VerdictId);
            if (result != VerdictResult.Ok)
            {
                // Recusado (ex.: General ainda nao registrado como vencido): nada mudou; deixa escolher de novo.
                Debug.LogWarning("[Story] Veredito recusado: " + result);
                applying = false;
                return;
            }
            GameSession.Save.Save(rules); // RF-54: a escolha irreversivel vai para o disco antes de qualquer efeito
            CloseVerdict();
            var state = Save.ReadStory(db);
            Save.ApplyStoryState(state);
            if (hero != null) hero.RefreshFromSave();
            RefreshHud();
            Announce(option);
        }

        void Announce(StoryVerdictInfo option)
        {
            ScreenHost.Banner(Loc.Get(option.VerdictId + ".name"), option.LastWordsKey.Length > 0 ? Loc.Get(option.LastWordsKey) : null, PostVerdictBannerSeconds);
            if (!string.IsNullOrEmpty(option.GrantsRelic))
                ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.story.relic_gained", ("name", Loc.Get(option.GrantsRelic + ".name"))), ToastKind.Item);
            if (option.StatBonusPct > 0.0)
                ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.story.bonus_gained", ("n", ((long)option.StatBonusPct).ToString())), ToastKind.Info);
            if (!string.IsNullOrEmpty(option.GrantsSignature))
                ScreenHost.Toast(ScreenKit.Fmt(Loc, "ui.story.signature_gained", ("name", Loc.Get(option.GrantsSignature + ".name"))), ToastKind.Item);
            ShowRegionState(option);
        }

        void ShowRegionState(StoryVerdictInfo verdict)
        {
            var key = verdict.RegionState == "purified" ? "ui.story.region_purified" : verdict.RegionState == "stain" ? "ui.story.region_stain" : null;
            if (key != null) ScreenHost.Toast(Loc.Get(key), ToastKind.Banner);
        }

        // ------------------------------------------------------------------------------------------------ Refugio

        void StartRefuge(StoryState state)
        {
            var hub = state.HubState;
            if (string.IsNullOrEmpty(hub)) return;
            // Estado do Refugio pela escolha (hub_state do core). Provisorio: banner e um tom na luz ambiente; os modelos de cada estado
            // dependem de arte nova, que passa pela aprovacao do dono.
            ScreenHost.Banner(Loc.Get(hub + ".name"), Loc.Get(hub + ".desc"), PostVerdictBannerSeconds);
            ApplyHubTint(hub);
        }

        static void ApplyHubTint(string hubState)
        {
            var tint = hubState == "hub.fortified_village" ? VillageTint : hubState == "hub.fortified_garrison" ? GarrisonTint : (Color?)null;
            if (tint == null) return;
            RenderSettings.ambientLight = Color.Lerp(RenderSettings.ambientLight, tint.Value, HubTintAmount);
        }

        // ------------------------------------------------------------------------------------------------ Fome na HUD

        void BuildHud()
        {
            if (host == null || host.Root == null) return;
            hungerBox = new VisualElement { name = "hunger-hud" };
            hungerBox.style.position = Position.Absolute;
            hungerBox.style.top = 170;
            hungerBox.style.left = 28;
            hungerBox.style.paddingLeft = 12;
            hungerBox.style.paddingRight = 12;
            hungerBox.style.paddingTop = 4;
            hungerBox.style.paddingBottom = 4;
            hungerBox.style.backgroundColor = new Color(0.07f, 0.06f, 0.09f, 0.85f);
            hungerBox.style.borderBottomWidth = 2;
            hungerBox.style.borderBottomColor = ScreenKit.Bad;
            hungerBox.pickingMode = PickingMode.Ignore;
            hungerBox.style.display = DisplayStyle.None;
            hungerLabel = ScreenKit.Line(hungerBox, string.Empty, 22, ScreenKit.Bad, true);
            hungerLabel.pickingMode = PickingMode.Ignore;
            host.Root.Add(hungerBox);
        }

        /// <summary>Texto da Fome: "Fome ●●○○" (cheios = Fome atual, vazios = ate o maximo do core).</summary>
        public static string HungerText(string title, int hunger, int hungerMax)
        {
            var text = new StringBuilder(title).Append(' ');
            for (var i = 0; i < hungerMax; i++) text.Append(i < hunger ? '●' : '○');
            return text.ToString();
        }

        void RefreshHud()
        {
            if (hungerBox == null || db == null) return;
            var state = Save.ReadStory(db);
            // So aparece depois do primeiro veredito: antes dele a Fome nao existe para o jogador.
            var visible = state.HungerMax > 0 && state.Verdicts.Count > 0;
            hungerBox.style.display = visible ? DisplayStyle.Flex : DisplayStyle.None;
            if (visible) hungerLabel.text = HungerText(Loc.Get("ui.hunger.title"), state.Hunger, state.HungerMax);
        }

        // ------------------------------------------------------------------------------------------------ tabelas

        // echoes.csv (id,regionId,kind,revealsSkill,minToReveal): a ordem das linhas da regiao decide o ponto de cada Eco.
        void LoadEchoRows(string storyDirectory)
        {
            echoRows.Clear();
            var path = Path.Combine(storyDirectory, "echoes.csv");
            if (!File.Exists(path)) return;
            var lines = File.ReadAllLines(path, Encoding.UTF8);
            for (var i = 1; i < lines.Length; i++)
            {
                var cells = lines[i].Split(',');
                if (cells.Length < 4 || cells[1] != RegionId) continue;
                var row = new EchoRow { Id = cells[0] };
                if (cells[3].Length > 0) row.RevealsSkills.Add(cells[3]);
                echoRows.Add(row);
            }
        }
    }
}
