#!/bin/bash
readonly num_loops="$1"

for ((i=0; i<=$num_loops; i++)) do
  if /bin/bash host/test_all.sh; then
    echo "all tests passed!"
  else
    exit 1
  fi
done
echo looks like everything works!
