using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// O que o motor precisa para montar os atributos do herói (equivale a um
    /// <c>CharacterState</c> reduzido). Os IDs de equipamento são bases de item; afixos entram
    /// quando o inventário existir.
    /// </summary>
    public readonly struct HeroBuild
    {
        public readonly string ClassId;
        public readonly int Level;
        public readonly IReadOnlyList<string> EquipmentBaseIds;

        public HeroBuild(string classId, int level, IReadOnlyList<string> equipmentBaseIds)
        {
            ClassId = classId;
            Level = level;
            EquipmentBaseIds = equipmentBaseIds;
        }
    }
}
