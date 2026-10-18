# ShatterCore — motor de regras de Echoes of the Shatter (C++17 puro, sem Unreal).
#
#   cmake -S ShatterCore -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build -j
#   ctest --test-dir build --output-on-failure      (ou ./build/shattercore_tests)
#
# Opções:
#   SHATTER_BUILD_TESTS  (ON)  executável shattercore_tests a partir de tests/*.cpp
#   SHATTER_BUILD_BENCH  (OFF) executável shattercore_bench a partir de bench/*.cpp
#   SHATTER_WERROR       (OFF) warnings viram erro (ligado no CI)
#   SHATTER_SANITIZE     (OFF) ASan + UBSan (GCC/Clang)
#   SHATTER_BUILD_SHARED (ON)  DLL/so "shattercore" com a API C (include/shatter/shatter_c.h) para o Unity
cmake_minimum_required(VERSION 3.16)
project(ShatterCore VERSION 0.1.0 LANGUAGES C CXX)

option(SHATTER_BUILD_TESTS "Compila os testes" ON)
option(SHATTER_BUILD_BENCH "Compila o benchmark (bench/)" OFF)
option(SHATTER_WERROR "Trata warnings como erro" OFF)
option(SHATTER_SANITIZE "Ativa ASan/UBSan" OFF)
option(SHATTER_BUILD_SHARED "Compila a DLL/so shattercore (API C para P/Invoke)" ON)

