using System.Collections.Generic;
using Echoes.Core;
using Echoes.Interop;

namespace Echoes.UI
{
    /// <summary>
    /// Bloqueio da expedicao por habilidade ou item sem perfil idle (RF-43): o core devolve em <c>blockers</c> um JSON com os IDs que bloqueiam; a
    /// tela mostra o NOME de cada um (Loc, chave "&lt;id&gt;.name"). Tolerante ao formato: junta toda string do JSON que tenha nome no Loc.
    /// </summary>
    public static class ExpeditionBlockers
    {
        /// <summary>IDs com nome conhecido no Loc, na ordem do JSON e sem repetir.</summary>
        public static List<string> Ids(string blockersJson, LocalizationService loc)
        {
            var ids = new List<string>();
            if (string.IsNullOrWhiteSpace(blockersJson)) return ids;
            object parsed;
            try
            {
                parsed = MiniJson.Parse(blockersJson);
            }
            catch (System.Exception)
            {
                return ids;
            }
            Collect(parsed, loc, ids);
            return ids;
        }

        static void Collect(object node, LocalizationService loc, List<string> ids)
        {
            switch (node)
            {
                case string text:
                    if (!ids.Contains(text) && loc.TryGet(text + ".name", out _)) ids.Add(text);
                    break;
                case List<object> list:
                    foreach (var item in list) Collect(item, loc, ids);
                    break;
                case Dictionary<string, object> map:
                    foreach (var pair in map) Collect(pair.Value, loc, ids);
                    break;
            }
        }

        /// <summary>Nomes (Loc) separados por virgula, ou vazio se o core nao disse quem bloqueia.</summary>
        public static string Names(string blockersJson, LocalizationService loc)
        {
            var names = new List<string>();
            foreach (var id in Ids(blockersJson, loc)) names.Add(loc.Get(id + ".name"));
            return string.Join(", ", names);
        }
    }
}
