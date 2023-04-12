#!/bin/bash
readonly num_jobs=$((4 + $RANDOM % 4))

# Unit Tests
if python -m unittest discover -s tests/unit_tests -vvv; then
  echo "unit_tests passed!"
else
  echo "unit_tests failed"
  exit 1
fi

# Reset the database with a dummy test
if python -m unittest tests.integration_tests.test_frontend.BasicCase.test_webserver_is_up; then
  echo "database reset!"
else
  echo "unit_tests failed"
  exit 1
fi

# Integration Tests
if unittest-parallel -s tests/integration_tests -j $num_jobs -vvv; then
  echo "integration_tests passed!"
else
  echo "integration_tests failed"
  exit 1
fi

# Acceptance Tests
if unittest-parallel -s tests/acceptance_tests -j $num_jobs -vvv; then
  echo "acceptance_tests passed!"
else
  echo "acceptance_tests failed"
  exit 1
fi

# Smoke Tests
if unittest-parallel -s tests/smoke_tests -j $num_jobs -vvv; then
  echo "smoke_tests passed!"
else
  echo "smoke_tests failed"
  exit 1
fi
