using System.Collections.Generic;
using System.IO;
using System.Linq;
using Echoes.EditorTools;
using Echoes.Gameplay;
using Echoes.Interop;
using Echoes.Presentation;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;

namespace Echoes.Tests.EditMode
{
    /// <summary>
    /// A Cripta montada pelo <see cref="CriptaBuilder"/> bate com o bloco JSON do docs/14 (salas, corredores, encontros, pilares, baús,
    /// checkpoints) e com os CSV (encounters.csv, maps.csv, enemies.csv). Também cobre as regras do dono (porta da arena, reaparição)
    /// no nível da lógica e a R-VIS-1 do atirador.
    /// </summary>
    [Category("Cripta")]
    public sealed class CriptaBuilderTests
    {
        static CriptaLayout Layout => CriptaLayout.LoadFromDocument();

        // ---------------------------------------------------------------------------------------------
        // O documento
        // ---------------------------------------------------------------------------------------------

        [Test]
        public void LayoutIsReadFromTheDocumentWithTheExpectedShape()
        {
            var l = Layout;
            Assert.AreEqual("map.act1.crypt", l.MapId);
            Assert.AreEqual(11, l.Rooms.Count, "10 salas e o nicho secreto");
            Assert.AreEqual(10, l.Corridors.Count, "9 corredores da serpentina e o atalho");
            Assert.AreEqual(8, l.Encounters.Count, "7 encontros e o chefe");
            Assert.AreEqual(31, l.Pillars.Count);
            Assert.AreEqual(4, l.Checkpoints.Count);
            Assert.AreEqual(5, l.Chests.Count);
            Assert.AreEqual(1, l.Secrets.Count);
            Assert.AreEqual(2, l.Gates.Count);
            foreach (var c in l.Corridors) Assert.AreEqual(l.CorridorWidth, Mathf.Min(c.Rect.width, c.Rect.height), 1e-4f, c.Id + ": corredor de 6 m");
            var arena = l.Room("room.crypt.r09_arena");
            Assert.AreEqual(40f, arena.Rect.width);
            Assert.AreEqual(40f, arena.Rect.height);
            Assert.AreEqual(8, l.Pillars.Count(p => p.Id.StartsWith("pil.arena.")), "os 8 pilares da arena");
            foreach (var p in l.Pillars.Where(p => p.Id.StartsWith("pil.arena."))) Assert.IsTrue(arena.Rect.Contains(p.Pos), p.Id + " dentro da arena");
            Assert.AreEqual(56f, l.CameraHeight);
        }

        [Test]
        public void EncountersMatchTheCsv()
        {
            var l = Layout;
            var dataDir = TestWorld.DataDirectory;
            var csv = ReadCsv(Path.Combine(dataDir, "encounters.csv"));
            var map = ReadCsv(Path.Combine(dataDir, "maps.csv")).Single(r => r["id"] == l.MapId);
            var expected = map["encounters"].Split('|').ToList();
            expected.Add(map["bossEncounter"]);
            Assert.AreEqual(expected.Count, l.Encounters.Count, "um encontro do layout por encontro do mapa");
            foreach (var id in expected)
            {
                var row = csv.Single(r => r["id"] == id);
                var enc = l.Encounters.Single(e => e.Id == id);
                var groups = row["groups"].Split('|');
                Assert.AreEqual(groups.Length, enc.Groups.Count, id + " grupos");
                for (var i = 0; i < groups.Length; i++)
                {
                    var parts = groups[i].Split(':');
                    Assert.AreEqual(parts[0], enc.Groups[i].EnemyId, id);
                    Assert.AreEqual(int.Parse(parts[1]), enc.Groups[i].Min, id + " min");
                    Assert.AreEqual(int.Parse(parts[2]), enc.Groups[i].Max, id + " max");
                    Assert.GreaterOrEqual(enc.Groups[i].Slots.Count, enc.Groups[i].Max, id + ": espacos para o maximo");
                }
                Assert.AreEqual(row["isBoss"] == "true", enc.IsBoss, id);
            }
        }

        [Test]
        public void FixedElitesReadTheirModifierFromEnemiesCsv()
        {
            using (var rules = TestWorld.LoadRules())
            {
                Assert.AreEqual("modifier.elite.shield", rules.FindEnemy("enemy.shielded_sentinel").ModifierId);
                Assert.AreEqual("modifier.elite.swift", rules.FindEnemy("enemy.swift_ash_hound").ModifierId);
                Assert.IsEmpty(rules.FindEnemy("enemy.hollow_sentinel").ModifierId);
                Assert.AreEqual("loot.crypt.elite", rules.FindEnemy("enemy.shielded_sentinel").EliteLootTableId);
            }
        }

        // ---------------------------------------------------------------------------------------------
        // A cena montada
        // ---------------------------------------------------------------------------------------------

