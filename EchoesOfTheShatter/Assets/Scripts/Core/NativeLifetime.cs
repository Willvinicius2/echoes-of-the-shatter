using Echoes.Interop.Native;
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
#endif

namespace Echoes.Core
{
    /// <summary>
    /// Dono do ciclo de vida dos handles da DLL no processo da Unity (docs/tecnico/04_arquitetura.md, secao 9.4, e A-06 da revisao).
    /// Cada <c>SafeHandle</c> tem dono (quem criou descarta: RulesService, AttributeComponent, TestWorld); este hook e a rede de
    /// seguranca para tudo que sobrou: descarta os nucleos nativos vivos ao fechar o jogo, ao sair do Play e antes da recarga
    /// de dominio do editor. Com "Enter Play Mode Options" (sem recarga) nenhum static guarda handle entre sessoes de Play.
    /// </summary>
    public static class NativeLifetime
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void RegisterRuntime()
        {
            // Entrada no Play sem recarga de dominio: sobras da sessao anterior saem antes de a nova comecar.
            NativeRulesCore.DisposeAllLive();
            Application.quitting -= NativeRulesCore.DisposeAllLive;
            Application.quitting += NativeRulesCore.DisposeAllLive;
        }

#if UNITY_EDITOR
        [InitializeOnLoadMethod]
        static void RegisterEditor()
        {
            AssemblyReloadEvents.beforeAssemblyReload -= NativeRulesCore.DisposeAllLive;
            AssemblyReloadEvents.beforeAssemblyReload += NativeRulesCore.DisposeAllLive;
            EditorApplication.playModeStateChanged -= OnPlayModeChanged;
            EditorApplication.playModeStateChanged += OnPlayModeChanged;
        }

        static void OnPlayModeChanged(PlayModeStateChange change)
        {
            if (change == PlayModeStateChange.ExitingPlayMode) NativeRulesCore.DisposeAllLive();
        }
#endif
    }
}
