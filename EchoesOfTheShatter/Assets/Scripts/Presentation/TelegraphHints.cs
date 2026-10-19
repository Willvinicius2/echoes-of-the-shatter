using System;

namespace Echoes.Presentation
{
    /// <summary>
    /// Dicas do golpe de um chefe pelos Ecos: o desenho no chão de um golpe com Eco só aparece depois que o core
    /// confirma o golpe como revelado (<c>IsSkillRevealed</c>). A animação de windup continua valendo.
    /// Sem história carregada (sandbox) o gate é nulo e tudo aparece. Quem liga o gate é o StoryDirector.
    /// </summary>
    public static class TelegraphHints
    {
        /// <summary>true = esconder o desenho no chão deste golpe por enquanto.</summary>
        public static Func<string, bool> Hidden;

        public static bool IsHidden(string skillId)
        {
            return Hidden != null && !string.IsNullOrEmpty(skillId) && Hidden(skillId);
        }
    }
}
