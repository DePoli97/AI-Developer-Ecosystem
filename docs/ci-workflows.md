# CI workflows (copy under `.github/workflows/`)

The two GitHub Actions workflows below are ready to drop into
`.github/workflows/`. They are kept here in `docs/` because the GitHub
PAT used by the autonomous session that wrote this repo does not have
the `workflow` scope; the operator copies them by hand the first time.

Once the files are under `.github/workflows/`, future sessions can
update them like any other file (the rejection only happens for *new*
or *modified* workflow files).

## `tests.yml` - run every snippet self-test on push and PR

Save as `.github/workflows/tests.yml`:

```yaml
name: snippet-self-tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  run-self-tests:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install "numpy>=1.26" "pydantic>=2.5" "anthropic>=0.40"

      - name: Run snippet self-tests
        env:
          ANTHROPIC_API_KEY: "sk-ant-ci-fake"
        run: |
          set -uo pipefail
          require_real_api=(
            "snippets/python/anthropic_tool_use_loop.py"
          )
          failed=0
          for f in snippets/python/*.py; do
            echo "=== $f ==="
            skip=0
            for needs in "${require_real_api[@]}"; do
              if [ "$f" = "$needs" ]; then skip=1; break; fi
            done
            if [ "$skip" -eq 1 ]; then
              python -c "import ast, sys; ast.parse(open('$f').read())" \
                && echo "  import-syntax OK (real-api file)" \
                || { echo "  FAIL: syntax check"; failed=1; }
              continue
            fi
            if python "$f" --self-test; then
              :
            elif python "$f"; then
              :
            else
              echo "  FAIL: $f"
              failed=1
            fi
          done
          exit $failed

      - name: Run cookbook self-tests
        run: |
          set -euxo pipefail
          for f in cookbook/*.py; do
            echo "=== $f ==="
            python "$f" --self-test
          done
```

## `eval.yml` - run prompt eval on PRs touching prompts

Save as `.github/workflows/eval.yml`:

```yaml
name: prompt-eval

on:
  pull_request:
    paths:
      - "templates/**/prompts/**"
      - "tutorials/**prompt**"
      - "snippets/python/prompt_version_runner.py"
      - "snippets/python/minimal_eval_harness.py"
      - "cookbook/eval_on_commit.py"
  workflow_dispatch:

permissions:
  pull-requests: write
  contents: read

jobs:
  run-evals:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install "numpy>=1.26" "pydantic>=2.5" "anthropic>=0.40"

      - name: Run eval-on-commit cookbook (offline)
        id: evals
        run: |
          set +e
          python cookbook/eval_on_commit.py 2>&1 | tee eval_output.txt
          echo "exit_code=$?" >> "$GITHUB_OUTPUT"

      - name: Comment result on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('eval_output.txt', 'utf8');
            const status = '${{ steps.evals.outputs.exit_code }}' === '0' ? 'PASS' : 'FAIL';
            const heading = status === 'PASS'
              ? '### Prompt eval: PASS'
              : '### Prompt eval: FAIL';
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: heading + '\n\n```\n' + body + '\n```'
            });

      - name: Fail job on regression
        if: steps.evals.outputs.exit_code != '0'
        run: exit 1
```

## One-time installation steps

1. Create the directory: `mkdir -p .github/workflows`
2. Save the two YAML blocks above as `tests.yml` and `eval.yml`.
3. Commit and push from your local machine (your personal GitHub login
   has the `workflow` scope; autonomous sessions do not).
4. After the first push, future sessions can update these files normally.
