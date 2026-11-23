# lewitt

> *"The idea becomes a machine that makes the art."* — Sol LeWitt

**`lewitt`** 是一个 agent skill：给一个网址，反推出**有证据支撑的 Design DNA**、一个**零依赖的交互预览页**，以及 AI 写代码时必须遵守的**可执行 guardrail**。

只给 AI hex 和字号，它就会产出模板化的东西。品味不是规格表，而是**取舍与克制**。名字取自观念艺术家 Sol LeWitt —— 他的墙面绘画由一份精确的书面指令执行；`lewitt` 提取的是"为什么长这样"，并把网站**拒绝做什么**编码成约束，在你动手写界面时强制检查。

![stripe.com 的交互预览：实时色板、证据 id、token 分层](docs/preview.png)

## 三条铁律

- **R1 证据不降级**：在隔离的浏览器上下文里抓渲染后的 DOM、计算样式与截图（Playwright，经 CDP 求值）。每条结论都标 `Observed` / `Inferred` / `Proposed` / `Unknown`，截图估测绝不冒充实测 CSS。
- **R2 品味 = 取舍 + 代码 guardrail**：测量先压成结构模式，再提炼成「选 A 弃 B」。每条 **Restraint** 原则都带机器可读的 guardrail（禁用 CSS 属性、Tailwind v3/v4 类名模式、数值上限），由 linter 检查，而不是写在文档里自说自话。
- **R3 单一真源**：`dna.json` 是唯一手写的文件。`taste.md`、`tokens.css`、`tokens.resolved.json`、`agent-rules.md`、`preview.html` 都由它确定性渲染（约 33ms），并做逐字节漂移比对。
- **诚实的验收**：视觉保真度记录在 `fidelity.json`（`unverified` / `PARTIAL` / `PASS`），偏差逐条写明，绝不悄悄宣称 1:1 还原。

## 两种模式

**1. DNA 模式（默认，1–2 分钟）**：抓 1 个首页 + 最多 3 个代表性子页，输出 `preview.html`（单文件、无远程资源、与 `tokens.css` 同源：实时色板、字阶/圆角/阴影样例、可点击的动效回放、Taste DNA 卡片、源站截图、一键下载栏）、`agent-rules.md`（MUST NOT 硬约束置顶，token 按 Semantic → Component → Primitive 排列）、`taste.md`、`tokens.css`、`tokens.resolved.json`、`VERIFY.md`。

**2. 完整模式（`--full`）**：额外生成可运行的 `system/` 参考站，页面底色取自源站自己的 canvas token（不会把深色文档主题硬套到浅色系统上）：组件解剖与状态矩阵、用同一套 token 拼出的真实组合（Hero / Pricing / Checkout）、5 个压力测试开关、与源站并排的保真度对照。

![保真度对照：左为抓取的源站，右为用 token 重建的 Hero](docs/fidelity.png)

## 产物结构

```text
{dest}/{domain}/
├── dna.json               # 唯一真源（evidence / measurements / patterns / taste / tokens）
├── preview.html           # 零依赖交互预览
├── taste.md / agent-rules.md / tokens.css / tokens.resolved.json
├── VERIFY.md / verify.json
├── fidelity.json          # --full：一致项与偏差项
├── capture/               # 原始 DOM 快照与视口截图
└── system/                # --full：可运行的参考站
```

仓库内附带三个样例：`runs/stripe.com/`（完整模式）、`runs/linear.app/`、`runs/binance.com/`。

## 安装

```sh
git clone https://github.com/CClishan/lewitt-skill.git ~/Projects/skills/lewitt
ln -s ~/Projects/skills/lewitt ~/.codex/skills/lewitt
ln -s ~/Projects/skills/lewitt ~/.claude/skills/lewitt
cd ~/Projects/skills/lewitt && bash scripts/setup.sh
```

## 用 guardrail 检查你自己的代码

```sh
python3 scripts/lint_output.py --dest runs/stripe.com --check-code ./src
```

例：Linear 的「层次靠 1px 细线，不靠阴影」会拦下 `shadow-lg` 和任何带位移/模糊的 `box-shadow`；Stripe 的「颜色一页只用一次」会拦下 `bg-gradient-to-*` 和 Tailwind v4 的 `bg-linear-to-*`。

## 致谢

推理链（Measure → Pattern → Taste）与反 slop 词表来自 [`taste-skill`](https://github.com/senlindesign/taste-skill)（MIT，Senlin）；证据台账、token 分层与验收表来自 [`website-design-system`](https://github.com/DiqingWWW/Web-Design-System-Skill)（DiqingWWW）。`lewitt` 是两者的合体。

## License

MIT
