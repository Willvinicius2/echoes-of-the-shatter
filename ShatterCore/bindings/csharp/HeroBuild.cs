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

        /// <summary>Com save: os atributos saem do personagem do save (equipamento com afixos), pelo core; <see cref="EquipmentBaseIds"/> segue valendo para a arma e o visual.</summary>
        public readonly Native.SaveGame Save;
        public readonly int SaveCharacterIndex;

        public HeroBuild(string classId, int level, IReadOnlyList<string> equipmentBaseIds, Native.SaveGame save = null, int saveCharacterIndex = 0)
        {
            ClassId = classId;
            Level = level;
            EquipmentBaseIds = equipmentBaseIds;
            Save = save;
            SaveCharacterIndex = saveCharacterIndex;
        }
    }
}
