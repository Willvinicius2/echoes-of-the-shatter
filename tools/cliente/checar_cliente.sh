#!/usr/bin/env bash
# Checagem do cliente C# sem o editor da Unity (Linux, ou Git Bash/WSL no Windows).
#   1. compila Assets/Scripts inteiro (menos EditorTools) contra as referências UnityEngine 2021.3 do NuGet "UnityEngine.Modules";
#   2. compila e roda os testes EditMode puros (os que não dependem do editor) com NUnitLite contra a shattercore real (.so).
# Não substitui o editor: o 2021.3 não tem Input System, URP nem Unity 6; os pontos faltantes entram como stubs em tools/cliente/stubs.cs.
# Testes que chamam código nativo da Unity (PlayerPrefs, MonoBehaviour estático) falham aqui por motivo do ambiente: ver LISTA_ESPERADA.
# Requer: dotnet 8 SDK, cmake, g++, curl, unzip, python3. Uso: tools/cliente/checar_cliente.sh [pasta-de-trabalho]
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
work="${1:-${TMPDIR:-/tmp}/echoes-cliente-check}"
assets="$repo/EchoesOfTheShatter/Assets"
mkdir -p "$work/lib" "$work/tst"

if [ ! -d "$work/um/lib/net45" ]; then
  curl -fsSL -o "$work/um.nupkg" https://api.nuget.org/v3-flatcontainer/unityengine.modules/2021.3.33/unityengine.modules.2021.3.33.nupkg
  mkdir -p "$work/um" && unzip -oq "$work/um.nupkg" -d "$work/um"
fi
echo "referencias UnityEngine: $(ls "$work"/um/lib/net45/*.dll | wc -l) dlls em $work/um/lib/net45"

# stubs: Debug por namespace (o Debug da Unity nao roda fora do editor) + o que o 2021.3 nao traz
python3 - "$assets/Scripts" "$repo/tools/cliente/stubs.cs" "$work/stubs.cs" <<'PY'
import re, glob, sys
scripts, template, out = sys.argv[1:4]
nss = set()
for f in glob.glob(scripts + '/**/*.cs', recursive=True):
    if 'EditorTools' in f: continue
    nss.update(re.findall(r'^\s*namespace\s+([\w.]+)', open(f, encoding='utf-8-sig').read(), re.M))
dbg = ('internal static class Debug { public static bool isDebugBuild => false; public static void Log(object o, object c = null) { System.Console.WriteLine(o); } '
       'public static void LogWarning(object o, object c = null) { System.Console.WriteLine("WARN " + o); } public static void LogError(object o, object c = null) { System.Console.WriteLine("ERR " + o); } '
       'public static void LogException(System.Exception e, object c = null) { System.Console.WriteLine(e); } public static void LogFormat(string f, params object[] a) { } '
       'public static void DrawLine(Vector3 a, Vector3 b, Color c = default, float d = 0f) { } public static void DrawRay(Vector3 a, Vector3 b, Color c = default, float d = 0f) { } }')
text = open(template, encoding='utf-8').read()
for ns in sorted(nss): text += 'namespace %s { using UnityEngine; %s }\n' % (ns, dbg)
open(out, 'w', encoding='utf-8').write(text)
PY
# UiArt usa unitySliceScale (so Unity 6): copia sem essa linha
sed '/unitySliceScale/d' "$assets/Scripts/UI/UiArt.cs" > "$work/UiArt.patched.cs"
printf 'public static class P { public static int Main(string[] a) => new NUnitLite.AutoRun(typeof(P).Assembly).Execute(a); }\n' > "$work/main.cs"

props='<TargetFramework>net8.0</TargetFramework><LangVersion>9.0</LangVersion><AllowUnsafeBlocks>true</AllowUnsafeBlocks><EnableDefaultCompileItems>false</EnableDefaultCompileItems><GenerateAssemblyInfo>false</GenerateAssemblyInfo><NoWarn>CS1701;CS1702;CS0649;CS0169;CS0414;CS0618;MSB3277;CS8632</NoWarn>'
cat > "$work/lib/lib.csproj" <<XML
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>$props</PropertyGroup>
  <ItemGroup>
    <Compile Include="$assets/Scripts/**/*.cs" Exclude="$assets/Scripts/EditorTools/**;$assets/Scripts/UI/UiArt.cs" />
    <Compile Include="$work/stubs.cs;$work/UiArt.patched.cs" />
    <Reference Include="$work/um/lib/net45/*.dll" />
  </ItemGroup>
</Project>
XML
echo "== 1/2 compilando Assets/Scripts =="
(cd "$work/lib" && dotnet build -nologo -v q 2>&1 | grep -E "error|Build succeeded" | sed 's/ \[.*//' | sort -u | head -40) || true
if ! (cd "$work/lib" && dotnet build -nologo -v q >/dev/null 2>&1); then echo "FALHOU: erros de compilacao acima"; exit 1; fi

# testes EditMode puros: tira os que dependem do UnityEditor (AnimatorController, SceneManagement, EditorTools)
excl=""
for f in "$assets"/Tests/EditMode/*.cs; do
  if grep -qE "UnityEditor|Echoes\.EditorTools|UnityEngine\.Rendering\.Universal" "$f"; then excl="$excl;$f"; fi
done
cat > "$work/tst/tst.csproj" <<XML
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>$props<OutputType>Exe</OutputType><AssemblyName>Echoes.Tests.EditMode</AssemblyName><GenerateProgramFile>false</GenerateProgramFile></PropertyGroup>
  <ItemGroup>
    <Compile Include="$work/main.cs;$assets/Tests/EditMode/**/*.cs" Exclude="${excl#;}" />
    <ProjectReference Include="../lib/lib.csproj" />
    <Reference Include="$work/um/lib/net45/*.dll" />
    <PackageReference Include="NUnitLite" Version="3.14.0" />
  </ItemGroup>
</Project>
XML
echo "== 2/2 testes EditMode contra a shattercore real =="
cmake -S "$repo/ShatterCore" -B "$work/core" -DCMAKE_BUILD_TYPE=Release -DSHATTER_BUILD_SHARED=ON >/dev/null
cmake --build "$work/core" -j --target shattercore_dll >/dev/null
(cd "$work/tst" && dotnet build -nologo -v q 2>&1 | grep -E " error " | sed 's/ \[.*//' | sort -u) || true
cp "$work/core/libshattercore.so" "$work/tst/bin/Debug/net8.0/"
export ECHOES_CONTENT_DIR="$repo/EchoesOfTheShatter/Content/Data"
{ dotnet "$work/tst/bin/Debug/net8.0/Echoes.Tests.EditMode.dll" --work="$work" 2>&1 || true; } | grep -v "non_NULL" | tee "$work/resultado.txt" | sed -n "/Test Run Summary/,/Duration/p"
echo "Falhas (confira em tools/cliente/LISTA_ESPERADA.txt):"
grep -E "^[0-9]+\) " "$work/resultado.txt" | sed -E 's/^[0-9]+\) [A-Za-z]+ : //' | sort > "$work/falhas.txt" || true
cat "$work/falhas.txt"
if ! diff -q "$work/falhas.txt" <(grep -v '^#' "$repo/tools/cliente/LISTA_ESPERADA.txt" | sort) >/dev/null; then
  echo "DIFERENTE da lista esperada: veja a diferenca abaixo"; diff "$work/falhas.txt" <(grep -v '^#' "$repo/tools/cliente/LISTA_ESPERADA.txt" | sort) || true; exit 2
fi
echo "OK: so as falhas esperadas (limitacao do ambiente sem editor)."
