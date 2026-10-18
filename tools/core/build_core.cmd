@echo off
rem Compila e testa o ShatterCore com o MSVC e o CMake do Visual Studio Build Tools.
rem Uso: tools\core\build_core.cmd [Debug|Release] [--werror]
setlocal
set CONFIG=%~1
if "%CONFIG%"=="" set CONFIG=Release
set WERROR=OFF
if /I "%~2"=="--werror" set WERROR=ON

for /f "usebackq delims=" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -property installationPath`) do set VSROOT=%%i
if not defined VSROOT (echo Visual Studio nao encontrado & exit /b 1)
call "%VSROOT%\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul || exit /b 1
set CMAKE="%VSROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set CTEST="%VSROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\ctest.exe"
set NINJA=%VSROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe

pushd "%~dp0..\.."
%CMAKE% -S ShatterCore -B build\%CONFIG% -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=%CONFIG% -DSHATTER_WERROR=%WERROR% || goto :fail
%CMAKE% --build build\%CONFIG% || goto :fail
if exist build\%CONFIG%\CTestTestfile.cmake %CTEST% --test-dir build\%CONFIG% --output-on-failure || goto :fail
popd
exit /b 0
:fail
popd
exit /b 1