        [Test]
        public void BuiltSceneMatchesTheLayout()
        {
            var l = Layout;
            CriptaBuilder.BuildScene();
            var scene = EditorSceneManager.OpenScene(CriptaBuilder.ScenePath, OpenSceneMode.Single);
            Assert.IsTrue(scene.IsValid());

            foreach (var room in l.Rooms) Assert.IsNotNull(GameObject.Find(room.Id), room.Id);
            foreach (var corridor in l.Corridors) Assert.IsNotNull(GameObject.Find(corridor.Id), corridor.Id);
            foreach (var pillar in l.Pillars)
            {
                var go = GameObject.Find(pillar.Id);
                Assert.IsNotNull(go, pillar.Id);
                var capsule = go.GetComponent<CapsuleCollider>();
                Assert.IsNotNull(capsule, pillar.Id + ": colisor solido simples");
                Assert.AreEqual(pillar.Radius, capsule.radius * Mathf.Max(go.transform.lossyScale.x, go.transform.lossyScale.z), 0.05f, pillar.Id + " raio");
                var center = capsule.transform.TransformPoint(capsule.center);
                Assert.AreEqual(pillar.Pos.x, center.x, 0.05f, pillar.Id);
                Assert.AreEqual(pillar.Pos.y, center.z, 0.05f, pillar.Id);
            }

            var enemies = Object.FindObjectsByType<EnemyController>(FindObjectsSortMode.None);
            var expected = l.Encounters.Sum(e => l.EnemyCount(e));
            Assert.AreEqual(expected, enemies.Length, "um inimigo por espaco usado nos 8 encontros");
            foreach (var encounter in l.Encounters)
            {
                var parent = GameObject.Find(encounter.Id);
                Assert.IsNotNull(parent, encounter.Id);
                Assert.AreEqual(l.EnemyCount(encounter), parent.GetComponentsInChildren<EnemyController>().Length, encounter.Id);
                var room = l.Room(encounter.Room).Rect;
                foreach (var e in parent.GetComponentsInChildren<EnemyController>()) Assert.IsTrue(room.Contains(new Vector2(e.transform.position.x, e.transform.position.z)), encounter.Id + " dentro da sala");
            }

            var guardian = enemies.Single(e => e.EnemyId == "enemy.crypt_guardian");
            Assert.IsTrue(new SerializedObject(guardian).FindProperty("startDormant").boolValue, "o Guardiao so acorda no gatilho");
            var archers = enemies.Where(e => e.EnemyId == "enemy.ghost_archer").ToList();
            Assert.IsNotEmpty(archers);
            foreach (var a in archers) Assert.IsTrue(new SerializedObject(a).FindProperty("requireOnScreen").boolValue, "R-VIS-1 vem do layout");

            Assert.AreEqual(l.Chests.Count, Object.FindObjectsByType<ChestPickup>(FindObjectsSortMode.None).Length);
            Assert.AreEqual(l.Checkpoints.Count, Object.FindObjectsByType<CheckpointZone>(FindObjectsSortMode.None).Length);
            Assert.AreEqual(l.Portals.Count, Object.FindObjectsByType<PortalZone>(FindObjectsSortMode.None).Length + 1, "o portal de saida nasce desligado");
            Assert.AreEqual(l.Gates.Count, Object.FindObjectsByType<GateBarrier>(FindObjectsSortMode.None).Length);
            Assert.AreEqual(l.Secrets.Count, Object.FindObjectsByType<SecretWall>(FindObjectsSortMode.None).Length);
            Assert.AreEqual(1, Object.FindObjectsByType<ArenaController>(FindObjectsSortMode.None).Length);
            Assert.AreEqual(1, Object.FindObjectsByType<EncounterDirector>(FindObjectsSortMode.None).Length);

            var hero = Object.FindFirstObjectByType<HeroController>();
            Assert.AreEqual(l.HeroSpawn.x, hero.transform.position.x, 1e-3f);
            Assert.AreEqual(l.HeroSpawn.y, hero.transform.position.z, 1e-3f);
            Assert.IsNotNull(hero.GetComponentInChildren<SkinnedMeshRenderer>(), "P_Hero_Warrior");
            var follow = Object.FindFirstObjectByType<FollowCamera>();
            Assert.AreEqual(l.CameraHeight, Mathf.Abs(follow.GetComponentInChildren<Camera>().transform.localPosition.z), 1e-3f, "camera de 56 m");

            var triangulation = NavMesh.CalculateTriangulation();
            Assert.Greater(triangulation.indices.Length, 0, "NavMesh assada");
            Assert.IsTrue(NavMesh.SamplePosition(new Vector3(l.HeroSpawn.x, 0f, l.HeroSpawn.y), out _, 1f, NavMesh.AllAreas), "o spawn esta sobre a NavMesh");
            var arena = l.Room("room.crypt.r09_arena").Rect;
            Assert.IsTrue(NavMesh.SamplePosition(new Vector3(arena.center.x, 0f, arena.center.y + 6f), out _, 1f, NavMesh.AllAreas), "a arena tem NavMesh");
        }

