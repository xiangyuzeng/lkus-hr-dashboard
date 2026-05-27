# 瑞幸咖啡北美 · 人事系统数据分析仪表盘

> 内部数据分析仪表盘 — 涵盖两项 HR 数据需求
> 数据时段：2025-05-27 至 2026-05-27

## 简介

本仪表盘整合两项数据分析需求：

| 需求 | 内容 | 状态 |
|---|---|---|
| 需求一 | 2026-01-01 至 2026-05-27 SM 职位变更人员清单 | 数据待提取 |
| 需求二 | 2025-05-27 至 2026-05-27 LSO 各等级资质获取周期分析 | 已完成 |

单文件静态 HTML 仪表盘，数据已内嵌，无需后端 / API / 构建步骤。直接拖入 Vercel 即可上线。

## 部署到 Vercel

### 方式 A：拖拽部署（最快）

1. 打开 https://vercel.com/new
2. 把整个文件夹拖入浏览器窗口
3. Framework Preset 选择 **Other**
4. Build & Output Settings 全部留空
5. 点击 Deploy
6. ~10 秒后获得线上 URL

### 方式 B：Vercel CLI

```bash
npm i -g vercel
cd lkus-hr-dashboard
vercel --prod
```

### 方式 C：GitHub 自动部署

```bash
git init
git add .
git commit -m "v1.0 — initial dashboard"
gh repo create lkus-hr-dashboard --private --source=. --push
# 然后在 vercel.com 连接仓库，后续 push 自动部署
```

## 本地预览

```bash
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000
```

或直接双击 `index.html` 用浏览器打开。

## 访问密码

进入仪表盘前需要输入密码：**`luckin2026`**

密码在客户端 JavaScript 中校验，**不是真正的安全边界**——拿到部署 URL 的人查看页面源码即可绕过。如需真正的访问控制：
- Vercel Pro / Enterprise 套餐 → Project Settings → Password Protection
- 或部署后挂在 Cloudflare Access 后面

## 文件结构

```
lkus-hr-dashboard/
├── index.html          ← 单页应用，含内嵌数据，约 220 KB
├── vercel.json         ← Vercel 配置（安全头、缓存）
└── README.md           ← 本文件
```

## 仪表盘内容

| 章节 | 内容 |
|---|---|
| Hero + 需求概览 | 两项需求卡片，时间窗口、数据路径、状态 |
| 一、SM 职位变更 | 数据提取方案 + 数据回填占位结构 |
| 二、LSO 资质获取 | KPI（210 / 372 / 18 / 4）+ 6 项核心发现 |
| 三、培训管线漏斗 | 自定义 SVG 漏斗图 + 环比留存率表 |
| 三段发现条 | 暗底卡片，核心结论提炼 |
| 四、各等级周期分布 | LSO100/200/300/400 卡片 + 频次直方图 |
| 五、全通道队列复盘 | 18 人时间轴可视化 + 段间天数统计 |
| 六、流失与持证模式 | 4 级流失率条形图 + 7 类持证模式分布 |
| 七、门店与岗位分布 | Top 15 门店 + 当前职位持证透视 |
| 八、异常与离群 | Daniel Chu / Jocelyn Lopez 详情 + 培训阻塞 Top 5 |
| 九、行动建议 | 短期 / 中期 / 长期建议 + 数据治理 |
| 十、全量数据 | 372 行可搜索、可筛选明细表 |

## 需求一数据回填工作流

需求一目前处于 **数据待提取** 状态。回填步骤：

1. 在 Claude Code 终端运行配套的提取脚本：
   ```bash
   claude --dangerously-skip-permissions -p "$(cat iadmin_sm_promotion_query_prompt.md)"
   ```
2. 得到 `iadmin_sm_promotions_2026H1.csv` 和 `iadmin_sm_promotions_2026H1_summary.md`
3. 把 CSV 数据填入仪表盘 `index.html` 中需求一的 KPI 占位符与表格结构（搜索 "数据回填后将呈现" 锚点）
4. 重新部署：`vercel --prod`

## 需求二数据刷新工作流

如需用新的 LSO 数据替换：

1. 重新跑 LSO 数据提取脚本（配套 `iadmin_lso_days_extraction_prompt.md`）
2. 把新的 5 个 CSV 文件放进 `_source/` 目录
3. 跑两条命令重新生成：
   ```bash
   python3 _source/build_data.py --source-dir _source --output _source/data.json
   python3 _source/build_html.py
   ```
4. 重新部署：`vercel --prod`

## 配套交付件

| 编号 | 类型 | 用途 |
|---|---|---|
| LCNA-HR-LSO-2026-001 | docx | 正式分析报告 — HR / 培训委员会评审 |
| LCNA-HR-LSO-2026-002 | xlsx | 明细工作簿 — HR 个案跟进（9 个工作表） |
| **本仪表盘** | **html** | **交互仪表盘 — 共享分析参考** |

## 技术备注

- **零构建步骤** — 单 HTML 文件含内嵌 CSS/JS 与 JSON 数据
- **无外部依赖**，仅 Google Fonts (Noto Sans SC, IBM Plex Mono)
- **响应式** — 支持到 380px 视口
- **打印友好** — `@media print` 隐藏导航与筛选器
- **仅 sessionStorage 鉴权** — 无 cookie、无埋点
- **数据量** — 372 行约 220 KB；扩展至数千行仍稳定

## 配置

修改访问密码：

```javascript
// index.html 约 700 行处:
const PW = 'luckin2026';  // ← 改这里
```

修改主题色：编辑 `index.html` 顶部 `:root` CSS 变量。

---

© 2026 Luckin Coffee North America · 数据库运营组 · 仅供内部使用
