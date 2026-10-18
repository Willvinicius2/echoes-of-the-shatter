namespace Echoes.Gameplay
{
    /// <summary>O herói abriu um baú (o loot de verdade entra com o inventário; por enquanto só o evento).</summary>
    public struct ChestOpenedEvent
    {
        public string ChestId;
        public string LootTableId;
        public UnityEngine.Vector3 Position;
    }

    /// <summary>O herói limpou todos os inimigos de um encontro (a primeira vez na visita): a UI pede o loot da área ao core.</summary>
    public struct EncounterClearedEvent
    {
        public string EncounterId;
        public UnityEngine.Vector3 Position;
    }

    /// <summary>O atalho abriu (alavanca): o estado vai para o save pelo ID do portão.</summary>
    public struct ShortcutOpenedEvent
    {
        public string ShortcutId;
    }

    /// <summary>O herói passou num checkpoint novo (F-07): poções cheias, salvar e mostrar o retorno visual.</summary>
    public struct CheckpointReachedEvent
    {
        public string CheckpointId;
        public UnityEngine.Vector3 Position;
    }

    /// <summary>O herói entrou num portal. O Refúgio ainda não existe: o portal devolve ao checkpoint (TODO area.refuge).</summary>
    public struct PortalUsedEvent
    {
        public string PortalId;
        public string TargetArea;
    }

    /// <summary>A parede rachada abriu (Investida, Fenda de Pedra ou Escudada).</summary>
    public struct SecretOpenedEvent
    {
        public string SecretId;
    }

    /// <summary>Estado da luta do Guardião (porta da arena fecha atrás do herói e só reabre ao fim da luta).</summary>
    public enum ArenaPhase
    {
        Waiting,
        Fighting,
        Won,
    }

    public struct ArenaStateEvent
    {
        public ArenaPhase Phase;
    }
}
