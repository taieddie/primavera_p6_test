from pathlib import Path
import re

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?$")
VALID_STATUS_CODES = {"TK_NotStart", "TK_Active", "TK_Complete"}
VALID_TASK_TYPES = {"TT_Task", "TT_Rsrc", "TT_LOE", "TT_Mile", "TT_FinMile", "TT_WBS"}
VALID_PRED_TYPES = {"PR_FS", "PR_SS", "PR_FF", "PR_SF"}


def validate_row_types(row, table):
    """Check column values in a row against P6 data type and enum rules."""
    for col, val in row.items():
        val = val.strip()
        if not val:
            continue

        if col.endswith("_id"):
            try:
                int(val)
            except ValueError:
                return f"invalid integer in {col}: '{val}'"

        elif col.endswith(("_hr_cnt", "_qty", "_pct")):
            try:
                float(val)
            except ValueError:
                return f"invalid number in {col}: '{val}'"

        elif col.endswith("_date"):
            if not DATE_RE.match(val):
                return f"invalid date in {col}: '{val}'"

        elif table == "TASK" and col == "status_code" and val not in VALID_STATUS_CODES:
            return f"invalid status_code: '{val}'"

        elif col == "task_type" and val not in VALID_TASK_TYPES:
            return f"invalid task_type: '{val}'"

        elif col == "pred_type" and val not in VALID_PRED_TYPES:
            return f"invalid pred_type: '{val}'"

    return None


def get_hours_per_day(tables):
    """Get work hours per day from the default calendar, defaulting to 8.0."""
    for row in tables.get("CALENDAR", []):
        if row.get("default_flag", "").strip() == "Y":
            try:
                hrs = float(row.get("day_hr_cnt", "").strip())
                if hrs > 0:
                    return hrs
            except ValueError:
                pass
    return 8.0


def load_xer(file_path):
    """Parse a .xer file and flag broken rows."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        numbered_lines = [
            (line_num, raw.rstrip("\r\n"))
            for line_num, raw in enumerate(f, start=1)
            if raw.strip()
        ]

    broken_rows = []
    tables = {}
    tasks = {}
    links = []

    if not numbered_lines or not numbered_lines[0][1].startswith("ERMHDR\t"):
        broken_rows.append((1, "HEADER", "missing ERMHDR header"))

    if numbered_lines and numbered_lines[-1][1].split("\t")[0] != "%E":
        broken_rows.append((numbered_lines[-1][0], "EOF", "missing %E end marker"))

    current_table = None
    current_headers = []

    for line_num, line in numbered_lines[1:]:
        parts = line.split("\t")
        tag = parts[0]

        if tag == "%T":
            current_table = parts[1].strip() if len(parts) > 1 else "UNKNOWN"
            current_headers = []
            tables.setdefault(current_table, [])

        elif tag == "%F":
            current_headers = [h.strip() for h in parts[1:]]

        elif tag == "%R":
            if not current_table:
                broken_rows.append((line_num, "NONE", "data row %R before any %T table"))
                continue

            values = parts[1:]
            if len(values) != len(current_headers):
                broken_rows.append((
                    line_num,
                    current_table,
                    f"expected {len(current_headers)} columns, got {len(values)}",
                ))
                continue

            row = dict(zip(current_headers, values))

            err = validate_row_types(row, current_table)
            if err:
                broken_rows.append((line_num, current_table, err))
                continue

            if current_table == "TASK":
                task_id = row.get("task_id", "").strip()
                if not task_id:
                    broken_rows.append((line_num, "TASK", "missing task_id"))
                    continue
                if task_id in tasks:
                    broken_rows.append((line_num, "TASK", f"duplicate task_id '{task_id}'"))
                    continue
                tasks[task_id] = row

            elif current_table == "TASKPRED":
                if not row.get("task_id", "").strip() or not row.get("pred_task_id", "").strip():
                    broken_rows.append((line_num, "TASKPRED", "missing task_id or pred_task_id"))
                    continue
                row["_line"] = line_num
                links.append(row)

            tables[current_table].append(row)

        elif tag == "%E":
            break

        else:
            broken_rows.append((line_num, current_table or "NONE", f"unexpected tag '{tag}'"))

    proj_rows = tables.get("PROJECT", [])
    proj_name = proj_rows[0].get("proj_short_name", Path(file_path).stem) if proj_rows else Path(file_path).stem

    return {
        "file_name": Path(file_path).name,
        "project_name": proj_name,
        "hours_per_day": get_hours_per_day(tables),
        "tasks": tasks,
        "links": links,
        "broken_rows": broken_rows,
    }
