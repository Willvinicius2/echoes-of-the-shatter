using System;
using System.Collections.Generic;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Cenario da Cripta com o kit pintado (substitui o graybox e as primitivas): pisos na grade de 2 m com seed fixa, paredes de 2 m, postes de canto,
    /// pilares pintados, arcos nos corredores, vistas (abismo, colunata, portao) e props (sarcofagos, braseiros, ossos, velas, estandartes, entulho)
    /// espalhados pelas salas pelo layout do docs/14. Props com colisor ficam so na faixa junto das paredes, longe de vaos, da rota principal, dos
    /// espacos de inimigo, dos pilares da Investida e dos pontos de interacao; o que fica no meio do chao (ossos, velas, pedras) nao tem colisor
    /// nem entra na NavMesh.
    /// </summary>
    internal static class CriptaScenery
    {
        sealed class Keep
        {
            public Vector2 Pos;
            public float Radius;
        }

        sealed class Spots
        {
            public readonly List<Keep> Keeps = new List<Keep>();
            public readonly List<Rect> KeepRects = new List<Rect>();

            public bool Free(Vector2 p, float radius)
            {
                foreach (var k in Keeps) if ((k.Pos - p).sqrMagnitude < (k.Radius + radius) * (k.Radius + radius)) return false;
                foreach (var r in KeepRects)
                {
                    var e = new Rect(r.xMin - radius, r.yMin - radius, r.width + 2f * radius, r.height + 2f * radius);
                    if (e.Contains(p)) return false;
                }
                return true;
            }

            public void Add(Vector2 p, float radius) => Keeps.Add(new Keep { Pos = p, Radius = radius });
        }

        public static void Build(CriptaBuilder.Context ctx, Transform level, Transform decor)
        {
            var layout = ctx.Layout;
            EnvironmentKit.Import();
            var rooms = Group(level, "Rooms");
            var corridors = Group(level, "Corridors");
            var walls = Group(level, "Walls");
            var pillars = Group(level, "Pillars");
            var props = Group(level, "Props");
            var small = Group(decor, "SmallProps");

            var holes = new List<Rect>();
            foreach (var vista in layout.Vistas) if (vista.Id.Contains("pit")) holes.Add(vista.Rect);

            foreach (var room in layout.Rooms)
            {
                var go = new GameObject(room.Id);
                go.transform.SetParent(rooms, false);
                CriptaBuilder.AddFloorCollider(go.transform, room.Rect);
                SceneryBuilder.BuildFloor(go.transform, room.Id, room.Rect, holes);
            }
            foreach (var corridor in layout.Corridors)
            {
                var go = new GameObject(corridor.Id);
                go.transform.SetParent(corridors, false);
                CriptaBuilder.AddFloorCollider(go.transform, corridor.Rect);
                SceneryBuilder.BuildFloor(go.transform, corridor.Id, corridor.Rect, null);
            }

            foreach (var room in layout.Rooms)
            {
                BuildRoomWalls(layout, walls, room);
                SceneryBuilder.CornerPosts(walls, room.Id, room.Rect);
            }
            foreach (var corridor in layout.Corridors) BuildCorridorWalls(walls, corridor);

            BuildGlyphs(layout, decor);
            foreach (var p in layout.Pillars) BuildPillar(pillars, p);
            BuildVistas(ctx, level, decor);
            BuildCorridorArches(layout, props);
            BuildProps(ctx, props, small);
        }

        /// <summary>
        /// Simbolo de bussola so onde marca algo de jogo: checkpoint e portal (no maximo 2 por sala; corredor conta como a propria area). Nunca sorteado,
        /// nunca em grade, e os props e inimigos ja ficam longe desses pontos (Spots).
        /// </summary>
        static void BuildGlyphs(CriptaLayout layout, Transform decor)
        {
            var perArea = new Dictionary<string, int>();
            void Mark(string id, Vector2 pos)
            {
                var area = "";
                foreach (var r in layout.Rooms) if (r.Rect.Contains(pos)) area = r.Id;
                foreach (var c in layout.Corridors) if (c.Rect.Contains(pos)) area = c.Id;
                perArea.TryGetValue(area, out var n);
                if (n >= 2) return;
                perArea[area] = n + 1;
                SceneryBuilder.Glyph(decor, pos, 0f, id + ".glyph");
            }
            foreach (var cp in layout.Checkpoints) Mark(cp.Id, cp.Pos);
            foreach (var portal in layout.Portals) Mark(portal.Id, portal.Pos);
        }

        static Transform Group(Transform parent, string name)
        {
            var t = new GameObject(name).transform;
            t.SetParent(parent, false);
            return t;
        }

        // ============================================================================================== paredes

        /// <summary>Vaos de um lado da sala (0 sul, 1 norte, 2 oeste, 3 leste): onde um corredor (ou o segredo) encosta, como faixas ao longo do lado.</summary>
        public static List<Vector2> Openings(CriptaLayout layout, CriptaLayout.RoomData room, int side)
        {
            const float eps = 0.01f;
            var r = room.Rect;
            var alongX = side < 2;
            var line = side == 0 ? r.yMin : side == 1 ? r.yMax : side == 2 ? r.xMin : r.xMax;
            var a = alongX ? r.xMin : r.yMin;
            var b = alongX ? r.xMax : r.yMax;
            var openings = new List<Vector2>();
            foreach (var c in layout.Corridors)
            {
                var cr = c.Rect;
                bool touches;
                Vector2 span;
                switch (side)
                {
                    case 0: touches = Mathf.Abs(cr.yMax - line) < eps; span = new Vector2(cr.xMin, cr.xMax); break;
                    case 1: touches = Mathf.Abs(cr.yMin - line) < eps; span = new Vector2(cr.xMin, cr.xMax); break;
                    case 2: touches = Mathf.Abs(cr.xMax - line) < eps; span = new Vector2(cr.yMin, cr.yMax); break;
                    default: touches = Mathf.Abs(cr.xMin - line) < eps; span = new Vector2(cr.yMin, cr.yMax); break;
                }
                if (touches && span.y > a && span.x < b) openings.Add(span);
            }
            foreach (var s in layout.Secrets)
            {
                if (!alongX) continue; // parede rachada: vao nos lados sul/norte onde o retangulo do segredo atravessa a linha
                if (line >= s.Rect.yMin - eps && line <= s.Rect.yMax + eps && s.Rect.xMin >= a && s.Rect.xMax <= b) openings.Add(new Vector2(s.Rect.xMin, s.Rect.xMax));
            }
            openings.Sort((p, q) => p.x.CompareTo(q.x));
            return openings;
        }

        static void BuildRoomWalls(CriptaLayout layout, Transform parent, CriptaLayout.RoomData room)
        {
            const float eps = 0.01f;
            var r = room.Rect;
            for (var side = 0; side < 4; side++)
            {
                var alongX = side < 2;
                var line = side == 0 ? r.yMin : side == 1 ? r.yMax : side == 2 ? r.xMin : r.xMax;
                var a = alongX ? r.xMin : r.yMin;
                var b = alongX ? r.xMax : r.yMax;
                var outsidePositive = side == 1 || side == 3;
                var cursor = a;
                foreach (var o in Openings(layout, room, side))
                {
                    if (o.x > cursor + eps) SceneryBuilder.WallRun(parent, room.Id, alongX, line, cursor, o.x, outsidePositive);
                    cursor = Mathf.Max(cursor, o.y);
                }
                if (b > cursor + eps) SceneryBuilder.WallRun(parent, room.Id, alongX, line, cursor, b, outsidePositive);
            }
        }

        static void BuildCorridorWalls(Transform parent, CriptaLayout.CorridorData c)
        {
            var r = c.Rect;
            if (c.AlongX)
            {
                SceneryBuilder.WallRun(parent, c.Id, true, r.yMin, r.xMin, r.xMax, false);
                SceneryBuilder.WallRun(parent, c.Id, true, r.yMax, r.xMin, r.xMax, true);
            }
            else
            {
                SceneryBuilder.WallRun(parent, c.Id, false, r.xMin, r.yMin, r.yMax, false);
                SceneryBuilder.WallRun(parent, c.Id, false, r.xMax, r.yMin, r.yMax, true);
            }
        }

        // ============================================================================================== pilares, vistas, arcos

        /// <summary>Pilar pintado (PilarInteiro) na escala do raio e da altura do layout; o colisor e a capsula do layout (cobertura contra flecha e Investida).</summary>
        static void BuildPillar(Transform parent, CriptaLayout.PillarData p)
        {
            var piece = EnvironmentKit.Get("PilarInteiro");
            var xz = 2f * p.Radius / Mathf.Max(0.01f, piece.Size.x);
            var go = EnvironmentKit.Place("PilarInteiro", parent, new Vector3(p.Pos.x, 0f, p.Pos.y), 0f, new Vector3(xz, p.Height / Mathf.Max(0.01f, piece.Size.y), xz), colliders: false, instanceName: p.Id);
            var capsule = go.AddComponent<CapsuleCollider>();
            capsule.radius = p.Radius / xz;
            capsule.height = p.Height / go.transform.lossyScale.y;
            capsule.center = new Vector3(0f, capsule.height * 0.5f, 0f);
        }

        static void BuildVistas(CriptaBuilder.Context ctx, Transform level, Transform decor)
        {
            foreach (var vista in ctx.Layout.Vistas)
            {
                var r = vista.Rect;
                if (vista.Id.Contains("pit"))
                {
                    // Abismo parcial: sem piso dentro do retangulo, andar de baixo escuro, bordas de pedra e um bloco invisivel que impede entrar.
                    var block = new GameObject(vista.Id);
                    block.transform.SetParent(level, false);
                    var box = block.AddComponent<BoxCollider>();
                    box.center = new Vector3(r.center.x, 1.5f, r.center.y);
                    box.size = new Vector3(r.width, 3f, r.height);
                    var abyss = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    abyss.name = vista.Id + ".abyss";
                    Object.DestroyImmediate(abyss.GetComponent<Collider>());
                    abyss.transform.SetParent(decor, false);
                    abyss.transform.position = new Vector3(r.center.x, -2.5f, r.center.y);
                    abyss.transform.localScale = new Vector3(r.width, 0.1f, r.height);
                    abyss.GetComponent<Renderer>().sharedMaterial = EnsureAbyssMaterial();
                    abyss.GetComponent<Renderer>().shadowCastingMode = ShadowCastingMode.Off;
                    var edge = EnvironmentKit.Get("AbismoBordo");
                    foreach (var side in new[] { 0, 1, 2, 3 })
                    {
                        var alongX = side < 2;
                        var length = alongX ? r.width : r.height;
                        var count = Mathf.Max(1, Mathf.RoundToInt(length / edge.Size.x));
                        var step = length / count;
                        for (var i = 0; i < count; i++)
                        {
                            var t = (i + 0.5f) * step;
                            Vector3 pos;
                            float yaw;
                            switch (side)
                            {
                                case 0: pos = new Vector3(r.xMin + t, 0f, r.yMin); yaw = 0f; break;     // lado sul: a face aponta para o poco (+Z)
                                case 1: pos = new Vector3(r.xMin + t, 0f, r.yMax); yaw = 180f; break;
                                case 2: pos = new Vector3(r.xMin, 0f, r.yMin + t); yaw = 90f; break;
                                default: pos = new Vector3(r.xMax, 0f, r.yMin + t); yaw = 270f; break;
                            }
                            EnvironmentKit.Place("AbismoBordo", decor, pos, yaw, new Vector3(step / edge.Size.x, 1f, 1f), colliders: false, instanceName: vista.Id + ".edge");
                        }
                    }
                }
                else if (vista.Id.Contains("colonnade"))
                {
                    // Colunata: pilares altos (6 m, cortados pelo topo da tela) ao longo da faixa junto a parede oeste; colisor de caixa fina.
                    var piece = EnvironmentKit.Get("PilarInteiro");
                    var count = Mathf.Max(2, Mathf.RoundToInt(r.height / 4f));
                    for (var i = 0; i < count; i++)
                    {
                        var z = r.yMin + (i + 0.5f) * r.height / count;
                        var go = EnvironmentKit.Place("PilarInteiro", level, new Vector3(r.center.x, 0f, z), 0f, new Vector3(1f, 1.5f, 1f), colliders: true, instanceName: vista.Id + ".col");
                    }
                }
                else if (vista.Id.Contains("gate"))
                {
                    // Portao gradeado ao fim da antecamara: moldura de portal aberto (passagem livre) com brilho ambar vazando para a arena.
                    var center = new Vector3(r.center.x, 0f, r.yMax - 0.3f);
                    var frame = EnvironmentKit.Place("PortalAberto", level, center, 0f, new Vector3(2.4f, 1f, 1f), colliders: true, instanceName: vista.Id);
                    SceneryBuilder.AddFire(frame, false, 2.4f, new Color(1f, 0.62f, 0.2f), 1.8f, 8f);
                }
            }
        }

        static Material EnsureAbyssMaterial()
        {
            SandboxBuilder.EnsureDir(EnvironmentKit.MaterialDir);
            var path = EnvironmentKit.MaterialDir + "/M_Cripta_Abismo.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.SetColor("_BaseColor", new Color(0.02f, 0.015f, 0.03f));
            EditorUtility.SetDirty(mat);
            return mat;
        }

        /// <summary>Um arco em ruina a 3 m da entrada de cada corredor (de lado a lado do corredor, sobrando 1,7 m de passagem de cada lado dos pilares).</summary>
        static void BuildCorridorArches(CriptaLayout layout, Transform parent)
        {
            foreach (var c in layout.Corridors)
            {
                var r = c.Rect;
                var pos = c.AlongX ? new Vector3(r.xMin + 3f, 0f, r.center.y) : new Vector3(r.center.x, 0f, r.yMin + 3f);
                EnvironmentKit.Place("ArcoRuina", parent, pos, c.AlongX ? 90f : 0f, instanceName: c.Id + ".arch");
            }
        }

        // ============================================================================================== props

        static void BuildProps(CriptaBuilder.Context ctx, Transform props, Transform small)
        {
            var layout = ctx.Layout;
            var spots = new Spots();
            foreach (var e in layout.Encounters)
            {
                foreach (var g in e.Groups)
                {
                    foreach (var s in g.Slots) spots.Add(s, 3.2f);
                    foreach (var s in g.Patrol) spots.Add(s, 2.0f);
                }
                if (e.IsBoss) { spots.Add(e.Respawn, 4f); foreach (var m in e.SummonMarks) spots.Add(m, 3f); }
            }
            foreach (var cp in layout.Checkpoints) spots.Add(cp.Pos, 3.5f);
            foreach (var p in layout.Portals) spots.Add(p.Pos, 4f);
            foreach (var m in layout.Markers) spots.Add(m.Pos, 4f);
            foreach (var c in layout.Chests) spots.Add(c.Pos, 3f);
            foreach (var g in layout.Gates) spots.Add(g.Pos, 4.5f);
            foreach (var p in layout.Pillars) spots.Add(p.Pos, p.Radius + 1.6f);
            foreach (var v in layout.Vistas) spots.KeepRects.Add(v.Rect);
            spots.Add(layout.HeroSpawn, 3f);
            // Rota principal: faixa livre de 3 m de cada lado (amostras a cada 1,5 m).
            for (var i = 0; i + 1 < layout.Route.Count; i++)
            {
                var a = layout.Route[i];
                var b = layout.Route[i + 1];
                var len = Vector2.Distance(a, b);
                var steps = Mathf.Max(1, Mathf.CeilToInt(len / 1.5f));
                for (var k = 0; k <= steps; k++) spots.Add(Vector2.Lerp(a, b, k / (float)steps), 3.2f);
            }

            foreach (var room in layout.Rooms)
            {
                var rng = SceneryBuilder.Rng(room.Id + ".props");
                var r = room.Rect;
                var boss = room.Role == "boss";
                var entry = room.Role == "entry";
                var rest = room.Role == "rest";
                var secret = room.Role == "secret";
                if (secret) { PlaceBraziers(props, room, rng, spots, 1); continue; }

                PlaceBraziers(props, room, rng, spots, boss || entry || rest ? 4 : 2);

                var sarcophagi = boss ? 0 : entry ? 1 : rest ? 2 : 2 + rng.Next(0, 2);
                for (var i = 0; i < sarcophagi; i++)
                {
                    var name = rng.NextDouble() < 0.4 ? "SarcofagoAberto" : "SarcofagoFechado";
                    if (!TryWallSpot(layout, room, rng, spots, 1.0f, 1.5f, out var pos, out var yaw)) continue;
                    var go = EnvironmentKit.Place(name, props, new Vector3(pos.x, 0f, pos.y), yaw, instanceName: room.Id + "." + name);
                    spots.Add(pos, 1.4f);
                    // Ossos e velas ao pe do sarcofago, sem colisor.
                    SmallNear(small, rng, pos, yaw, "Velas", true);
                    SmallNear(small, rng, pos, yaw, "Ossos", false);
                }

                var blocks = boss ? 4 : 2 + rng.Next(0, 3);
                for (var i = 0; i < blocks; i++)
                {
                    var name = new[] { "BlocoA", "BlocoB", "BlocoC", "BlocoD" }[rng.Next(0, 4)];
                    if (!TryWallSpot(layout, room, rng, spots, 1.0f, 1.0f, out var pos, out var yaw)) continue;
                    EnvironmentKit.Place(name, props, new Vector3(pos.x, 0f, pos.y), yaw + (float)rng.Next(-20, 21), instanceName: room.Id + "." + name);
                    spots.Add(pos, 1.0f);
                }
                if (Mathf.Max(r.width, r.height) >= 28f && TryWallSpot(layout, room, rng, spots, 1.7f, 1.6f, out var rp, out var ryaw))
                {
                    EnvironmentKit.Place("RuinaGrande", props, new Vector3(rp.x, 0f, rp.y), ryaw, instanceName: room.Id + ".RuinaGrande");
                    spots.Add(rp, 1.6f);
                }
                if (room.Role == "combat" && rng.NextDouble() < 0.6 && TryStairSpot(layout, room, rng, spots, out var sp, out var syaw))
                {
                    EnvironmentKit.Place("Escada", props, new Vector3(sp.x, 0f, sp.y), syaw, instanceName: room.Id + ".Escada");
                    spots.Add(sp, 2.2f);
                }
                var banners = boss ? 4 : 2;
                for (var i = 0; i < banners; i++)
                {
                    if (!TryWallSpot(layout, room, rng, spots, 1.2f, 1.2f, out var pos, out var yaw)) continue;
                    EnvironmentKit.Place("Estandarte", props, new Vector3(pos.x, 0f, pos.y), yaw, instanceName: room.Id + ".Estandarte");
                    spots.Add(pos, 1.3f);
                }

                // Entulho: poucos montes de pedra e osso encostados na parede (nunca espalhados pelo meio do chao nem em grade).
                var rubble = boss ? 2 : 2 + rng.Next(0, 2);
                for (var i = 0; i < rubble; i++)
                {
                    if (!TryWallSpot(layout, room, rng, spots, 0.8f, 0.9f, out var rubblePos, out var rubbleYaw)) continue;
                    var name = i % 2 == 0 ? "PedraE" : "PedraF";
                    EnvironmentKit.Place(name, small, new Vector3(rubblePos.x, 0f, rubblePos.y), (float)rng.NextDouble() * 360f, colliders: false, instanceName: room.Id + "." + name);
                    spots.Add(rubblePos, 0.9f);
                    SmallNear(small, rng, rubblePos, rubbleYaw, "Ossos", false);
                }
            }

            // Brazeiros nos checkpoints (a luz e a chama vem do pool) e arcos nos portais.
            foreach (var cp in layout.Checkpoints)
            {
                var go = EnvironmentKit.Place("Braseiro", props, new Vector3(cp.Pos.x + 1.8f, 0f, cp.Pos.y), 0f, instanceName: cp.Id + ".brazier");
                SceneryBuilder.AddBrazierFire(go);
            }

            // Estandartes e braseiros no corredor do chefe e na porta: ja cobertos por PlaceBraziers (antecamara e arena).
        }

        static void PlaceBraziers(Transform parent, CriptaLayout.RoomData room, System.Random rng, Spots spots, int count)
        {
            var r = room.Rect;
            const float inset = 1.8f;
            var corners = new[]
            {
                new Vector2(r.xMin + inset, r.yMin + inset), new Vector2(r.xMax - inset, r.yMax - inset),
                new Vector2(r.xMin + inset, r.yMax - inset), new Vector2(r.xMax - inset, r.yMin + inset),
            };
            var start = rng.Next(0, 2); // alterna a diagonal que recebe os dois primeiros
            for (var i = 0; i < Mathf.Min(count, 4); i++)
            {
                var pos = corners[(i + start * 2) % 4];
                if (!spots.Free(pos, 0.9f)) continue;
                var go = EnvironmentKit.Place("Braseiro", parent, new Vector3(pos.x, 0f, pos.y), (float)rng.Next(0, 4) * 90f, instanceName: room.Id + ".brazier");
                SceneryBuilder.AddBrazierFire(go);
                spots.Add(pos, 1.2f);
            }
        }

        static void SmallNear(Transform small, System.Random rng, Vector2 pos, float yaw, string name, bool fire)
        {
            var offset = Quaternion.Euler(0f, yaw, 0f) * new Vector3((float)(rng.NextDouble() * 2.0 - 1.0) * 1.0f, 0f, (rng.NextDouble() < 0.5 ? -1f : 1f) * 1.1f);
            var go = EnvironmentKit.Place(name, small, new Vector3(pos.x + offset.x, 0f, pos.y + offset.z), (float)rng.NextDouble() * 360f, colliders: false, instanceName: name);
            if (fire) SceneryBuilder.AddCandleFire(go);
        }

        /// <summary>Escada (rampa de 1 m, so cenario) encostada na parede: o topo (+Z da peca) fica contra a parede e sobra espaco livre ao redor.</summary>
        static bool TryStairSpot(CriptaLayout layout, CriptaLayout.RoomData room, System.Random rng, Spots spots, out Vector2 pos, out float yaw)
        {
            var r = room.Rect;
            for (var attempt = 0; attempt < 24; attempt++)
            {
                var side = rng.Next(0, 4);
                var alongX = side < 2;
                var a = alongX ? r.xMin : r.yMin;
                var b = alongX ? r.xMax : r.yMax;
                var t = Mathf.Lerp(a + 5f, b - 5f, (float)rng.NextDouble());
                var blockedByDoor = false;
                foreach (var o in Openings(layout, room, side)) if (t > o.x - 5f && t < o.y + 5f) blockedByDoor = true;
                if (blockedByDoor) continue;
                Vector2 p;
                switch (side)
                {
                    case 0: p = new Vector2(t, r.yMin + 1f); yaw = 180f; break;
                    case 1: p = new Vector2(t, r.yMax - 1f); yaw = 0f; break;
                    case 2: p = new Vector2(r.xMin + 1f, t); yaw = 270f; break;
                    default: p = new Vector2(r.xMax - 1f, t); yaw = 90f; break;
                }
                if (!spots.Free(p, 2.2f)) continue;
                pos = p;
                return true;
            }
            pos = Vector2.zero;
            yaw = 0f;
            return false;
        }

        /// <summary>Um ponto junto a uma parede da sala (faixa de ate ~3 m), fora dos vaos (+3 m), longe dos cantos e livre dos espacos ja ocupados. yaw alinha o eixo longo da peca com a parede.</summary>
        static bool TryWallSpot(CriptaLayout layout, CriptaLayout.RoomData room, System.Random rng, Spots spots, float depth, float radius, out Vector2 pos, out float yaw)
        {
            var r = room.Rect;
            for (var attempt = 0; attempt < 24; attempt++)
            {
                var side = rng.Next(0, 4);
                var alongX = side < 2;
                var a = alongX ? r.xMin : r.yMin;
                var b = alongX ? r.xMax : r.yMax;
                var t = Mathf.Lerp(a + 4f, b - 4f, (float)rng.NextDouble());
                var blockedByDoor = false;
                foreach (var o in Openings(layout, room, side)) if (t > o.x - 3.5f - radius && t < o.y + 3.5f + radius) blockedByDoor = true;
                if (blockedByDoor) continue;
                var d = depth * 0.5f + 0.4f + (float)rng.NextDouble() * 1.2f;
                Vector2 p;
                switch (side)
                {
                    case 0: p = new Vector2(t, r.yMin + d); break;
                    case 1: p = new Vector2(t, r.yMax - d); break;
                    case 2: p = new Vector2(r.xMin + d, t); break;
                    default: p = new Vector2(r.xMax - d, t); break;
                }
                if (!spots.Free(p, radius)) continue;
                pos = p;
                yaw = (alongX ? 0f : 90f) + (rng.NextDouble() < 0.5 ? 0f : 180f);
                return true;
            }
            pos = Vector2.zero;
            yaw = 0f;
            return false;
        }
    }
}
