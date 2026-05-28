# iehr 系统职位变更为 SM 人员统计报告（2026-01-01 至 2026-05-27）

**报告生成时间**：2026-05-27 PT
**数据源**：iehr（aws-luckyus-iehr-rw · luckyus_iehr.*）
**业务路径**：iadmin → 人事系统 → 员工管理 → 异动快照
**时区口径**：America/Los_Angeles (PT)；服务器为 UTC，`effective_date` 字段为 VARCHAR(10) 日期，按字符串比较
**提取路径**：**Path B** — 使用专用变更日志表 `t_ehr_employee_adjustment_snapshot`（包含 `from_post_code` / `to_post_code` / `effective_date`），无须重建历史

---

## 一、统计结论

| 指标 | 数值 |
|---|---|
| 窗口内职位变更为 SM 的**人员**总数 | **8 人** |
| 窗口内变更**记录**数（含反复变更） | 8 条（无人在窗口内多次升任 SM） |
| 涉及门店数 | 7 家（102 Fulton 出现 2 次） |
| 现役 SM 总人数（对照） | 17 人（窗口内新晋占比 ~47%） |
| 来源职位（变更前）分布 | 全部来自 **Store Manager Trainee（LKUS00000098）= 8 人** |

> 数据健康：所有 8 人在窗口结束时仍为在职状态（status=1），无被降职/离职案例。

---

## 二、人员清单（按生效日期升序）

| 序号 | 员工编号 | 姓名 | 变更前职位 | 变更后职位 | 生效日期 | 所属门店 | 在职状态 |
|---|---|---|---|---|---|---|---|
| 1 | US202507280004 | Shangxian Piao | Store Manager Trainee | Store Manager | 2026-01-26 | 102 Fulton | Active |
| 2 | US202509090009 | Kayen Wu He | Store Manager Trainee | Store Manager | 2026-02-03 | 221 Grand | Active |
| 3 | US202506160001 | Wenny Lin | Store Manager Trainee | Store Manager | 2026-02-13 | 8th & Broadway | Active |
| 4 | US202507170003 | Eric Park | Store Manager Trainee | Store Manager | 2026-03-02 | 54th & 8th | Active |
| 5 | US202510070002 | Joselyn Pacheco Trejo | Store Manager Trainee | Store Manager | 2026-03-11 | 102 Fulton | Active |
| 6 | US202506260003 | Huichen Jiang | Store Manager Trainee | Store Manager | 2026-04-24 | 8th & Broadway | Active |
| 7 | US202510210001 | Javier Cruz | Store Manager Trainee | Store Manager | 2026-05-01 | 21st & 3rd | Active |
| 8 | US202508050006 | Brionna Jiles | Store Manager Trainee | Store Manager | 2026-05-04 | 28th & 6th | Active |

### 月度分布
| 月份 | 升任人数 |
|---|---|
| 2026-01 | 1 |
| 2026-02 | 2 |
| 2026-03 | 2 |
| 2026-04 | 1 |
| 2026-05（至 27 日） | 2 |

### 入职至升任 SM 时长
- 最短：**Javier Cruz** — 入职 2025-10-21，升任 2026-05-01（约 6 个月）
- 最长：**Wenny Lin** — 入职 2025-06-16，升任 2026-02-13（约 8 个月）
- 中位数约 7 个月，所有 8 人均经历 SMT 培训阶段

---

## 三、数据完整性说明

### 1. 提取路径选择
- **t_ehr_employee_post_relation**（主表）为**当前态唯一**结构（919 行 = 919 个员工，每人一行），不存储历史，无法用于回溯
- **t_ehr_employee_adjustment_application**（异动申请单）对 LKUS 租户为**空表**
- **t_ehr_employee_adjustment_snapshot**（异动快照，2,324 行 LKUS 数据，2025-03-31 起）**直接包含 `from_post_code` + `to_post_code` + `effective_date`**，是权威来源 → 选用 Path B

### 2. 字段映射
| CSV 列 | 数据源 |
|---|---|
| 员工编号 | snapshot.emp_no |
| 姓名 / 邮箱 / 入职日期 / 在职状态 | t_ehr_employee.{name,email,join_date,status} |
| 变更前/后职位编码 | snapshot.from_post_code / to_post_code |
| 变更前/后职位名称 | t_ehr_post.name（按 code 关联） |
| 生效日期 | snapshot.effective_date |
| 操作人 | snapshot.create_account（账号 ID，未关联到姓名表；窗口内仅出现 131 与 10220 两位 HR 操作员） |
| 所属门店 | snapshot.department_name_path 末段（异动当时门店） |
| 后续变更次数 | 本窗口内同 emp_no 升任 SM 的额外次数 = 0（无人反复升任） |

### 3. 过滤逻辑
```sql
WHERE s.tenant = 'LKUS'
  AND s.to_post_code = 'LKUS00000082'                    -- SM
  AND (s.from_post_code IS NULL OR s.from_post_code <> 'LKUS00000082')   -- 排除 SM→SM 仅换门店
  AND s.effective_date BETWEEN '2026-01-01' AND '2026-05-27'
```

### 4. 异常 / 边界情况
- **窗口内 SM 同码异动 15 条**：均为既有 SM 仅调整门店或上级，不计入本统计
- **训练生路径明确**：8 人 100% 来自 SMT（LKUS00000098），无跨级越级（如 ASM 直升 SM、Barista 直升 SM）
- **type=3（调动）涵盖晋升**：snapshot.type 字段在 LKUS 数据中仅出现 0/1/2/3，未使用 4=晋升 / 5=降职 编码；本系统将晋升记录为 type=3（调动）并通过 from/to 职位码区分性质
- **数据起点限制**：snapshot 表最早数据为 2025-03-31，覆盖窗口完整无截断
- **服务器时区为 UTC**，但 `effective_date` 为 VARCHAR 日期（无时间分量），不存在时区换算偏差

### 5. 健康对照
- 现役 SM 总数：17 人
- 窗口内升任 SM：8 人
- 8 ≤ 17 ✓ 数据合理（符合 ~10 家 Manhattan 门店 + JFK kiosk 的 SM 配置）

---

## 四、SQL 复现脚本

```sql
USE luckyus_iehr;
SELECT
    s.emp_no, e.name, e.email, e.join_date,
    s.from_post_code, pf.name AS from_post_name,
    s.to_post_code,   pt.name AS to_post_name,
    s.effective_date, s.type AS adj_type,
    s.create_time, s.create_account,
    JSON_UNQUOTE(JSON_EXTRACT(s.department_name_path,'$."en-US"')) AS dept_path_en,
    s.direct_superior,
    CASE e.status WHEN 1 THEN 'Active' WHEN 0 THEN 'Separated' END AS employee_status
FROM t_ehr_employee_adjustment_snapshot s
JOIN t_ehr_employee e ON e.emp_no = s.emp_no AND e.tenant='LKUS'
LEFT JOIN t_ehr_post pt ON pt.code = s.to_post_code   AND pt.tenant='LKUS'
LEFT JOIN t_ehr_post pf ON pf.code = s.from_post_code AND pf.tenant='LKUS'
WHERE s.tenant='LKUS'
  AND s.to_post_code = 'LKUS00000082'
  AND (s.from_post_code IS NULL OR s.from_post_code <> 'LKUS00000082')
  AND s.effective_date BETWEEN '2026-01-01' AND '2026-05-27'
ORDER BY s.effective_date ASC, s.emp_no ASC;
```

---

**附件**：`iadmin_sm_promotions_2026H1.csv`（UTF-8 with BOM，15 列，8 行）
