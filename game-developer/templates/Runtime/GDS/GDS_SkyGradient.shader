// GDS/SkyGradient — art-directable skybox: top / horizon / bottom colours + soft sun disc and halo.
// GDS.LookDev.Apply sets it from the preset (horizon = fog colour, so distant geometry melts into the sky).
Shader "GDS/SkyGradient"
{
    Properties
    {
        _TopColor ("Top", Color) = (0.36, 0.60, 0.95, 1)
        _HorizonColor ("Horizon", Color) = (0.78, 0.86, 0.93, 1)
        _BottomColor ("Bottom", Color) = (0.30, 0.33, 0.36, 1)
        _HorizonSharpness ("Horizon sharpness", Range(0.5, 8)) = 2.2
        _SunColor ("Sun", Color) = (1, 0.96, 0.88, 1)
        _SunDirection ("Sun direction (towards sun)", Vector) = (0.3, 0.7, 0.3, 0)
        _SunSize ("Sun size", Range(0.0005, 0.05)) = 0.006
        _SunHalo ("Sun halo", Range(0, 2)) = 0.35
        _Exposure ("Exposure", Range(0, 4)) = 1
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" }
        Cull Off ZWrite Off
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            half4 _TopColor, _HorizonColor, _BottomColor, _SunColor;
            float4 _SunDirection;
            half _HorizonSharpness, _SunSize, _SunHalo, _Exposure;

            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; };

            v2f vert (appdata_base v)
            {
                v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.dir = v.vertex.xyz; return o;
            }

            half4 frag (v2f i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float up = saturate(d.y), down = saturate(-d.y);
                half3 col = lerp(_HorizonColor.rgb, _TopColor.rgb, pow(up, 1.0 / _HorizonSharpness));
                col = lerp(col, _BottomColor.rgb, saturate(pow(down, 0.35)));
                float3 s = normalize(_SunDirection.xyz);
                float c = saturate(dot(d, s));
                float disc = smoothstep(1.0 - _SunSize, 1.0 - _SunSize * 0.6, c);
                float halo = pow(c, 64.0) * _SunHalo + pow(c, 8.0) * _SunHalo * 0.25;
                col += _SunColor.rgb * (disc * 6.0 + halo) * step(-0.05, d.y);
                return half4(col * _Exposure, 1);
            }
            ENDCG
        }
    }
    Fallback Off
}