        // ---------------------------------------------------------------------------------------------
        // Regras do dono e R-VIS-1 (logica)
        // ---------------------------------------------------------------------------------------------

        [Test]
        public void ArcherHoldsFireOutsideTheVisibleAreaAndShootsInside()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var archer = world.AddEnemy("enemy.ghost_archer", new PlanarVector(0f, 6f));
                var telegraphs = new List<TelegraphEvent>();
                world.Events.Subscribe<TelegraphEvent>((in TelegraphEvent e) => { if (e.Started) telegraphs.Add(e); });
                var inside = false;
                archer.logic.RequireOnScreen = true;
                archer.logic.IsInsideVisibleArea = p => inside;
                world.Run(4.0);
                Assert.IsEmpty(telegraphs, "fora da area visivel o atirador nao comeca a mira");
                inside = true;
                world.Run(4.0);
                Assert.IsNotEmpty(telegraphs, "dentro da area visivel ele mira");
            }
        }

        [Test]
        public void DormantBossDoesNothingUntilActivated()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var hero = world.AddHero(PlanarVector.Zero);
                var boss = world.AddEnemy("enemy.crypt_guardian", new PlanarVector(0f, 6f), 3, 1f);
                boss.logic.Dormant = true;
                var telegraphs = 0;
                world.Events.Subscribe<TelegraphEvent>((in TelegraphEvent e) => { if (e.Started) telegraphs++; });
                world.Run(6.0);
                Assert.AreEqual(0, telegraphs);
                Assert.IsNull(boss.logic.Boss, "o chefe nativo so nasce quando acorda");
                boss.logic.Dormant = false;
                world.Run(6.0);
                Assert.IsNotNull(boss.logic.Boss);
                Assert.Greater(telegraphs, 0);
            }
        }

        [Test]
        public void FixedEliteGetsItsModifierFromTheCore()
        {
            using (var world = new TestWorld(null, TestWorld.LoadNativeRules()))
            {
                var info = world.Rules.FindEnemy("enemy.shielded_sentinel");
                var profile = world.Rules.GetEliteProfile(info.ModifierId, false);
                Assert.IsFalse(profile.IsNone);
                Assert.IsFalse(profile.Rolled, "elite fixo nao e sorteado");
                var elite = world.AddEnemy(info.Id, new PlanarVector(50f, 50f), 3, 0.5f, profile);
                Assert.Greater(elite.combatant.Barrier, 0.0, "o modificador Escudo da barreira inicial");
                Assert.IsTrue(elite.combatant.IsElite);
            }
        }

        [Test]
        public void VisibleAreaComesFromTheCameraFrustum()
        {
            var l = Layout;
            var rig = new GameObject("rig");
            try
            {
                var camGo = new GameObject("cam");
                camGo.transform.SetParent(rig.transform, false);
                var cam = camGo.AddComponent<Camera>();
                cam.aspect = 16f / 9f;
                var follow = rig.AddComponent<FollowCamera>();
                new SerializedObject(follow).FindProperty("viewCamera").objectReferenceValue = cam;
                var so = new SerializedObject(follow);
                so.FindProperty("viewCamera").objectReferenceValue = cam;
                so.ApplyModifiedPropertiesWithoutUndo();
                follow.ApplySettings();
                rig.transform.position = new Vector3(0f, 0.52f, 0f);
                Assert.IsTrue(VisibleArea.TryGetHalfExtents(cam, new PlanarVector(0f, 0f), 0f, out var hx, out var hz));
                Assert.That(hx, Is.InRange(l.VisibleHalfX * 0.6f, l.VisibleHalfX * 1.15f), "metade em X da area visivel");
                Assert.That(hz, Is.InRange(l.VisibleHalfZ * 0.5f, l.VisibleHalfZ * 1.15f), "metade em Z da area visivel");
                Assert.IsTrue(VisibleArea.TryGetHalfExtents(cam, new PlanarVector(0f, 0f), 1f, out var mx, out _));
                Assert.AreEqual(hx - 1f, mx, 1e-3f, "a margem de 1 m sai de cada lado");
            }
            finally
            {
                Object.DestroyImmediate(rig);
            }
        }

        static List<Dictionary<string, string>> ReadCsv(string path)
        {
            var lines = File.ReadAllLines(path);
            var header = lines[0].Split(',');
            var rows = new List<Dictionary<string, string>>();
            for (var i = 1; i < lines.Length; i++)
            {
                if (string.IsNullOrWhiteSpace(lines[i])) continue;
                var cells = lines[i].Split(',');
                var row = new Dictionary<string, string>();
                for (var c = 0; c < header.Length; c++) row[header[c]] = c < cells.Length ? cells[c] : string.Empty;
                rows.Add(row);
            }
            return rows;
        }
    }
}
