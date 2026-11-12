def get_float_days(task, hours_per_day=8.0):
    """Convert total_float_hr_cnt from hours to working days."""
    raw = task.get("total_float_hr_cnt", "").strip()
    if not raw:
        return None
    return float(raw) / hours_per_day


def validate_and_filter_links(tasks, links, broken_rows):
    """Flag TASKPRED rows that reference a missing task_id and return valid links."""
    valid_links = []
    for row in links:
        succ_id = row["task_id"].strip()
        pred_id = row["pred_task_id"].strip()
        if succ_id not in tasks or pred_id not in tasks:
            broken_rows.append((row["_line"], "TASKPRED", f"link {pred_id} -> {succ_id} references missing task"))
        else:
            valid_links.append(row)
    return valid_links


def check_missing_links(tasks, valid_links):
    """Flag tasks missing a predecessor (except TT_Mile) or successor (except TT_FinMile)."""
    tasks_with_preds = {link["task_id"].strip() for link in valid_links}
    tasks_with_succs = {link["pred_task_id"].strip() for link in valid_links}

    flagged = []
    for task in tasks.values():
        task_id = task["task_id"].strip()
        task_type = task.get("task_type", "").strip()

        no_pred = (task_id not in tasks_with_preds) and (task_type != "TT_Mile")
        no_succ = (task_id not in tasks_with_succs) and (task_type != "TT_FinMile")

        if no_pred or no_succ:
            side = "missing pred & succ" if (no_pred and no_succ) else ("missing pred" if no_pred else "missing succ")
            flagged.append((task.get("task_code", task_id), task.get("task_name", ""), side))

    return flagged


def check_negative_float(tasks, hours_per_day=8.0):
    """Flag tasks with total float < 0 days."""
    flagged = []
    for task in tasks.values():
        days = get_float_days(task, hours_per_day)
        if days is not None and days < 0:
            flagged.append((task.get("task_code", ""), task.get("task_name", ""), f"{days:.1f}d"))
    return flagged


def check_high_float(tasks, hours_per_day=8.0, limit_days=44.0):
    """Flag tasks with total float > 44 working days."""
    flagged = []
    for task in tasks.values():
        days = get_float_days(task, hours_per_day)
        if days is not None and days > limit_days:
            flagged.append((task.get("task_code", ""), task.get("task_name", ""), f"{days:.1f}d"))
    return flagged
