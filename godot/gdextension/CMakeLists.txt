# GDExtension do módulo `rogue` do ShatterCore.
#   cmake -S godot/gdextension -B build-ext -DCMAKE_BUILD_TYPE=Release -DGODOT_CPP_DIR=<pasta do godot-cpp 4.4>
#   cmake --build build-ext
# A biblioteca sai em godot/gdextension/bin/. O core entra como biblioteca estática (sem DLL separada).
cmake_minimum_required(VERSION 3.20)
project(shatter_gdextension CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(GODOT_CPP_DIR "" CACHE PATH "Pasta do godot-cpp (branch 4.4)")
if(NOT GODOT_CPP_DIR)
  message(FATAL_ERROR "Informe -DGODOT_CPP_DIR=<pasta do godot-cpp>")
endif()

set(SHATTER_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(SHATTER_BUILD_SHARED OFF CACHE BOOL "" FORCE)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../ShatterCore ${CMAKE_BINARY_DIR}/shattercore)
add_subdirectory(${GODOT_CPP_DIR} ${CMAKE_BINARY_DIR}/godot-cpp)

add_library(shatter_gdextension SHARED src/register_types.cpp src/shatter_rogue_node.cpp)
target_link_libraries(shatter_gdextension PRIVATE godot::cpp shattercore_c_static)

if(WIN32)
  set(_so "windows.x86_64")
else()
  set(_so "linux.x86_64")
endif()
set_target_properties(shatter_gdextension PROPERTIES
  PREFIX "" OUTPUT_NAME "libshatter_gdextension.${_so}"
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin)
if(WIN32)
  set_target_properties(shatter_gdextension PROPERTIES OUTPUT_NAME "shatter_gdextension.${_so}")
endif()
