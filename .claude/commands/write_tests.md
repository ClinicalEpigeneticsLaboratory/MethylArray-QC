Write comprehensive tests for: $ARGUMENTS

Testing conventions:
- Use nf-test - a testing framework for Nextflow pipelines
- Place test files in a tests/ project directory
- Name test files as:
* module tests: modules.[module_name].nf.test(x)
* subworkflow tests: [subworkflow_name].nf.test(x)

Coverage:
- Test happy paths
- Test edge cases
- Test error states
- test specific pipeline components (unit tests for processes within modules, subworkflows)
- prepare snapshot tests