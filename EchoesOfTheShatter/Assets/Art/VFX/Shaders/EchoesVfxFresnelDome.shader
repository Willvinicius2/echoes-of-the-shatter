// Cúpula translúcida da Barreira Arcana (docs/18, fx.barrier.mage): preenchimento fraco, borda por fresnel e ondas hexagonais que rolam.
// Aditivo, sem sombra, dos dois lados. Sem ZWrite. Cabe no SRP Batcher (propriedades no CBUFFER).
Shader "Echoes/VFX/FresnelDome"
{
    Properties
    {
        [HDR] _FillColor("Cor do preenchimento", Color) = (0.23, 0.35, 0.9, 1)
        [HDR] _RimColor("Cor da borda (fresnel)", Color) = (0.5, 0.7, 1.8, 1)
        [HDR] _HexColor("Cor dos hexágonos", Color) = (0.6, 0.8, 2.0, 1)
        _FillAlpha("Alfa do preenchimento", Range(0, 1)) = 0.18
        _RimPower("Expoente da borda", Range(0.5, 8)) = 2.6
        _HexMap("Hexágonos (alfa)", 2D) = "white" {}
        _HexTiling("Repetição dos hexágonos", Float) = 5
        _Scroll("Rolagem dos hexágonos (xy)", Vector) = (0.04, 0.09, 0, 0)
        _Alpha("Alfa geral", Range(0, 1)) = 1
    }

    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }

        Pass
        {
            Name "ForwardUnlit"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha One
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D(_HexMap);
            SAMPLER(sampler_HexMap);

            CBUFFER_START(UnityPerMaterial)
                half4 _FillColor;
                half4 _RimColor;
                half4 _HexColor;
                half _FillAlpha;
                half _RimPower;
                float4 _HexMap_ST;
                float _HexTiling;
                float4 _Scroll;
                half _Alpha;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD0;
                float3 viewDirWS : TEXCOORD1;
                float2 uv : TEXCOORD2;
            };

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs positions = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = positions.positionCS;
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.viewDirWS = GetWorldSpaceViewDir(positions.positionWS);
                output.uv = input.uv;
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                float3 normal = normalize(input.normalWS);
                float3 view = normalize(input.viewDirWS);
                half facing = abs(dot(normal, view));
                half rim = pow(saturate(1.0h - facing), _RimPower);

                float2 uv = input.uv * float2(_HexTiling * 2.0, _HexTiling) + _Scroll.xy * _Time.y;
                half hex = SAMPLE_TEXTURE2D(_HexMap, sampler_HexMap, uv).a;

                half3 color = _FillColor.rgb * _FillAlpha + _RimColor.rgb * rim + _HexColor.rgb * hex * (0.35h + 0.65h * rim);
                half alpha = saturate(_FillAlpha + rim * 0.9h + hex * 0.35h) * _Alpha;
                return half4(color, alpha);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
