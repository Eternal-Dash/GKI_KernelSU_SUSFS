<div align="center">

# GKI KernelSU + SUSFS（Eternal-Dash Fork）

**本仓库是 [zzh20188/GKI_KernelSU_SUSFS](https://github.com/zzh20188/GKI_KernelSU_SUSFS) 的 fork，
只做「构建流程」层面的适配与修复，内核 / SUSFS / KernelSU 源码一律沿用上游。**

[English](README-EN.md) | 简体中文

</div>

---

## 0. 我去，这啥啊这是？

| | 说明 |
|:---|:---|
| **是什么** | 一个 GitHub Actions 自动构建 GKI 内核的工作流仓库，Fork 自 `zzh20188/GKI_KernelSU_SUSFS`，最上游为 `WildKernels/GKI_KernelSU_SUSFS` |
| **不是什么** | 不是内核源码仓库；不含任何自行开发的内核特性；不主张上游代码的著作权 |
| **改了什么** | 只有 `.github/workflows/build.yml`、`.github/workflows/main.yml`、`config/config` 三个文件（外加本说明与 `CREDITS.md`） |
| **谁改的** | Fork 维护者：**Eternal-Dash**（2026-10）。改动范围与时序见 [CREDITS.md](CREDITS.md) 与各文件头部注释 |

Fork 关系：

```
WildKernels/GKI_KernelSU_SUSFS  (main)      ← 最上游
  └── zzh20188/GKI_KernelSU_SUSFS (dev)     ← 本仓库的直接上游（绝大多数构建逻辑来自这里）
        └── Eternal-Dash/GKI_KernelSU_SUSFS ← 本 fork（只加构建期修补 + KPM 相关调整）
```

---

## 1. 我们干啥了

围绕「**让 SukiSU 的 builtin（内置 SUSFS）分支能正常编出可用的内核，并且 KPM 真的能加载**」这一件事，做了四件事：

1. **给 builtin 分支补三处构建期修补**
   - UAPI 版本号对齐（`2` → `5`）
   - `pkg_observer.c` 的上游编译错误（`TRACK_THRONE_FORCE_SYNCHRONOUS` 未定义）
   - `selinux_hide.c` 对外部 `_fn` 符号的引用（链接期 undefined symbol）

2. **恢复并扩展 KPM 步骤**
   上游把 KPM 步骤整段注释掉了，并且即使打开也只开 `CONFIG_KPM`、不做宿主注入。本 fork 恢复该步骤，允许 `enabled` / `patched` 两种取值都执行，并补上 `Image.lz4` 的重建。

3. **让修补「只打在该打的地方」**
   三处修补收敛到「SukiSU + 启用 SUSFS」这一种场景；`clean_build` 时可整体跳过；找不到上游特征就跳过而不是报错。

4. **修正两处会产出「假成功」产物的逻辑**
   - `config/config` 里固定的 sukisu 提交在「关闭 SUSFS」时原本也会生效 → 现在只在启用 SUSFS 时生效
   - `CONFIG_KPM` 的注入集合与「真正会注入 KernelPatch 宿主」的集合原本不一致 → 现在统一为 `SukiSU / BakaSU / Next`

---

## 2. ！？啥子方法做的？！

核心思路：**不改内核源码，只在构建流水线里、按上游源码的实际特征做幂等修补**。这样上游一改动，本仓库不需要跟着改代码，最坏情况是修补自动失效（并有自检兜底）。

| 修补 | 定位方式 | 幂等性 | 兜底 |
|:---|:---|:---|:---|
| UAPI 版本号 | 解析 `KERNEL_SU_UAPI_VERSION` 的实际数值 | 只升不降：已 ≥ 5 就原样保留，绝不把上游的 6 改回 5 | 改完再解析一遍，必须等于目标值，否则 `::error::` 中断 |
| `pkg_observer.c` | `grep` 常量名 | 上游已修复（无该常量）则整步跳过 | 若改完仍存在该常量 → 中断 |
| `selinux_hide.c` | `grep _av_fn` + 正则匹配 extern 与 if/else 结构 | 上游若已改成函数指针，正则不匹配 → 跳过 | 处理完仍残留 `_av_fn` → 中断 |
| `Image.lz4` | `command -v lz4` | 每次都用打过补丁的 `Image` 重新压缩 | 解压回来与 `Image` 逐字节比对（`cmp`），不一致 → 中断 |
| KPM 产物目录 | 探测「哪个目录里真的有 `Image`」 | 不依赖 android/kernel 组合猜路径 | 找不到 → 明确报错，不静默继续 |

KPM 的完整链路是：`CONFIG_KPM=y` → `patch_linux` 对 `Image` 注入 KernelPatch 宿主 → 用注入后的 `Image` 重建 `Image.lz4` → 打 boot 镜像。四步中任何一步缺失，产物就会变成「装了模块却加载不了」的内核，所以每一步都做了显式校验。

---

## 3. 能干啥玩意捏

- **builtin 分支能编过了**：三处上游问题都在构建期被消掉，不再需要手工改源码。
- **KPM 有了实际可能性**：`CONFIG_KPM` 与 KernelPatch 宿主同时存在，而不是只有前者。
- **lz4 镜像不再「偷偷降级」**：`boot-lz4.img` 的内核与 `boot.img` 一致，不会出现「刷 lz4 就没有 KPM」的隐形差异。
- **其他变体不被误伤**：Official / Next / BakaSU / 老版本 SukiSU 走各自原有路径；KPM 开关在不支持的变体上会被明确忽略并给出 warning。
- **上游更新时不会炸**：所有修补都是「有则改、无则跳过、改完自检」，上游修复后本仓库不需要追着改。
- **可审计**：每处修补都在工作流里留了「改前 / 改后」日志，构建记录里能直接看出有没有生效。

---

## 4. 那么，代价是什么呢？

诚实列出，请自行权衡：

1. **本质是「构建期打补丁」，不是真修复**
   问题在上游，这里是症状级处理。上游逻辑一变（例如把 `supercall.h` 改到别的路径、把 extern 换成函数指针），修补会失效——本仓库设计成「失效即跳过」，于是可能悄悄退回未修补状态，需要看构建日志确认。

2. **UAPI 是「声明式对齐」，存在语义风险**
   把内核自报的 UAPI 改成 5，等于告诉管理器「我支持 UAPI 5 的接口」。实际上 3 和 5 的能力在该提交里确实存在，但 **4（`KSU_GET_INFO_FLAG_BUNDLED`）并未实现**。管理器若按 UAPI ≥ 4 去读 BUNDLED 标志位，会读到 0，理论上可能影响它判断「内建内核 / LKM 内核」的方式。这属于「未实测」范围。

3. **版本被钉死，容易变成技术债**
   `config/config` 钉在 builtin 的 v4.2.1 提交上，原因之一是更晚的提交引入了动态管理器且带编译错误。钉住换来稳定，代价是拿不到后续修复，且管理器一旦升级到更高 UAPI，可能出现「内核 5 / 管理器要 6」的错配。

4. **KPM 部分无上游背书**
   KPM 的宿主注入来自 `SukiSU_patch/kpm/patch_linux`，本仓库只是把它接回流水线。稳定性、与各机型 bootloader 的兼容性、以及对内核的副作用，都**未经上游验证**，也没有大规模实测。

5. **产物一致性依赖环境**
   `Image.lz4` 由 CI 里的 `lz4` 重新压缩（legacy 帧、`-12 --favor-decSpeed`）。参数与 GKI 构建一致，且做了解压比对，但如果某天 runner 上的 `lz4` 版本行为变化，仍需以校验结果为准。

6. **维护成本落在 fork 维护者身上**
   上游合并了同类修复后，这里的代码应当被删除而不是保留，否则会出现「两边各改一次」的重叠维护。

---

## 5. 需要你使用[深度思考]的点

- **是否值得开 KPM**：它是本 fork 与上游最大的行为差异，也是风险最集中的地方。只在内核与模块版本严格匹配、且愿意承担「刷了可能不开机」的前提下再开。
- **管理器版本必须与内核一致**：内核对 UAPI 的声明、管理器对 UAPI 的期待、SUSFS 模块版本，三者错一个就可能出现「能连上但功能异常」。
- **变体选择影响一切**：`SukiSU` 走 builtin（内置 SUSFS）；`Official` 走 main 并由 SUSFS 补丁注入；`Next` 走 dev_susfs；老版本 SukiSU 走各自的固定提交。四者的 UAPI、SUSFS 形态、KPM 能力都不同，别混着看文档。
- **`clean_build=true` 会跳过三处修补**：它只用于「对比纯上游源码」的场景，日常构建不要开。
- **不要把它当作「官方支持」**：本 fork 不是 SukiSU / SUSFS / KernelSU 官方产物，上游不为其负责。

---

## 6. 这玩意咋整？

按流水线顺序的检查清单：

1. **变体 + 模式**：选 `SukiSU` 且未禁用 SUSFS 才会命中 builtin 与三处修补；这两个条件缺一个，修补步骤不会执行（日志里会明确写跳过原因）。
2. **KPM 开关**：只有 `SukiSU / BakaSU / Next` 会真正注入宿主。其余变体下即使选了 `enabled`，也只会收到一条 warning，`CONFIG_KPM` 不会写入。
3. **`config/config`**：`custom=true` 时 `sukisu=` 的提交只在启用 SUSFS 时生效；把提交改成别的分支的 hash 会直接导致源码结构不匹配。
4. **签名密钥**：`BOOT_SIGN_KEY_PATH` 相关 secrets 必须齐全，否则 AVB 签名阶段失败；刷入前务必与机型分区大小核对（脚本里按 64MB 分区处理）。
5. **看日志，不要只看「构建成功」**：重点确认这几行
   - `OK: UAPI 已对齐到 5` / `保持上游原值不动`
   - `OK: 已改用 track_throne(false)`
   - `OK: 已消除外部符号引用`
   - `OK: Image 已注入 KernelPatch 宿主`
   - `OK: Image.lz4 已由打过补丁的 Image 重建，解压校验一致`
6. **验收产物再刷机**：`boot.img`、`boot-gz.img`、`boot-lz4.img` 三者内核应当一致；AnyKernel3 包内只有 `Image`。若日志里出现「缺少 lz4，跳过 boot-lz4.img」，说明这次没有 lz4 镜像，不要误拿旧包刷。
7. **先在非主力机 / 可救砖环境验证**：KPM 宿主注入会改变 `Image` 结构，失败表现为不开机或进 fastboot，准备好救砖手段再上。
8. **回滚路径**：保留原厂 / 上一版 `boot` 分区镜像，确认能进系统后再长期使用。

---

## 7. 许可、致谢与二次 Fork

- **许可证**：GPL-2.0（见 [LICENSE](LICENSE)）。本仓库是衍生作品，**必须继续以 GPL-2.0 分发**。
- **版权归属**：内核、SUSFS（simonpunk/susfs4ksu）、KernelSU / SukiSU / KernelSU-Next、以及构建脚本的上游部分，版权归各自作者。本 fork **只对「构建流程适配」这一小部分主张自己的改动**，不主张上游任何代码的著作权。
- **署名原则**：GPL-2.0 第 2 条 a 款要求「修改过的文件标注修改人与日期」——所以本仓库在各文件头部标注了 `Eternal-Dash / 2026-10` 的改动说明。这属于合规标注，不是把上游成果据为己有；同理，**fork 后也不应把别人的项目整体改名为自己的项目**。
- **完整致谢列表**：[CREDITS.md](CREDITS.md)。

**如果你要再 fork 本仓库，请：**

1. 保留 `LICENSE`、`CREDITS.md` 与本段说明；
2. 把你自己的改动单独写一节（改了什么、为什么、验证到什么程度）；
3. 不要删除上游署名，也不要把上游的说明文档整段复制成「原创」；
4. 若你改了 KPM 相关逻辑，请一并更新第 4、5、6 节的风险描述，别让后来者按旧文档操作。

---

<div align="center">

**本 fork 的所有改动都属于「适配与修复」，稳定性以你自己机型上的实测为准。**

上游文档、教程与 Wiki 仍然有效，见 [zzh20188/GKI_KernelSU_SUSFS](https://github.com/zzh20188/GKI_KernelSU_SUSFS/wiki)。

</div>
