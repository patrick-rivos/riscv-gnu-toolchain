#!/bin/bash -x

if [ "$1" == "multilib" ]; then
  cd tc && cd build && ../configure --prefix=/tc/build --enable-multilib
    --with-multilib-generator="rv64gc-lp64d--;rv32gc-ilp32d--";
else
  TARGET_TUPLE=($(echo $2 | tr "-" "\n"))
  cd tc && cd build && ../configure --prefix=/tc/build \
    --with-multilib-generator="${TARGET_TUPLE[0]}-${TARGET_TUPLE[1]}--"
fi
