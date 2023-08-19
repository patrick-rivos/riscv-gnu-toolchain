#!/bin/bash

echo $(pwd)


while getopts "e:f:hl:t:" opt; do
  case "$opt" in 
    e)
      exp_file="$OPTARG"
      echo "exp file is $exp_file"
      ;;
    l)
      libc="$OPTARG"
      echo "libc is $libc"
      ;;
    f)
      test_case="$OPTARG"
      echo "test case is $test_case"
      ;;
    t)
      target_arch="$OPTARG"
      echo "target arch is $target_arch"
      ;;
    ?|h)
      echo "Usage: $(basename $0) -l <libc> -e <exp file> -f <test file> -t <target arch>"
      exit 0
      ;;
  esac
done

if [ -z "$exp_file" ] || [ -z "$libc" ] || [ -z "$test_case" ] || [ -z "$target_arch" ]; then
  echo 'Missing required parameter. Run with -h to see all parameters.' >&2
  exit 1
fi

current_commit=$(git rev-parse HEAD)
cd ../build
make distclean
../configure --prefix=$(pwd)
if [[ "$libc" == "newlib" ]]; then
  RUNTESTFLAGS="$exp_file" make report-newlib -j nproc
else
  RUNTESTFLAGS="$exp_file" make report-linux -j nproc
fi

dummy=$(python3 script.py -bdir "build-gcc-$libc-stage2" -tt "$exp_file=$test_case" -tb $target_arch -vv &> "$current_commit-log.txt")
found_lines=$(python3 script.py -bdir "build-gcc-$libc-stage2" -tt "$exp_file=$test_case" -tb $target_arch | grep "# of unexpected")
ret=$?
cd ../gcc
echo "current iteration on $current_commit found:\n$found_lines" >> "../build/$current_commit-log.txt"

# if grep found FAIL: exit(1) else exit(0)
# this is opposite of what grep normally does
if [[ $ret == 1 ]]; then
  exit 0
else
  exit 1
fi


