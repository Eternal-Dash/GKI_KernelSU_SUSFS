#!/usr/bin/env python3
"""加载 data/devices/<profile>.json，按需输出三种格式。

    --format=github   → 裸值，直接追加到 $GITHUB_ENV（GitHub 不解释引号）
    --format=shell    → shlex 转义，可被 `set -a; . file; set +a` 安全 source
    --format=outputs  → 仅四个版本字段 + vermagic，直接追加到 $GITHUB_OUTPUT

为什么要分 github / shell 两种：
    DEVICE_NAME 之类的值带空格和括号（如 "一加 Ace 6 (PLQ110 / ktm)"），
    裸值写进 $GITHUB_ENV 是对的，但拿去 source 会被 shell 当成命令执行；
    反过来 shlex.quote 的结果写进 $GITHUB_ENV 又会把引号带进变量值。

不要在 workflow 里用 `python3 <<'PY'` 内联多行脚本：YAML 块标量会统一去掉缩进，
一旦内联代码的缩进与块缩进不一致，就会出现 IndentationError 或 heredoc 不闭合。
"""
import json
import os
import re
import shlex
import sys

WS = os.environ.get("GITHUB_WORKSPACE", os.getcwd())

REQUIRED = ("id", "source_type", "android_version", "kernel_version")


