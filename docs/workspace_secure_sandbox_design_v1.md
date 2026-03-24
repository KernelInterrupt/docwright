# Workspace Secure Sandbox Design v1

This document refines the **security-grade sandbox backend** direction for
DocWright workspaces.

It exists because the current repository now contains:
- a transport-neutral `SandboxBackend` contract
- a `LocalProcessSandboxBackend`
- an annotation-first LaTeX compiler path

That baseline is useful for development and testing, but it is **not** a strong
security boundary against hostile or semi-trusted model behavior.

---

## 1. Core conclusion

`LocalProcessSandboxBackend` must be treated as:
- development-friendly
- deterministic for tests
- architecture-valid
- **not production-safe against jailbreak attempts**

The production direction should be:

```text
WorkspaceSession
  -> WorkspaceCompiler
  -> SecureSandboxBackend
       -> isolated filesystem
       -> isolated process/user
       -> no ambient host secrets
       -> bounded resources
       -> explicit artifact export
```

In short:

> temporary local-process execution is acceptable for developer workflows, but
> untrusted model compilation must run inside a stronger isolation backend.

---


## 1.5 Current repository status

The repository now contains two concrete sandbox backends:
- `LocalProcessSandboxBackend`
- `BubblewrapSandboxBackend`

Recommended positioning:
- keep `LocalProcessSandboxBackend` for tests, debugging, and portable fallback
- use `BubblewrapSandboxBackend` when the host supports `bwrap` and stronger isolation is needed

So the correct near-term strategy is **parallel backends**, not immediate replacement.

---

## 2. Threat model

DocWright should assume that workspace content may be controlled by a model that
is at least partially untrusted.

That means the sandbox design must defend against:

### 2.1 Filesystem escape
Examples:
- `../` traversal
- absolute-path reads
- reading parent directories
- probing mounted host paths
- writing outside the allowed workspace root

### 2.2 Compiler-mediated file exfiltration
Examples in LaTeX-like environments:
- `\input{../../secret}`
- `\include{...}`
- reading arbitrary local files into the final rendered artifact or log
- shell-escape style execution if the engine/profile permits it

### 2.3 Host secret leakage
Examples:
- environment variables
- SSH keys
- API keys
- home-directory config
- CI credentials
- repository-local secrets not intended for the workspace

### 2.4 Resource abuse
Examples:
- infinite compile loops
- huge memory use
- fork bombs
- massive temporary-file generation
- network abuse

### 2.5 Artifact abuse
Examples:
- exporting arbitrary files as artifacts
- symlink tricks
- embedding host data into output files

---

## 3. Non-goals

The secure sandbox backend should **not**:
- turn `WorkspaceSession` into a container abstraction
- move host-runtime implementation details into Core
- pretend content validation alone is sufficient security
- rely on prompt instructions as the primary defense

Prompting and tool descriptions help, but they are not the security boundary.

---

## 4. Why the current local-process backend is insufficient

The current local backend does this:
- creates a temporary working directory
- writes requested input files there
- runs a subprocess in that directory
- captures stdout/stderr
- collects configured artifacts

This is useful, but it does **not** guarantee:
- no access to `../`
- no access to absolute paths
- no access to ambient environment variables
- no network access
- no syscall restrictions
- no mount isolation

So this backend is best described as:

> a local execution backend with temporary workspace isolation, not a hardened
> security sandbox.

That distinction must stay explicit in docs and API expectations.

---

## 5. Security boundary requirements

A security-grade backend should provide the following minimum properties.

### 5.1 Filesystem isolation
The executing process should only see:
- an isolated writable workspace root
- a tiny explicit read-only runtime/toolchain view if required
- no ambient home directory
- no repository parent tree by default

Practical ways to achieve this:
- mount namespace + bind mounts
- container rootfs
- chroot/pivot_root style isolation
- host-provided secure workspace mounts

### 5.2 Process/user isolation
The process should run:
- as a dedicated low-privilege user
- without inheriting host agent privileges
- without access to sensitive process capabilities

### 5.3 Network isolation
Default policy should be:
- no outbound network
- no inbound listeners
- opt-in only if a future compiler truly needs it

### 5.4 Resource limits
The backend should be able to enforce:
- wall-clock timeout
- CPU quota
- memory limit
- file-size limit
- process-count limit

### 5.5 Artifact allowlisting
Only declared artifact paths should be exportable.

