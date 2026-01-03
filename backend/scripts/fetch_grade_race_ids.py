"""
Script to fetch grade race IDs (G1, G2, G3) from netkeiba.

Usage:
    python scripts/fetch_grade_race_ids.py --grade G3 --years 2022 2023 2024
    python scripts/fetch_grade_race_ids.py --grade G3 --years 2022 2023 2024 --output data/g3_race_ids.json
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class GradeRaceIdFetcher:
    """Fetch grade race IDs from netkeiba."""

    DB_URL = "https://db.netkeiba.com"

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )

    async def close(self):
        await self.client.aclose()

    async def fetch_race_ids_for_year(self, year: int, grade: str) -> list[dict]:
        """
        Fetch race IDs for a specific year and grade.

        Args:
            year: Year to fetch (e.g., 2024)
            grade: Grade to fetch (G1, G2, G3)

        Returns:
            List of dicts with race_id, race_name, race_date
        """
        # Grade mapping for netkeiba URL parameter
        grade_param = {"G1": "1", "G2": "2", "G3": "3"}
        grade_value = grade_param.get(grade, "3")

        # Netkeiba race list URL with grade filter
        # https://db.netkeiba.com/?pid=race_list&start_year=2024&end_year=2024&grade[]=3
        url = (
            f"{self.DB_URL}/?pid=race_list"
            f"&start_year={year}&start_mon=none"
            f"&end_year={year}&end_mon=none"
            f"&grade%5B%5D={grade_value}"
        )

        races = []
        page = 1

        while True:
            page_url = f"{url}&page={page}" if page > 1 else url

            await asyncio.sleep(self.delay)
            print(f"Fetching {grade} races for {year}, page {page}...")

            try:
                response = await self.client.get(page_url)
                if response.status_code != 200:
                    print(f"  Error: HTTP {response.status_code}")
                    break

                # Decode EUC-JP (netkeiba uses EUC-JP)
                html = response.content.decode("euc-jp", errors="ignore")
                soup = BeautifulSoup(html, "lxml")

                # Find race list table
                race_table = soup.select_one("table.race_table_01")
                if not race_table:
                    race_table = soup.select_one("table.nk_tb_common")
                if not race_table:
                    print("  No race table found")
                    break

                rows = race_table.select("tr")
                found_races = 0

                for row in rows:
                    # Skip header row
                    if row.select("th"):
                        continue

                    cells = row.select("td")
                    if len(cells) < 5:
                        continue

                    # Extract race link from race name column (5th column)
                    race_name_cell = cells[4] if len(cells) > 4 else None
                    if not race_name_cell:
                        continue

                    race_link = race_name_cell.select_one("a[href*='/race/']")
                    if not race_link:
                        continue

                    href = race_link.get("href", "")
                    # Extract race ID from URL: /race/202409030811/
                    race_id_match = re.search(r"/race/(\d+)/", href)
                    if not race_id_match:
                        continue

                    race_id = race_id_match.group(1)

                    # Skip non-JRA races (race_id starting with year + venue code 01-10)
                    # JRA venue codes: 01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
                    if len(race_id) >= 6:
                        venue_code = race_id[4:6]
                        if not venue_code.isdigit() or int(venue_code) > 10:
                            # Skip overseas races (non-JRA)
                            continue

                    race_name = race_link.get_text(strip=True)

                    # Extract date from first column
                    race_date = ""
                    date_text = cells[0].get_text(strip=True)
                    # Format: 2024/04/14
                    date_match = re.search(r"(\d{4})/(\d{2})/(\d{2})", date_text)
                    if date_match:
                        race_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

                    # Extract venue from second column
                    venue = ""
                    if len(cells) > 1:
                        venue = cells[1].get_text(strip=True)

                    races.append({
                        "race_id": race_id,
                        "race_name": race_name,
                        "race_date": race_date,
                        "venue": venue,
                        "grade": grade,
                        "year": year,
                    })
                    found_races += 1

                print(f"  Found {found_races} races on page {page}")

                # Check for next page
                pager = soup.select_one("div.common_pager")
                if not pager:
                    pager = soup.select_one("div.pager")
                if not pager:
                    break

                # Check if there's a "next" link (look for page=N+1 in any link)
                next_link = pager.select_one(f"a[href*='page={page + 1}']")
                if not next_link:
                    # Also check for "次" (next) link
                    next_link = pager.select_one("a[title='次']")
                if not next_link:
                    break

                page += 1

            except Exception as e:
                print(f"  Error fetching page {page}: {e}")
                break

        return races

    async def fetch_all(self, years: list[int], grade: str) -> list[dict]:
        """Fetch race IDs for multiple years."""
        all_races = []

        for year in years:
            races = await self.fetch_race_ids_for_year(year, grade)
            all_races.extend(races)
            print(f"Total for {year}: {len(races)} {grade} races")

        return all_races


async def main():
    parser = argparse.ArgumentParser(description="Fetch grade race IDs from netkeiba")
    parser.add_argument(
        "--grade",
        choices=["G1", "G2", "G3"],
        default="G3",
        help="Grade to fetch (default: G3)",
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=[2022, 2023, 2024],
        help="Years to fetch (default: 2022 2023 2024)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: data/{grade.lower()}_race_ids.json)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Default output path
    output_path = args.output
    if not output_path:
        output_path = f"data/{args.grade.lower()}_race_ids.json"

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    fetcher = GradeRaceIdFetcher(delay=args.delay)

    try:
        print(f"Fetching {args.grade} race IDs for years: {args.years}")
        races = await fetcher.fetch_all(args.years, args.grade)

        # Extract just the race IDs for the simple list
        race_ids = [r["race_id"] for r in races]

        # Save full data
        output_data = {
            "grade": args.grade,
            "years": args.years,
            "fetched_at": datetime.now().isoformat(),
            "total_count": len(races),
            "race_ids": race_ids,
            "races": races,  # Full race info for reference
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\nSaved {len(races)} {args.grade} race IDs to {output_path}")
        print(f"Race IDs: {race_ids[:5]}... (showing first 5)")

    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
