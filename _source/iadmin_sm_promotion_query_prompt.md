# Claude Code Prompt — iadmin 职位变更为 SM 人员清单 (2026-01-01 至 2026-05-27)

## 需求背景

需求一：统计 2026 年 1 月 1 日 至 2026 年 5 月 27 日期间，iadmin 系统里所有从其他职位（例如 ASM、SMT、BR、SS 等）**变更为 SM（Store Manager / 店长）** 职位的人员**数量**及**姓名清单**。

- 业务路径：iadmin → 人事系统 → 员工管理
- 数据库：AWS RDS MySQL，iadmin 实例（后台管理系统 / iEMP）
- 时区基准：以 **America/Los_Angeles (PT)** 作为 HR 业务日期口径，DB 内部存储应为 UTC
- 仅统计净变更（即变更生效后职位 = SM，且变更前职位 ≠ SM）

---

## 运行方式

```bash
claude --dangerously-skip-permissions -p "$(cat ./iadmin_sm_promotion_query_prompt.md)"
```

或直接把下面 Prompt 块整段贴入终端。

---

## Prompt（粘贴运行）

```
You are running a read-only HR data extraction on the Luckin Coffee North America iadmin / iEMP system. MCP DB Gateway is connected to all Luckin RDS clusters (SSE endpoint http://10.238.3.43:8001/sse).

## BUSINESS REQUEST (需求一)
Pull the complete list and headcount of employees whose position (职位 / job_title / position_code) changed FROM any non-SM role (e.g. ASM, SMT, BR, SS, trainee) TO **SM (Store Manager / 店长)** during the window:

    Start: 2026-01-01 00:00:00 America/Los_Angeles
    End:   2026-05-27 23:59:59 America/Los_Angeles

Path in iadmin UI for reference: 人事系统 → 员工管理.

Output two artifacts:
  (a) /home/claude/outputs/iadmin_sm_promotions_2026H1.csv  — full row-level detail
  (b) /home/claude/outputs/iadmin_sm_promotions_2026H1_summary.md — Chinese-language summary with headcount + name list

## HARD RULES
- READ-ONLY SELECT queries ONLY. Abort immediately on any INSERT/UPDATE/DELETE/DDL/CALL.
- Production environment — no schema changes, no test writes, no transactions, no SET GLOBAL.
- Use the MCP DB Gateway, NOT direct mysql client connections. Server alias for iadmin should be discoverable via the gateway's list-servers tool.
- Echo \`@@global.time_zone\`, \`@@session.time_zone\`, \`NOW()\`, \`UTC_TIMESTAMP()\` once at the start of CHECKPOINT 3 so all timestamp interpretations are auditable.
- If any CHECKPOINT yields zero rows where rows are expected, STOP and surface the finding before proceeding — do not silently fall through.
- Do NOT mask employee names or employee_no in the final CSV — this is an internal HR request from a trusted stakeholder. Email addresses can be included in full.
- Write every intermediate finding to ./savepoints/SAVEPOINT_N_<topic>.md so the run is fully resumable.

## EXECUTION PLAN — CHECKPOINT METHODOLOGY

### CHECKPOINT 1 — Cluster + schema discovery
- Use the MCP DB Gateway list-servers tool to find the iadmin RDS endpoint (likely server alias \`iadmin\` or \`luckin-iadmin\`).
- On the iadmin cluster:
    SHOW DATABASES LIKE '%iadmin%';
    SHOW DATABASES LIKE '%iemp%';
    SHOW DATABASES LIKE '%hr%';
    SHOW DATABASES LIKE '%emp%';
- Pick the primary schema (most likely \`iadmin\` itself, or \`iemp\`). If multiple candidates, prefer the one with the largest user/employee table by row count.
- In the chosen schema, enumerate candidate tables:
    SHOW TABLES LIKE '%user%';
    SHOW TABLES LIKE '%employee%';
    SHOW TABLES LIKE '%staff%';
    SHOW TABLES LIKE '%emp_info%';
    SHOW TABLES LIKE '%position%';
    SHOW TABLES LIKE '%job%';
    SHOW TABLES LIKE '%role%';
    SHOW TABLES LIKE '%post%';
    SHOW TABLES LIKE '%transfer%';
    SHOW TABLES LIKE '%change%';
    SHOW TABLES LIKE '%history%';
    SHOW TABLES LIKE '%log%';
    SHOW TABLES LIKE '%audit%';
    SHOW TABLES LIKE '%record%';
- Output: ./savepoints/SAVEPOINT_1_discovery.md with cluster endpoint, schema name, employee table candidate, position-history table candidate(s).

### CHECKPOINT 2 — Schema inspection
For each candidate table from CHECKPOINT 1, run:
    DESC <table>;
    SELECT COUNT(*) FROM <table>;
    SELECT * FROM <table> LIMIT 5;  -- sample for column understanding

Identify:
- **Employee master table** columns: employee_no/工号, full_name/姓名, email, current_position_code/职位编码, current_position_name/职位名称, store_id/门店ID, status/状态, update_time, update_by.
- **Position history / transfer / job-change table** columns: target user_id or employee_no, old_position_code, new_position_code, old_position_name, new_position_name, effective_date / change_time / operate_time, operator_id, change_reason. Field names in Luckin-style schemas may be Chinese-romanized: \`old_post\`, \`new_post\`, \`yuan_zhiwei\`, \`xin_zhiwei\`, etc.

If a dedicated position-change history table does NOT exist, fall back to a generic operation/audit log table where \`field_name LIKE '%position%' OR field_name LIKE '%post%' OR field_name LIKE '%zhiwei%' OR field_name LIKE '%job_title%'\`.

Determine the canonical code/name for SM:
    SELECT DISTINCT position_code, position_name, COUNT(*) AS headcount
    FROM <employee_table>
    GROUP BY position_code, position_name
    ORDER BY headcount DESC;

Confirm with the user-facing iadmin UI convention: SM = 店长 / Store Manager. Common code values seen in Luckin-style schemas: \`SM\`, \`STORE_MANAGER\`, \`DZ\`, \`10\`, \`P_SM\`. Pick the code that matches the row whose position_name contains "店长" or "Store Manager" exclusively.

Save findings to ./savepoints/SAVEPOINT_2_schema.md including the resolved SM code(s) and the field names that hold old/new position on the history table.

### CHECKPOINT 3 — Time zone & boundary check
Run and record:
    SELECT @@global.time_zone, @@session.time_zone, NOW(), UTC_TIMESTAMP();

Convert the request window to whatever the history table uses. Default assumption: history.effective_date or history.change_time is stored in UTC. If session TZ is UTC and business window is PT:
    PT 2026-01-01 00:00:00 = UTC 2026-01-01 08:00:00
    PT 2026-05-27 23:59:59 = UTC 2026-05-28 06:59:59

If the column is DATE (not DATETIME), use [2026-01-01, 2026-05-27] inclusive on both ends with no TZ adjustment, but flag this in the summary.

### CHECKPOINT 4 — Primary extraction query
Run the position-change query against the resolved schema. Generic template (adapt column names from CHECKPOINT 2):

    -- A: history-table path (preferred)
    SELECT
        h.id                              AS change_id,
        h.employee_no                     AS employee_no,
        e.full_name                       AS full_name,
        e.email                           AS email,
        h.old_position_code               AS from_position_code,
        h.old_position_name               AS from_position_name,
        h.new_position_code               AS to_position_code,
        h.new_position_name               AS to_position_name,
        h.effective_date                  AS effective_date_utc,
        CONVERT_TZ(h.effective_date,'+00:00','-08:00') AS effective_date_pt,
        h.operator_id                     AS operator_id,
        h.operator_name                   AS operator_name,
        e.store_id                        AS store_id,
        e.dept_name                       AS dept_name,
        h.change_reason                   AS change_reason
    FROM   <position_history_table>  h
    JOIN   <employee_table>          e ON e.employee_no = h.employee_no
    WHERE  h.new_position_code = '<SM_CODE>'           -- to-state = SM
      AND  h.old_position_code <> '<SM_CODE>'          -- from-state != SM (real promotion/transfer-in)
      AND  h.effective_date >= '2026-01-01 08:00:00'   -- PT 2026-01-01 → UTC
      AND  h.effective_date <  '2026-05-28 07:00:00'   -- PT 2026-05-27 23:59:59 → UTC
    ORDER BY h.effective_date ASC, h.employee_no;

    -- B: generic audit-log fallback (if no history table)
    SELECT
        l.operate_time                     AS effective_date_utc,
        CONVERT_TZ(l.operate_time,'+00:00','-08:00') AS effective_date_pt,
        l.target_employee_no               AS employee_no,
        e.full_name                        AS full_name,
        l.field_name,
        l.old_value                        AS from_position,
        l.new_value                        AS to_position,
        l.operator_id,
        l.operator_name
    FROM   <audit_log_table>      l
    JOIN   <employee_table>       e ON e.employee_no = l.target_employee_no
    WHERE  l.field_name IN ('position_code','position_name','job_title','post','zhiwei')
      AND  (l.new_value = '<SM_CODE>' OR l.new_value = '店长' OR l.new_value = 'Store Manager')
      AND  (l.old_value <> '<SM_CODE>' AND l.old_value <> '店长' AND l.old_value <> 'Store Manager')
      AND  l.operate_time >= '2026-01-01 08:00:00'
      AND  l.operate_time <  '2026-05-28 07:00:00'
    ORDER BY l.operate_time ASC;

Save the raw result set to ./savepoints/SAVEPOINT_4_raw_results.tsv.

### CHECKPOINT 5 — Dedup & sanity checks
- If a person was promoted to SM multiple times in the window (e.g. ASM→SM→ASM→SM), keep the FIRST promotion record but include a \`subsequent_changes_count\` column on the summary row, and list all change records on the detail CSV.
- Verify no employee_no in the result set has current_position != SM today UNLESS \`subsequent_changes_count > 0\` (i.e., they were demoted back). Flag any inconsistency.
- Cross-check headcount against employee master table:
    SELECT COUNT(*) FROM <employee_table>
    WHERE current_position_code = '<SM_CODE>'
      AND hire_date <= '2026-05-27';
  If the # of unique promoted-to-SM people in the window is wildly inconsistent (e.g. > total SM headcount), STOP and re-examine the SM code resolution.
- Count distinct employee_no in the result — this is the headcount answer.

### CHECKPOINT 6 — Output generation

Write two files to /home/claude/outputs/ :

**File 1: iadmin_sm_promotions_2026H1.csv** (UTF-8 with BOM for Excel compatibility)
Columns:
  序号, 员工编号, 姓名, 邮箱, 变更前职位编码, 变更前职位名称, 变更后职位编码, 变更后职位名称,
  生效日期(PT), 生效日期(UTC), 操作人, 所属门店, 部门, 变更原因, 后续变更次数

**File 2: iadmin_sm_promotions_2026H1_summary.md** (Chinese-language, formal Luckin/LCNA-DBA report style)

Structure:

    # iadmin 系统职位变更为 SM 人员统计报告（2026-01-01 至 2026-05-27）

    报告生成时间：<now PT>
    数据源：iadmin (iEMP) RDS MySQL — <cluster_endpoint>
    业务路径：iadmin → 人事系统 → 员工管理
    时区口径：America/Los_Angeles (PT)
    查询执行人：DBA 自动化（DevOps DBA - David Zeng / Xiangyu Zeng）

    ## 一、统计结论
    - 统计周期内职位变更为 SM 的人员总数：**XX 人**
    - 涉及变更记录数（含重复变更）：XX 条
    - 涉及门店数：XX 家
    - 来源职位分布（变更前）：ASM XX 人、SMT XX 人、其他 XX 人

    ## 二、人员清单
    | 序号 | 员工编号 | 姓名 | 变更前职位 | 变更后职位 | 生效日期(PT) | 所属门店 |
    |------|----------|------|------------|------------|--------------|----------|
    | 1    | ...      | ...  | ASM        | SM         | 2026-01-15   | US00008  |
    ...

    ## 三、数据完整性说明
    - 时区基准、UTC↔PT 转换、字段映射（old_position / new_position）
    - 是否存在多次反复变更人员
    - 数据源表名、主键字段、变更生效日期字段

    ## 四、附件
    - 完整 CSV：iadmin_sm_promotions_2026H1.csv

## DELIVERABLE CHECKLIST
- [ ] CHECKPOINT 1-6 savepoints written
- [ ] CSV exported to /home/claude/outputs/
- [ ] Markdown summary written
- [ ] Print headcount + name list to stdout at the end for the operator to eyeball
- [ ] If the position-history table was NOT found and only audit-log fallback worked, surface this loudly in the summary §三 (it affects data confidence)
- [ ] If timezone conversion was applied, document the SQL boundaries used
"
```

---

## 验证步骤（运行完后人工确认）

1. 打开 `iadmin_sm_promotions_2026H1_summary.md`，核对总人数与 HR/运营预期是否相符
2. 抽样 2-3 个人员在 iadmin UI（人事系统-员工管理-员工详情-异动记录）核对变更生效日期与职位流转
3. 关注 §三 数据完整性说明：如果 fallback 到了 audit-log 路径而非专用 history 表，需要联系 iadmin 后端确认 schema 是否变更过
4. CSV 编码为 UTF-8 BOM，可直接拖入 Excel 查看；如需发送给 HR，建议另存为 .xlsx

---

## 备注

- 如果 iadmin 实例上有专用的 `position_change_history` / `employee_transfer` / `job_change_log` 表，CHECKPOINT 4 走 A 路径会非常干净
- 如果只有通用 `sys_operation_log` 这种审计表，走 B 路径，但 `field_name` 字段命名可能因实现而异（可能是 `position`、`zhiwei`、`job_title` 三选一甚至 JSON diff），需要在 CHECKPOINT 2 仔细确认
- 同一人多次变更：如 ASM→SM→ASM→SM 这种 case，summary 只算 1 人但 detail CSV 全保留，方便 HR 复盘
