using UnityEngine;
using UnityEngine.Rendering;

namespace Echoes.Presentation
{
    /// <summary>
    /// O item no chao: marcador neutro (TODO asset ART-ITEM-GROUND: modelo 3D de item caido), feixe de raridade do docs/03 2.3 (brilho no Magico,
    /// coluna no Raro e no Unico, esta com pulso de 800 ms) e o rotulo com o nome (Magico ou melhor). So apresentacao: o item e o uid vem do core.
    /// </summary>
    public sealed class GroundItemView : MonoBehaviour
    {
        public ulong Uid { get; private set; }
        public int Rarity { get; private set; }

        Renderer beam;
        float pulseSeconds;
        Color beamColor;
        TextMesh label;
        Transform labelTransform;
        MaterialPropertyBlock block;
        float born;

        public void Setup(ulong uid, int rarity, string displayName, LootBeamSettings settings)
        {
            Uid = uid;
            Rarity = rarity;
            born = Time.time;
            block = new MaterialPropertyBlock();
            var color = settings.TryGet(rarity, out var tier) ? tier.color : new Color(0.85f, 0.82f, 0.78f);

            var marker = GameObject.CreatePrimitive(PrimitiveType.Cube);
            marker.name = "Marker";
            Destroy(marker.GetComponent<Collider>());
            marker.transform.SetParent(transform, false);
            var size = settings.placeholderSize;
            marker.transform.localScale = new Vector3(size * 1.4f, size * 0.5f, size);
            marker.transform.localPosition = new Vector3(0f, size * 0.25f, 0f);
            marker.transform.localRotation = Quaternion.Euler(0f, 30f, 0f);
            var markerRenderer = marker.GetComponent<Renderer>();
            if (settings.markerMaterial != null) markerRenderer.sharedMaterial = settings.markerMaterial;
            markerRenderer.shadowCastingMode = ShadowCastingMode.Off;
            block.SetColor("_BaseColor", color);
            markerRenderer.SetPropertyBlock(block);

            if (rarity == 1 && settings.glowMaterial != null)
            {
                var glow = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                glow.name = "Glow";
                Destroy(glow.GetComponent<Collider>());
                glow.transform.SetParent(transform, false);
                var d = tier.glowRadiusMeters * 2f;
                glow.transform.localScale = new Vector3(d, d * 0.6f, d);
                glow.transform.localPosition = new Vector3(0f, 0.2f, 0f);
                var gr = glow.GetComponent<Renderer>();
                gr.sharedMaterial = settings.glowMaterial;
                gr.shadowCastingMode = ShadowCastingMode.Off;
                SetTint(gr, color, 0.5f);
            }
            else if (rarity >= 2 && settings.beamMaterial != null)
            {
                var column = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                column.name = "Beam";
                Destroy(column.GetComponent<Collider>());
                column.transform.SetParent(transform, false);
                column.transform.localScale = new Vector3(tier.radiusMeters * 2f, tier.heightMeters * 0.5f, tier.radiusMeters * 2f);
                column.transform.localPosition = new Vector3(0f, tier.heightMeters * 0.5f, 0f);
                beam = column.GetComponent<Renderer>();
                beam.sharedMaterial = settings.beamMaterial;
                beam.shadowCastingMode = ShadowCastingMode.Off;
                beamColor = color;
                pulseSeconds = tier.pulseSeconds;
                SetTint(beam, color, 0.55f);
            }

            if (rarity >= 1)
            {
                var go = new GameObject("Label");
                go.transform.SetParent(transform, false);
                go.transform.localPosition = new Vector3(0f, rarity >= 3 ? 1.2f : 0.9f, 0f);
                label = go.AddComponent<TextMesh>();
                label.text = displayName;
                label.anchor = TextAnchor.MiddleCenter;
                label.alignment = TextAlignment.Center;
                label.characterSize = rarity >= 3 ? 0.16f : 0.12f; // o unico tem rotulo maior
                label.fontSize = 48;
                label.color = color;
                labelTransform = go.transform;
            }
        }

        void SetTint(Renderer r, Color color, float alpha)
        {
            block.Clear();
            block.SetColor("_BaseColor", new Color(color.r, color.g, color.b, alpha));
            r.SetPropertyBlock(block);
        }

        void Update()
        {
            // Queda curta ao nascer (0,35 s).
            var t = Mathf.Clamp01((Time.time - born) / 0.35f);
            transform.localScale = Vector3.one;
            var p = transform.position;
            p.y = Mathf.Lerp(0.8f, 0f, t * t);
            transform.position = p;

            if (beam != null && pulseSeconds > 0f)
            {
                var pulse = 0.5f + 0.5f * Mathf.Sin(Time.time * (2f * Mathf.PI / pulseSeconds));
                SetTint(beam, beamColor, Mathf.Lerp(0.3f, 0.7f, pulse));
            }
            if (labelTransform != null)
            {
                var cam = Camera.main;
                if (cam != null) labelTransform.rotation = cam.transform.rotation;
            }
        }
    }
}
