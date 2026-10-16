using System;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>Ícone de habilidade para a barra (T_Icon_Skill_&lt;id&gt;_128; docs/03, seção 2.11).</summary>
    [Serializable]
    public sealed class SkillIconEntry
    {
        public string skillId = string.Empty;
        public Texture2D icon;
    }
}
