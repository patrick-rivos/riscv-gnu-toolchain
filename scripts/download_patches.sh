#!/bin/bash

while getopts "hp:" opt; do
  case "$opt" in 
    p)
      patch_name="$OPTARG"
      echo "patch name is $patch_name"
      ;;
    ?|h)
      echo "Usage: $(basename $0) -p <patch file>"
      exit 0
      ;;
  esac
done

mkdir -p patches
cd patches
let num=1
while IFS="" read -r line; do
  echo "downloading patch from $line"
  if [[ "$line" == "" || "$line" == "\n" ]]; then
    continue
  fi
  wget -O "patch-$num.patch" $line
  num=$(($num+1))
done < "../patch_urls/$patch_name"
