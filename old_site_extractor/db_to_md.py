import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify
from typing import Any
from pathlib import Path

def fetch_data_as_dict(database_path: str, query: str) -> list[dict[str, Any]]:
    # Connect to the SQLite3 database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Execute the query
    cursor.execute(query)

    # Fetch the column names
    columns = [description[0] for description in cursor.description]

    # Fetch rows and convert each row to a dictionary
    rows = cursor.fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        results.append(row_dict)

    # Close the connection
    conn.close()

    return results


def filter_data(data: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    # For a given title, remove duplicates and preserve only the most recent one
    date_format = "%Y-%m-%d %H:%M:%S"
    trimmed_data: dict[str, dict[str, str]] = {}
    for row in data:
        post_title = row["post_title"]
        if post_title in trimmed_data:
            candidate_date = datetime.strptime(row["post_date"], date_format).date()
            existing_date = datetime.strptime(
                trimmed_data[post_title]["post_date"], date_format
            ).date()
            if existing_date < candidate_date:
                trimmed_data[post_title] = row
        else:
            trimmed_data[post_title] = row

    return trimmed_data

def main() -> None:
    # keys:
    # ID post_author post_date post_date_gmt post_content post_title post_excerpt post_status comment_status ping_status post_password post_name to_ping pinged post_modified post_modified_gmt post_content_filtered post_parent guid menu_order post_type post_mime_type comment_count
    data = fetch_data_as_dict("ydw.db", "SELECT * FROM wp_ydw_posts")
    data = filter_data(data)
    data = {k:v for k, v in data.items() if "<p>" in v["post_content"]}

    print(f"Found {len(data)} unique posts")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True, parents=True)

    for entry in data.values():
        file_path = output_dir / (entry['post_title'].lower().replace(" ", "_").replace("/", "_") + ".md")
        md = markdownify(entry["post_content"])
        md = md.replace(r"\\n", "\n")
        md = md.replace("!!!SPAG!!!", "'")
        file_path.write_text(md)


if __name__ == "__main__":
    main()