using System.Collections.Generic;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Resolve os pontos de origem dos VFX no corpo do herói (docs/18 seção 6): <c>weapon_tip</c>, <c>weapon_base</c>, <c>staff_crystal</c>,
    /// <c>bow_nock</c>, <c>shield_face</c>, <c>hand_r</c>, <c>hand_l</c>, <c>chest</c>, <c>root_feet</c>. Procura primeiro um Transform com o nome
    /// pedido no rig (um artista pode criá-lo no modelo); se não houver, cria o ponto como filho do socket da mão, medindo a malha da arma
    /// uma única vez (a ponta do cajado é a extremidade mais longe da mão; o centro do arco é onde a flecha encaixa). Cada ponto criado
    /// fica em cache por dono. Não toca no PresentationController nem no Animator.
    /// </summary>
    public sealed class SkillAnchors
    {
        static readonly string[] RightSockets = { "socket_weapon_r", "RightHand", "hand_r", "Hand_R", "hand.R" };
        static readonly string[] LeftSockets = { "socket_weapon_l", "LeftHand", "hand_l", "Hand_L", "hand.L" };
        static readonly string[] ChestBones = { "Chest", "UpperChest", "Spine" };

        readonly Dictionary<int, Dictionary<string, Transform>> cache = new Dictionary<int, Dictionary<string, Transform>>();

        public void Clear() => cache.Clear();

        /// <summary>O ponto nomeado do dono; nunca devolve null (cai na raiz do dono).</summary>
        public Transform Get(Transform owner, string name)
        {
            if (owner == null) return null;
            if (string.IsNullOrEmpty(name) || name == "root" || name == "root_feet") return owner;
            var id = owner.GetInstanceID();
            if (!cache.TryGetValue(id, out var perOwner))
            {
                perOwner = new Dictionary<string, Transform>(8);
                cache.Add(id, perOwner);
            }
            if (perOwner.TryGetValue(name, out var found) && found != null) return found;
            found = Create(owner, name) ?? owner;
            perOwner[name] = found;
            return found;
        }

        static Transform Create(Transform owner, string name)
        {
            var existing = FindDeep(owner, name);
            if (existing != null) return existing;

            switch (name)
            {
                case "hand_r": return FindAny(owner, RightSockets);
                case "hand_l": return FindAny(owner, LeftSockets);
                case "weapon_base": return FindAny(owner, RightSockets);
                case "weapon_tip":
                case "staff_crystal":
                    return Extremity(owner, RightSockets, name);
                case "bow_nock":
                case "shield_face":
                    return Center(owner, LeftSockets, name);
                case "chest":
                    return FindAny(owner, ChestBones) ?? MakeChild(owner, name, Vector3.up * 1.0f);
                default:
                    return null;
            }
        }

        static Transform FindAny(Transform owner, string[] names)
        {
            for (var i = 0; i < names.Length; i++)
            {
                var t = FindDeep(owner, names[i]);
                if (t != null) return t;
            }
            return null;
        }

        static Transform MakeChild(Transform parent, string name, Vector3 localPosition)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPosition;
            return go.transform;
        }

        /// <summary>Extremidade mais longe do socket ao longo do maior eixo da arma (ponta do cajado, topo do martelo).</summary>
        static Transform Extremity(Transform owner, string[] sockets, string name)
        {
            var socket = FindAny(owner, sockets);
            if (socket == null) return MakeChild(owner, name, new Vector3(0.3f, 1.0f, 0.5f));
            if (!WeaponBounds(socket, out var center, out var extents))
                return MakeChild(socket, name, Vector3.zero);
            var axis = LongestAxis(extents);
            // Das duas pontas do eixo, a que está mais longe da mão (origem do socket).
            var plus = center + axis * Vector3.Dot(extents, axis).Abs();
            var minus = center - axis * Vector3.Dot(extents, axis).Abs();
            return MakeChild(socket, name, plus.sqrMagnitude >= minus.sqrMagnitude ? plus : minus);
        }

        static Transform Center(Transform owner, string[] sockets, string name)
        {
            var socket = FindAny(owner, sockets);
            if (socket == null) return MakeChild(owner, name, new Vector3(-0.3f, 1.0f, 0.4f));
            if (!WeaponBounds(socket, out var center, out _)) return MakeChild(socket, name, Vector3.zero);
            return MakeChild(socket, name, center);
        }

        static Vector3 LongestAxis(Vector3 extents)
        {
            if (extents.x >= extents.y && extents.x >= extents.z) return Vector3.right;
            return extents.y >= extents.z ? Vector3.up : Vector3.forward;
        }

        /// <summary>Caixa (no espaço do socket) de todas as malhas rígidas penduradas no socket: a arma. Ignora malhas skinned (o corpo).</summary>
        static bool WeaponBounds(Transform socket, out Vector3 center, out Vector3 extents)
        {
            center = Vector3.zero;
            extents = Vector3.zero;
            var filters = socket.GetComponentsInChildren<MeshFilter>(true);
            var has = false;
            var min = Vector3.zero;
            var max = Vector3.zero;
            for (var f = 0; f < filters.Length; f++)
            {
                var mesh = filters[f].sharedMesh;
                if (mesh == null) continue;
                var b = mesh.bounds;
                for (var c = 0; c < 8; c++)
                {
                    var corner = b.center + Vector3.Scale(b.extents, new Vector3((c & 1) == 0 ? -1 : 1, (c & 2) == 0 ? -1 : 1, (c & 4) == 0 ? -1 : 1));
                    var p = socket.InverseTransformPoint(filters[f].transform.TransformPoint(corner));
                    if (!has) { min = max = p; has = true; }
                    else { min = Vector3.Min(min, p); max = Vector3.Max(max, p); }
                }
            }
            if (!has) return false;
            center = (min + max) * 0.5f;
            extents = (max - min) * 0.5f;
            return true;
        }

        public static Transform FindDeep(Transform parent, string childName)
        {
            if (parent.name == childName) return parent;
            for (var i = 0; i < parent.childCount; i++)
            {
                var found = FindDeep(parent.GetChild(i), childName);
                if (found != null) return found;
            }
            return null;
        }
    }

    static class FloatExtensions
    {
        public static float Abs(this float value) => value < 0f ? -value : value;
    }
}
