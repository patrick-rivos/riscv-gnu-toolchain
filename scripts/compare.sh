#!/bin/bash
echo $(pwd)
while getopts "b:c:hl:" opt; do
  case "$opt" in
    b)
      baseline="$OPTARG"
      ;;
    c)
      compare="$OPTARG"
      ;;
    l)
      libc="$OPTARG"
      ;;
    ?|h)
      echo "Usage: $(basename $0) -b <base directory> -c <compare directory> -l <linux|newlib>"
      exit 0
      ;;
  esac
done
if [ $libc == "linux" ]; then
  ../scripts/testsuite-filter gcc glibc ../test/allowlist `find $baseline/build-gcc-$libc-stage2/gcc/testsuite/ -name "*.sum" |paste -sd "," -` > $baseline/results.log
  ../scripts/testsuite-filter gcc glibc ../test/allowlist `find $compare/build-gcc-$libc-stage2/gcc/testsuite/ -name "*.sum" |paste -sd "," -` > $compare/results.log
else
  ../scripts/testsuite-filter gcc $libc ../test/allowlist `find $baseline/build-gcc-$libc-stage2/gcc/testsuite/ -name "*.sum" |paste -sd "," -` > $baseline/results.log
  ../scripts/testsuite-filter gcc $libc ../test/allowlist `find $compare/build-gcc-$libc-stage2/gcc/testsuite/ -name "*.sum" |paste -sd "," -` > $compare/results.log
fi
python ../scripts/compare_testsuite_log.py -plog $baseline/results.log -clog $compare/results.log -phash baseline -chash compare