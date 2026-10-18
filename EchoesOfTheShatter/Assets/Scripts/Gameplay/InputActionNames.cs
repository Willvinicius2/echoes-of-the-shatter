namespace Echoes.Gameplay
{
    /// <summary>
    /// Nomes das ações do <c>Assets/Settings/Echoes.inputactions</c> (mapa Gameplay;
    /// docs/04_arquitetura.md, seções 2 e 10.4). Nenhuma tecla fica no código (RF-65).
    /// </summary>
    public static class InputActionNames
    {
        public const string Map = "Gameplay";
        public const string Move = "Move";
        public const string Aim = "Aim";
        public const string BasicAttack = "BasicAttack";
        public const string Skill1 = "Skill1";
        public const string Skill2 = "Skill2";
        public const string Skill3 = "Skill3";
        public const string Skill4 = "Skill4";
        public const string Skill5 = "Skill5";
        public const string Dodge = "Dodge";
        public const string Potion1 = "Potion1";
        public const string Potion2 = "Potion2";
        public const string Inventory = "Inventory";
        public const string PassiveTree = "PassiveTree";
        public const string WorldMap = "Map";
        public const string Pause = "Pause";
        public const string Interact = "Interact";
        public const string Flask = "Flask";

        /// <summary>Ação de cada <see cref="HeroCommand"/> (índice = valor do enum).</summary>
        public static readonly string[] ByCommand =
        {
            BasicAttack, Skill1, Skill2, Skill3, Skill4, Skill5, Dodge, Potion1, Potion2,
        };
    }
}
