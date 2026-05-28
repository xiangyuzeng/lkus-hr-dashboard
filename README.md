# 瑞幸咖啡北美 · 人事系统数据分析仪表盘

> 内部数据分析仪表盘 — 涵盖两项 HR 数据需求
> 数据时段：2025-05-27 至 2026-05-27

## 简介

本仪表盘整合两项数据分析需求 (均已完成)：

| 需求 | 内容 | 状态 |
|---|---|---|
| 需求一 | 2026-01-01 至 2026-05-27 SM 职位变更人员清单 | ✅ 已完成 (8 人) |
| 需求二 | 2025-05-27 至 2026-05-27 LSO 各等级资质获取周期分析 | ✅ 已完成 (210 人, 372 张证书) |
| 加值 | 数据闭环 · LSO 资质 × SM 晋升 交叉分析 | ✅ 已完成 |

单文件静态 HTML 仪表盘，数据已内嵌，无需后端 / API / 构建步骤。

## 部署到 Vercel

### 方式 A：拖拽部署 (最快)
1. 打开 https://vercel.com/new
2. 把整个文件夹拖入浏览器窗口
3. Framework Preset 选 **Other**
4. Build & Output Settings 全部留空
5. 点击 Deploy → ~10 秒获得线上 URL

### 方式 B：Vercel CLI
```bash
npm i -g vercel
cd lkus-hr-dashboard
vercel --prod
```

### 方式 C：GitHub 自动部署
```bash
git init && git add . && git commit -m "v1.1 — both requests complete + closed-loop"
gh repo create lkus-hr-dashboard --private --source=. --push
```

## 访问密码

进入仪表盘前需输入密码：**`luckin2026`**

(客户端 sessionStorage 鉴权，非真正安全边界。如需真正保护，启用 Vercel Pro 的 Password Protection 或挂 Cloudflare Access。)

## 文件结构

```
lkus-hr-dashboard/
├── index.html          ← 单页应用，含两项数据内嵌，约 244 KB
├── vercel.json         ← Vercel 配置
└── README.md           ← 本文件
```

## 仪表盘内容

| 章节 | 内容 |
|---|---|
| Hero + 需求概览 | 两项需求状态卡片 (均已完成) |
| 一、SM 职位变更 | KPI · 8 人清单 · 月度分布 · 入职至升任 · 来源职位 100% SMT |
| ★ 数据闭环 | LSO400 → SM 中位 6 天 · 18 人全通道队列流向追踪 |
| 二、LSO 资质获取 | KPI · 6 项核心发现 (含闭环发现) |
| 三、培训管线漏斗 | 203 → 105 → 40 → 24 自定义 SVG |
| 四、各等级周期分布 | LSO100/200/300/400 卡片 + 频次直方图 |
| 五、全通道队列复盘 | 18 人时间轴可视化 + 段间天数统计 |
| 六、流失与持证模式 | 4 级流失率条形图 + 7 类持证模式分布 |
| 七、门店与岗位分布 | Top 15 门店 + 当前职位持证透视 |
| 八、异常与离群 | Daniel Chu / Jocelyn Lopez 详情 + 培训阻塞 Top 5 |
| 九、行动建议 | 短期 / 中期 / 长期建议 + 数据治理 |
| 十、全量数据 | 372 行可搜索、可筛选明细表 |

## 配套交付件

| 编号 | 类型 | 用途 |
|---|---|---|
| LCNA-HR-LSO-2026-001 | docx | LSO 正式分析报告 |
| LCNA-HR-LSO-2026-002 | xlsx | LSO 明细工作簿 (9 个工作表) |
| 本仪表盘 | html | 交互仪表盘 (含 SM + LSO + 闭环) |

## 配置

修改访问密码：
```javascript
// index.html 约 700 行处:
const PW = 'luckin2026';  // ← 改这里
```

修改主题色：编辑 `index.html` 顶部 `:root` CSS 变量。

---

© 2026 Luckin Coffee North America · 数据库运营组 · 仅供内部使用
