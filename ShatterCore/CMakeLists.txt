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
cmake_minimum_required(VERSION 3.16)
project(ShatterCore VERSION 0.1.0 LANGUAGES CXX)

option(SHATTER_BUILD_TESTS "Compila os testes" ON)
option(SHATTER_BUILD_BENCH "Compila o benchmark (bench/)" OFF)
option(SHATTER_WERROR "Trata warnings como erro" OFF)
option(SHATTER_SANITIZE "Ativa ASan/UBSan" OFF)

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
  shatter_set_warnings(shattercore)
  if(SHATTER_SANITIZE AND NOT MSVC)
    target_link_options(shattercore PUBLIC -fsanitize=address,undefined)
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

# --- Testes -----------------------------------------------------------------
if(SHATTER_BUILD_TESTS)
  file(GLOB SHATTER_TEST_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.cpp)
  if(SHATTER_TEST_SOURCES)
    enable_testing()
    add_executable(shattercore_tests ${SHATTER_TEST_SOURCES})
    target_link_libraries(shattercore_tests PRIVATE shattercore)
    target_include_directories(shattercore_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
    # Dados de teste (CSV de exemplo, saves de cada versão publicada).
    target_compile_definitions(shattercore_tests PRIVATE
      SHATTER_TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/tests/data"
      SHATTER_CONTENT_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../EchoesOfTheShatter/Content/Data")
    shatter_set_warnings(shattercore_tests)
    add_test(NAME shattercore_tests COMMAND shattercore_tests)
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
