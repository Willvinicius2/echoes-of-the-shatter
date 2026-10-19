using System;
using System.Collections.Generic;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Liga os prefabs às habilidades: regrava <see cref="SkillPresentationSet.vfx"/> dos SO_SkillPresentation_* (Guerreiro, Arqueiro, Mago,
    /// Arqueiro Fantasma). As entradas de animação (<see cref="SkillPresentationSet.entries"/>) são do AnimatorControllerBuilder e ficam intactas;
    /// se o conjunto ainda não existe (Arqueiro e Mago antes da animação), é criado vazio e o outro builder o completa depois.
    /// </summary>
    public static partial class VfxLibraryBuilder
    {
        public const string WarriorSetPath = AnimatorControllerBuilder.SkillSetDir + "/SO_SkillPresentation_Warrior.asset";
        public const string ArcherSetPath = AnimatorControllerBuilder.SkillSetDir + "/SO_SkillPresentation_Archer.asset";
        public const string MageSetPath = AnimatorControllerBuilder.SkillSetDir + "/SO_SkillPresentation_Mage.asset";
        public const string GhostArcherSetPath = AnimatorControllerBuilder.SkillSetDir + "/SO_SkillPresentation_GhostArcher.asset";

        // Altura de contato no corpo (peito do alvo) e do projétil, em metros.
        const float ChestHeight = 1.0f;

        static VfxSpec Spec(GameObject prefab, VfxPlace place, string anchor, float seconds, bool follow = false, bool align = true, float y = 0f,
            float scale = 1f, float radius = 0f, bool lengthFromRange = false)
        {
            return new VfxSpec
            {
                prefab = prefab, place = place, anchor = anchor, seconds = seconds, follow = follow, alignToDirection = align,
                yOffset = y, scale = scale, authoredRadiusMeters = radius, lengthFromRange = lengthFromRange,
            };
        }

        static VfxSpec OnAnchor(GameObject prefab, string anchor, float seconds, bool follow = false, float scale = 1f) =>
            Spec(prefab, VfxPlace.Anchor, anchor, seconds, follow, true, 0f, scale);

        static VfxSpec OnTarget(GameObject prefab, float seconds, float y = ChestHeight, float scale = 1f, float radius = 0f) =>
            Spec(prefab, VfxPlace.Target, string.Empty, seconds, false, true, y, scale, radius);

        static SkillVfxEntry Melee(string id, GameObject arc, GameObject trail, float coverage, float emit, float trailSeconds, GameObject hit)
        {
            return new SkillVfxEntry
            {
                skillId = id,
                releaseFx = new[] { Spec(arc, VfxPlace.OwnerFeet, string.Empty, 0.6f, false, true) },
                trail = Spec(trail, VfxPlace.Anchor, string.Empty, trailSeconds, false, false),
                trailBase = "weapon_base", trailTip = "weapon_tip", trailWidth = coverage, trailEmitSeconds = emit,
                hitFx = new[] { OnTarget(hit, 1.0f) },
            };
        }

        static SkillPresentationSet LoadSet(string path)
        {
            EnsureDir(AnimatorControllerBuilder.SkillSetDir);
            return SandboxBuilder.LoadOrCreate<SkillPresentationSet>(path);
        }

        static void BuildSets()
        {
            var warrior = LoadSet(WarriorSetPath);
            warrior.vfx = new List<SkillVfxEntry>
            {
                Melee("skill.warrior.iron_cut", pArc1, pTrail1, 0.3f, 0.22f, 0.5f, pHitSpark),
                Melee("skill.warrior.combo_2", pArc2, pTrail2, 0.3f, 0.22f, 0.5f, pHitSpark),
                // O 3º golpe do combo: faixa mais larga (cobre a arma toda), fio dourado, faísca pesada e anel.
                Melee("skill.warrior.combo_3", pArc3, pTrail3, 0.4f, 0.3f, 0.65f, pHitSparkHeavy),
                new SkillVfxEntry
                {
                    skillId = "skill.warrior.heavy_slash",
                    chargeFx = new[] { OnAnchor(pChargeGlowWarrior, "weapon_tip", 30f, true), Spec(pChargeRing, VfxPlace.OwnerFeet, string.Empty, 30f, true, false) },
                    chargeFullFx = new[] { OnAnchor(pChargeFlash, "weapon_tip", 0.4f, true) },
                    releaseFx = new[] { Spec(pArcHeavy, VfxPlace.OwnerFeet, string.Empty, 0.7f, false, true) },
                    trail = Spec(pTrailHeavy, VfxPlace.Anchor, string.Empty, 0.8f, false, false),
                    trailBase = "weapon_base", trailTip = "weapon_tip", trailWidth = 0.4f, trailEmitSeconds = 0.34f,
                    hitFx = new[] { OnTarget(pHitSparkHeavy, 1.0f) },
                },
                Melee("skill.warrior.charge", pArc2, pTrail2, 0.3f, 0.2f, 0.5f, pHitSpark),
                new SkillVfxEntry { skillId = "skill.warrior.stone_rift", hitFx = new[] { OnTarget(pHitSparkHeavy, 1.0f) } },
                new SkillVfxEntry { skillId = "skill.warrior.shield_bash", hitFx = new[] { OnTarget(pHitSparkHeavy, 1.0f) } },
                new SkillVfxEntry { skillId = "skill.devoured.guardian_slam", hitFx = new[] { OnTarget(pHitSparkHeavy, 1.0f) } },
                // Estados do kit (IDs virtuais): defesa erguida, golpe absorvido e defesa perfeita.
                new SkillVfxEntry
                {
                    skillId = "class.warrior#guard",
                    windupFx = new[] { Spec(pGuardArc, VfxPlace.OwnerFeet, string.Empty, 60f, true, true), OnAnchor(pGuardShimmer, "shield_face", 60f, true) },
                    hitFx = new[] { OnTarget(pGuardBlock, 0.6f, 0f) },
                },
                new SkillVfxEntry { skillId = "class.warrior#perfect", releaseFx = new[] { OnTarget(pGuardPerfect, 0.6f, 0f) } },
            };
            EditorUtility.SetDirty(warrior);

            var archer = LoadSet(ArcherSetPath);
            archer.vfx = new List<SkillVfxEntry>
            {
                Arrow("skill.archer.quick_shot", pArrow, 1f, pArrowMuzzle, pArrowHit),
                Arrow("skill.archer.fan_shot", pArrow, 1f, pFanMuzzle, pArrowHit),
                new SkillVfxEntry
                {
                    skillId = "skill.archer.piercing_shot",
                    chargeFx = new[] { OnAnchor(pChargeArcher, "bow_nock", 30f, true) },
                    chargeFullFx = new[] { OnAnchor(pChargeFlash, "bow_nock", 0.4f, true) },
                    releaseFx = new[] { OnAnchor(pArrowMuzzle, "bow_nock", 0.5f, false, 1.4f) },
                    projectile = pArrowPierce, launchAnchor = "bow_nock", launchBlendMeters = 1.5f, lingerSeconds = 0.4f,
                    hitFx = new[] { OnTarget(pPierceHit, 1.0f) },
                },
                new SkillVfxEntry
                {
                    skillId = "skill.archer.back_leap",
                    releaseFx = new[] { Spec(pLeapDust, VfxPlace.OwnerFeet, string.Empty, 0.8f), OnAnchor(pArrowMuzzle, "bow_nock", 0.5f) },
                    projectile = pArrow, launchAnchor = "bow_nock", launchBlendMeters = 1.2f, lingerSeconds = 0.25f,
                    hitFx = new[] { OnTarget(pArrowHit, 1.0f) },
                },
                new SkillVfxEntry
                {
                    skillId = "skill.archer.arrow_rain",
                    // A logica acerta ao fim do impacto: a marcacao fica na preparacao e as flechas caem no impacto, pousando no instante do golpe (ate 0,1 s antes).
                    windupFx = new[] { Marker() },
                    releaseFx = new[] { Rain() },
                    hitFx = new[] { OnTarget(pArrowHit, 1.0f) },
                },
                new SkillVfxEntry { skillId = "class.archer#guard", hitFx = new[] { OnAnchor(pGuardArcher, "bow_nock", 0.4f) } },
            };
            EditorUtility.SetDirty(archer);

            var mage = LoadSet(MageSetPath);
            mage.vfx = new List<SkillVfxEntry>
            {
                new SkillVfxEntry
                {
                    skillId = "skill.mage.arcane_dart",
                    windupFx = new[] { OnAnchor(pCastArcane, "staff_crystal", 1f, true) },
                    releaseFx = new[] { OnAnchor(pDartPop, "staff_crystal", 0.6f, false, 0.45f) },
                    projectile = pDart, launchAnchor = "staff_crystal", launchBlendMeters = 1.6f, lingerSeconds = 0.2f,
                    endFx = new[] { OnTarget(pDartPop, 0.8f, ChestHeight) },
                },
                new SkillVfxEntry
                {
                    skillId = "skill.mage.arcane_orb",
                    windupFx = new[] { OnAnchor(pCastArcane, "staff_crystal", 1f, true, 1.25f) },
                    releaseFx = new[] { OnAnchor(pDartPop, "staff_crystal", 0.6f, false, 0.7f) },
                    projectile = pOrb, launchAnchor = "staff_crystal", launchBlendMeters = 1.6f, lingerSeconds = 0.3f,
                    endFx = new[] { OnTarget(pOrbExplosion, 1.2f, 0f, 1f, 1.3f) },
                    missFx = new[] { OnTarget(pOrbExplosion, 1.2f, 0f, 1f, 1.3f) },
                },
                new SkillVfxEntry
                {
                    skillId = "skill.mage.fireball",
                    chargeFx = new[] { OnAnchor(pChargeFire, "staff_crystal", 30f, true) },
                    chargeFullFx = new[] { OnAnchor(pChargeFlash, "staff_crystal", 0.4f, true) },
                    windupFx = new[] { OnAnchor(pCastFire, "staff_crystal", 1f, true) },
                    releaseFx = new[] { OnAnchor(pFireMuzzle, "staff_crystal", 0.7f) },
                    projectile = pFireball, launchAnchor = "staff_crystal", launchBlendMeters = 1.8f, lingerSeconds = 0.9f,
                    endFx = new[] { OnTarget(pFireballExplosion, 3.8f, 0f, 1f, 2.2f) },
                    missFx = new[] { OnTarget(pFireballExplosion, 3.8f, 0f, 1f, 2.2f) },
                },
                new SkillVfxEntry
                {
                    skillId = "skill.mage.frost_nova",
                    releaseFx = new[] { Spec(pNova, VfxPlace.OwnerFeet, string.Empty, 1.8f, false, false, 0f, 1f, 3.4f) },
                    hitFx = new[] { OnTarget(pIceHit, 0.9f) },
                },
                new SkillVfxEntry
                {
                    skillId = "skill.mage.arcane_ray",
                    windupFx = new[] { OnAnchor(pCastArcane, "staff_crystal", 1f, true) },
                    releaseFx = new[] { OnAnchor(pRayMuzzle, "staff_crystal", 0.5f), Spec(pRay, VfxPlace.Anchor, "staff_crystal", 0.45f, false, true, 0f, 1f, 0f, true) },
                    hitFx = new[] { OnTarget(pRayHit, 0.9f) },
                },
                new SkillVfxEntry
                {
                    skillId = "class.mage#guard",
                    windupFx = new[] { OnAnchor(pDome, "chest", 120f, true) },
                    hitFx = new[] { OnTarget(pBarrierHit, 0.6f, 0f) },
                },
                new SkillVfxEntry { skillId = "class.mage#guard_break", releaseFx = new[] { OnAnchor(pBarrierBreak, "chest", 0.8f) } },
            };
            EditorUtility.SetDirty(mage);

            var ghost = LoadSet(GhostArcherSetPath);
            ghost.vfx = new List<SkillVfxEntry>
            {
                new SkillVfxEntry
                {
                    skillId = "skill.enemy.ghost_arrow",
                    windupFx = new[] { OnAnchor(pGhostCast, "bow_nock", 1.2f, true) },
                    projectile = pGhostArrow, launchAnchor = "bow_nock", launchBlendMeters = 1.5f, lingerSeconds = 0.35f,
                    hitFx = new[] { OnTarget(pGhostHit, 0.9f) },
                },
            };
            EditorUtility.SetDirty(ghost);

            var library = SandboxBuilder.LoadOrCreate<SkillVfxLibrary>(LibraryPath);
            library.sets = new List<SkillPresentationSet> { warrior, archer, mage, ghost };
            library.maxVfxLights = 2;
            library.projectileHeight = 1f;
            EditorUtility.SetDirty(library);
        }

        static VfxSpec Marker()
        {
            var spec = Spec(pRainMarker, VfxPlace.AimGround, string.Empty, 1.1f, false, false, 0f, 1f, 3f);
            spec.survivePhaseChange = true;
            return spec;
        }

        static VfxSpec Rain()
        {
            var spec = Spec(pRain, VfxPlace.AimGround, string.Empty, 1.2f, false, false, 0f, 1f, 3f);
            spec.endsWithPhaseAfter = RainSeconds;
            return spec;
        }

        static SkillVfxEntry Arrow(string id, GameObject projectile, float scale, GameObject muzzle, GameObject hit)
        {
            return new SkillVfxEntry
            {
                skillId = id,
                releaseFx = new[] { OnAnchor(muzzle, "bow_nock", 0.5f) },
                projectile = projectile, projectileScale = scale, launchAnchor = "bow_nock", launchBlendMeters = 1.2f, lingerSeconds = 0.25f,
                hitFx = new[] { OnTarget(hit, 1.0f) },
            };
        }
    }
}
