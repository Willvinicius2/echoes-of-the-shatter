// SG_Character: mestre de personagem (docs/04_arquitetura.md, secao 3.5), estilo medido em
// docs/arte/regua_spell_brigade.md (secoes 4 e 8, item 7): albedo pintado, iluminacao suave (half-lambert, sem
// rampa), rim suave e discreto (polimento da etapa 3: forca 1,0, smoothstep (0,65; 0), mistura 0,5), emissao HDR pela mascara,
// _HitFlash (liga/desliga + cor), dissolucao e variacao por tinta (regiao B da mascara).
//
// DESVIO REGISTRADO: o contrato diz "Shader Graph". Um .shadergraph nao se gera de forma confiavel por
// script/batchmode (o formato e interno e muda por versao), entao este mestre e HLSL URP com as MESMAS
// propriedades e nomes pedidos para o SG_Character. Pode ser refeito como grafo no editor sem mudar nenhum
// material nem codigo (PresentationController usa so _HitFlash e _Dissolve por nome).
//
// Mascara _MaskMap (linear): R = emissivo, G = rim, B = regiao de tinta, A reservado.
// TODO(luzes adicionais): so a luz principal e o ambiente entram; luzes pontuais (magia em neon) quando o VFX pedir.
Shader "Echoes/SG_Character"
{
    Properties
    {
        [MainTexture] _BaseMap("Albedo pintado", 2D) = "white" {}
        [MainColor] _BaseColor("Tinta global (multiplicador)", Color) = (1,1,1,1)
        _MaskMap("Mascara (R emissivo, G rim, B tinta)", 2D) = "white" {}

        [Header(Iluminacao suave)]
        _ShadeSoftness("Suavidade (half-lambert)", Range(0, 1)) = 0.6
        _ShadowTint("Cor da sombra", Color) = (0.42, 0.36, 0.5, 1)
        _AmbientStrength("Ambiente", Range(0, 2)) = 1

        [Header(Rim suave e discreto)]
        [HDR] _RimColor("Cor do rim", Color) = (1, 0.82, 0.62, 1)
        _FresnelStrength("Forca", Float) = 1.0
        _FresnelBlend("Mistura", Range(0, 1)) = 0.5
        _RimMaskInfluence("Quanto a mascara G controla o rim (0 = rim em tudo)", Range(0, 1)) = 1
        _FresnelSmoothStepRange("Faixa smoothstep (x = borda, y = interior)", Vector) = (0.65, 0, 0, 0)
        _RimLitInfluence("Rim so no lado iluminado (0 = em toda a silhueta)", Range(0, 1)) = 1
        _RimNoiseRange("Rim some onde a normal varia depressa (x = comeca a sumir, y = some de vez): triangulos finos da silhueta nao viram dente", Vector) = (0.12, 0.35, 0, 0)

        _RimIntensity("Intensidade do rim por raridade (base 0,5)", Range(0, 2)) = 0.5
        _RimTint("Cor do rim da raridade", Color) = (1, 1, 1, 1)
        _RimTintMix("Mistura do rim da raridade (0 = rim da nevoa)", Range(0, 1)) = 0

        [Header(Emissao)]
        [HDR] _EmissionColor("Cor HDR (multiplica o albedo pintado)", Color) = (1, 1, 1, 1)
        _EmissionIntensity("Intensidade", Float) = 0.6
        _AccentEmissive("Acento emissivo da raridade (0 a 1; 1 = intensidade 2,0)", Range(0, 1)) = 0
        _AccentColor("Cor do acento", Color) = (1, 0.82, 0.29, 1)
        [Toggle] _AccentPulse("Pulso do acento (Unico; desligado em Reduzir movimento)", Float) = 0
        _AccentPulsePeriod("Periodo do pulso (s)", Float) = 2.4
        _AccentPulseVariation("Variacao do pulso", Range(0, 1)) = 0.2

        [Header(Variacao por tinta e raridade)]
        _TintColor("Cor da tinta", Color) = (1, 1, 1, 1)
        _TintStrength("Forca da tinta", Range(0, 1)) = 0
        _TintDesat("Desbotamento previo (luma) na regiao B", Range(0, 1)) = 0
        _TintGain("Ganho de luminancia da tinta", Range(0, 3)) = 1

        [Header(Feedback)]
        _HitFlash("Flash de acerto (0 ou 1)", Range(0, 1)) = 0
        _HitColor("Cor do acerto", Color) = (0.60, 0.35, 0.39, 1)
        _Dissolve("Dissolucao", Range(0, 1)) = 0
        [HDR] _DissolveEdgeColor("Borda da dissolucao", Color) = (1, 0.5, 0.2, 1)
        _DissolveEdgeWidth("Largura da borda", Range(0, 0.2)) = 0.06
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" "UniversalMaterialType" = "Lit" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);
        TEXTURE2D(_MaskMap);  SAMPLER(sampler_MaskMap);

        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4 _BaseColor;
            half _ShadeSoftness;
            half4 _ShadowTint;
            half _AmbientStrength;
            half _RimIntensity;
            half4 _RimTint;
            half _RimTintMix;
            half4 _AccentColor;
            half _AccentPulse;
            half _AccentPulsePeriod;
            half _AccentPulseVariation;
            half _TintDesat;
            half _TintGain;
            half4 _RimColor;
            half _FresnelStrength;
            half _FresnelBlend;
            half _RimMaskInfluence;
            float4 _FresnelSmoothStepRange;
            float4 _RimNoiseRange;
            half _RimLitInfluence;
            half4 _EmissionColor;
            half _EmissionIntensity;
            half _AccentEmissive;
            half4 _TintColor;
            half _TintStrength;
            half _HitFlash;
            half4 _HitColor;
            half _Dissolve;
            half4 _DissolveEdgeColor;
            half _DissolveEdgeWidth;
        CBUFFER_END

        // Ruido barato por posicao no objeto para a dissolucao.
        float EchoesHash(float3 p)
        {
            p = frac(p * 0.3183099 + 0.1);
            p *= 17.0;
            return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
        }

        float EchoesDissolveNoise(float3 positionOS)
        {
            float3 p = positionOS * 6.0;
            float3 i = floor(p);
            float3 f = frac(p);
            f = f * f * (3.0 - 2.0 * f);
            float n000 = EchoesHash(i);
            float n100 = EchoesHash(i + float3(1, 0, 0));
            float n010 = EchoesHash(i + float3(0, 1, 0));
            float n110 = EchoesHash(i + float3(1, 1, 0));
            float n001 = EchoesHash(i + float3(0, 0, 1));
            float n101 = EchoesHash(i + float3(1, 0, 1));
            float n011 = EchoesHash(i + float3(0, 1, 1));
            float n111 = EchoesHash(i + float3(1, 1, 1));
            return lerp(lerp(lerp(n000, n100, f.x), lerp(n010, n110, f.x), f.y),
                        lerp(lerp(n001, n101, f.x), lerp(n011, n111, f.x), f.y), f.z);
        }
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float3 positionWS : TEXCOORD2;
                float3 positionOS : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings Vert(Attributes input)
            {
                Varyings output = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                VertexPositionInputs pos = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = pos.positionCS;
                output.positionWS = pos.positionWS;
                output.positionOS = input.positionOS.xyz;
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);

                // Dissolucao (morte): clip pelo ruido; borda emissiva.
                float edgeGlow = 0;
                if (_Dissolve > 0.001)
                {
                    float n = EchoesDissolveNoise(input.positionOS);
                    float t = n - _Dissolve * (1.0 + _DissolveEdgeWidth);
                    clip(t);
                    edgeGlow = 1.0 - saturate(t / max(_DissolveEdgeWidth, 1e-4));
                }

                half4 baseSample = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv);
                half4 mask = SAMPLE_TEXTURE2D(_MaskMap, sampler_MaskMap, input.uv);
                half3 albedo = baseSample.rgb * _BaseColor.rgb;
                // Raridade (docs/03 3.11): base = lerp(albedo, luma, desat*B); rgb = base * lerp(1, tint*gain, strength*B).
                half luma = dot(albedo, half3(0.2126h, 0.7152h, 0.0722h));
                half regionB = saturate(mask.b);
                half3 desaturated = lerp(albedo, half3(luma, luma, luma), _TintDesat * regionB);
                albedo = desaturated * lerp(half3(1, 1, 1), _TintColor.rgb * _TintGain, _TintStrength * regionB);

                float3 normalWS = normalize(input.normalWS);
                float3 viewWS = GetWorldSpaceNormalizeViewDir(input.positionWS);

                float4 shadowCoord = TransformWorldToShadowCoord(input.positionWS);
                Light mainLight = GetMainLight(shadowCoord);

                // Iluminacao suave: half-lambert misturado ao lambert, sem rampa de toon (a regua nao tem textura de rampa).
                half ndl = dot(normalWS, mainLight.direction);
                half lit = lerp(saturate(ndl), ndl * 0.5h + 0.5h, _ShadeSoftness);
                lit *= mainLight.shadowAttenuation * mainLight.distanceAttenuation;
                half3 ambient = SampleSH(normalWS) * _AmbientStrength;
                half3 direct = mainLight.color * lit;
                half shadowAmount = 1.0h - saturate(lit);
                half3 color = albedo * (direct + ambient + shadowAmount * _ShadowTint.rgb * 0.25h);

                // Rim suave: smoothstep largo sobre N.V (degrade da silhueta para dentro), forca 1,0, mistura 0,5.
                half ndv = saturate(dot(normalWS, viewWS));
                half rim = 1.0h - smoothstep(_FresnelSmoothStepRange.y, _FresnelSmoothStepRange.x, ndv);
                rim *= lerp(1.0h, mask.g, _RimMaskInfluence);
                // Triangulos finos da silhueta tem normal interpolada instavel: o rim apareceria como dente. Onde a normal varia depressa por pixel, o rim some.
                half normalVariation = length(fwidth(normalWS));
                rim *= 1.0h - smoothstep(_RimNoiseRange.x, _RimNoiseRange.y, normalVariation);
                rim *= lerp(1.0h, saturate(lit), _RimLitInfluence);
                half3 rimColor = lerp(_RimColor.rgb, _RimTint.rgb, _RimTintMix);
                color += rimColor * (rim * _FresnelStrength * _FresnelBlend * (_RimIntensity / 0.5h));

                // Emissao HDR pela mascara (R) mais o acento da raridade.
                // Emissao pela mascara R: o detalhe pintado brilha na propria cor do albedo (filete dourado, runa).
                color += albedo * _EmissionColor.rgb * (mask.r * _EmissionIntensity);
                // Acento da raridade: _AccentEmissive * _AccentColor pelo canal R (so os detalhes pintados), com pulso lento no Unico.
                half pulse = lerp(1.0h, 1.0h + _AccentPulseVariation * sin(_Time.y * 6.2831853h / max(_AccentPulsePeriod, 0.01h)), _AccentPulse);
                color += _AccentColor.rgb * (mask.r * _AccentEmissive * 2.0h * pulse);

                color += _DissolveEdgeColor.rgb * edgeGlow * step(0.001, _Dissolve);

                // Flash de acerto: liga/desliga, cor do acerto.
                color = lerp(color, _HitColor.rgb, step(0.5h, _HitFlash));

                return half4(color, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex ShadowVert
            #pragma fragment ShadowFrag
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

            float3 _LightDirection;
            float3 _LightPosition;

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionOS : TEXCOORD0;
            };

            Varyings ShadowVert(Attributes input)
            {
                Varyings output;
                UNITY_SETUP_INSTANCE_ID(input);
                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
            #if _CASTING_PUNCTUAL_LIGHT_SHADOW
                float3 lightDirectionWS = normalize(_LightPosition - positionWS);
            #else
                float3 lightDirectionWS = _LightDirection;
            #endif
                float4 positionCS = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS));
            #if UNITY_REVERSED_Z
                positionCS.z = min(positionCS.z, UNITY_NEAR_CLIP_VALUE);
            #else
                positionCS.z = max(positionCS.z, UNITY_NEAR_CLIP_VALUE);
            #endif
                output.positionCS = positionCS;
                output.positionOS = input.positionOS.xyz;
                return output;
            }

            half4 ShadowFrag(Varyings input) : SV_Target
            {
                if (_Dissolve > 0.001) clip(EchoesDissolveNoise(input.positionOS) - _Dissolve * (1.0 + _DissolveEdgeWidth));
                return 0;
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On
            ColorMask R
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DepthVert
            #pragma fragment DepthFrag
            #pragma multi_compile_instancing

            struct Attributes
            {
                float4 positionOS : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionOS : TEXCOORD0;
            };

            Varyings DepthVert(Attributes input)
            {
                Varyings output;
                UNITY_SETUP_INSTANCE_ID(input);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.positionOS = input.positionOS.xyz;
                return output;
            }

            half DepthFrag(Varyings input) : SV_Target
            {
                if (_Dissolve > 0.001) clip(EchoesDissolveNoise(input.positionOS) - _Dissolve * (1.0 + _DissolveEdgeWidth));
                return input.positionCS.z;
            }
            ENDHLSL
        }
    }
    FallBack Off
}
