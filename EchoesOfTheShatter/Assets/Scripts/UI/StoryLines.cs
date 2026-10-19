using System.Collections.Generic;
using Echoes.Interop;

namespace Echoes.UI
{
    /// <summary>
    /// Quais falas da Regiao 1 (dialogue.csv) cada NPC do Refugio diz, conforme o progresso da historia (docs/design/21). Logica pura, sem Unity: o
    /// estado vem do core (<see cref="StoryState"/>), nada e gravado no save. Sem marca de "ja ouvi", a introducao se repete a cada conversa
    /// ate o jogador achar o primeiro Eco (decisao de prototipo).
    /// </summary>
    public static class StoryLines
    {
        /// <summary>Chaves de fala, em ordem, que o NPC diz agora. Vazio sem historia carregada (state null) ou NPC sem fala de historia.</summary>
        public static List<string> For(string npcId, StoryState state, string regionId)
        {
            var lines = new List<string>();
            if (state == null) return lines;
            var verdict = state.VerdictOf(regionId);
            var hasEchoes = state.Echoes.Count > 0;
            switch (npcId)
            {
                case InteractableNpc.Ilsa:
                    if (verdict == null)
                    {
                        if (hasEchoes) lines.Add("dlg.ilsa.general_lore");
                        else AddAll(lines, "dlg.ilsa.intro_1", "dlg.ilsa.intro_2", "dlg.ilsa.intro_3");
                    }
                    else
                    {
                        lines.Add(verdict.IsDevour ? "dlg.ilsa.after_devour" : "dlg.ilsa.after_exorcise");
                        lines.Add("dlg.ilsa.years_pass");
                    }
                    break;
                case InteractableNpc.Tico:
                    lines.Add(verdict != null ? "dlg.tico.after_years" : hasEchoes ? "dlg.tico.echo_found" : "dlg.tico.intro");
                    break;
                case InteractableNpc.Bram:
                    if (verdict != null && verdict.IsDevour) lines.Add("dlg.bram.after_devour");
                    else lines.Add(hasEchoes ? "dlg.bram.echo_blade" : "dlg.bram.intro");
                    lines.Add("dlg.bram.farewell");
                    break;
                case InteractableNpc.Odete:
                    lines.Add(hasEchoes || verdict != null ? "dlg.odete.echo_read" : "dlg.odete.intro");
                    if (verdict == null) lines.Add("dlg.odete.warning"); // o aviso vem antes da escolha
                    lines.Add("dlg.odete.farewell");
                    break;
            }
            return lines;
        }

        static void AddAll(List<string> lines, params string[] keys) => lines.AddRange(keys);
    }
}
