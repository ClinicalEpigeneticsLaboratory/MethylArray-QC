# Commands were ran manually, but this script serves as a reminder of the steps to run the tests and update snapshots.

# 1. Smoke-test the config
nf-test list

# 2. Generate snapshot baselines (all tests, stub mode)
nf-test test --update-snapshot

# 3. Confirm snapshots are locked
nf-test test

# 4. Run validator error-state tests with real containers
#    (remove the stub option and uncomment error blocks first)
nf-test test \
  tests/modules.additional_validators_init.nf.test \
  tests/modules.additional_validators_after_impute.nf.test \
  --verbose
