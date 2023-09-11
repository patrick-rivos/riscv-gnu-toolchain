#!/bin/bash -x

if [ "$1" == "newlib" ]; then
  /tc/scripts/testsuite-filter gcc newlib /tc/test/allowlist `find /tc/build/build-gcc-newlib-stage2/gcc/testsuite -name *.sum |paste -sd "," -`
else \
  /tc/scripts/testsuite-filter gcc glibc /tc/test/allowlist `find /tc/build/build-gcc-newlib-stage2/gcc/testsuite -name *.sum |paste -sd "," -`
fi
