using Echoes.Presentation;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Os prefabs de VFX (docs/18 seção 6), um por efeito. Origem no chão para o que nasce no piso (anel, nova, explosão) e no ponto de contato
    /// para faíscas; +Z do prefab é a direção do golpe (ou, nas faíscas, a direção do atacante). Tamanhos em metros, pensados para a câmera
    /// de 56 m (1 m ≈ 77 px a 1080p). Cada prefab que mora no chão traz o raio com que foi feito (VfxSpec.authoredRadiusMeters).
    /// </summary>
    public static partial class VfxLibraryBuilder
    {
        // Warrior
        static GameObject pTrail1, pTrail2, pTrail3, pTrailHeavy, pHitSpark, pHitSparkHeavy, pChargeGlowWarrior, pChargeRing, pChargeFlash,
            pGuardShimmer, pGuardBlock, pGuardPerfect;
        // Archer
        static GameObject pArrow, pArrowPierce, pArrowMuzzle, pFanMuzzle, pArrowHit, pPierceHit, pChargeArcher, pRain, pRainMarker, pLeapDust, pGuardArcher;
        // Mage
        static GameObject pCastArcane, pCastFire, pDart, pDartPop, pOrb, pOrbExplosion, pFireball, pFireballExplosion, pChargeFire, pNova,
            pDome, pBarrierHit, pBarrierBreak, pRay, pRayMuzzle, pRayHit, pFireMuzzle, pIceHit;
        // Enemy
        static GameObject pGhostArrow, pGhostHit, pGhostCast;

        const float Ground = 0.04f; // 4 cm acima do piso para o efeito plano não brigar com o chão

        static void BuildPrefabs()
        {
            BuildWarriorPrefabs();
            BuildArcherPrefabs();
            BuildMagePrefabs();
            BuildEnemyPrefabs();
        }

        // =============================================================================================================== Guerreiro

        static GameObject MakeTrail(string name, float life, Color hilt, Color mid, Color tip, Material mat, int samples)
        {
            return SavePrefab(name, root =>
            {
                var go = Child(root, "Ribbon", Vector3.zero);
                var renderer = go.AddComponent<MeshRenderer>();
                renderer.sharedMaterial = mat;
                renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                renderer.receiveShadows = false;
                go.AddComponent<MeshFilter>();
                var g = new Gradient();
                g.SetKeys(
                    new[] { new GradientColorKey(hilt, 0f), new GradientColorKey(mid, 0.55f), new GradientColorKey(tip, 1f) },
                    new[] { new GradientAlphaKey(0.35f, 0f), new GradientAlphaKey(0.8f, 0.55f), new GradientAlphaKey(1f, 1f) });
                go.AddComponent<BladeTrail>().Configure(life, g, samples);
            });
        }

        static void HitSpark(GameObject root, int sparks, int dust, bool ring, float scale)
        {
            new Layer
            {
                Name = "Flash", Mat = mAddStar4, Duration = 0.3f, Life = R(0.09f), Size = R(0.6f * scale), Bursts = new[] { (0f, 1, 1) },
                Grad = Snap(Color.white, SparkYellow, 1f, 0.4f), SizeCurve = Curve(0f, 0.55f, 0.3f, 1f, 1f, 0.8f), Radius = 0.001f,
            }.Build(root.transform);
            new Layer
            {
                Name = "Sparks", Mat = mAddStreak, Duration = 0.4f, Life = R(0.22f, 0.42f), Speed = R(3f, 6.5f), Size = R(0.05f, 0.09f) * scale,
                Bursts = new[] { (0f, sparks / 2, sparks) }, Shape = ParticleSystemShapeType.Cone, Angle = 40f, Radius = 0.04f, Gravity = 0.9f,
                Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.8f, VelocityScale = 0.045f, Drag = 1.2f, World = true,
                Grad = Snap(SparkYellow, Hex("#FF8A2E"), 1f, 0.5f),
            }.Build(root.transform);
            new Layer
            {
                Name = "Dust", Mat = mAlphaSmoke, Duration = 0.5f, Life = R(0.3f, 0.7f), Speed = R(0.7f, 1.8f), Size = R(0.14f, 0.24f) * scale,
                Bursts = new[] { (0f, dust - 2, dust) }, Shape = ParticleSystemShapeType.Cone, Angle = 55f, Radius = 0.05f, Gravity = -0.04f, World = true,
                Grad = Flat(PhysEdge, 0.5f, 0.05f, 0.3f), SizeCurve = Curve(0f, 0.5f, 1f, 1.3f), StartRotation = R(0f, 360f),
            }.Build(root.transform);
            if (!ring) return;
            new Layer
            {
                Name = "Ring", Mat = mAddRingSoft, Duration = 0.3f, Life = R(0.22f), Size = R(1.7f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                Grad = Snap(PhysCore, PhysMid, 0.9f, 0.2f), SizeCurve = Curve(0f, 0.15f, 0.5f, 0.7f, 1f, 1f),
            }.Build(root.transform);
        }

        static void BuildWarriorPrefabs()
        {
            // Rastro da arma: 180, 180, 240 e 300 ms (o 3º golpe é mais largo e leva um fio dourado no núcleo).
            pTrail1 = MakeTrail("FX_Warrior_Trail_1", 0.18f, FireEdge, FireMid, FireCore, mAddSlash, 28);
            pTrail2 = MakeTrail("FX_Warrior_Trail_2", 0.18f, FireEdge, FireMid, FireCore, mAddSlash, 28);
            pTrail3 = MakeTrail("FX_Warrior_Trail_3", 0.24f, FireEdge, FireMid, GoldCore, mAddSlashGold, 32);
            pTrailHeavy = MakeTrail("FX_Warrior_Trail_Heavy", 0.30f, FireEdge, FireMid, GoldCore, mAddSlashGold, 40);

            pHitSpark = SavePrefab("FX_Hit_Spark", root => HitSpark(root, 7, 8, false, 1f));
            pHitSparkHeavy = SavePrefab("FX_Hit_Spark_Heavy", root => HitSpark(root, 14, 14, true, 1.25f));

            // Brilho de carga na lâmina: cresce, pisca no máximo (80 ms em branco) e solta brasas.
            pChargeGlowWarrior = SavePrefab("FX_Warrior_Charge_Glow", root =>
            {
                var grow = Child(root, "Grow", Vector3.zero);
                grow.AddComponent<VfxGrow>().Configure(0.12f, 0.9f);
                new Layer { Name = "Halo", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.3f), Size = R(1.1f), Rate = 34f, Grad = Flat(FireMid, 0.30f, 0.1f, 0.5f) }.Build(grow.transform);
                new Layer { Name = "Core", Mat = mAddCore, Duration = 1f, Loop = true, Life = R(0.18f), Size = R(0.55f), Rate = 40f, Grad = Flat(FireCore, 0.9f, 0.05f, 0.5f) }.Build(grow.transform);
                new Layer
                {
                    Name = "Pulse", Mat = mAddSoft, Duration = 4f, Loop = true, Delay = 0.9f, Life = R(0.16f), Size = R(1.5f), Rate = 6f,
                    Grad = Flat(FireCore, 0.55f, 0.1f, 0.5f), SizeCurve = Curve(0f, 0.7f, 1f, 1.2f),
                }.Build(grow.transform);
                new Layer
                {
                    Name = "Embers", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.5f, 0.9f), Speed = R(0.3f, 0.8f), Size = R(0.05f, 0.09f), Rate = 14f,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.14f, Gravity = -0.2f, World = true, Grad = Snap(SparkYellow, FireMid, 1f, 0.5f),
                }.Build(root.transform);
            });

            // Anel no chão que fecha com a carga (leitura sem olhar o personagem): #FCD58A com alfa 0,5, nunca vermelho.
            pChargeRing = SavePrefab("FX_Charge_Ring", root =>
            {
                var g = Child(root, "Ground", new Vector3(0f, Ground, 0f));
                new Layer
                {
                    Name = "Closing", Mat = mAddRing, Duration = 1f, Life = R(0.9f), Size = R(3.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Flat(ChargeGold, 0.55f, 0.12f, 0.9f), SizeCurve = Curve(0f, 1f, 1f, 0.28f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Hold", Mat = mAddRing, Duration = 4f, Loop = true, Delay = 0.9f, Life = R(0.5f), Size = R(0.95f), Rate = 3f, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Flat(ChargeGold, 0.55f, 0.2f, 0.6f), SizeCurve = Curve(0f, 0.9f, 1f, 1.1f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Fill", Mat = mAddSoft, Duration = 1f, Life = R(0.9f), Size = R(3.2f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Flat(ChargeGold, 0.12f, 0.2f, 0.9f), SizeCurve = Curve(0f, 1f, 1f, 0.28f),
                }.Build(g.transform);
            });

            // Máximo da carga: pisca em branco por 80 ms (serve às três classes, muda só a âncora).
            pChargeFlash = SavePrefab("FX_Charge_Full", root =>
            {
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.2f, Life = R(0.1f), Size = R(1.1f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, GoldCore, 1f, 0.4f) }.Build(root.transform);
                new Layer { Name = "Glow", Mat = mAddSoft, Duration = 0.2f, Life = R(0.12f), Size = R(1.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, GoldMid, 0.8f, 0.3f) }.Build(root.transform);
            });

            // Defesa do escudo: placa hexagonal fraca e reflexos dourados; enquanto segura.
            pGuardShimmer = SavePrefab("FX_Guard_Shimmer", root =>
            {
                new Layer
                {
                    Name = "Plate", Mat = mAddHex, Duration = 1f, Loop = true, Life = R(1.2f), Size = R(1.0f), Rate = 1.2f, Radius = 0.001f, Position = new Vector3(0f, 0f, 0.1f),
                    Grad = Flat(GoldMid, 0.28f, 0.3f, 0.6f), StartRotation = R(0f, 60f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "Glints", Mat = mAddStar4, Duration = 1f, Loop = true, Life = R(0.25f, 0.4f), Size = R(0.18f, 0.3f), Rate = 4f, Shape = ParticleSystemShapeType.Sphere,
                    Radius = 0.28f, ShapeScale = new Vector3(1f, 1f, 0.3f), Grad = Flat(GoldCore, 0.9f, 0.2f, 0.5f), StartRotation = R(0f, 90f),
                }.Build(root.transform);
            });
            pGuardBlock = SavePrefab("FX_Guard_BlockSpark", root =>
            {
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.2f, Life = R(0.08f), Size = R(0.5f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, PhysMid, 1f, 0.4f) }.Build(root.transform);
                new Layer
                {
                    Name = "Sparks", Mat = mAddStreak, Duration = 0.3f, Life = R(0.1f, 0.15f), Speed = R(3f, 5f), Size = R(0.04f, 0.07f), Bursts = new[] { (0f, 5, 7) },
                    Shape = ParticleSystemShapeType.Cone, Angle = 50f, Radius = 0.03f, Gravity = 0.6f, Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.6f, VelocityScale = 0.04f, World = true,
                    Grad = Snap(PhysMid, SparkYellow, 1f, 0.5f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "Chips", Mat = mAlphaSmoke, Duration = 0.3f, Life = R(0.12f, 0.2f), Speed = R(1f, 2.2f), Size = R(0.05f, 0.09f), Bursts = new[] { (0f, 3, 4) },
                    Shape = ParticleSystemShapeType.Cone, Angle = 60f, Radius = 0.03f, Gravity = 1f, World = true, Grad = Flat(PhysMid, 0.8f, 0.05f, 0.4f),
                }.Build(root.transform);
            });

            // Defesa perfeita: anel dourado até 120 cm de raio + estrela de 6 pontas + clarão, 220 ms.
            pGuardPerfect = SavePrefab("FX_Guard_Perfect", root =>
            {
                new Layer { Name = "Flash", Mat = mAddSoft, Duration = 0.3f, Life = R(0.13f), Size = R(2.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, GoldMid, 0.95f, 0.3f), SizeCurve = Curve(0f, 0.5f, 0.4f, 1f, 1f, 1.1f) }.Build(root.transform);
                new Layer { Name = "Star", Mat = mAddStar6, Duration = 0.3f, Life = R(0.22f), Size = R(1.5f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, GoldCore, 1f, 0.5f), SizeCurve = Curve(0f, 0.4f, 0.3f, 1f, 1f, 0.9f) }.Build(root.transform);
                new Layer { Name = "Ring", Mat = mAddRing, Duration = 0.3f, Life = R(0.22f), Size = R(2.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(GoldCore, GoldMid, 1f, 0.35f), SizeCurve = Curve(0f, 0.08f, 0.5f, 0.7f, 1f, 1f) }.Build(root.transform);
                new Layer
                {
                    Name = "Sparks", Mat = mAddStreak, Duration = 0.3f, Life = R(0.2f, 0.36f), Speed = R(4f, 8f), Size = R(0.06f, 0.1f), Bursts = new[] { (0f, 12, 16) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.1f, Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.8f, VelocityScale = 0.05f, Drag = 1.5f, World = true,
                    Grad = Snap(GoldCore, GoldMid, 1f, 0.5f),
                }.Build(root.transform);
            });
        }

        // =============================================================================================================== Arqueiro

        static GameObject MakeArrowProjectile(string name, float meshScale, float trailSeconds, float trailWidth, Color core, Color mid, Color halo)
        {
            return SavePrefab(name, root =>
            {
                MeshObject(root, "Arrow", meshArrow, mMeshArrow, Vector3.zero, Vector3.one * meshScale);
                var tail = Child(root, "Trail", new Vector3(0f, 0f, -0.3f * meshScale));
                AddTrail(tail, mAddTrail, trailSeconds, trailWidth, TrailGradient(core, mid, 0.95f));
                new Layer { Name = "Halo", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.3f), Size = R(0.55f * meshScale), Rate = 36f, Position = new Vector3(0f, 0f, 0.3f * meshScale), Grad = Flat(halo, 0.24f, 0.1f, 0.5f) }.Build(root.transform);
            });
        }

        static void SparkBurst(GameObject root, Color core, Color edge, int minCount, int maxCount, float speedMin, float speedMax, float size, float life)
        {
            new Layer
            {
                Name = "Flash", Mat = mAddStar4, Duration = 0.3f, Life = R(0.1f), Size = R(size * 3.5f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                Grad = Snap(Color.white, core, 1f, 0.4f), SizeCurve = Curve(0f, 0.5f, 0.3f, 1f, 1f, 0.8f),
            }.Build(root.transform);
            new Layer
            {
                Name = "Sparks", Mat = mAddStreak, Duration = 0.4f, Life = R(life * 0.6f, life), Speed = R(speedMin, speedMax), Size = R(size * 0.5f, size), Bursts = new[] { (0f, minCount, maxCount) },
                Shape = ParticleSystemShapeType.Sphere, Radius = 0.05f, Gravity = 0.5f, Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.8f, VelocityScale = 0.045f, Drag = 1.3f, World = true,
                Grad = Snap(core, edge, 1f, 0.5f),
            }.Build(root.transform);
        }

        static void BuildArcherPrefabs()
        {
            pArrow = MakeArrowProjectile("FX_Arrow", 1f, 0.12f, 0.16f, AcidCore, AcidMid, AcidMid);
            pArrowPierce = MakeArrowProjectile("FX_Arrow_Pierce", 1.45f, 0.25f, 0.26f, Color.white, AcidMid, AcidCore);

            pArrowMuzzle = SavePrefab("FX_Arrow_Muzzle", root =>
            {
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.2f, Life = R(0.08f), Size = R(0.7f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, AcidCore, 1f, 0.4f) }.Build(root.transform);
                new Layer { Name = "Glow", Mat = mAddSoft, Duration = 0.2f, Life = R(0.1f), Size = R(0.8f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(AcidCore, AcidMid, 0.7f, 0.3f) }.Build(root.transform);
            });
            pFanMuzzle = SavePrefab("FX_Arrow_FanMuzzle", root =>
            {
                for (var i = -1; i <= 1; i++)
                {
                    new Layer
                    {
                        Name = "Ray" + i, Mat = mAddStreak, Duration = 0.2f, Life = R(0.08f), Speed = R(14f), Size = R(0.22f), Bursts = new[] { (0f, 1, 1) },
                        Shape = ParticleSystemShapeType.Cone, Angle = 0f, Radius = 0.001f, ShapeRotation = new Vector3(0f, i * 14f, 0f),
                        Render = ParticleSystemRenderMode.Stretch, LengthScale = 6f, VelocityScale = 0.04f, Grad = Snap(AcidCore, AcidMid, 1f, 0.5f),
                    }.Build(root.transform);
                }
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.2f, Life = R(0.08f), Size = R(0.8f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, AcidCore, 1f, 0.4f) }.Build(root.transform);
            });
            pArrowHit = SavePrefab("FX_Arrow_Hit", root =>
            {
                SparkBurst(root, AcidCore, AcidMid, 5, 8, 2.5f, 5f, 0.07f, 0.35f);
                new Layer
                {
                    Name = "Puff", Mat = mAlphaSmoke, Duration = 0.4f, Life = R(0.3f, 0.5f), Speed = R(0.4f, 1f), Size = R(0.18f, 0.26f), Bursts = new[] { (0f, 3, 4) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.05f, World = true, Grad = Flat(AcidEdge, 0.4f, 0.1f, 0.3f), SizeCurve = Curve(0f, 0.5f, 1f, 1.4f),
                }.Build(root.transform);
            });
            pPierceHit = SavePrefab("FX_Arrow_PierceHit", root =>
            {
                SparkBurst(root, Color.white, AcidMid, 9, 13, 3f, 7f, 0.09f, 0.4f);
                new Layer
                {
                    Name = "Ring", Mat = mAddRingSoft, Duration = 0.3f, Life = R(0.2f), Size = R(1.2f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Grad = Snap(Color.white, AcidMid, 0.8f, 0.2f), SizeCurve = Curve(0f, 0.15f, 0.5f, 0.7f, 1f, 1f),
                }.Build(root.transform);
            });

            // Carga do Arqueiro: a ponta da flecha acende e linhas de tensão convergem no encaixe.
            pChargeArcher = SavePrefab("FX_Archer_Charge", root =>
            {
                var grow = Child(root, "Grow", Vector3.zero);
                grow.AddComponent<VfxGrow>().Configure(0.15f, 0.9f);
                new Layer { Name = "Tip", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.3f), Size = R(0.9f), Rate = 34f, Grad = Flat(AcidMid, 0.32f, 0.1f, 0.5f) }.Build(grow.transform);
                new Layer { Name = "TipCore", Mat = mAddCore, Duration = 1f, Loop = true, Life = R(0.18f), Size = R(0.45f), Rate = 40f, Grad = Flat(AcidCore, 0.9f, 0.05f, 0.5f) }.Build(grow.transform);
                new Layer
                {
                    Name = "Tension", Mat = mAddStreak, Duration = 1f, Loop = true, Life = R(0.3f), Speed = R(-1.8f), Size = R(0.05f), Rate = 26f,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.55f, RadiusThickness = 0f, Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.6f, VelocityScale = 0.1f,
                    Grad = Snap(AcidCore, AcidMid, 0.9f, 0.4f),
                }.Build(root.transform);
            });

            // Chuva de Flechas: círculo de marcação (ácido, nunca vermelho), 12 a 16 flechas caindo de 6 m em 0,6 s e poeira no impacto.
            pRainMarker = SavePrefab("FX_Rain_Marker", root =>
            {
                var g = Child(root, "Ground", new Vector3(0f, Ground, 0f));
                new Layer
                {
                    Name = "Marker", Mat = mAddRune, Duration = 1.2f, Life = R(1.1f), Size = R(6f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Flat(AcidMid, 0.55f, 0.12f, 0.75f), StartRotation = R(0f, 360f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Disc", Mat = mAddSoft, Duration = 1.2f, Life = R(1.1f), Size = R(5.9f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Flat(AcidMid, 0.14f, 0.12f, 0.75f),
                }.Build(g.transform);
            });

            pRain = SavePrefab("FX_Rain", root =>
            {
                new Layer
                {
                    Name = "Arrows", Mat = mMeshArrow, Duration = 0.5f, Life = R(0.3f), Speed = R(22f), Size = R(0.7f), Rate = 30f, Max = 24,
                    Shape = ParticleSystemShapeType.Cone, Angle = 0f, Radius = 2.9f, RadiusThickness = 1f, Position = new Vector3(0f, 6f, 0f), ShapeRotation = new Vector3(90f, 0f, 0f),
                    Render = ParticleSystemRenderMode.Mesh, Mesh = meshArrow, AlignToVelocity = true, Grad = Flat(Color.white, 1f, 0.01f, 0.85f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "ArrowTrails", Mat = mAddStreak, Duration = 0.5f, Life = R(0.28f), Speed = R(22f), Size = R(0.1f), Rate = 30f, Max = 24,
                    Shape = ParticleSystemShapeType.Cone, Angle = 0f, Radius = 2.9f, Position = new Vector3(0f, 6.5f, 0f), ShapeRotation = new Vector3(90f, 0f, 0f),
                    Render = ParticleSystemRenderMode.Stretch, LengthScale = 1f, VelocityScale = 0.12f, Grad = Flat(AcidCore, 0.85f, 0.02f, 0.8f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "Impacts", Mat = mAlphaSmoke, Duration = 0.5f, Delay = 0.25f, Life = R(0.35f, 0.55f), Speed = R(0.5f, 1.4f), Size = R(0.4f, 0.7f), Rate = 30f, Max = 24,
                    Shape = ParticleSystemShapeType.Cone, Angle = 18f, Radius = 2.8f, ShapeRotation = new Vector3(-90f, 0f, 0f), Position = new Vector3(0f, Ground, 0f), World = true,
                    Grad = Flat(PhysEdge, 0.45f, 0.1f, 0.35f), SizeCurve = Curve(0f, 0.4f, 1f, 1.4f), StartRotation = R(0f, 360f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "ImpactSparks", Mat = mAddStreak, Duration = 0.5f, Delay = 0.25f, Life = R(0.15f, 0.3f), Speed = R(2f, 4.5f), Size = R(0.05f, 0.08f), Rate = 36f, Max = 30,
                    Shape = ParticleSystemShapeType.Cone, Angle = 30f, Radius = 2.8f, ShapeRotation = new Vector3(-90f, 0f, 0f), Position = new Vector3(0f, Ground, 0f), Gravity = 1f,
                    Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.6f, VelocityScale = 0.04f, World = true, Grad = Snap(AcidCore, AcidMid, 1f, 0.5f),
                }.Build(root.transform);
            });

            pLeapDust = SavePrefab("FX_Leap_Dust", root =>
            {
                new Layer
                {
                    Name = "Ring", Mat = mAddRingSoft, Duration = 0.4f, Life = R(0.3f), Size = R(2.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Position = new Vector3(0f, Ground, 0f),
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Snap(PhysMid, PhysEdge, 0.45f, 0.2f), SizeCurve = Curve(0f, 0.15f, 0.5f, 0.7f, 1f, 1f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "Dust", Mat = mAlphaSmoke, Duration = 0.4f, Life = R(0.4f, 0.7f), Speed = R(0.8f, 2f), Size = R(0.3f, 0.5f), Bursts = new[] { (0f, 8, 10) },
                    Shape = ParticleSystemShapeType.Circle, Radius = 0.3f, ShapeRotation = new Vector3(90f, 0f, 0f), Position = new Vector3(0f, 0.1f, 0f), World = true,
                    Grad = Flat(PhysEdge, 0.5f, 0.1f, 0.35f), SizeCurve = Curve(0f, 0.5f, 1f, 1.5f), StartRotation = R(0f, 360f),
                }.Build(root.transform);
                // 3 linhas de vento atrás (o salto vai para trás: +Z do prefab é a direção do tiro, o vento sai para o lado oposto ao do pulo)
                for (var i = -1; i <= 1; i++)
                {
                    new Layer
                    {
                        Name = "Wind" + i, Mat = mAddStreak, Duration = 0.4f, Life = R(0.25f), Speed = R(6f), Size = R(0.12f), Bursts = new[] { (0f, 1, 1) },
                        Shape = ParticleSystemShapeType.Cone, Angle = 0f, Radius = 0.001f, Position = new Vector3(i * 0.28f, 0.7f + i * 0.15f, 0f),
                        Render = ParticleSystemRenderMode.Stretch, LengthScale = 5f, VelocityScale = 0.05f, World = true, Grad = Snap(PhysMid, PhysEdge, 0.6f, 0.4f),
                    }.Build(root.transform);
                }
            });

            pGuardArcher = SavePrefab("FX_Guard_Archer", root =>
            {
                new Layer { Name = "Glow", Mat = mAddSoft, Duration = 0.3f, Life = R(0.15f), Size = R(1.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(AcidCore, AcidMid, 0.8f, 0.3f) }.Build(root.transform);
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.3f, Life = R(0.1f), Size = R(0.6f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, AcidCore, 1f, 0.4f) }.Build(root.transform);
            });
        }

        // =============================================================================================================== Mago

        static void SteadyOrb(GameObject root, Color core, Color mid, Color halo, float coreSize, float haloSize, float ringSize)
        {
            new Layer { Name = "Halo", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.25f), Size = R(haloSize), Rate = 40f, Grad = Flat(halo, 0.26f, 0.1f, 0.5f) }.Build(root.transform);
            new Layer { Name = "Core", Mat = mAddCore, Duration = 1f, Loop = true, Life = R(0.14f), Size = R(coreSize), Rate = 50f, Grad = Flat(core, 0.95f, 0.05f, 0.5f) }.Build(root.transform);
            new Layer { Name = "Mid", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.16f), Size = R(coreSize * 1.45f), Rate = 40f, Grad = Flat(mid, 0.55f, 0.06f, 0.5f) }.Build(root.transform);
            if (ringSize > 0f)
            {
                new Layer
                {
                    Name = "Ring", Mat = mAddRing, Duration = 1f, Loop = true, Life = R(0.5f), Size = R(ringSize), Rate = 4f, RotationSpeed = 140f, StartRotation = R(0f, 360f),
                    Grad = Flat(mid, 0.6f, 0.1f, 0.6f), SizeCurve = Curve(0f, 0.8f, 1f, 1.1f),
                }.Build(root.transform);
            }
        }

        static void BuildMagePrefabs()
        {
            pCastArcane = SavePrefab("FX_Mage_Cast_Arcane", root =>
            {
                var grow = Child(root, "Grow", Vector3.zero);
                grow.AddComponent<VfxGrow>().Configure(0.2f, 0.18f);
                new Layer { Name = "Halo", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.25f), Size = R(0.8f), Rate = 34f, Grad = Flat(ShadowMid, 0.32f, 0.1f, 0.5f) }.Build(grow.transform);
                new Layer { Name = "Core", Mat = mAddCore, Duration = 1f, Loop = true, Life = R(0.15f), Size = R(0.4f), Rate = 40f, Grad = Flat(ShadowCore, 0.9f, 0.05f, 0.5f) }.Build(grow.transform);
                new Layer
                {
                    Name = "Motes", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.3f), Speed = R(-1.2f), Size = R(0.05f, 0.08f), Rate = 22f,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.45f, RadiusThickness = 0f, Grad = Snap(ShadowCore, ShadowMid, 1f, 0.5f),
                }.Build(root.transform);
            });
            pCastFire = SavePrefab("FX_Mage_Cast_Fire", root =>
            {
                var grow = Child(root, "Grow", Vector3.zero);
                grow.AddComponent<VfxGrow>().Configure(0.2f, 0.25f);
                new Layer { Name = "Halo", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.25f), Size = R(1.0f), Rate = 34f, Grad = Flat(FireMid, 0.32f, 0.1f, 0.5f) }.Build(grow.transform);
                new Layer { Name = "Core", Mat = mAddCore, Duration = 1f, Loop = true, Life = R(0.15f), Size = R(0.5f), Rate = 40f, Grad = Flat(FireCore, 0.95f, 0.05f, 0.5f) }.Build(grow.transform);
                new Layer
                {
                    Name = "Embers", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.4f, 0.7f), Speed = R(0.3f, 0.9f), Size = R(0.05f, 0.08f), Rate = 16f, Shape = ParticleSystemShapeType.Sphere,
                    Radius = 0.2f, Gravity = -0.2f, World = true, Grad = Snap(SparkYellow, FireMid, 1f, 0.5f),
                }.Build(root.transform);
            });

            pFireMuzzle = SavePrefab("FX_Mage_Muzzle_Fire", root =>
            {
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.3f, Life = R(0.12f), Size = R(1.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, FireMid, 1f, 0.4f) }.Build(root.transform);
                new Layer { Name = "Glow", Mat = mAddSoft, Duration = 0.3f, Life = R(0.18f), Size = R(1.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(FireCore, FireMid, 0.8f, 0.3f) }.Build(root.transform);
                new Layer
                {
                    Name = "Embers", Mat = mAddStreak, Duration = 0.3f, Life = R(0.25f, 0.5f), Speed = R(2.5f, 5.5f), Size = R(0.05f, 0.08f), Bursts = new[] { (0f, 8, 12) }, Shape = ParticleSystemShapeType.Cone,
                    Angle = 30f, Radius = 0.05f, Gravity = 0.6f, Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.8f, VelocityScale = 0.045f, World = true, Grad = Snap(SparkYellow, FireMid, 1f, 0.5f),
                }.Build(root.transform);
            });
            pIceHit = SavePrefab("FX_Ice_Hit", root =>
            {
                SparkBurst(root, IceCore, IceMid, 7, 10, 2.5f, 5f, 0.07f, 0.4f);
                new Layer
                {
                    Name = "Frost", Mat = mAlphaSmoke, Duration = 0.4f, Life = R(0.4f, 0.7f), Speed = R(0.3f, 0.9f), Size = R(0.3f, 0.5f), Bursts = new[] { (0f, 3, 4) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.1f, World = true, Grad = Flat(IceCore, 0.45f, 0.1f, 0.35f), SizeCurve = Curve(0f, 0.5f, 1f, 1.3f), StartRotation = R(0f, 360f),
                }.Build(root.transform);
            });

            // Dardo Arcano: violeta (sombra do docs/03) com núcleo claro e fagulhas, rápido, rastro de 150 ms.
            pDart = SavePrefab("FX_Dart", root =>
            {
                SteadyOrb(root, ShadowCore, ShadowMid, ShadowMid, 0.3f, 0.75f, 0f);
                new Layer
                {
                    Name = "Sparks", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.12f, 0.22f), Speed = R(0.2f, 0.9f), Size = R(0.04f, 0.07f), Rate = 42f,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.1f, World = true, Grad = Snap(ShadowCore, ShadowMid, 1f, 0.5f),
                }.Build(root.transform);
                var trail = Child(root, "Trail", Vector3.zero);
                AddTrail(trail, mAddTrail, 0.15f, 0.22f, TrailGradient(BoltCore, ShadowMid, 0.95f));
            });
            pDartPop = SavePrefab("FX_Dart_Pop", root =>
            {
                SparkBurst(root, ShadowCore, ShadowMid, 8, 11, 2.5f, 5.5f, 0.07f, 0.35f);
                new Layer
                {
                    Name = "Ring", Mat = mAddRingSoft, Duration = 0.3f, Life = R(0.2f), Size = R(1.1f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Grad = Snap(ShadowCore, ShadowMid, 0.85f, 0.2f), SizeCurve = Curve(0f, 0.15f, 0.5f, 0.7f, 1f, 1f),
                }.Build(root.transform);
            });

            // Orbe Arcano: esfera de 45 cm que pulsa, com anel girando; explosão de 130 uu com onda curta.
            pOrb = SavePrefab("FX_Orb", root =>
            {
                SteadyOrb(root, ShadowCore, BoltMid, ShadowMid, 0.45f, 1.1f, 0.85f);
                new Layer
                {
                    Name = "Pulse", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.45f), Size = R(0.9f), Rate = 4.5f, Grad = Flat(BoltMid, 0.42f, 0.2f, 0.5f),
                    SizeCurve = Curve(0f, 0.7f, 1f, 1.25f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "Sparks", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.15f, 0.3f), Speed = R(0.3f, 1f), Size = R(0.05f, 0.08f), Rate = 36f,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.2f, World = true, Grad = Snap(BoltCore, ShadowMid, 1f, 0.5f),
                }.Build(root.transform);
                var trail = Child(root, "Trail", Vector3.zero);
                AddTrail(trail, mAddTrail, 0.2f, 0.4f, TrailGradient(ShadowCore, BoltEdge, 0.9f));
            });
            pOrbExplosion = SavePrefab("FX_Orb_Explosion", root =>
            {
                var air = Child(root, "Air", new Vector3(0f, 0.9f, 0f));
                new Layer { Name = "Flash", Mat = mAddSoft, Duration = 0.3f, Life = R(0.13f), Size = R(2.8f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, ShadowMid, 0.95f, 0.3f), SizeCurve = Curve(0f, 0.4f, 0.4f, 1f, 1f, 1.1f) }.Build(air.transform);
                new Layer { Name = "Core", Mat = mAddCore, Duration = 0.3f, Life = R(0.16f), Size = R(1.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(BoltCore, ShadowCore, 1f, 0.3f) }.Build(air.transform);
                new Layer
                {
                    Name = "ShockAir", Mat = mAddRing, Duration = 0.4f, Life = R(0.25f), Size = R(2.6f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Grad = Snap(BoltCore, ShadowMid, 0.95f, 0.3f), SizeCurve = Curve(0f, 0.15f, 0.45f, 0.75f, 1f, 1f),
                }.Build(air.transform);
                var g = Child(root, "Ground", new Vector3(0f, Ground, 0f));
                new Layer
                {
                    Name = "ShockGround", Mat = mAddRingSoft, Duration = 0.5f, Life = R(0.35f), Size = R(2.6f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Snap(ShadowCore, ShadowMid, 0.9f, 0.3f), SizeCurve = Curve(0f, 0.1f, 0.4f, 0.75f, 1f, 1f),
                }.Build(g.transform);
                SparkBurst(air, ShadowCore, ShadowMid, 14, 18, 3f, 6.5f, 0.08f, 0.6f);
                new Layer
                {
                    Name = "Wisps", Mat = mAlphaGhostWisp, Duration = 0.5f, Life = R(0.5f, 0.8f), Speed = R(0.3f, 1f), Size = R(0.5f, 0.8f), Bursts = new[] { (0f, 4, 5) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.3f, Gravity = -0.05f, World = true, Grad = Flat(ShadowEdge, 0.4f, 0.1f, 0.4f), SizeCurve = Curve(0f, 0.5f, 1f, 1.4f), StartRotation = R(0f, 360f),
                }.Build(air.transform);
            });

            // Bola de Fogo (docs/18: 70 cm, núcleo, chamas, fumaça e luz que viaja; explosão de 220 uu).
            pFireball = SavePrefab("FX_Fireball", root =>
            {
                new Layer { Name = "Halo", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.25f), Size = R(1.5f), Rate = 36f, Grad = Flat(FireMid, 0.24f, 0.1f, 0.5f) }.Build(root.transform);
                new Layer { Name = "Body", Mat = mAddFlame, Duration = 1f, Loop = true, Life = R(0.2f, 0.3f), Size = R(0.7f, 0.95f), Rate = 70f, World = true, Speed = R(0.1f, 0.5f), Shape = ParticleSystemShapeType.Sphere, Radius = 0.12f,
                    Grad = Ramp(FireCore, FireMid, FireEdge, 0.95f, 0.05f, 0.5f), SizeCurve = Curve(0f, 0.7f, 0.3f, 1f, 1f, 0.35f), StartRotation = R(0f, 360f), RotationSpeed = 50f }.Build(root.transform);
                new Layer { Name = "Core", Mat = mAddCore, Duration = 1f, Loop = true, Life = R(0.12f), Size = R(0.55f), Rate = 60f, Grad = Flat(FireCore, 1f, 0.05f, 0.5f) }.Build(root.transform);
                new Layer
                {
                    Name = "Embers", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.3f, 0.6f), Speed = R(0.3f, 1.4f), Size = R(0.04f, 0.08f), Rate = 36f, Shape = ParticleSystemShapeType.Sphere,
                    Radius = 0.2f, Gravity = -0.1f, World = true, Grad = Snap(SparkYellow, FireMid, 1f, 0.55f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "Smoke", Mat = mAlphaSmoke, Duration = 1f, Loop = true, Life = R(0.45f, 0.65f), Speed = R(0.1f, 0.4f), Size = R(0.25f, 0.4f), Rate = 22f, World = true,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.14f, Gravity = -0.05f, Grad = Flat(Hex("#403836"), 0.42f, 0.1f, 0.35f), SizeCurve = Curve(0f, 0.6f, 1f, 2.2f), StartRotation = R(0f, 360f),
                }.Build(root.transform);
                var lamp = Child(root, "Light", Vector3.zero);
                AddLight(lamp, new Color(1f, 0.52f, 0.2f), 7f, 3.2f, 0f, null, 0.22f);
            });
            pFireballExplosion = SavePrefab("FX_Fireball_Explosion", root =>
            {
                var air = Child(root, "Air", new Vector3(0f, 0.9f, 0f));
                new Layer { Name = "Flash", Mat = mAddSoft, Duration = 0.3f, Life = R(0.14f), Size = R(4.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, FireMid, 0.95f, 0.3f), SizeCurve = Curve(0f, 0.4f, 0.35f, 1f, 1f, 1.1f) }.Build(air.transform);
                new Layer { Name = "Core", Mat = mAddCore, Duration = 0.3f, Life = R(0.2f), Size = R(2.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(FireCore, FireMid, 1f, 0.35f) }.Build(air.transform);
                new Layer
                {
                    Name = "ShockAir", Mat = mAddRing, Duration = 0.4f, Life = R(0.24f), Size = R(4.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Grad = Snap(FireCore, FireMid, 0.95f, 0.3f), SizeCurve = Curve(0f, 0.12f, 0.45f, 0.75f, 1f, 1f),
                }.Build(air.transform);
                new Layer
                {
                    Name = "FireBurst", Mat = mAddFlame, Duration = 0.4f, Life = R(0.4f, 0.75f), Speed = R(1.5f, 4.5f), Size = R(0.8f, 1.5f), Bursts = new[] { (0f, 14, 18) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.3f, Gravity = -0.15f, Grad = Ramp(FireCore, FireMid, FireEdge, 0.9f, 0.06f, 0.45f),
                    SizeCurve = Curve(0f, 0.6f, 0.4f, 1f, 1f, 0.6f), StartRotation = R(0f, 360f), RotationSpeed = 60f, Drag = 1.2f,
                }.Build(air.transform);
                new Layer
                {
                    Name = "Embers", Mat = mAddStreak, Duration = 0.4f, Life = R(0.55f, 1.1f), Speed = R(4f, 9f), Size = R(0.06f, 0.1f), Bursts = new[] { (0f, 26, 32) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.3f, Gravity = 1.6f, Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.8f, VelocityScale = 0.045f, Drag = 0.8f, World = true,
                    Grad = Snap(SparkYellow, FireMid, 1f, 0.55f),
                }.Build(air.transform);
                new Layer
                {
                    Name = "Smoke", Mat = mAlphaSmoke, Duration = 0.5f, Delay = 0.05f, Life = R(0.9f, 1.4f), Speed = R(0.4f, 1.4f), Size = R(1f, 1.6f), Bursts = new[] { (0f, 7, 9) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.6f, ShapeScale = new Vector3(1f, 0.4f, 1f), Gravity = -0.05f, World = true,
                    Grad = Flat(Hex("#2E2826"), 0.5f, 0.1f, 0.4f), SizeCurve = Curve(0f, 0.5f, 1f, 1.4f), StartRotation = R(0f, 360f),
                }.Build(air.transform);
                var g = Child(root, "Ground", new Vector3(0f, Ground, 0f));
                new Layer
                {
                    Name = "ShockGround", Mat = mAddRingSoft, Duration = 0.5f, Life = R(0.32f), Size = R(4.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Snap(FireCore, FireMid, 0.9f, 0.3f), SizeCurve = Curve(0f, 0.1f, 0.4f, 0.75f, 1f, 1f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "GroundGlow", Mat = mAddSoft, Duration = 1.2f, Life = R(0.9f), Size = R(4.2f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Snap(FireMid, FireEdge, 0.3f, 0.25f),
                }.Build(g.transform);
                // Marca de queimado no chão: some em ~3 s.
                new Layer
                {
                    Name = "Scorch", Mat = mAlphaScorch, Duration = 3.4f, Life = R(3.2f), Size = R(3.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Position = new Vector3(0f, -0.015f, 0f),
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Flat(Color.white, 0.85f, 0.02f, 0.62f), StartRotation = R(0f, 360f), SizeCurve = Curve(0f, 0.7f, 0.05f, 1f, 1f, 1.03f),
                }.Build(g.transform);
                var lamp = Child(root, "Light", new Vector3(0f, 1.2f, 0f));
                AddLight(lamp, new Color(1f, 0.55f, 0.25f), 8f, 7f, 0.45f, Curve(0f, 1f, 0.2f, 0.75f, 1f, 0f), 0.1f);
            });
            pChargeFire = SavePrefab("FX_Mage_Charge_Fire", root =>
            {
                var grow = Child(root, "Grow", Vector3.zero);
                grow.AddComponent<VfxGrow>().Configure(0.14f, 0.9f);
                new Layer { Name = "Halo", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.25f), Size = R(1.6f), Rate = 36f, Grad = Flat(FireMid, 0.26f, 0.1f, 0.5f) }.Build(grow.transform);
                new Layer { Name = "Body", Mat = mAddFlame, Duration = 1f, Loop = true, Life = R(0.3f, 0.4f), Size = R(0.8f, 1.0f), Rate = 50f, Shape = ParticleSystemShapeType.Sphere, Radius = 0.12f, Speed = R(0.1f, 0.4f),
                    Grad = Ramp(FireCore, FireMid, FireEdge, 0.95f, 0.05f, 0.5f), SizeCurve = Curve(0f, 0.7f, 0.3f, 1f, 1f, 0.35f), StartRotation = R(0f, 360f), RotationSpeed = 60f }.Build(grow.transform);
                new Layer { Name = "Core", Mat = mAddCore, Duration = 1f, Loop = true, Life = R(0.14f), Size = R(0.6f), Rate = 50f, Grad = Flat(FireCore, 1f, 0.05f, 0.5f) }.Build(grow.transform);
                new Layer
                {
                    Name = "Embers", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.4f, 0.8f), Speed = R(0.3f, 1f), Size = R(0.04f, 0.08f), Rate = 18f, Shape = ParticleSystemShapeType.Sphere,
                    Radius = 0.35f, Gravity = -0.2f, World = true, Grad = Snap(SparkYellow, FireMid, 1f, 0.5f),
                }.Build(root.transform);
            });

            // Nova de Gelo: anel de gelo cresce até 340 uu em 350 ms; cristais no chão por 600 ms.
            pNova = SavePrefab("FX_Nova", root =>
            {
                var g = Child(root, "Ground", new Vector3(0f, Ground, 0f));
                new Layer
                {
                    Name = "Wave", Mat = mAddRingSoft, Duration = 0.5f, Life = R(0.4f), Size = R(6.8f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Snap(IceCore, IceMid, 0.95f, 0.3f), SizeCurve = Curve(0f, 0.06f, 0.35f, 0.8f, 1f, 1f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Edge", Mat = mAddRing, Duration = 0.5f, Delay = 0.03f, Life = R(0.45f), Size = R(6.8f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Snap(IceCore, IceCore, 0.9f, 0.3f), SizeCurve = Curve(0f, 0.06f, 0.33f, 0.8f, 1f, 1f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Frost", Mat = mAddSoft, Duration = 1.2f, Delay = 0.03f, Life = R(1.0f), Size = R(6.4f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f,
                    Render = ParticleSystemRenderMode.HorizontalBillboard, Grad = Flat(IceMid, 0.22f, 0.15f, 0.5f), SizeCurve = Curve(0f, 0.1f, 0.3f, 1f, 1f, 1f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Crystals", Mat = mMeshCrystal, Duration = 0.4f, Life = R(0.9f, 1.15f), Size = R(0.55f, 1.15f), Rate = 70f, Max = 40,
                    Shape = ParticleSystemShapeType.Circle, Radius = 3.1f, RadiusThickness = 0.55f, ShapeRotation = new Vector3(90f, 0f, 0f),
                    Render = ParticleSystemRenderMode.Mesh, Mesh = meshCrystal, UseRotation3D = true, StartRotation3DMin = new Vector3(-12f, 0f, -12f), StartRotation3DMax = new Vector3(12f, 360f, 12f),
                    Grad = Flat(Color.white, 1f, 0.01f, 0.78f), SizeCurve = Curve(0f, 0f, 0.1f, 1.1f, 0.2f, 1f, 0.72f, 1f, 1f, 0f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Mist", Mat = mAlphaSmoke, Duration = 0.4f, Life = R(0.9f, 1.3f), Speed = R(0.2f, 0.6f), Size = R(1.1f, 1.7f), Bursts = new[] { (0f, 8, 10) },
                    Shape = ParticleSystemShapeType.Circle, Radius = 3f, ShapeRotation = new Vector3(90f, 0f, 0f), Position = new Vector3(0f, 0.1f, 0f), Gravity = -0.02f, World = true,
                    Grad = Flat(IceCore, 0.3f, 0.15f, 0.4f), SizeCurve = Curve(0f, 0.5f, 1f, 1.3f), StartRotation = R(0f, 360f),
                }.Build(g.transform);
                new Layer
                {
                    Name = "Glints", Mat = mAddStar4, Duration = 0.5f, Delay = 0.05f, Life = R(0.35f, 0.6f), Size = R(0.22f, 0.42f), Bursts = new[] { (0f, 14, 18) },
                    Shape = ParticleSystemShapeType.Circle, Radius = 3.2f, ShapeRotation = new Vector3(90f, 0f, 0f), Position = new Vector3(0f, 0.25f, 0f),
                    Grad = Flat(IceCore, 1f, 0.15f, 0.5f), StartRotation = R(0f, 90f),
                }.Build(g.transform);
                new Layer { Name = "Flash", Mat = mAddSoft, Duration = 0.3f, Life = R(0.14f), Size = R(2.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Position = new Vector3(0f, 0.6f, 0f), Grad = Snap(Color.white, IceMid, 0.9f, 0.3f) }.Build(g.transform);
                var lamp = Child(root, "Light", new Vector3(0f, 1.0f, 0f));
                AddLight(lamp, new Color(0.45f, 0.78f, 1f), 6f, 3.5f, 0.45f, Curve(0f, 1f, 0.3f, 0.7f, 1f, 0f), 0.05f);
            });

            // Barreira Arcana: cúpula de 110 uu de raio com fresnel e hexágonos; ondas nos pontos de impacto; estilhaça ao acabar a Mana.
            pDome = SavePrefab("FX_Barrier_Dome", root =>
            {
                var sphereMesh = BuiltinSphere();
                var dome = MeshObject(root, "Dome", sphereMesh, mDome, Vector3.zero, Vector3.one * 2.2f);
                var fade = dome.AddComponent<VfxFade>();
                fade.Configure(2.4f, true, Curve(0f, 0.85f, 0.5f, 1f, 1f, 0.85f), null, null, Color.white, true);
                new Layer
                {
                    Name = "Motes", Mat = mAddSpark, Duration = 1f, Loop = true, Life = R(0.5f, 0.9f), Speed = R(0.1f, 0.4f), Size = R(0.04f, 0.07f), Rate = 10f,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 1.1f, RadiusThickness = 0f, Grad = Flat(BoltCore, 0.9f, 0.2f, 0.5f),
                }.Build(root.transform);
            });
            pBarrierHit = SavePrefab("FX_Barrier_Hit", root =>
            {
                new Layer { Name = "Hex", Mat = mAddHex, Duration = 0.4f, Life = R(0.3f), Size = R(1.5f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(BoltCore, BoltMid, 0.9f, 0.3f), SizeCurve = Curve(0f, 0.3f, 1f, 1f), StartRotation = R(0f, 60f) }.Build(root.transform);
                new Layer { Name = "Ring", Mat = mAddRingSoft, Duration = 0.4f, Life = R(0.3f), Size = R(1.5f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(BoltCore, BoltMid, 0.8f, 0.3f), SizeCurve = Curve(0f, 0.1f, 1f, 1f) }.Build(root.transform);
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.3f, Life = R(0.1f), Size = R(0.7f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, BoltMid, 1f, 0.4f) }.Build(root.transform);
            });
            pBarrierBreak = SavePrefab("FX_Barrier_Break", root =>
            {
                new Layer { Name = "Flash", Mat = mAddSoft, Duration = 0.3f, Life = R(0.15f), Size = R(3.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(BoltCore, BoltMid, 0.85f, 0.3f), SizeCurve = Curve(0f, 0.6f, 1f, 1f) }.Build(root.transform);
                new Layer
                {
                    Name = "Shards", Mat = mAddHex, Duration = 0.4f, Life = R(0.3f, 0.5f), Speed = R(2f, 4.5f), Size = R(0.3f, 0.55f), Bursts = new[] { (0f, 12, 14) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.9f, RadiusThickness = 0f, Gravity = 0.4f, World = true, Grad = Snap(BoltCore, BoltEdge, 0.9f, 0.4f), StartRotation = R(0f, 360f), RotationSpeed = 200f,
                }.Build(root.transform);
                SparkBurst(root, BoltCore, BoltMid, 18, 24, 3f, 7f, 0.07f, 0.5f);
            });

            // Raio Arcano: feixe de 40 uu (clarão de 80 ms + brilho residual de 250 ms); o comprimento vem do alcance da habilidade.
            pRay = SavePrefab("FX_Ray", root =>
            {
                var glow = MeshObject(root, "Glow", meshBeam, mMeshBeam, Vector3.zero, new Vector3(0.55f, 0.55f, 1f));
                glow.AddComponent<VfxFade>().Configure(0.33f, false, Curve(0f, 1f, 0.24f, 0.85f, 1f, 0f), Curve(0f, 1f, 0.24f, 0.8f, 1f, 0.2f), null,
                    new Color(BoltMid.r * 1.6f, BoltMid.g * 1.6f, BoltMid.b * 1.9f, 1f), false);
                var core = MeshObject(root, "Core", meshBeam, mMeshBeam, Vector3.zero, new Vector3(0.16f, 0.16f, 1f));
                core.AddComponent<VfxFade>().Configure(0.33f, false, Curve(0f, 1f, 0.24f, 0.9f, 1f, 0f), Curve(0f, 1f, 0.24f, 0.7f, 1f, 0.1f), null,
                    new Color(BoltCore.r * 1.4f, BoltCore.g * 1.4f, BoltCore.b * 1.6f, 1f), false);
            });
            pRayMuzzle = SavePrefab("FX_Ray_Muzzle", root =>
            {
                new Layer { Name = "Flash", Mat = mAddStar4, Duration = 0.3f, Life = R(0.14f), Size = R(1.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(Color.white, BoltMid, 1f, 0.4f) }.Build(root.transform);
                new Layer { Name = "Glow", Mat = mAddSoft, Duration = 0.3f, Life = R(0.25f), Size = R(1.0f), Bursts = new[] { (0f, 1, 1) }, Radius = 0.001f, Grad = Snap(BoltCore, BoltMid, 0.8f, 0.3f) }.Build(root.transform);
            });
            pRayHit = SavePrefab("FX_Ray_Hit", root => SparkBurst(root, BoltCore, BoltMid, 9, 12, 3f, 6f, 0.07f, 0.4f));
        }

        // =============================================================================================================== Inimigos

        static void BuildEnemyPrefabs()
        {
            // Flecha do Arqueiro Fantasma: ameaça (docs/03 seção 3.8): massa opaca com contorno quase preto, rastro translúcido e a faixa vermelha.
            pGhostArrow = SavePrefab("FX_Enemy_GhostArrow", root =>
            {
                MeshObject(root, "Outline", meshGhostArrow, mMeshOutline, Vector3.zero, Vector3.one * 1.28f);
                MeshObject(root, "Arrow", meshGhostArrow, mMeshGhost, Vector3.zero, Vector3.one);
                var tail = Child(root, "Trail", new Vector3(0f, 0f, -0.4f));
                AddTrail(tail, mAlphaGhostTrail, 0.35f, 0.22f, TrailGradient(ThreatShadowMid, ThreatShadowEdge, 0.7f));
                new Layer
                {
                    Name = "Wisps", Mat = mAlphaGhostWisp, Duration = 1f, Loop = true, Life = R(0.5f, 0.7f), Speed = R(0.05f, 0.3f), Size = R(0.22f, 0.32f), Rate = 18f, World = true,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.06f, Grad = Flat(ThreatShadowMid, 0.55f, 0.1f, 0.4f), SizeCurve = Curve(0f, 0.6f, 1f, 1.8f), StartRotation = R(0f, 360f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "RedBand", Mat = mAddStreak, Duration = 1f, Loop = true, Life = R(0.18f, 0.28f), Speed = R(0.05f, 0.4f), Size = R(0.06f, 0.1f), Rate = 34f, World = true,
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.05f, Position = new Vector3(0f, 0f, 0.45f), Render = ParticleSystemRenderMode.Stretch, LengthScale = 2.2f, VelocityScale = 0.05f,
                    Grad = Snap(ThreatRed, ThreatShadowEdge, 0.95f, 0.5f),
                }.Build(root.transform);
            });
            pGhostHit = SavePrefab("FX_Enemy_GhostArrow_Hit", root =>
            {
                new Layer
                {
                    Name = "Puff", Mat = mAlphaGhostWisp, Duration = 0.4f, Life = R(0.4f, 0.7f), Speed = R(0.5f, 1.4f), Size = R(0.3f, 0.5f), Bursts = new[] { (0f, 5, 7) },
                    Shape = ParticleSystemShapeType.Sphere, Radius = 0.08f, World = true, Grad = Flat(ThreatShadowMid, 0.7f, 0.1f, 0.4f), SizeCurve = Curve(0f, 0.5f, 1f, 1.6f), StartRotation = R(0f, 360f),
                }.Build(root.transform);
                new Layer
                {
                    Name = "Embers", Mat = mAddStreak, Duration = 0.4f, Life = R(0.18f, 0.32f), Speed = R(2f, 4.5f), Size = R(0.05f, 0.08f), Bursts = new[] { (0f, 5, 7) },
                    Shape = ParticleSystemShapeType.Cone, Angle = 50f, Radius = 0.04f, Gravity = 0.6f, Render = ParticleSystemRenderMode.Stretch, LengthScale = 1.8f, VelocityScale = 0.045f, World = true,
                    Grad = Snap(ThreatRed, ThreatShadowEdge, 1f, 0.5f),
                }.Build(root.transform);
            });
            pGhostCast = SavePrefab("FX_Enemy_GhostArrow_Cast", root =>
            {
                new Layer { Name = "Wisps", Mat = mAlphaGhostWisp, Duration = 1f, Loop = true, Life = R(0.4f, 0.6f), Speed = R(0.05f, 0.25f), Size = R(0.3f, 0.45f), Rate = 14f, Shape = ParticleSystemShapeType.Sphere, Radius = 0.12f,
                    World = true, Grad = Flat(ThreatShadowMid, 0.6f, 0.15f, 0.4f), SizeCurve = Curve(0f, 0.6f, 1f, 1.5f), StartRotation = R(0f, 360f) }.Build(root.transform);
                new Layer { Name = "Eye", Mat = mAddSoft, Duration = 1f, Loop = true, Life = R(0.3f), Size = R(0.38f), Rate = 20f, Grad = Flat(ThreatRed, 0.5f, 0.15f, 0.5f) }.Build(root.transform);
            });
        }

        static Mesh builtinSphere;

        static Mesh BuiltinSphere()
        {
            if (builtinSphere != null) return builtinSphere;
            var temp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            builtinSphere = temp.GetComponent<MeshFilter>().sharedMesh;
            UnityEngine.Object.DestroyImmediate(temp);
            return builtinSphere;
        }
    }
}