def die(msg):
    print(f"::error::load_profile: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    args = []
    fmt = "github"
    variant = ""
    kernel_version_input = ""
    firmware_input = ""
    for a in sys.argv[1:]:
        if a.startswith("--format="):
            fmt = a.split("=", 1)[1].strip()
        elif a.startswith("--variant="):
            variant = a.split("=", 1)[1].strip()
        elif a.startswith("--kernel-version="):
            kernel_version_input = a.split("=", 1)[1].strip()
        elif a.startswith("--firmware="):
            firmware_input = a.split("=", 1)[1].strip()
        else:
            args.append(a)

    if fmt not in ("github", "shell", "outputs"):
        die(f"未知输出格式 {fmt}")
    if not args or not args[0].strip():
        die("缺少 profile 名称")

    pid = args[0].strip()
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
    expect_v = p.get("expect_vermagic") or ""

    # 内核版本选择：kernel_variants 里的一项覆盖 sub_level / os_patch_level / expect_vermagic
    variants = p.get("kernel_variants") or {}
    vkey = variant or "default"
    if variants:
        if vkey not in variants:
            die(f"未知 kernel_variant={vkey}，可选: {', '.join(variants.keys())}")
        v = variants[vkey] or {}
        sub = str(v.get("sub_level", sub))
        patch = str(v.get("os_patch_level", patch))
        expect_v = v.get("expect_vermagic", expect_v) or expect_v
        print(f"内核版本: {vkey} -> {kernel}.{sub} / {patch} / {expect_v or '(未指定)'}", file=sys.stderr)

    # 版本选择：--firmware=PLQ110_16.0.9.401 或 --kernel-version=6.6.89
    # 通过 firmware_map 解析到三个仓库的真实 commit，repo sync 后再 checkout，
    # 这样才是"真正按这个版本编译"，而不只是改个名字。
    expect_prefix = ""
    rev_common = rev_msm = rev_modules = ""
    resolved_fw = ""

    fmap = p.get("firmware_map") or {}
    if firmware_input or kernel_version_input:
        if firmware_input:
            if firmware_input not in fmap:
                die(f"未知固件 {firmware_input}，可选: {', '.join(fmap.keys())}")
            resolved_fw = firmware_input
        else:
            m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", kernel_version_input)
            if not m:
                die(f"kernel_version 格式应为 X.Y.Z（如 6.6.89），收到 {kernel_version_input}")
            if f"{m.group(1)}.{m.group(2)}" != kernel:
                die(f"版本 {kernel_version_input} 与设备配置的 {kernel} 不一致")
            cands = [fw for fw, v in fmap.items() if v.get("kernel_version") == kernel_version_input]
            if not cands:
                avail = sorted({v.get("kernel_version") for v in fmap.values() if v.get("kernel_version")})
                die(f"官方源码历史里没有内核 {kernel_version_input}，可用: {', '.join(avail)}")
            resolved_fw = cands[0]          # firmware_map 已按新到旧排序

        info = fmap[resolved_fw]
        rev_common = info.get("common") or ""
        rev_msm = info.get("msm") or ""
        rev_modules = info.get("modules") or ""
        if info.get("kernel_version"):
            kv = info["kernel_version"]
            sub = kv.split(".")[2]
            expect_prefix = f"{kv}-"
        print(f"版本解析: {resolved_fw} -> 内核 {info.get('kernel_version')}", file=sys.stderr)
        print(f"  common={rev_common[:10]} msm={rev_msm[:10]} modules={rev_modules[:10]}", file=sys.stderr)

        # 安全补丁级别仍按子版本号查表
        kmidir = os.path.join(WS, "data", p.get("susfs_kmi") or android)
        jf = os.path.join(kmidir, f"{kernel}.json")
        if os.path.isfile(jf):
            try:
                for e in json.load(open(jf, encoding="utf-8")).get("entries", []):
                    if str(e.get("kernel")) == f"{kernel}.{sub}":
                        patch = str(e.get("date") or patch)
                        break
            except Exception:
                pass
        expect_v = ""

    sync_root = os.path.join(WS, f"{p['source_type']}-{pid}")
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
        "BUILD_ENGINE": p.get("build_engine") or "oplus",
        "BUILD_CMD": p.get("build_cmd") or "",
        "MANIFEST_REPOS": " ".join(repos),
        "MANIFEST_BRANCH": manifest.get("branch") or "",
        "MANIFEST_FILE": manifest.get("file") or "",
        "LOCALVERSION_MODE": p.get("localversion_mode") or "keep",
        "EXPECT_VERMAGIC": expect_v,
        "EXPECT_PREFIX": expect_prefix,
        "REQUESTED_KERNEL_VERSION": kernel_version_input,
        "RESOLVED_FIRMWARE": resolved_fw,
        "REV_COMMON": rev_common,
        "REV_MSM": rev_msm,
        "REV_MODULES": rev_modules,
        "VERMAGIC_STRICT": "true" if (p.get("vermagic_strict") or kernel_version_input or firmware_input) else "false",
        "PACK_MODE": pack.get("mode") or "anykernel",
        "AK3_BLOCK": pack.get("block") or "boot",
        "AK3_DO_MODULES": str(pack.get("do_modules", "0")),
        "AK3_DEVICECHECK": str(pack.get("devicecheck", "0")),
        "PROFILE_KSU_VARIANTS": ",".join(p.get("ksu_variants") or []),
    }

    if fmt == "outputs":
        for src_key, out_key in (
            ("PROFILE_ANDROID_VERSION", "android_version"),
            ("PROFILE_KERNEL_VERSION", "kernel_version"),
            ("PROFILE_SUB_LEVEL", "sub_level"),
            ("PROFILE_OS_PATCH_LEVEL", "os_patch_level"),
            ("EXPECT_VERMAGIC", "expect_vermagic"),
            ("EXPECT_PREFIX", "expect_prefix"),
            ("REQUESTED_KERNEL_VERSION", "requested_kernel_version"),
        ):
            print(f"{out_key}={kv[src_key]}")
    else:
        for k, v in kv.items():
            print(f"{k}={shlex.quote(v) if fmt == 'shell' else v}")

    print(f"设备: {kv['DEVICE_NAME']} ({pid})", file=sys.stderr)
    print(f"源码: {p['source_type']} / {manifest.get('branch','-')} / {manifest.get('file','-')}", file=sys.stderr)
    print(f"构建: {kv['BUILD_CMD'] or '(AOSP bazel)'}", file=sys.stderr)
    print(f"版本串: {kv['LOCALVERSION_MODE']} 期望 {kv['EXPECT_VERMAGIC'] or '-'}", file=sys.stderr)


if __name__ == "__main__":
    main()
