import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from xer_parser import load_xer
from schedule_checks import (
    validate_and_filter_links,
    check_missing_links,
    check_negative_float,
    check_high_float,
)

CHECK_NAMES = [
    ("missing_links", "missing links"),
    ("negative_float", "negative float"),
    ("high_float", "high float (>44d)"),
]


def check_file(file_path):
    """Load a .xer file, validate links, run all 3 schedule checks, and return the summary dict."""
    sched = load_xer(file_path)
    tasks = sched["tasks"]
    hrs = sched["hours_per_day"]
    valid_links = validate_and_filter_links(tasks, sched["links"], sched["broken_rows"])

    return {
        "file_name": sched["file_name"],
        "project_name": sched["project_name"],
        "total_tasks": len(tasks),
        "total_links": len(valid_links),
        "broken_rows": sched["broken_rows"],
        "missing_links": check_missing_links(tasks, valid_links),
        "negative_float": check_negative_float(tasks, hrs),
        "high_float": check_high_float(tasks, hrs),
    }


def save_chart(results, out_path="chart.png"):
    """Plot the percentage of tasks flagged by each check across files."""
    labels = ["Missing links", "Negative float (< 0d)", "High float (> 44d)"]
    x = range(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=140)

    for i, res in enumerate(results):
        n = max(res["total_tasks"], 1)
        counts = [len(res[key]) for key, _ in CHECK_NAMES]
        pcts = [c / n * 100 for c in counts]
        offset = (i - (len(results) - 1) / 2) * width

        bars = ax.bar(
            [pos + offset for pos in x],
            pcts,
            width=width * 0.9,
            label=f"{res['file_name']} ({res['total_tasks']} tasks)",
        )
        ax.bar_label(
            bars,
            labels=[f"{p:.1f}% ({c})" for p, c in zip(pcts, counts)],
            padding=3,
            fontsize=8.5,
        )

    ax.set_ylabel("% of tasks")
    ax.set_title("P6 Schedule Check Comparison")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 90)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    ax.legend()

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close(fig)


def print_summary(results):
    """Print the terminal report showing total tasks, broken rows, and top flagged activities."""
    for res in results:
        n = max(res["total_tasks"], 1)
        print(f"\n{res['file_name']} ({res['project_name']})")
        print(f"  tasks: {res['total_tasks']} | links: {res['total_links']}")

        print(f"  broken rows: {len(res['broken_rows'])}")
        for line_num, table, reason in res["broken_rows"][:5]:
            print(f"    line {line_num} ({table}): {reason}")

        for key, label in CHECK_NAMES:
            flagged = res[key]
            print(f"  {label}: {len(flagged)}/{res['total_tasks']} ({len(flagged)/n*100:.1f}%)")
            for code, name, detail in flagged[:3]:
                print(f"    {code} - {name} ({detail})")


def main():
    base_dir = Path(__file__).resolve().parent
    if len(sys.argv) > 1:
        files = [Path(p) for p in sys.argv[1:]]
    else:
        files = list((base_dir / "schedules").glob("*.xer"))

    results = [check_file(f) for f in files]
    print_summary(results)

    if len(sys.argv) == 1 and results:
        out_file = base_dir / "chart.png"
        save_chart(results, str(out_file))
        print(f"\nSaved chart to {out_file.name}")


if __name__ == "__main__":
    main()
