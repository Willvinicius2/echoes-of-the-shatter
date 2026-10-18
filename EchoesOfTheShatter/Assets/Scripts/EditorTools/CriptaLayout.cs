using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Layout da Cripta (docs/tecnico/14_layout_cripta.md, seção 11): o bloco JSON legível por máquina, lido direto do documento. O builder e os
    /// testes usam só estes dados; nenhum número do mapa é copiado para o código. Coordenadas em metros, <c>rect</c> = x0, z0, x1, z1.
    /// </summary>
    public sealed class CriptaLayout
    {
        public const string DocumentRelativePath = "docs/tecnico/14_layout_cripta.md";

        public sealed class RoomData
        {
            public string Id, Role;
            public Rect Rect; // x = x0, y = z0, width = x1 - x0, height = z1 - z0 (plano XZ)
        }

        public sealed class CorridorData
        {
            public string Id, From, To, Gate;
            public Rect Rect;
            public bool AlongX => Rect.width >= Rect.height;
        }

        public sealed class GroupData
        {
            public string EnemyId;
            public int Min, Max;
            public List<Vector2> Slots = new List<Vector2>();
            public List<Vector2> Patrol = new List<Vector2>();
            public bool RequireOnScreen;
            public string Facing;
        }

        public sealed class EncounterData
        {
            public string Id, Room;
            public int Order;
            public bool IsBoss;
            public List<GroupData> Groups = new List<GroupData>();
            public bool HasTrigger;
            public Rect Trigger;
            public Vector2 Respawn;
            public List<Vector2> SummonMarks = new List<Vector2>();
        }

        public sealed class PointData
        {
            public string Id, Room, Target, Active, LootTable, Secret;
            public Vector2 Pos;
        }

        public sealed class SecretData
        {
            public string Id, LeadsTo;
            public Rect Rect;
            public List<string> OpensWith = new List<string>();
        }

        public sealed class GateData
        {
            public string Id, OpensFrom, ClosesOn;
            public Vector2 Pos;
            public float Width;
        }

        public sealed class PillarData
        {
            public string Id;
            public Vector2 Pos;
            public float Radius, Height;
        }

        public string MapId;
        public Vector2 HeroSpawn;
        public float CorridorWidth;
        public float CameraHeight, VisibleHalfX, VisibleHalfZ, CameraYawDegrees;
        public readonly List<RoomData> Rooms = new List<RoomData>();
        public readonly List<CorridorData> Corridors = new List<CorridorData>();
        public readonly List<Vector2> Route = new List<Vector2>();
        public readonly List<EncounterData> Encounters = new List<EncounterData>();
        public readonly List<PointData> Checkpoints = new List<PointData>();
        public readonly List<PointData> Portals = new List<PointData>();
        public readonly List<PointData> Markers = new List<PointData>();
        public readonly List<PointData> Chests = new List<PointData>();
        public readonly List<SecretData> Secrets = new List<SecretData>();
        public readonly List<GateData> Gates = new List<GateData>();
        public readonly List<PillarData> Pillars = new List<PillarData>();
        public readonly List<RoomData> Vistas = new List<RoomData>();

        public static string DocumentPath => Path.GetFullPath(Path.Combine(Application.dataPath, "../../" + DocumentRelativePath));

        public static CriptaLayout LoadFromDocument() => LoadFromDocument(DocumentPath);

        public static CriptaLayout LoadFromDocument(string path)
        {
            if (!File.Exists(path)) throw new FileNotFoundException("Documento do layout nao encontrado", path);
            return ParseDocument(File.ReadAllText(path, Encoding.UTF8));
        }

        /// <summary>Extrai o ultimo bloco ```json do documento e le o layout.</summary>
        public static CriptaLayout ParseDocument(string markdown)
        {
            var open = markdown.LastIndexOf("```json", StringComparison.Ordinal);
            if (open < 0) throw new InvalidOperationException("O documento nao tem bloco ```json");
            var start = markdown.IndexOf('\n', open) + 1;
            var end = markdown.IndexOf("```", start, StringComparison.Ordinal);
            if (end < 0) throw new InvalidOperationException("Bloco ```json sem fechamento");
            return ParseJson(markdown.Substring(start, end - start));
        }

        public static CriptaLayout ParseJson(string json)
        {
            var root = MiniJson.Parse(json) as Dictionary<string, object>;
            if (root == null) throw new InvalidOperationException("JSON do layout invalido");
            var layout = new CriptaLayout { MapId = Str(root, "mapId") };

            var camera = Obj(root, "camera");
            layout.CameraHeight = Num(camera, "heightMeters");
            // O retangulo visivel e alinhado a TELA (direita/cima), nao aos eixos do mundo: a camera tem yaw (docs/14, bloco JSON).
            layout.VisibleHalfX = Num(camera, "visibleHalfScreenH") > 0f ? Num(camera, "visibleHalfScreenH") : Num(camera, "visibleHalfX");
            layout.VisibleHalfZ = Num(camera, "visibleHalfScreenV") > 0f ? Num(camera, "visibleHalfScreenV") : Num(camera, "visibleHalfZ");
            layout.CameraYawDegrees = Num(camera, "yawDegrees");
            layout.HeroSpawn = Vec(Arr(Obj(root, "hero"), "spawn"));
            layout.CorridorWidth = Num(root, "corridorWidth");

            foreach (var o in Items(root, "rooms")) layout.Rooms.Add(new RoomData { Id = Str(o, "id"), Role = Str(o, "role"), Rect = RectOf(o) });
            foreach (var o in Items(root, "corridors"))
                layout.Corridors.Add(new CorridorData { Id = Str(o, "id"), From = Str(o, "from"), To = Str(o, "to"), Gate = Str(o, "gate"), Rect = RectOf(o) });
            foreach (var p in Arr(root, "route")) layout.Route.Add(Vec((List<object>)p));

            foreach (var o in Items(root, "encounters"))
            {
                var e = new EncounterData { Id = Str(o, "id"), Room = Str(o, "room"), Order = (int)Num(o, "order"), IsBoss = Bool(o, "isBoss") };
                foreach (var g in Items(o, "groups"))
                {
                    var group = new GroupData { EnemyId = Str(g, "enemyId"), Min = (int)Num(g, "min"), Max = (int)Num(g, "max"), RequireOnScreen = Bool(g, "requireOnScreen"), Facing = Str(g, "facing") };
                    foreach (var s in Arr(g, "slots")) group.Slots.Add(Vec((List<object>)s));
                    foreach (var s in Arr(g, "patrol")) group.Patrol.Add(Vec((List<object>)s));
                    e.Groups.Add(group);
                }
                if (o.TryGetValue("trigger", out var t) && t is Dictionary<string, object> trigger)
                {
                    e.HasTrigger = true;
                    e.Trigger = RectOf(trigger);
                }
                if (o.ContainsKey("respawn")) e.Respawn = Vec(Arr(o, "respawn"));
                foreach (var s in Arr(o, "summonMarks")) e.SummonMarks.Add(Vec((List<object>)s));
                layout.Encounters.Add(e);
            }

            foreach (var o in Items(root, "checkpoints")) layout.Checkpoints.Add(Point(o));
            foreach (var o in Items(root, "portals")) layout.Portals.Add(Point(o));
            foreach (var o in Items(root, "markers")) layout.Markers.Add(Point(o));
            foreach (var o in Items(root, "chests")) layout.Chests.Add(Point(o));
            foreach (var o in Items(root, "secrets"))
            {
                var s = new SecretData { Id = Str(o, "id"), LeadsTo = Str(o, "leadsTo"), Rect = RectOf(o) };
                foreach (var w in Arr(o, "opensWith")) s.OpensWith.Add((string)w);
                layout.Secrets.Add(s);
            }
            foreach (var o in Items(root, "gates"))
                layout.Gates.Add(new GateData { Id = Str(o, "id"), OpensFrom = Str(o, "opensFrom"), ClosesOn = Str(o, "closesOn"), Pos = Vec(Arr(o, "pos")), Width = Num(o, "width") });
            foreach (var o in Items(root, "pillars"))
                layout.Pillars.Add(new PillarData { Id = Str(o, "id"), Pos = Vec(Arr(o, "pos")), Radius = Num(o, "radius"), Height = Num(o, "height") });
            foreach (var o in Items(root, "vistas")) layout.Vistas.Add(new RoomData { Id = Str(o, "id"), Rect = RectOf(o) });
            return layout;
        }

        public RoomData Room(string id) => Rooms.Find(r => r.Id == id);

        public int EnemyCount(EncounterData e)
        {
            var n = 0;
            foreach (var g in e.Groups) n += Math.Min(g.Max, g.Slots.Count);
            return n;
        }

        // ---------------------------------------------------------------------------------------------- JSON helpers

        static PointData Point(Dictionary<string, object> o)
        {
            return new PointData
            {
                Id = Str(o, "id"), Room = Str(o, "room"), Target = Str(o, "target"), Active = Str(o, "active"),
                LootTable = Str(o, "lootTable"), Secret = Str(o, "secret"), Pos = Vec(Arr(o, "pos")),
            };
        }

        static Rect RectOf(Dictionary<string, object> o)
        {
            var r = Arr(o, "rect");
            var x0 = Convert.ToSingle(r[0], CultureInfo.InvariantCulture);
            var z0 = Convert.ToSingle(r[1], CultureInfo.InvariantCulture);
            var x1 = Convert.ToSingle(r[2], CultureInfo.InvariantCulture);
            var z1 = Convert.ToSingle(r[3], CultureInfo.InvariantCulture);
            return new Rect(x0, z0, x1 - x0, z1 - z0);
        }

        static Vector2 Vec(List<object> a) =>
            new Vector2(Convert.ToSingle(a[0], CultureInfo.InvariantCulture), Convert.ToSingle(a[1], CultureInfo.InvariantCulture));

        static string Str(Dictionary<string, object> o, string key) => o != null && o.TryGetValue(key, out var v) && v is string s ? s : string.Empty;

        static float Num(Dictionary<string, object> o, string key) => o != null && o.TryGetValue(key, out var v) && v is double d ? (float)d : 0f;

        static bool Bool(Dictionary<string, object> o, string key) => o != null && o.TryGetValue(key, out var v) && v is bool b && b;

        static Dictionary<string, object> Obj(Dictionary<string, object> o, string key) => o.TryGetValue(key, out var v) ? v as Dictionary<string, object> : null;

        static List<object> Arr(Dictionary<string, object> o, string key) => o != null && o.TryGetValue(key, out var v) && v is List<object> l ? l : new List<object>();

        static IEnumerable<Dictionary<string, object>> Items(Dictionary<string, object> o, string key)
        {
            foreach (var item in Arr(o, key))
            {
                if (item is Dictionary<string, object> d) yield return d;
            }
        }
    }

    /// <summary>Leitor minimo de JSON (objetos, listas, textos, numeros, booleanos e nulo), so para o bloco do layout.</summary>
    internal static class MiniJson
    {
        public static object Parse(string text)
        {
            var i = 0;
            var value = ReadValue(text, ref i);
            return value;
        }

        static void SkipSpace(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        static object ReadValue(string s, ref int i)
        {
            SkipSpace(s, ref i);
            if (i >= s.Length) throw new FormatException("JSON truncado");
            var c = s[i];
            if (c == '{') return ReadObject(s, ref i);
            if (c == '[') return ReadArray(s, ref i);
            if (c == '"') return ReadString(s, ref i);
            if (string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
            if (string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
            if (string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
            var start = i;
            while (i < s.Length && (char.IsDigit(s[i]) || s[i] == '-' || s[i] == '+' || s[i] == '.' || s[i] == 'e' || s[i] == 'E')) i++;
            if (start == i) throw new FormatException("Valor JSON invalido na posicao " + i);
            return double.Parse(s.Substring(start, i - start), CultureInfo.InvariantCulture);
        }

        static Dictionary<string, object> ReadObject(string s, ref int i)
        {
            var result = new Dictionary<string, object>();
            i++;
            SkipSpace(s, ref i);
            if (s[i] == '}') { i++; return result; }
            while (true)
            {
                SkipSpace(s, ref i);
                var key = ReadString(s, ref i);
                SkipSpace(s, ref i);
                if (s[i] != ':') throw new FormatException("Esperado ':' na posicao " + i);
                i++;
                result[key] = ReadValue(s, ref i);
                SkipSpace(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return result; }
                throw new FormatException("Esperado ',' ou '}' na posicao " + i);
            }
        }

        static List<object> ReadArray(string s, ref int i)
        {
            var result = new List<object>();
            i++;
            SkipSpace(s, ref i);
            if (s[i] == ']') { i++; return result; }
            while (true)
            {
                result.Add(ReadValue(s, ref i));
                SkipSpace(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return result; }
                throw new FormatException("Esperado ',' ou ']' na posicao " + i);
            }
        }

        static string ReadString(string s, ref int i)
        {
            if (s[i] != '"') throw new FormatException("Esperado '\"' na posicao " + i);
            i++;
            var sb = new StringBuilder();
            while (s[i] != '"')
            {
                if (s[i] == '\\')
                {
                    i++;
                    switch (s[i])
                    {
                        case 'n': sb.Append('\n'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u': sb.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; break;
                        default: sb.Append(s[i]); break;
                    }
                    i++;
                    continue;
                }
                sb.Append(s[i++]);
            }
            i++;
            return sb.ToString();
        }
    }
}
