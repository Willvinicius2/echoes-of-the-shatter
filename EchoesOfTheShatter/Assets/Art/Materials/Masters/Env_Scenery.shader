// Env_Scenery: mestre de cenario (rodada 17, spec_cenario.md). Iluminacao suave igual ao SG_Character (half-lambert, sem rampa), MAS com as luzes
// pontuais do FirePool (as pocas quentes das tochas, Forward+), o AO de tela (SSAO) e a normal para o DepthNormals.
//
// Modos (por keyword local; nenhuma = KIT, o albedo pintado da peca por UV, com a mascara R de emissao como no SG_Character):
//   _ENV_FLOOR  piso: projecao planar XZ no MUNDO (1 tile = _FloorTile m); celulas de ~12 m com borda curva, cada uma com A ou B, giro, espelho e
//               deslocamento sorteados por hash (emenda estreita com a vizinha); mais uma variacao suave de brilho.
//   _ENV_WALL   alvenaria: projecao pelo eixo dominante da normal no mundo (1 tile = _WallTile m), topo e laterais com a mesma textura.
//   _ENV_BAND   faixa: nas faces verticais usa a textura da faixa (U no mundo, 1 tile = _BandTile m; V = altura da peca / _BandHeight, topo =
//               coroamento e base = rodape); nas faces de cima, a alvenaria.
//   _ENV_RUNE   runa: emissao pura (cor HDR e intensidade), sem iluminacao; o bloom faz o brilho.
//   _ENV_DECAL  simbolo no chao (alfa): albedo/alfa da _BaseMap por UV, com brilho de emissao; passa por cima do piso (Offset).
// DESVIO REGISTRADO (igual ao SG_Character): HLSL URP, nao Shader Graph.
Shader "Echoes/Env_Scenery"
{
    Properties
    {
        [MainTexture] _BaseMap("Albedo pintado da peca (modo kit/decal)", 2D) = "white" {}
        _MaskMap("Mascara (R emissivo)", 2D) = "black" {}
        _MapA("Piso A", 2D) = "gray" {}
        _MapB("Piso B", 2D) = "gray" {}
        _WallMap("Parede", 2D) = "gray" {}
        _BandMap("Faixa", 2D) = "gray" {}
        _Tint("Tinta global (multiplicador)", Color) = (1, 1, 1, 1)

        [Header(Escalas em metros por tile)]
        _FloorTile("Piso", Float) = 8
        _WallTile("Parede", Float) = 4
        _BandTile("Faixa (largura)", Float) = 6.5
        _BandHeight("Faixa (altura da peca)", Float) = 3
        _CellSize("Piso: tamanho da celula de variacao (m)", Float) = 12
        _WarpAmp("Piso: curvatura das bordas da celula (m)", Float) = 4
        _WarpFreq("Piso: frequencia da curvatura", Float) = 0.09
        _EdgeWidth("Piso: largura da emenda entre celulas (fracao da celula)", Range(0.005, 0.2)) = 0.05
        _BShare("Piso: fracao de celulas com a lajota B", Range(0, 1)) = 0.35
        _FloorContrast("Piso: contraste lajota x rejunte (1 = textura pura)", Range(0.8, 1.8)) = 1.35
        [HDR] _RuneColor("Runa: cor (emissao)", Color) = (1, 0.7, 0.3, 1)
        _RuneIntensity("Runa: intensidade", Float) = 2.5
        _Variation("Variacao suave de brilho (0 = nenhuma)", Range(0, 0.3)) = 0.07

        [Header(Iluminacao suave)]
        _ShadeSoftness("Suavidade (half-lambert)", Range(0, 1)) = 0.6
        _ShadowTint("Cor da sombra", Color) = (0.35, 0.3, 0.55, 1)
        _AmbientStrength("Ambiente", Range(0, 2)) = 1
        _PoolStrength("Luz das tochas (pontuais)", Range(0, 3)) = 1.5
        _PoolSoftClip("Tochas: compressao do brilho perto da fonte (0 = nenhuma)", Range(0, 2)) = 0.3

        [Header(Emissao)]
        _EmissionIntensity("Emissao pela mascara R", Float) = 0.6

        [HideInInspector] _SrcBlend("", Float) = 1
        [HideInInspector] _DstBlend("", Float) = 0
        [HideInInspector] _ZWrite("", Float) = 1
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" "UniversalMaterialType" = "Lit" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        TEXTURE2D(_BaseMap);  SAMPLER(sampler_BaseMap);
        TEXTURE2D(_MaskMap);  SAMPLER(sampler_MaskMap);
        TEXTURE2D(_MapA);     SAMPLER(sampler_MapA);
        TEXTURE2D(_MapB);     SAMPLER(sampler_MapB);
        TEXTURE2D(_WallMap);  SAMPLER(sampler_WallMap);
        TEXTURE2D(_BandMap);  SAMPLER(sampler_BandMap);

        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4 _Tint;
            float _FloorTile;
            float _WallTile;
            float _BandTile;
            float _BandHeight;
            float _CellSize;
            float _WarpAmp;
            float _WarpFreq;
            float _EdgeWidth;
            float _BShare;
            half _Variation;
            half _FloorContrast;
            half4 _RuneColor;
            half _RuneIntensity;
            half _ShadeSoftness;
            half4 _ShadowTint;
            half _AmbientStrength;
            half _PoolStrength;
            half _PoolSoftClip;
            half _EmissionIntensity;
        CBUFFER_END
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite [_ZWrite]
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma shader_feature_local _ _ENV_FLOOR _ENV_WALL _ENV_BAND _ENV_DECAL _ENV_RUNE
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
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
                float3 objectBase : TEXCOORD3; // origem da peca no mundo (a altura da faixa conta a partir do chao da peca)
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
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
                output.objectBase = TransformObjectToWorld(float3(0, 0, 0));
                return output;
            }

            // Ruido de valor suave (quintico), barato: so a mascara A/B e a variacao de brilho.
            float Hash21(float2 p)
            {
                p = frac(p * float2(123.34, 456.21));
                p += dot(p, p + 45.32);
                return frac(p.x * p.y);
            }

            float ValueNoise(float2 p)
            {
                float2 i = floor(p);
                float2 f = frac(p);
                f = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
                return lerp(lerp(Hash21(i), Hash21(i + float2(1, 0)), f.x),
                            lerp(Hash21(i + float2(0, 1)), Hash21(i + float2(1, 1)), f.x), f.y);
            }

            float FbmNoise(float2 p)
            {
                return ValueNoise(p) * 0.65 + ValueNoise(p * 2.07 + 17.3) * 0.35;
            }

            float2 Hash22(float2 p)
            {
                float3 q = frac(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
                q += dot(q, q.yzx + 33.33);
                return frac((q.xx + q.yz) * q.zy);
            }

            // Uma celula do piso: escolhe A ou B, giro de 90 graus (0..3), espelho e deslocamento por hash da celula. As derivadas vem do uv base
            // (continuo), girado igual, para nao aparecer linha de mip na emenda das celulas.
            half3 FloorCell(float2 uv, float2 dx, float2 dy, float2 cell)
            {
                float2 h = Hash22(cell);
                float2 h2 = Hash22(cell + 17.31);
                bool useB = h.x < _BShare;
                float rot = floor(h.y * 2.0) * 2.0; // so 0 ou 180 graus: a 90 graus as lajotas viravam escama sob a camera a 45 graus (variedade vem do espelho, do deslocamento e de A/B)
                float flip = h2.x > 0.5 ? -1.0 : 1.0;
                float2 u = uv, ddx_ = dx, ddy_ = dy;
                if (rot == 1.0) { u = float2(-u.y, u.x); ddx_ = float2(-ddx_.y, ddx_.x); ddy_ = float2(-ddy_.y, ddy_.x); }
                else if (rot == 2.0) { u = -u; ddx_ = -ddx_; ddy_ = -ddy_; }
                else if (rot == 3.0) { u = float2(u.y, -u.x); ddx_ = float2(ddx_.y, -ddx_.x); ddy_ = float2(ddy_.y, -ddy_.x); }
                u.x *= flip; ddx_.x *= flip; ddy_.x *= flip;
                u += h2.yx;
                [branch] if (useB) return SAMPLE_TEXTURE2D_GRAD(_MapB, sampler_MapB, u, ddx_, ddy_).rgb;
                return SAMPLE_TEXTURE2D_GRAD(_MapA, sampler_MapA, u, ddx_, ddy_).rgb;
            }

            // Piso: projecao planar no mundo (1 tile = _FloorTile m). Em vez de uma mascara de ruido que mistura A e B (a mistura larga fantasmava as
            // lajotas), o mundo e dividido em celulas de ~12 m com bordas curvas (domain warp); cada celula sorteia A ou B, giro, espelho e deslocamento,
            // e so a faixa estreita da borda mistura com a celula vizinha. Duas amostras por pixel, como antes, e nenhuma repeticao visivel.
            half3 SampleFloor(float3 positionWS)
            {
                float2 xz = positionWS.xz;
                float2 uv = xz / _FloorTile;
                float2 dx = ddx(uv);
                float2 dy = ddy(uv);
                // Piso uniforme: _CellSize <= 0 desliga a mistura de celulas (uma lajota so, sem giro, espelho nem emenda).
                [branch] if (_CellSize <= 0.0)
                {
                    half3 u0 = SAMPLE_TEXTURE2D_GRAD(_MapA, sampler_MapA, uv, dx, dy).rgb;
                    const half pv = 0.075h;
                    return pv * pow(max(u0, 1e-4) / pv, _FloorContrast);
                }
                float2 warp = float2(FbmNoise(xz * _WarpFreq), FbmNoise(xz * _WarpFreq + 31.7)) - 0.5;
                float2 p = (xz + warp * 2.0 * _WarpAmp) / _CellSize;
                float2 id = floor(p);
                float2 f = frac(p);
                float2 toEdge = min(f, 1.0 - f);
                float2 nb = id;
                float d;
                if (toEdge.x < toEdge.y) { d = toEdge.x; nb.x += f.x < 0.5 ? -1.0 : 1.0; }
                else { d = toEdge.y; nb.y += f.y < 0.5 ? -1.0 : 1.0; }
                half3 own = FloorCell(uv, dx, dy, id);
                half3 other = FloorCell(uv, dx, dy, nb);
                half3 c = lerp(other, own, 0.5 + 0.5 * smoothstep(0.0, _EdgeWidth, d));
                float v = FbmNoise(xz * 0.031 + 91.7); // brilho suave em manchas de ~30 m
                c *= 1.0 + (v - 0.5) * 2.0 * _Variation;
                const half pivot = 0.075h; // media linear das lajotas: acima clareia, abaixo (rejunte) escurece
                return pivot * pow(max(c, 1e-4) / pivot, _FloorContrast);
            }

            half3 SampleWall(float3 positionWS, float3 normalWS)
            {
                float3 n = abs(normalWS);
                float2 uv;
                if (n.y > n.x && n.y > n.z) uv = positionWS.xz;
                else if (n.x > n.z) uv = float2(positionWS.z, positionWS.y);
                else uv = float2(positionWS.x, positionWS.y);
                return SAMPLE_TEXTURE2D(_WallMap, sampler_WallMap, uv / _WallTile).rgb;
            }

            half3 SampleBand(float3 positionWS, float3 normalWS, float3 objectBase)
            {
                float3 n = abs(normalWS);
                if (n.y > 0.6) return SampleWall(positionWS, normalWS);
                float u = n.x > n.z ? positionWS.z : positionWS.x;
                float v = saturate((positionWS.y - objectBase.y) / _BandHeight);
                return SAMPLE_TEXTURE2D(_BandMap, sampler_BandMap, float2(u / _BandTile, v)).rgb;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);

            #if defined(_ENV_RUNE)
                // Runa: so emissao (acende com bloom), com pulso lento e defasado pelo mundo.
                float pulse = 0.85 + 0.15 * sin(_Time.y * 2.2 + dot(input.positionWS.xz, float2(0.9, 0.6)));
                return half4(_RuneColor.rgb * _RuneIntensity * pulse, 1);
            #endif
                half3 albedo;
                half alpha = 1;
                half emission = 0;
            #if defined(_ENV_FLOOR)
                albedo = SampleFloor(input.positionWS);
            #elif defined(_ENV_WALL)
                albedo = SampleWall(input.positionWS, input.normalWS);
            #elif defined(_ENV_BAND)
                albedo = SampleBand(input.positionWS, input.normalWS, input.objectBase);
            #elif defined(_ENV_DECAL)
                half4 s = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv);
                albedo = s.rgb;
                alpha = s.a;
                emission = 0.35h;
            #else
                albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).rgb;
                emission = SAMPLE_TEXTURE2D(_MaskMap, sampler_MaskMap, input.uv).r * _EmissionIntensity;
            #endif
                albedo *= _Tint.rgb;

                float3 normalWS = normalize(input.normalWS);
                float4 shadowCoord = TransformWorldToShadowCoord(input.positionWS);
                Light mainLight = GetMainLight(shadowCoord);

                half ndl = dot(normalWS, mainLight.direction);
                half lit = lerp(saturate(ndl), ndl * 0.5h + 0.5h, _ShadeSoftness);
                lit *= mainLight.shadowAttenuation * mainLight.distanceAttenuation;

                half3 ambient = SampleSH(normalWS) * _AmbientStrength;
                half occlusion = 1.0h;
            #if defined(_SCREEN_SPACE_OCCLUSION)
                float2 screenUV = GetNormalizedScreenSpaceUV(input.positionCS);
                AmbientOcclusionFactor ao = GetScreenSpaceAmbientOcclusion(screenUV);
                occlusion = ao.indirectAmbientOcclusion;
                lit *= lerp(1.0h, ao.directAmbientOcclusion, 0.5h);
            #endif
                half shadowAmount = 1.0h - saturate(lit);
                half3 color = albedo * (mainLight.color * lit + ambient * occlusion + shadowAmount * _ShadowTint.rgb * 0.25h);

                // Pocas de luz quente das tochas (FirePool): pontuais por pixel, Forward+, sem sombra.
            #if defined(_ADDITIONAL_LIGHTS)
                InputData inputData = (InputData)0;
                inputData.positionWS = input.positionWS;
                inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
                uint pixelLightCount = GetAdditionalLightsCount();
                half3 pool = 0;
                LIGHT_LOOP_BEGIN(pixelLightCount)
                    Light light = GetAdditionalLight(lightIndex, input.positionWS);
                    half pndl = dot(normalWS, light.direction);
                    half plit = lerp(saturate(pndl), pndl * 0.5h + 0.5h, _ShadeSoftness);
                    pool += light.color * (plit * light.distanceAttenuation * _PoolStrength);
                LIGHT_LOOP_END
                // Compressao suave (Reinhard) da soma das tochas: a 1/d2 estoura a pedra clara colada na fonte (pilar ao lado do braseiro); longe da fonte quase nao muda.
                pool = pool / (1.0h + _PoolSoftClip * pool);
                color += albedo * pool;
            #endif

                color += albedo * (emission * 1.0h);
                return half4(color, alpha);
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
                return output;
            }

            half4 ShadowFrag(Varyings input) : SV_Target { return 0; }
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
            };

            Varyings DepthVert(Attributes input)
            {
                Varyings output;
                UNITY_SETUP_INSTANCE_ID(input);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                return output;
            }

            half DepthFrag(Varyings input) : SV_Target { return input.positionCS.z; }
            ENDHLSL
        }

        // Normais para o SSAO (Source = Depth Normals) e para o pre-passe do URP.
        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On
            Cull Back

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex NormalsVert
            #pragma fragment NormalsFrag
            #pragma multi_compile_instancing
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD0;
            };

            Varyings NormalsVert(Attributes input)
            {
                Varyings output;
                UNITY_SETUP_INSTANCE_ID(input);
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                return output;
            }

            half4 NormalsFrag(Varyings input) : SV_Target
            {
                float3 n = normalize(input.normalWS);
            #if defined(_GBUFFER_NORMALS_OCT)
                float2 octNormalWS = PackNormalOctQuadEncode(n);
                float2 remapped = octNormalWS * 0.5 + 0.5;
                return half4(PackFloat2To888(remapped), 0.0);
            #else
                return half4(n, 0.0);
            #endif
            }
            ENDHLSL
        }
    }
    FallBack Off
}
