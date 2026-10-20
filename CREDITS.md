# 致谢与改动记录 / Credits & Change Log

本仓库是 GKI 内核构建流水线的 **fork**。以下内容用于说明「哪些是上游的、哪些是本 fork 的」，
既是致谢，也是 GPL-2.0 第 2 条 a 款所要求的修改声明。

---

## 1. 上游与依赖

| 项目 | 角色 | 地址 |
|:---|:---|:---|
| **WildKernels/GKI_KernelSU_SUSFS** | 最上游（原始项目） | https://github.com/WildKernels/GKI_KernelSU_SUSFS |
| **zzh20188/GKI_KernelSU_SUSFS** | 本仓库的直接上游：大量构建流程、脚本、网页、SUSFS 集成补丁均来自此项目 | https://github.com/zzh20188/GKI_KernelSU_SUSFS |
| **SukiSU-Ultra/SukiSU-Ultra** | KernelSU 系内核代码（`builtin` 分支内置 SUSFS） | https://github.com/SukiSU-Ultra/SukiSU-Ultra |
| **SukiSU-Ultra/SukiSU_patch** | KPM 宿主注入程序 `kpm/patch_linux` 等 | https://github.com/SukiSU-Ultra/SukiSU_patch |
| **simonpunk/susfs4ksu** | SUSFS 内核补丁 | https://gitlab.com/simonpunk/susfs4ksu |
| **KernelSU-Next / Baka-SU / tiann/KernelSU** | 其他 KSU 变体 | 各自仓库 |
| **maxsteeel/nomount** | NoMount 挂载元模块 | https://github.com/maxsteeel/nomount |

上述项目的版权归各自作者所有。本 fork **不主张**以上任何代码的著作权。

---

## 2. 本 fork 的改动（仅构建流程）

**修改者**：Eternal-Dash — https://github.com/Eternal-Dash
**时间**：2026-10-15 ~ 2026-10-20
**范围**：`.github/workflows/build.yml`、`.github/workflows/main.yml`、`config/config`、`README*.md`、`CREDITS.md`

| 文件 | 改动 |
|:---|:---|
| `build.yml` | 新增三处 SukiSU `builtin` 分支的构建期修补：UAPI 版本号对齐、`pkg_observer.c` 编译错误、`selinux_hide.c` 外部 `_fn` 符号引用 |
| `build.yml` | 恢复并扩展 KPM 步骤（`enabled` / `patched`），补 `Image` 产物探测、`oImage` 校验、`Image.lz4` 重建与解压自检 |
| `build.yml` | 三处修补收敛到 `KSU_BUILTIN_SUSFS=true`（SukiSU + 启用 SUSFS）场景；新增 `clean_build` 输入用于跳过修补 |
| `build.yml` | `config/config` 中 `sukisu` 固定提交仅在启用 SUSFS 时生效；`CONFIG_KPM` 注入集合与 KernelPatch 宿主注入集合统一为 `SukiSU / BakaSU / Next` |
| `build.yml` | `boot-lz4.img` 相关步骤增加「`Image.lz4` 是否存在」判断，避免发出未含 KPM 的 lz4 镜像 |
| `main.yml` | KPM 状态文案与实际行为对齐（支持集合判定、`enabled`/`patched` 等效、未实测标注） |
| `config/config` | 补齐注释，说明 `custom` / `sukisu` 的生效条件与钉死提交的原因 |
| `README*.md` | 重写为 fork 说明：改动、手法、收益、弊端、风险与构建注意事项 |

### 各修补的时序（便于日后删除）

| 修补 | 上游修复后的处理 |
|:---|:---|
| UAPI 版本号 | 上游给到 ≥ 5 时本步自动跳过，届时可整段删除 |
| `pkg_observer.c` | 上游改用 `track_throne(false)` 后本步自动跳过，可删除 |
| `selinux_hide.c` | 上游改为函数指针方式后本步自动跳过，可删除 |
| KPM 步骤 | 若上游正式支持 KPM，应以官方实现为准并删除本 fork 的扩展条件 |
| `Image.lz4` 重建 | 若上游 KPM 步骤自带重建，可删除本段 |

---

## 3. 署名原则（给再 fork 的人）

- **可以**：在文件头部标注你自己的修改人与日期；在 README 中单列「本 fork 的改动」章节；为自己的适配代码声明版权。
- **不建议**：把上游项目整体改名为自己的项目、删除上游 README 与致谢、把上游文档描述成自己的原创。
- **必须**：保留 `LICENSE`（GPL-2.0）与上游署名，衍生作品继续以 GPL-2.0 分发。

> 说明：GitHub 上「完全一致的 fork 不宜另加作者署名」的本意是——**没有实际改动时，不应把别人的成果署成自己的**。
> 本仓库存在实质性修改，因此按 GPL-2.0 的要求标注改动人，既不违规，也不构成对上游著作权的侵占。
