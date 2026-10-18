using Echoes.Core;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>
    /// Label com texto por chave de localização (docs/tecnico/04_arquitetura.md, seção 7). No UXML:
    /// <c>&lt;Echoes.UI.LocLabel loc-key="ui.hud.dodge" /&gt;</c>. A tela chama <see cref="ApplyAll"/>
    /// ao abrir e quando o idioma muda; o UXML nunca tem texto literal.
    /// </summary>
    [UxmlElement]
    public partial class LocLabel : Label
    {
        [UxmlAttribute]
        public string LocKey { get; set; } = string.Empty;

        public void Apply(LocalizationService localization)
        {
            if (localization == null || string.IsNullOrEmpty(LocKey)) return;
            text = localization.Get(LocKey);
        }

        /// <summary>Aplica o texto em todos os LocLabel abaixo de <paramref name="root"/>.</summary>
        public static void ApplyAll(VisualElement root, LocalizationService localization)
        {
            if (root == null || localization == null) return;
            root.Query<LocLabel>().ForEach(label => label.Apply(localization));
        }
    }
}
