from __future__ import annotations

import csv
import os
from datetime import datetime


def ensure_export_dir() -> str:
    export_dir = os.path.join(os.getcwd(), "exports")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


def build_csv(file_prefix: str, rows: list[dict]) -> str:
    export_dir = ensure_export_dir()
    filename = f"{file_prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    file_path = os.path.join(export_dir, filename)

    fieldnames = [
        "title",
        "authors",
        "year",
        "source",
        "url",
        "score",
    ]

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "title": row.get("title"),
                    "authors": ", ".join(row.get("authors", [])),
                    "year": row.get("year"),
                    "source": row.get("source"),
                    "url": row.get("url"),
                    "score": row.get("score"),
                }
            )

    return file_path


def build_pdf(file_prefix: str, summary: str) -> str:
    # 简化实现：生成txt并以.pdf后缀保存，便于后续替换真正PDF库
    export_dir = ensure_export_dir()
    filename = f"{file_prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    file_path = os.path.join(export_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(summary)
    return file_path
