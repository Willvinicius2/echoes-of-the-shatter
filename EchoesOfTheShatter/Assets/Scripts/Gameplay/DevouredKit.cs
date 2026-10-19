using System.Collections.Generic;
using System.IO;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Habilidades devoradas do herói (veredito Devorar): o golpe-assinatura entra na barra e cada uso gasta Fome da corrida.
    /// Fome da corrida = Fome do save + usos × custo; passou da Fome máxima, o golpe fica negado até o herói renascer (zera a conta).
    /// Regra e números do core (<c>shatter_story_state_json</c>, story_rules.csv); aqui só a conta de uma corrida.
    /// </summary>
    public sealed class DevouredKit : IHungerGate
    {
        const string DevouredPrefix = "skill.devoured.";

        readonly HashSet<string> skills = new HashSet<string>();
        readonly int baseHunger;
        readonly int hungerMax;
        readonly int cost;
        int spent;

        public DevouredKit(StoryState state)
        {
            baseHunger = state.Hunger;
            hungerMax = state.HungerMax;
            cost = state.DevouredHungerCost;
            foreach (var verdict in state.Verdicts)
                if (!string.IsNullOrEmpty(verdict.GrantsSignature) && verdict.GrantsSignature.StartsWith(DevouredPrefix))
                    skills.Add(verdict.GrantsSignature);
        }

        /// <summary>Golpes devorados que o save já tem (um por veredito Devorar).</summary>
        public IReadOnlyCollection<string> Skills => skills;

        /// <summary>Fome da corrida (save + usos), limitada à Fome máxima.</summary>
        public int Hunger => hungerMax > 0 ? System.Math.Min(hungerMax, baseHunger + spent) : baseHunger + spent;

        public int HungerMax => hungerMax;

        /// <summary>Lê o estado da história do save; null se a história não carrega ou o herói não devorou nada.</summary>
        public static DevouredKit Load(GameRoot root, NativeRulesCore rules, SaveGame save)
        {
            var state = ReadState(root, rules, save);
            if (state == null) return null;
            var kit = new DevouredKit(state);
            return kit.skills.Count > 0 ? kit : null;
        }

        /// <summary>
        /// Estado da história lido direto do core (sem depender de o StoryDirector já ter nascido na cena). null se a história não carrega.
        /// Usado por quem monta a cena no Awake: sorteio de encontros (Mancha) e herói.
        /// </summary>
        public static StoryState ReadState(GameRoot root, NativeRulesCore rules, SaveGame save)
        {
            if (root == null || rules == null || save == null) return null;
            var db = StoryDb.Load(rules, Path.Combine(root.Rules.DataDirectory, "Story"), out _);
            if (db == null) return null;
            using (db) return save.ReadStory(db);
        }

        /// <summary>Coloca os golpes devorados nos espaços vazios da barra da lógica (6 espaços; o 1 é a defesa e fica de fora), do último (F) para trás.</summary>
        public void FillBar(string[] bar)
        {
            if (bar == null) return;
            foreach (var id in skills)
            {
                if (System.Array.IndexOf(bar, id) >= 0) continue;
                for (var i = bar.Length - 1; i >= 2; i--)
                {
                    if (!string.IsNullOrEmpty(bar[i])) continue;
                    bar[i] = id;
                    break;
                }
            }
        }

        public bool CanCast(string skillId)
        {
            if (!skills.Contains(skillId) || cost <= 0 || hungerMax <= 0) return true;
            return baseHunger + spent + cost <= hungerMax;
        }

        public void Spent(string skillId)
        {
            if (skills.Contains(skillId) && cost > 0) spent += cost;
        }

        /// <summary>O herói renasceu: a Fome da corrida volta para a do save.</summary>
        public void ResetRun() => spent = 0;
    }
}
