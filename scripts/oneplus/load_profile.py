#!/usr/bin/env python3
"""加载 data/devices/<profile>.json，输出可直接追加到 $GITHUB_ENV 的键值对。

设计原则：
  * 只用标准库，任何 runner 都能跑；
  * 缺字段一律给保守默认值，不做隐式降级（宁可显式报错）；
  * 所有路径基于 $GITHUB_WORKSPACE 推导，不写死绝对路径。

用法：
    python3 scripts/oneplus/load_profile.py <profile_id> >> "$GITHUB_ENV"
"""
import json
import os
import sys

WS = os.environ.get("GITHUB_WORKSPACE", os.getcwd())

REQUIRED = ("id", "source_type", "android_version", "kernel_version")


def die(msg):
    print(f"::error::load_profile: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        die("缺少 profile 名称")

    pid = sys.argv[1].strip()
    path = os.path.join(WS, "data", "devices", f"{pid}.json")
    if not os.path.isfile(path):
        die(f"找不到设备配置 {path}")

    with open(path, encoding="utf-8") as f:
        p = json.load(f)

    for key in REQUIRED:
        if not p.get(key):
            die(f"{path} 缺少必填字段 {key}")

    manifest = p.get("manifest") or {}
    repos = manifest.get("repos") or []
    if p["source_type"] == "oplus" and not (repos and manifest.get("branch") and manifest.get("file")):
        die("source_type=oplus 需要 manifest.repos / branch / file")

    pack = p.get("pack") or {}
    android = p["android_version"]
    kernel = p["kernel_version"]
    sub = str(p.get("sub_level") or "0")
    patch = str(p.get("os_patch_level") or "2026-01")

    sync_root = os.path.join(WS, f"{p['source_type']}-{pid}")
    # 官方 manifest 把 kernel_platform/ 铺在同步根目录下，构建入口统一在 kernel_platform
    kernel_root = os.path.join(sync_root, "kernel_platform")
    config = f"{android}-{kernel}.{sub}"

    kv = {
        "DEVICE_PROFILE": pid,
        "DEVICE_NAME": p.get("display_name") or pid,
        "SOURCE_TYPE": p["source_type"],
        "PROFILE_ANDROID_VERSION": android,
        "PROFILE_KERNEL_VERSION": kernel,
        "PROFILE_SUB_LEVEL": sub,
        "PROFILE_OS_PATCH_LEVEL": patch,
        "KERNEL_SYNC_ROOT": sync_root,
        "KERNEL_ROOT": kernel_root,
        "CONFIG": config,
        "DEFCONFIG": os.path.join(kernel_root, "common/arch/arm64/configs/gki_defconfig"),
        "PLATFORM": p.get("platform") or "",
        "SUSFS_KMI": p.get("susfs_kmi") or android,
        "BUILD_METHOD": p.get("build_method") or "perf",
        "BUILD_CMD": p.get("build_cmd") or "",
        "MANIFEST_REPOS": " ".join(repos),
        "MANIFEST_BRANCH": manifest.get("branch") or "",
        "MANIFEST_FILE": manifest.get("file") or "",
        "LOCALVERSION_MODE": p.get("localversion_mode") or "keep",
        "EXPECT_VERMAGIC": p.get("expect_vermagic") or "",
        "VERMAGIC_STRICT": "true" if p.get("vermagic_strict") else "false",
        "PACK_MODE": pack.get("mode") or "anykernel",
        "AK3_BLOCK": pack.get("block") or "boot",
        "AK3_DO_MODULES": str(pack.get("do_modules", "0")),
        "AK3_DEVICECHECK": str(pack.get("devicecheck", "0")),
        "PROFILE_KSU_VARIANTS": ",".join(p.get("ksu_variants") or []),
    }
    for k, v in kv.items():
        print(f"{k}={v}")

    # 人类可读摘要走 stderr，避免污染 $GITHUB_ENV
    print(f"设备: {kv['DEVICE_NAME']} ({pid})", file=sys.stderr)
    print(f"源码: {p['source_type']} / {manifest.get('branch','-')} / {manifest.get('file','-')}", file=sys.stderr)
    print(f"构建: {kv['BUILD_CMD'] or '(AOSP bazel)'}", file=sys.stderr)
    print(f"版本串: {kv['LOCALVERSION_MODE']} 期望 {kv['EXPECT_VERMAGIC'] or '-'}", file=sys.stderr)


if __name__ == "__main__":
    main()
