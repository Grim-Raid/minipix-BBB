cmake_minimum_required(VERSION 3.1.2)
project(minipix_dummy_bbb)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_definitions(-DLLCP_LITTLE_ENDIAN)

add_definitions(-Wall)
add_definitions(-Wextra)
add_definitions(-Wpedantic)
# add_definitions(-O0)
# add_definitions(-g)

include_directories(
  ${CMAKE_CURRENT_SOURCE_DIR}/../linux/include
  ${CMAKE_CURRENT_SOURCE_DIR}/../../serial_port
  ${CMAKE_CURRENT_SOURCE_DIR}/../../llcp/include
  ${CMAKE_CURRENT_SOURCE_DIR}/../shared/include
)

find_package(Threads)

add_executable(minipix_dummy_bbb
  ${CMAKE_CURRENT_SOURCE_DIR}/../linux/src/main.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/../linux/src/minipix_dummy_linux.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/../../serial_port/serial_port.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/../../llcp/src/llcp.c
  ${CMAKE_CURRENT_SOURCE_DIR}/../../llcp/src/llcp_endian.c
  ${CMAKE_CURRENT_SOURCE_DIR}/../../llcp/src/llcp_minipix_messages.c
  ${CMAKE_CURRENT_SOURCE_DIR}/../shared/src/pixel_encoder.c
  ${CMAKE_CURRENT_SOURCE_DIR}/../shared/src/minipix_dummy.cpp
)

target_link_libraries(minipix_dummy_bbb
  Threads::Threads
)