# CRT estático no MSVC (/MT, /MTd) em todos os alvos: a DLL não depende de runtime instalado e a
# biblioteca estática ligada nela usa o mesmo CRT (docs/tecnico/04_arquitetura.md, seção 9.1).
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# Flags comuns. IMPORTANTE para o determinismo: nada de -ffast-math / /fp:fast.
function(shatter_set_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive- /fp:precise /utf-8)
    if(SHATTER_WERROR)
      target_compile_options(${target} PRIVATE /WX)
    endif()
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Wshadow -Wconversion
                                             -Wno-sign-conversion -ffp-contract=off)
    if(SHATTER_WERROR)
      target_compile_options(${target} PRIVATE -Werror)
    endif()
    if(SHATTER_SANITIZE)
      target_compile_options(${target} PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
      target_link_options(${target} PRIVATE -fsanitize=address,undefined)
    endif()
  endif()
endfunction()

# --- Biblioteca -------------------------------------------------------------
file(GLOB SHATTER_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)
file(GLOB SHATTER_HEADERS CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/include/shatter/*.h)

if(NOT SHATTER_SOURCES)
  # Antes do Backend escrever src/: biblioteca só-headers para não quebrar a configuração.
  message(STATUS "ShatterCore: src/ vazio — criando alvo INTERFACE (só headers)")
  add_library(shattercore INTERFACE)
  target_include_directories(shattercore INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
  target_compile_features(shattercore INTERFACE cxx_std_17)
else()
  add_library(shattercore STATIC ${SHATTER_SOURCES} ${SHATTER_HEADERS})
  target_include_directories(shattercore PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
  target_compile_features(shattercore PUBLIC cxx_std_17)
  # PIC e visibilidade oculta: a biblioteca estática entra na DLL sem exportar símbolos C++.
  set_target_properties(shattercore PROPERTIES POSITION_INDEPENDENT_CODE ON
                                               CXX_VISIBILITY_PRESET hidden
                                               VISIBILITY_INLINES_HIDDEN ON
                                               COMPILE_PDB_NAME shattercore_static)
  shatter_set_warnings(shattercore)
  if(SHATTER_SANITIZE AND NOT MSVC)
    target_link_options(shattercore PUBLIC -fsanitize=address,undefined)
  endif()

  # --- API C (shatter_c.h) ---------------------------------------------------
  set(SHATTER_C_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/src/c_api/shatter_c.cpp
                        ${CMAKE_CURRENT_SOURCE_DIR}/include/shatter/shatter_c.h)
  if(SHATTER_BUILD_SHARED)
    # DLL/so "shattercore" (shattercore.dll, libshattercore.so): exporta SÓ os símbolos SHATTER_API.
    add_library(shattercore_dll SHARED ${SHATTER_C_SOURCES})
    set_target_properties(shattercore_dll PROPERTIES OUTPUT_NAME shattercore
                                                     ARCHIVE_OUTPUT_NAME shattercore_dll  # .lib de importação ≠ .lib estática
                                                     CXX_VISIBILITY_PRESET hidden
                                                     VISIBILITY_INLINES_HIDDEN ON)
    target_compile_definitions(shattercore_dll PRIVATE SHATTER_C_BUILDING_DLL)
    target_link_libraries(shattercore_dll PRIVATE shattercore)
    target_include_directories(shattercore_dll PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
    shatter_set_warnings(shattercore_dll)
    if(NOT WIN32 AND NOT APPLE)
      # Templates da STL (visibilidade "default" nos headers) também ficam locais.
      target_link_options(shattercore_dll PRIVATE
        "LINKER:--version-script=${CMAKE_CURRENT_SOURCE_DIR}/src/c_api/shatter_c.map")
      set_property(TARGET shattercore_dll APPEND PROPERTY LINK_DEPENDS
        ${CMAKE_CURRENT_SOURCE_DIR}/src/c_api/shatter_c.map)
    endif()
    set(SHATTER_C_TARGET shattercore_dll)
  else()
    # Sem DLL: a mesma API C como biblioteca estática (testes da fronteira continuam rodando).
    add_library(shattercore_c_static STATIC ${SHATTER_C_SOURCES})
    target_compile_definitions(shattercore_c_static PUBLIC SHATTER_C_STATIC)
    target_link_libraries(shattercore_c_static PUBLIC shattercore)
    shatter_set_warnings(shattercore_c_static)
    set(SHATTER_C_TARGET shattercore_c_static)
  endif()
endif()

# Verificação de que cada header compila sozinho (inclui o que usa).
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/header_check/.keep "")
set(SHATTER_HEADER_CHECK_SOURCES "")
foreach(h ${SHATTER_HEADERS})
  get_filename_component(hn ${h} NAME_WE)
  set(cpp ${CMAKE_CURRENT_BINARY_DIR}/header_check/check_${hn}.cpp)
  file(WRITE ${cpp} "#include \"shatter/${hn}.h\"\n")
  list(APPEND SHATTER_HEADER_CHECK_SOURCES ${cpp})
endforeach()
add_library(shattercore_header_check OBJECT ${SHATTER_HEADER_CHECK_SOURCES})
target_include_directories(shattercore_header_check PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
shatter_set_warnings(shattercore_header_check)

# shatter_c.h também compila como C puro (C99), como exige a fronteira P/Invoke.
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/header_check/check_shatter_c.c
     "#include \"shatter/shatter_c.h\"\nint shatter_header_check_c(void) { return (int)SHATTER_C_API_VERSION; }\n")
add_library(shattercore_header_check_c OBJECT ${CMAKE_CURRENT_BINARY_DIR}/header_check/check_shatter_c.c)
target_include_directories(shattercore_header_check_c PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
set_target_properties(shattercore_header_check_c PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON C_EXTENSIONS OFF)
if(MSVC)
  target_compile_options(shattercore_header_check_c PRIVATE /W4 $<$<BOOL:${SHATTER_WERROR}>:/WX>)
else()
  target_compile_options(shattercore_header_check_c PRIVATE -Wall -Wextra -Wpedantic $<$<BOOL:${SHATTER_WERROR}>:-Werror>)
endif()

# --- Testes -----------------------------------------------------------------
if(SHATTER_BUILD_TESTS)
  file(GLOB SHATTER_TEST_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.cpp)
  # test_c_api.cpp vira um executável próprio, ligado à DLL (testa a fronteira de verdade).
  list(FILTER SHATTER_TEST_SOURCES EXCLUDE REGEX ".*/test_c_api\\.cpp$")
  if(SHATTER_TEST_SOURCES)
    enable_testing()
    add_executable(shattercore_tests ${SHATTER_TEST_SOURCES})
    target_link_libraries(shattercore_tests PRIVATE shattercore)
    target_include_directories(shattercore_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    # Dados de teste (CSV de exemplo, saves de cada versão publicada).
    target_compile_definitions(shattercore_tests PRIVATE
      SHATTER_TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/data"
      SHATTER_CONTENT_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../EchoesOfTheShatter/Content/Data"
      SHATTER_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}"
      SHATTER_TEST_TMP_DIR="${CMAKE_CURRENT_BINARY_DIR}/test_tmp")
    shatter_set_warnings(shattercore_tests)
    add_test(NAME shattercore_tests COMMAND shattercore_tests)

    # RF-51: um save gravado pelo core passa no validador de esquema do Data Engineer (Python).
    find_package(Python3 COMPONENTS Interpreter QUIET)
    if(Python3_Interpreter_FOUND)
      add_test(NAME save_rf51_python_validator
               COMMAND ${CMAKE_COMMAND}
                       -DTEST_BIN=$<TARGET_FILE:shattercore_tests>
                       -DPYTHON=${Python3_EXECUTABLE}
                       -DREPO=${CMAKE_CURRENT_SOURCE_DIR}/..
                       -DOUT=${CMAKE_CURRENT_BINARY_DIR}/test_tmp/rf51_python/slot_1
                       -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/run_save_validator.cmake)
    else()
      message(STATUS "ShatterCore: Python 3 não encontrado — teste save_rf51_python_validator omitido")
    endif()

    # Fronteira da API C: o mesmo framework, ligado à DLL/so (ou à API C estática sem SHATTER_BUILD_SHARED).
    if(SHATTER_C_TARGET AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_c_api.cpp)
      add_executable(shattercore_c_api_tests ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_c_api.cpp
                                             ${CMAKE_CURRENT_SOURCE_DIR}/tests/main.cpp)
      target_link_libraries(shattercore_c_api_tests PRIVATE ${SHATTER_C_TARGET} shattercore)
      target_include_directories(shattercore_c_api_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
      target_compile_definitions(shattercore_c_api_tests PRIVATE
        SHATTER_TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/data"
        SHATTER_CONTENT_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../EchoesOfTheShatter/Content/Data"
        SHATTER_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}"
        SHATTER_TEST_TMP_DIR="${CMAKE_CURRENT_BINARY_DIR}/test_tmp")
      shatter_set_warnings(shattercore_c_api_tests)
      add_test(NAME shattercore_c_api_tests COMMAND shattercore_c_api_tests)
    endif()

    # A DLL/so exporta exatamente as funções SHATTER_API do header (nada do C++ do core).
    if(SHATTER_BUILD_SHARED AND NOT WIN32 AND NOT APPLE AND CMAKE_NM)
      add_test(NAME shattercore_dll_exports
               COMMAND ${CMAKE_COMMAND} -DNM=${CMAKE_NM} -DLIB=$<TARGET_FILE:shattercore_dll>
                       -DHEADER=${CMAKE_CURRENT_SOURCE_DIR}/include/shatter/shatter_c.h
                       -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/check_exports.cmake)
    endif()
  else()
    message(STATUS "ShatterCore: tests/*.cpp ainda não existe — alvo de testes omitido")
  endif()
endif()

# --- Benchmark --------------------------------------------------------------
if(SHATTER_BUILD_BENCH)
  file(GLOB SHATTER_BENCH_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/bench/*.cpp)
  if(SHATTER_BENCH_SOURCES)
    add_executable(shattercore_bench ${SHATTER_BENCH_SOURCES})
    target_link_libraries(shattercore_bench PRIVATE shattercore)
    target_compile_definitions(shattercore_bench PRIVATE
      SHATTER_CONTENT_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../EchoesOfTheShatter/Content/Data")
    shatter_set_warnings(shattercore_bench)
  else()
    message(STATUS "ShatterCore: bench/*.cpp ainda não existe — alvo de bench omitido")
  endif()
endif()
