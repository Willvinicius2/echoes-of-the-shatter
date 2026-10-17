using System;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop.Native;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

namespace Echoes.UI
{
    /// <summary>Autosave a cada 5 min (RF-54) e ao sair do jogo; a troca de area e a coleta gravam por conta propria.</summary>
    public sealed class AutosaveRunner : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        float next;

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            next = Time.realtimeSinceStartup + SaveSettings.AutosaveSeconds;
        }

        void Update()
        {
            if (Time.realtimeSinceStartup < next) return;
            next = Time.realtimeSinceStartup + SaveSettings.AutosaveSeconds;
            SaveNow();
        }

        void OnApplicationQuit() => SaveNow();

        public void SaveNow()
        {
            var rules = GameSession.NativeRules(root);
            if (rules != null && GameSession.Save.HasSave) GameSession.Save.Save(rules);
        }
    }
}