The backend should reject or ignore:
- paths outside workspace root
- symlink escapes
- directory traversal in artifact requests

### 5.6 Clean environment
Only a tiny allowlisted environment should be passed through.

Default should be closer to:
- empty env + minimal runtime vars

not:
- inherit the full host environment.

---

## 6. Recommended backend split

DocWright should keep the abstract contract and allow multiple concrete secure
backends.

### 6.1 `LocalProcessSandboxBackend`
Purpose:
- tests
- local development
- debugging compiler integration

Security posture:
- **not a hard boundary**

### 6.2 `ContainerSandboxBackend`
Recommended production-oriented default.

Implementation options:
- Docker
- Podman
- rootless container runtime
- nsjail/firejail/bubblewrap style wrapper if available

Expected guarantees:
- isolated filesystem view
- isolated user/process namespace
- explicit mounts
- resource controls
- network-off by default

### 6.3 `HostProvidedSandboxBackend`
For runtimes/platforms that already provide an isolated execution environment.

Examples:
- external agent runtime sandbox
- managed execution environment
- platform-owned per-run ephemeral workers

DocWright Core should only depend on the abstract backend contract, not the host
runtime internals.

---

## 7. Recommended contract extensions

The current `SandboxBackend` contract is enough for the first baseline, but a
security-grade path will likely need richer metadata.

Suggested additions:

```python
@dataclass(slots=True, frozen=True)
class SandboxDescriptor:
    name: str
    isolation_level: str  # e.g. "local_process", "container", "host_provided"
    network_default: str  # e.g. "disabled"
    filesystem_model: str  # e.g. "isolated_rootfs"
    available: bool = True
    details: dict[str, Any] = field(default_factory=dict)
```

```python
@dataclass(slots=True, frozen=True)
class SandboxPolicy:
    timeout_seconds: float = 20.0
    allow_network: bool = False
    memory_limit_mb: int | None = None
    cpu_limit: float | None = None
    process_limit: int | None = None
    writable_roots: tuple[str, ...] = ()
    readable_roots: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
```

Note: `readable_roots` / `writable_roots` should be interpreted by the backend
inside an isolated mount model, not as direct permission to browse the host
filesystem.

---

## 8. LaTeX-specific hardening guidance

Even with a strong OS/container sandbox, LaTeX compilation should still be
hardened at the compiler/profile layer.

Recommended policy:
- shell escape disabled by default
- fixed compiler profiles only
- no user-controlled command argv
- explicit main entry filename
- minimal preamble surface in built-in templates
- artifact exports restricted to allowlisted outputs

Optional later safeguards:
- content linting for suspicious constructs
- profile-level rejection of dangerous macros or file includes
- log scanning for escape attempts

Important:
- content validation is a helpful **secondary** defense
- isolation remains the **primary** defense

---

## 9. Migration plan

Recommended rollout order:

### Phase S1 — keep current baseline explicit
- retain `LocalProcessSandboxBackend`
- document it as dev/test only
- avoid marketing it as secure isolation

### Phase S2 — add secure backend abstraction details
- introduce richer sandbox descriptor/policy fields
- make compiler metadata surface isolation level clearly

### Phase S3 — implement first strong backend
Preferred first target:
- `ContainerSandboxBackend`

Requirements:
- isolated root filesystem or equivalent
- no ambient home/repo mounts
- network disabled by default
- artifact extraction through explicit allowlist
- resource limits

### Phase S4 — add host-provided backend
- integrate external runtime sandboxes through a backend adapter
- keep Core independent of host-specific SDK assumptions

---

## 10. What should be true before calling it production-safe

A DocWright sandbox backend should not be described as production-safe unless it
can demonstrate all of the following:

- untrusted content cannot read arbitrary parent/host files
- artifact export cannot escape the declared allowlist
- ambient host secrets are not visible by default
- network is disabled unless explicitly enabled
- time/memory/process limits are enforced
- compiler execution does not inherit full host privileges

If these are not true, the backend should be labeled clearly as:
- local
- debug
- test-only
- non-hardened

---

## 11. Final conclusion

The right design is **not** to make workspace itself more magical.
The right design is:

- keep workspace as the logical editing abstraction
- keep compiler as the assembly/diagnostic abstraction
- make sandbox the real execution security boundary

And for hostile-model scenarios:

> `LocalProcessSandboxBackend` is insufficient; DocWright should move toward a
> container-backed or host-provided secure sandbox backend.
