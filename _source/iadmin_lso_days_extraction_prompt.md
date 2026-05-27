# Claude Code Prompt — iadmin LSO100/200/300/400 Days-to-Certification Data Extraction

## Workflow Overview

1. **Run this prompt in Claude Code** (terminal, MCP DB Gateway connected) — it produces 5 CSV files + 1 discovery log
2. **Upload the CSV files back to Claude web** — Claude web will compile the final Chinese-language Luckin Coffee DBA-style report

This prompt does **NOT** generate any report. It only extracts raw, clean data.

---

## Run Command

```bash
claude --dangerously-skip-permissions -p "$(cat ./iadmin_lso_days_extraction_prompt.md)"
```

Or paste the prompt block below directly into your Claude Code session.

---

## Prompt (paste-ready, English only)

```
You are running a read-only HR data extraction on the Luckin Coffee North America iadmin / iEMP system. MCP DB Gateway is connected to all Luckin RDS clusters (SSE endpoint http://10.238.3.43:8001/sse).

## MISSION
Extract, for each of the four Luckin Store Operations certification levels (LSO100, LSO200, LSO300, LSO400), the list of employees who acquired that certification between 2025-05-27 and 2026-05-27 inclusive, and compute the number of days between their hire date and the date they acquired that certification.

This is a DATA-EXTRACTION-ONLY mission. Do NOT generate any narrative report, analysis, or markdown summary. Only produce structured CSV files and a discovery log. A separate downstream step (Claude web) will compile the business report.

## DATA SOURCES (iadmin UI paths for reference)
- Hire date:                  iadmin → HR System (人事系统) → Employee Management (员工管理)
- LSO100 acquisition date:    iadmin → HR System → Qualification Management (资质管理) → LSO100
- LSO200 acquisition date:    iadmin → HR System → Qualification Management → LSO200
- LSO300 acquisition date:    iadmin → HR System → Qualification Management → LSO300
- LSO400 acquisition date:    iadmin → HR System → Qualification Management → LSO400

LSO = Luckin Store Operations training/certification tier (100=entry, 200, 300, 400=highest).

## TIME WINDOW
Filter on CERTIFICATION ACQUISITION DATE, not hire date.

    Window start:  2025-05-27 00:00:00 America/Los_Angeles
    Window end:    2026-05-27 23:59:59 America/Los_Angeles  (inclusive)

If the certification table stores datetime in UTC, convert to:
    UTC start: 2025-05-27 07:00:00
    UTC end:   2026-05-28 06:59:59

If the certification column is DATE (no time component), use BETWEEN '2025-05-27' AND '2026-05-27' inclusive on both ends and flag this in SAVEPOINT_3.

Note in the discovery log if any employee's hire_date is AFTER their LSO acquisition date — this would indicate a data anomaly and the row should still be exported but tagged `data_anomaly=Y`.

## HARD RULES
- READ-ONLY SELECT queries ONLY. Abort immediately on any INSERT/UPDATE/DELETE/DDL/CALL/SET GLOBAL.
- Production environment — no schema changes, no test writes, no transactions.
- Use the MCP DB Gateway, NOT direct mysql client connections. The iadmin RDS cluster should be discoverable via the gateway's list-servers tool (likely alias `iadmin` or `luckin-iadmin`).
- Echo `@@global.time_zone`, `@@session.time_zone`, `NOW()`, `UTC_TIMESTAMP()` once at the start of CHECKPOINT 3.
- If any CHECKPOINT yields zero rows where rows are expected, STOP and surface the finding before proceeding — do not silently fall through.
- Do NOT mask employee names or employee_no in the final CSV — this is an internal HR request from a trusted stakeholder.
- Keep all employees who match the certification window, even if hire_date is missing — emit them with `hire_date=NULL` and `days_to_cert=NULL` so HR can chase the gap.
- Write every intermediate finding to `./savepoints/SAVEPOINT_N_<topic>.md` so the run is fully resumable.

## EXECUTION PLAN — CHECKPOINT METHODOLOGY

### CHECKPOINT 1 — Cluster + schema discovery
- Use the MCP DB Gateway list-servers tool to find the iadmin RDS endpoint.
- On the iadmin cluster:
    SHOW DATABASES LIKE '%iadmin%';
    SHOW DATABASES LIKE '%iemp%';
    SHOW DATABASES LIKE '%hr%';
- Pick the primary schema (likely `iadmin` or `iemp`). If multiple candidates, prefer the one with the largest user/employee table by row count.
- Enumerate candidate tables in the chosen schema:
    -- Employee master
    SHOW TABLES LIKE '%user%';
    SHOW TABLES LIKE '%employee%';
    SHOW TABLES LIKE '%staff%';
    SHOW TABLES LIKE '%emp_info%';
    -- Qualification / certification / training
    SHOW TABLES LIKE '%qualif%';
    SHOW TABLES LIKE '%cert%';
    SHOW TABLES LIKE '%training%';
    SHOW TABLES LIKE '%lso%';
    SHOW TABLES LIKE '%license%';
    SHOW TABLES LIKE '%zizhi%';      -- pinyin for 资质
    SHOW TABLES LIKE '%peixun%';     -- pinyin for 培训
    SHOW TABLES LIKE '%skill%';
    SHOW TABLES LIKE '%level%';
    SHOW TABLES LIKE '%grade%';
- Output: `./savepoints/SAVEPOINT_1_discovery.md` with cluster endpoint, schema name, employee table candidate, qualification table candidate(s).

### CHECKPOINT 2 — Schema inspection
For each candidate table from CHECKPOINT 1, run:
    DESC <table>;
    SELECT COUNT(*) FROM <table>;
    SELECT * FROM <table> LIMIT 5;

Identify:
- **Employee master table** columns: employee_no/工号, full_name/姓名, email, hire_date/入职日期/entry_date/join_date, current_position_code, store_id, status.
- **Qualification table** columns: target employee_no or user_id, qualification_code/cert_code/level_code (this holds 'LSO100' / 'LSO200' / 'LSO300' / 'LSO400' or a numeric ID mapping to those), acquired_date / pass_date / cert_date / effective_date / issue_date, status (active vs expired).

The qualification table may be either:
- **(a) Wide format**: one row per employee with columns `lso100_date`, `lso200_date`, `lso300_date`, `lso400_date`.
- **(b) Long format / EAV**: one row per employee+cert combination with `cert_code` and `acquired_date` columns. This is the more common Luckin schema pattern.

Resolve the canonical code/name for each LSO level:
    SELECT DISTINCT cert_code, cert_name, COUNT(*)
    FROM <qualification_table>
    WHERE cert_code LIKE '%LSO%' OR cert_name LIKE '%LSO%'
    GROUP BY cert_code, cert_name
    ORDER BY cert_code;

Confirm the four codes map cleanly to LSO100, LSO200, LSO300, LSO400. If the codes are numeric (e.g., 1, 2, 3, 4 or 100, 200, 300, 400) or otherwise non-obvious, document the mapping in SAVEPOINT_2.

Also confirm whether there are duplicate qualification rows per employee (e.g., re-certifications). Decision rule: if duplicates exist, take the **earliest** acquired_date per (employee, cert_level) — this is the "first time they earned it" date.

Save findings to `./savepoints/SAVEPOINT_2_schema.md` including the resolved LSO code mapping and the exact column names for employee_no, hire_date, cert_code, acquired_date.

### CHECKPOINT 3 — Time zone & boundary check
Run and record once:
    SELECT @@global.time_zone, @@session.time_zone, NOW(), UTC_TIMESTAMP();

Document the timezone assumption in SAVEPOINT_3:
- If the qualification.acquired_date column is DATETIME and session TZ is UTC → use the UTC bounds (2025-05-27 07:00:00 to 2026-05-28 06:59:59).
- If DATE only → use BETWEEN '2025-05-27' AND '2026-05-27'.
- Day calculation must use `DATEDIFF(acquired_date, hire_date)` so it returns whole calendar days regardless of time component.

### CHECKPOINT 4 — Per-level extraction (run 4 times, once per LSO level)

For LSO_LEVEL in (LSO100, LSO200, LSO300, LSO400):

    -- Long-format query (preferred; adapt column names from CHECKPOINT 2)
    SELECT
        e.employee_no                              AS employee_no,
        e.full_name                                AS full_name,
        e.email                                    AS email,
        e.hire_date                                AS hire_date,
        q.acquired_date                            AS lso_acquired_date,
        DATEDIFF(q.acquired_date, e.hire_date)     AS days_to_cert,
        e.store_id                                 AS store_id,
        e.dept_name                                AS dept_name,
        e.current_position_code                    AS current_position_code,
        e.current_position_name                    AS current_position_name,
        e.status                                   AS employee_status,
        CASE WHEN e.hire_date IS NULL THEN 'Y'
             WHEN q.acquired_date < e.hire_date THEN 'Y'
             ELSE 'N' END                          AS data_anomaly,
        '<LSO_LEVEL>'                              AS cert_level
    FROM (
        -- earliest acquired_date per employee for this cert level
        SELECT employee_no, MIN(acquired_date) AS acquired_date
        FROM <qualification_table>
        WHERE cert_code = '<RESOLVED_LSO_CODE>'      -- from CHECKPOINT 2
          AND acquired_date >= '<WINDOW_START>'
          AND acquired_date <  '<WINDOW_END_EXCLUSIVE>'
        GROUP BY employee_no
    ) q
    JOIN <employee_table> e ON e.employee_no = q.employee_no
    ORDER BY q.acquired_date ASC, e.employee_no ASC;

    -- Wide-format fallback (if qualification table is wide):
    SELECT
        e.employee_no, e.full_name, e.email,
        e.hire_date,
        q.lsoXXX_date AS lso_acquired_date,
        DATEDIFF(q.lsoXXX_date, e.hire_date) AS days_to_cert,
        e.store_id, e.dept_name,
        e.current_position_code, e.current_position_name,
        e.status,
        CASE WHEN e.hire_date IS NULL THEN 'Y'
             WHEN q.lsoXXX_date < e.hire_date THEN 'Y'
             ELSE 'N' END AS data_anomaly,
        '<LSO_LEVEL>' AS cert_level
    FROM <qualification_table> q
    JOIN <employee_table> e ON e.employee_no = q.employee_no
    WHERE q.lsoXXX_date BETWEEN '2025-05-27' AND '2026-05-27'
    ORDER BY q.lsoXXX_date ASC;

Save the raw result of each level to `./savepoints/SAVEPOINT_4_lsoXXX_raw.tsv` (4 files).

### CHECKPOINT 5 — Cross-level sanity checks
- For each level, count distinct employees vs. total rows — should be equal after MIN() dedup. If not, flag and re-examine.
- Check progression consistency: any employee with LSO300 should also have LSO100 and LSO200. Any LSO200 should have LSO100. Flag inversions as candidates for `data_anomaly`.
- Count overlap between levels (employees appearing in multiple level results) — this is expected if someone earned multiple LSO tiers during the window. Record the overlap matrix in SAVEPOINT_5.
- Spot-check: take 2 random employees per level and look up their full qualification history in the qualification table to verify the MIN(acquired_date) chosen really is their first cert.

### CHECKPOINT 6 — Output generation

Write the following to `/home/claude/outputs/` :

**1. `iadmin_lso100_days_to_cert.csv`** (UTF-8 with BOM)
Columns:
    employee_no, full_name, email, hire_date, lso_acquired_date, days_to_cert, store_id, dept_name, current_position_code, current_position_name, employee_status, data_anomaly, cert_level

**2. `iadmin_lso200_days_to_cert.csv`** — same columns
**3. `iadmin_lso300_days_to_cert.csv`** — same columns
**4. `iadmin_lso400_days_to_cert.csv`** — same columns

**5. `iadmin_lso_extraction_discovery.md`** — discovery log capturing:
    - iadmin cluster endpoint, schema name
    - Resolved table names (employee table, qualification table)
    - Column-name mapping (e.g., `hire_date` is actually `entry_dt`, `acquired_date` is actually `pass_time`)
    - Resolved LSO code mapping (LSO100 → 'LSO100' or 1 or whatever the raw value was)
    - Timezone confirmed and SQL bounds used for each level
    - Wide vs. long format choice
    - Row counts per level (LSO100=NN, LSO200=NN, LSO300=NN, LSO400=NN)
    - Distinct-employee count per level
    - Overlap matrix (employees appearing in 1/2/3/4 level CSVs)
    - Anomaly summary: how many rows tagged `data_anomaly=Y` per level and why
    - Any zero-row CHECKPOINTs or schema surprises

**6. (Optional) `iadmin_lso_all_levels_combined.csv`** — union of the 4 per-level CSVs with `cert_level` column distinguishing them. Useful for downstream pivot.

## DELIVERABLE CHECKLIST
- [ ] CHECKPOINT 1-6 savepoints written to `./savepoints/`
- [ ] 4 per-level CSV files in `/home/claude/outputs/`
- [ ] Discovery log markdown in `/home/claude/outputs/`
- [ ] Combined CSV (optional) in `/home/claude/outputs/`
- [ ] Print to stdout at the end: per-level row counts and any data_anomaly counts
- [ ] No report, no narrative, no analysis — only data

## FORBIDDEN
- Do NOT compose a Chinese-language summary report — that will be done downstream in Claude web.
- Do NOT make business interpretations (e.g., "training pipeline is slow") — only extract and structure data.
- Do NOT write to any directory other than `/home/claude/outputs/` and `./savepoints/`.
- Do NOT call any tool other than the MCP DB Gateway query tools and local file write tools.
"
```

---

## Post-Run Workflow

After Claude Code finishes:

1. Verify `/home/claude/outputs/` contains the 4 per-level CSVs + discovery log
2. Upload **all 5 files** (4 CSVs + discovery markdown) back to a Claude web session
3. In Claude web, ask: *"Compile the final Luckin Coffee DBA-style Chinese report for the LSO days-to-certification analysis using these files."*
4. Claude web will produce:
   - `LCNA-HR-LSO-2026-001 LSO资质获取周期分析报告.docx` (formal report)
   - 4 cleaned summary tables in Chinese for HR consumption
   - Headcount, median/avg/min/max days per level, anomaly callouts

---

## Notes for Schema Surprises

- If the qualification table is wide (one row per employee with `lso100_date`, `lso200_date`...) the prompt's fallback query handles it
- If LSO levels are stored as numeric IDs in a `cert_dict` lookup table, CHECKPOINT 2 must JOIN through that dict to resolve the code
- If there's a separate `qualification_history` audit table tracking revocations/re-issuances, prefer the master qualification table (current state) — re-issuances are out of scope for "first acquisition" question
- If `hire_date` is missing on the employee table but exists on a separate `employment_contract` or `onboarding` table, surface this in SAVEPOINT_1 and adjust the JOIN
