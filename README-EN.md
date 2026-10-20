<div align="center">

# GKI KernelSU + SUSFS (Eternal-Dash Fork)

**A fork of [zzh20188/GKI_KernelSU_SUSFS](https://github.com/zzh20188/GKI_KernelSU_SUSFS).
Only the build pipeline is adapted; kernel / SUSFS / KernelSU sources are used as-is.**

简体中文 | [中文说明](README.md)

</div>

---

## 0. Wait, what even is this?

| | |
|:---|:---|
| **Is** | A GitHub Actions workflow repository for building GKI kernels, forked from `zzh20188/GKI_KernelSU_SUSFS` (upstream of upstream: `WildKernels/GKI_KernelSU_SUSFS`) |
| **Is not** | A kernel source repository. It adds no kernel features of its own and claims no authorship over upstream code |
| **Changed files** | `.github/workflows/build.yml`, `.github/workflows/main.yml`, `config/config` (plus this doc and `CREDITS.md`) |
| **Maintainer of the fork-specific changes** | **Eternal-Dash** (2026-10) |

```
WildKernels/GKI_KernelSU_SUSFS  (main)      ← original upstream
  └── zzh20188/GKI_KernelSU_SUSFS (dev)     ← direct upstream (most build logic comes from here)
        └── Eternal-Dash/GKI_KernelSU_SUSFS ← this fork (build-time patches + KPM adjustments)
```

---

## 1. What did we do?

1. **Three build-time patches for SukiSU's `builtin` branch** (the one with SUSFS baked in)
   - UAPI version alignment (`2` → `5`)
   - upstream compile error in `pkg_observer.c` (`TRACK_THRONE_FORCE_SYNCHRONOUS` is undefined)
   - external `_fn` symbol references in `selinux_hide.c` (link-time undefined symbols)
2. **Re-enabled and extended the KPM step** — upstream commented it out and, even when enabled, only set `CONFIG_KPM` without injecting the KernelPatch host. This fork restores the step for both `enabled` and `patched`, and rebuilds `Image.lz4` afterwards.
3. **Scoped the patches** — they only run for `SukiSU` + SUSFS enabled, are skippable via `clean_build`, and skip themselves when the upstream source no longer matches.
4. **Fixed two "silently wrong artifact" paths**
   - the pinned `sukisu` commit in `config/config` no longer applies when SUSFS is disabled
   - the `CONFIG_KPM` injection set now matches the set that actually injects the KernelPatch host (`SukiSU / BakaSU / Next`)

## 2. How the heck did we pull that off?

No kernel source is modified. Everything happens at build time, located by **actual source features**, and is **idempotent**:

| Patch | Located by | Idempotency | Safety net |
|:---|:---|:---|:---|
| UAPI version | parsing the real `KERNEL_SU_UAPI_VERSION` value | raise-only: never downgrades an upstream value ≥ 5 | re-parse after edit; mismatch aborts |
| `pkg_observer.c` | `grep` for the constant | skips if upstream already fixed it | aborts if the constant survives |
| `selinux_hide.c` | `grep _av_fn` + regex on the extern/if-else shape | skips if upstream switched to function pointers | aborts if `_av_fn` survives |
| `Image.lz4` | `command -v lz4` | always recompressed from the patched `Image` | decompress + `cmp` against `Image` |
| KPM output dir | probing which directory actually contains `Image` | no longer guesses by android/kernel combo | explicit error instead of silent continue |

## 3. So what does it actually get you?

- The `builtin` branch compiles without hand-editing sources.
- KPM has a real chance of working: `CONFIG_KPM` **and** the KernelPatch host are both present.
- `boot-lz4.img` is no longer silently different from `boot.img`.
- Other variants (Official / Next / BakaSU / legacy SukiSU) are untouched; unsupported KPM requests produce a clear warning.
- Upstream movement does not break the pipeline: patches self-disable, and every change is logged before/after.

## 4. So what's the catch?

1. **Symptom-level fix, not a real upstream fix.** If upstream changes file layout or symbol style, the patches silently disappear (by design) — check the build log.
2. **UAPI is a declared alignment.** UAPI 3 and 5 features exist in that commit, but **4 (`KSU_GET_INFO_FLAG_BUNDLED`) is not implemented**. A manager reading that flag per UAPI ≥ 4 gets 0; behaviour impact is untested.
3. **Pinned commits are technical debt.** Frozen for stability, but you miss later fixes, and a newer manager may expect a higher UAPI.
4. **KPM has no upstream endorsement.** Host injection comes from `SukiSU_patch/kpm/patch_linux`; stability and device compatibility are unverified at scale.
5. **Environment dependency** — `Image.lz4` is compressed in CI (`lz4 -l -12 --favor-decSpeed`, legacy frame) and verified by decompressing.
6. **Maintenance burden** — once upstream merges equivalent fixes, these patches should be deleted rather than kept.

## 5. Stuff you should [think hard] about

- Whether you actually need KPM — it is the biggest behavioural difference and the biggest risk.
- Keeping kernel / manager / SUSFS module versions matched.
- Which variant you pick: `SukiSU` = builtin SUSFS, `Official` = main + SUSFS patch, `Next` = dev_susfs, legacy SukiSU = its own pinned commit.
- `clean_build=true` skips all three patches — for A/B comparison only.
- This is **not** an official SukiSU / SUSFS / KernelSU build.

## 6. How do I build this thing?

1. Variant must be `SukiSU` **and** SUSFS must stay enabled, otherwise the three patches do not run (the log says why).
2. KPM only works on `SukiSU / BakaSU / Next`; elsewhere `CONFIG_KPM` is not written and a warning is emitted.
3. `custom=true` + `sukisu=<hash>` only applies with SUSFS enabled; never point it at a commit from another branch.
4. Signing secrets must exist; verify partition size assumptions before flashing.
5. **Read the log, not just "build succeeded"** — look for:
   `UAPI 已对齐到 5`, `已改用 track_throne(false)`, `已消除外部符号引用`,
   `Image 已注入 KernelPatch 宿主`, `Image.lz4 … 解压校验一致`.
6. Verify the artifacts (`boot.img` / `boot-gz.img` / `boot-lz4.img`) share the same kernel; if the log says the lz4 image was skipped, do not flash an old package.
7. Test on a recoverable device first, and keep a stock `boot` image for rollback.

## 7. License, credits, re-forking

- **GPL-2.0** (see [LICENSE](LICENSE)). This is a derivative work and must stay GPL-2.0.
- Copyright of kernel, SUSFS, KernelSU / SukiSU / KernelSU-Next and the upstream build scripts remains with their authors. This fork only claims its **build-pipeline adaptations**.
- File headers note `Eternal-Dash / 2026-10` changes, as required by GPL-2.0 §2(a). That is compliance, not a claim over upstream work — and nobody should rename someone else's project as their own either.
- Full list: [CREDITS.md](CREDITS.md).

**If you fork this repository:** keep `LICENSE`, `CREDITS.md` and this notice; describe your own changes in a separate section (what/why/how far it was verified); do not strip upstream attribution; and if you touch the KPM logic, update sections 4–6 so the risk description stays accurate.
