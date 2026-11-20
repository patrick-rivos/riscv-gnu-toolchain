# RISE GCC CI Toolchain Maintenance

This fork carries the toolchain scripts, helper utilities, allowlists, and
submodule revisions used by the RISE GCC RISC-V CI services.

## Branch Ownership

`build-frequent` is the CI-maintained branch. It is consumed as a pinned
submodule by:

- `riseproject-dev/gcc-postcommit-ci`
- `riseproject-dev/gcc-precommit-ci`

The upstream RISC-V GNU toolchain project remains the source for normal
toolchain documentation and build behavior. This fork exists so CI-specific
scripts, Patchwork helpers, artifact lookup code, and test utilities can be
maintained under RISE ownership without depending on a personal repository.

## Updating The Submodule Revision

1. Make changes on `build-frequent`.
2. Run the migration guard, local Python tests, and pre-commit hooks, in that
   order:

   ```sh
   python scripts/check_migration_guards.py
   pytest test/pytests -m 'not github_token_required'
   pre-commit run --all-files
   ```

3. Commit and merge the toolchain change, then record the published commit SHA.
4. Once that commit is available, update each CI repository that consumes the
   change so its `riscv-gnu-toolchain` gitlink points to that SHA and `.gitmodules` uses
   `https://github.com/riseproject-dev/riscv-gnu-toolchain-ci.git`.
5. Run submodule sync and initialization checks in each affected CI repository.
6. For a change that affects both services, release post-commit CI first so it
   can establish the baseline used by pre-commit CI. A change confined to
   pre-commit Patchwork filtering only requires a gitlink update in
   `gcc-precommit-ci`.

Pull-request validation does not need production baseline artifacts or a
cross-repository token. Patch selection tests use local fixtures.

After post-commit CI has published a valid baseline and retained artifacts,
maintainers can manually dispatch `Pre-Pull-Request` with
`run_integration_tests=true`. Set the toolchain repository's
`RISE_CI_READ_TOKEN` secret to a RISE service credential with read access to
post-commit Actions artifacts. The ordinary repository `GITHUB_TOKEN` cannot
provide this cross-repository artifact access. This optional production check
is deliberately independent of the checks required to merge the toolchain PR.

## Repository Configuration

### Source mirrors and checkout retries

The binutils/GDB, glibc, newlib and musl URLs follow upstream
[riscv-gnu-toolchain#1891](https://github.com/riscv-collab/riscv-gnu-toolchain/pull/1891):
`gnutools/binutils-gdb`, `gnutools/glibc`, `cygwin/cygwin` and `kraj/musl`.
DejaGnu stays on Savannah. The mirror change does not change any gitlink SHA.

Both parent CI repositories initialize their required dependencies with
`bash scripts/update_ci_submodules.sh binutils dejagnu gdb glibc newlib qemu`.
This synchronizes existing submodule URLs and retries checkout up to five
times, with 30/60/90/120-second delays, failing the job if checkout still fails.
Unlike upstream's build-only workflow, these CI services keep complete Git
history for previous-result comparisons; do not add a blanket `--depth 1`.
Invalidate the numbered source caches in both parent repositories when
deploying this change, so old submodule configurations cannot be restored.

### Service configuration

Runtime helpers default to these RISE repositories:

- `POSTCOMMIT_REPOSITORY=riseproject-dev/gcc-postcommit-ci`
- `PRECOMMIT_REPOSITORY=riseproject-dev/gcc-precommit-ci`

Override them only for intentional staging or local testing. Missing baselines,
GitHub API failures, invalid issue payloads, and empty result sets should fail
with an actionable error instead of falling back to a personal repository.

`PATCHWORK_CHECK_USERNAME` is required by `scripts/check_patch_checks.py`. Set
it to the Patchwork username of the RISE CI account in the invoking workflow or
repository configuration. There is no legacy-account fallback. Completed
testsuite checks are recognized by the `toolchain-ci-rise-test` context.

`PATCHWORK_REPORTING_ENABLED` must be exactly `true` before Patchwork results
are posted. When it is disabled, `scripts/post_check_to_patchworks.py` does not
require a token. When it is enabled, a real Patchwork API token is mandatory
and any non-success response fails the command.

Aggregation marks a report `invalid` if any summary is damaged or a downloaded
testsuite report lacks its corresponding summary, even if other targets
completed. Artifact lookup skips expired entries; a failed download reports its
HTTP status before writing an archive.

## Patchwork Filtering

Patch discovery, manual IDs, ID files and nightly recovery accept Sourceware
GCC project patches with an explicit target tag (for example, `[PATCH,RISC-V]`
or a subject starting with `RISC-V:`, `RISCV`, or `GCC/RISC-V:` after any
bracketed tags), or whose diff changes a target directory listed in
`scripts/riscv_patch_scope.py`. A comparison such as `AArch64: Fix costs as
on RISC-V` in a patch that only touches AArch64 is outside the CI scope.
They do not use submitter addresses or arbitrary words in the mail body.
Selected patches include preceding members of the same series as prerequisites.
The override workflow can validate an ID using
`python scripts/riscv_patch_scope.py PATCH_ID`.

Overlap recovery only trusts checks from `PATCHWORK_CHECK_USERNAME` in the
`toolchain-ci-rise-` context namespace. A pending check from this service means
the patch has already started. With no username configured, shadow discovery
keeps overlapping patches instead of trusting another service's checks; a patch
can therefore be included in both adjacent polling windows. Nightly recovery
still requires an explicit username.

The first scheduled run in a new repository uses the preceding 15 minutes as
its discovery window, plus the normal 15-minute overlap. Later runs start from
the previous scheduled run's timestamp, including gaps in polling.

## Release Policy

Maintained release helpers follow the existing `release_15_` artifact prefix
and `release-15` workflow conventions. The current maintained release branch
uses the same convention with `release_16_` and `release-16`.
