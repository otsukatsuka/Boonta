"""
Script to collect historical race data for ML training.

Usage:
    python scripts/collect_training_data.py                    # G1 races (default)
    python scripts/collect_training_data.py --grade G3         # G3 races
    python scripts/collect_training_data.py --grade all        # Both G1 and G3
    python scripts/collect_training_data.py --grade all --with-history  # With horse history

Netkeiba Race ID format: YYYYVVKKDDNN
- YYYY: Year
- VV: Venue code (01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉)
- KK: 開催回 (1-5)
- DD: 日目 (1-12)
- NN: Race number (01-12)
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.fetchers.netkeiba import NetkeibaFetcher


# Major G1 races with typical venue codes and race numbers
G1_RACES = [
    # 春のG1
    {"name": "フェブラリーS", "venue": "05", "month": 2, "race_num": "11"},
    {"name": "高松宮記念", "venue": "07", "month": 3, "race_num": "11"},
    {"name": "大阪杯", "venue": "09", "month": 4, "race_num": "11"},
    {"name": "桜花賞", "venue": "09", "month": 4, "race_num": "11"},
    {"name": "皐月賞", "venue": "06", "month": 4, "race_num": "11"},
    {"name": "天皇賞春", "venue": "08", "month": 5, "race_num": "11"},  # 京都
    {"name": "NHKマイルC", "venue": "05", "month": 5, "race_num": "11"},
    {"name": "ヴィクトリアマイル", "venue": "05", "month": 5, "race_num": "11"},
    {"name": "オークス", "venue": "05", "month": 5, "race_num": "11"},
    {"name": "日本ダービー", "venue": "05", "month": 5, "race_num": "11"},
    {"name": "安田記念", "venue": "05", "month": 6, "race_num": "11"},
    {"name": "宝塚記念", "venue": "09", "month": 6, "race_num": "11"},
    # 秋のG1
    {"name": "スプリンターズS", "venue": "06", "month": 10, "race_num": "11"},
    {"name": "秋華賞", "venue": "08", "month": 10, "race_num": "11"},  # 京都
    {"name": "菊花賞", "venue": "08", "month": 10, "race_num": "11"},  # 京都
    {"name": "天皇賞秋", "venue": "05", "month": 10, "race_num": "11"},
    {"name": "エリザベス女王杯", "venue": "08", "month": 11, "race_num": "11"},  # 京都
    {"name": "マイルCS", "venue": "08", "month": 11, "race_num": "11"},  # 京都
    {"name": "ジャパンC", "venue": "05", "month": 11, "race_num": "11"},
    {"name": "チャンピオンズC", "venue": "07", "month": 12, "race_num": "11"},
    {"name": "阪神JF", "venue": "09", "month": 12, "race_num": "11"},
    {"name": "朝日杯FS", "venue": "09", "month": 12, "race_num": "11"},
    {"name": "有馬記念", "venue": "06", "month": 12, "race_num": "11"},
    {"name": "ホープフルS", "venue": "06", "month": 12, "race_num": "11"},
]


# Known G1 race IDs (manually collected for accuracy)
KNOWN_G1_RACE_IDS = [
    # 2024年度 G1 (netkeiba年度形式: 2024年12月〜2025年2月は2025、それ以前は2024)
    "202405050811",  # フェブラリーS 2024
    "202407010811",  # 高松宮記念 2024
    "202409020811",  # 大阪杯 2024
    "202409030811",  # 桜花賞 2024
    "202406030811",  # 皐月賞 2024
    "202408020811",  # 天皇賞春 2024
    "202405020811",  # NHKマイルC 2024
    "202405020911",  # ヴィクトリアマイル 2024
    "202405021011",  # オークス 2024
    "202405021111",  # 日本ダービー 2024
    "202405030811",  # 安田記念 2024
    "202409030911",  # 宝塚記念 2024
    "202406040811",  # スプリンターズS 2024
    "202408040811",  # 秋華賞 2024
    "202408040911",  # 菊花賞 2024
    "202405040811",  # 天皇賞秋 2024
    "202408050811",  # エリザベス女王杯 2024
    "202408050911",  # マイルCS 2024
    "202405050911",  # ジャパンC 2024
    "202407050811",  # チャンピオンズC 2024
    "202509040611",  # 阪神JF 2024 (12月開催は2025年度扱い)
    "202509040711",  # 朝日杯FS 2024
    "202506050811",  # 有馬記念 2024
    # 2023年 G1
    "202305050811",  # フェブラリーS 2023
    "202307010811",  # 高松宮記念 2023
    "202309020811",  # 大阪杯 2023
    "202309030811",  # 桜花賞 2023
    "202306030811",  # 皐月賞 2023
    "202308020811",  # 天皇賞春 2023
    "202305020811",  # NHKマイルC 2023
    "202305020911",  # ヴィクトリアマイル 2023
    "202305021011",  # オークス 2023
    "202305021111",  # 日本ダービー 2023
    "202305030811",  # 安田記念 2023
    "202309030911",  # 宝塚記念 2023
    "202306040811",  # スプリンターズS 2023 (中山)
    "202308040811",  # 秋華賞 2023
    "202308040911",  # 菊花賞 2023
    "202305040811",  # 天皇賞秋 2023
    "202308050811",  # エリザベス女王杯 2023
    "202308050911",  # マイルCS 2023
    "202305050911",  # ジャパンC 2023
    "202307050811",  # チャンピオンズC 2023
    "202409040611",  # 阪神JF 2023 (12月開催は2024年度扱い)
    "202409040711",  # 朝日杯FS 2023
    "202406050811",  # 有馬記念 2023
    # 2022年 G1
    "202205050811",  # フェブラリーS 2022
    "202207010811",  # 高松宮記念 2022
    "202209020811",  # 大阪杯 2022
    "202209030811",  # 桜花賞 2022
    "202206030811",  # 皐月賞 2022
    "202209030811",  # 天皇賞春 2022 (阪神代替)
    "202205020811",  # NHKマイルC 2022
    "202205020911",  # ヴィクトリアマイル 2022
    "202205021011",  # オークス 2022
    "202205021111",  # 日本ダービー 2022
    "202205030811",  # 安田記念 2022
    "202209030911",  # 宝塚記念 2022
    "202206040811",  # スプリンターズS 2022
    "202209040811",  # 秋華賞 2022 (阪神代替)
    "202209040911",  # 菊花賞 2022 (阪神代替)
    "202205040811",  # 天皇賞秋 2022
    "202209050811",  # エリザベス女王杯 2022 (阪神代替)
    "202209050911",  # マイルCS 2022 (阪神代替)
    "202205050911",  # ジャパンC 2022
    "202207050811",  # チャンピオンズC 2022
    "202209040611",  # 阪神JF 2022
    "202209040711",  # 朝日杯FS 2022
    "202206050811",  # 有馬記念 2022
]


@dataclass
class TrainingData:
    """Training data for a single horse entry."""
    # Race info
    race_id: str = ""
    race_name: str = ""
    race_date: str = ""
    venue: str = ""
    distance: int = 0
    course_type: str = ""
    grade: str = ""

    # Horse info
    horse_number: int = 0
    horse_name: str = ""
    jockey_name: str = ""
    weight: float = 0.0
    horse_weight: int | None = None

    # Result info (from race result)
    position: int = 0
    odds: float = 0.0
    popularity: int = 0
    time_seconds: float | None = None
    last_3f: float | None = None
    corner_positions: str = ""  # e.g., "6-5-5-3"
    running_style: str = ""

    # Target variable
    is_win: int = 0  # 1着かどうか
    is_place: int = 0  # 3着以内かどうか

    # Horse history (過去成績)
    total_races: int = 0           # 出走回数
    total_wins: int = 0            # 勝利数
    total_places: int = 0          # 複勝回数（3着以内）
    grade_wins: int = 0            # 重賞勝利数
    win_rate: float = 0.0          # 勝率
    place_rate: float = 0.0        # 複勝率
    avg_position_last5: float = 0.0  # 直近5走平均着順
    best_last_3f: float | None = None  # ベスト上がり3F
    avg_last_3f_hist: float | None = None  # 平均上がり3F（過去）
    days_since_last_race: int = 0  # 前走からの日数


async def fetch_race_result(fetcher: NetkeibaFetcher, race_id: str) -> list[TrainingData]:
    """Fetch race result and convert to training data."""
    print(f"  Fetching race result: {race_id}")

    # Get race info
    race_info = await fetcher.fetch_race_info(race_id)
    if not race_info:
        print(f"    Race info not found: {race_id}")
        return []

    # Get odds/result from result page
    odds_list = await fetcher.fetch_odds_from_result(race_id)
    if not odds_list:
        print(f"    Odds not found (race may not be finished): {race_id}")
        return []

    # Get entries for additional info
    entries = await fetcher.fetch_entries(race_id)
    entry_map = {e.horse_number: e for e in entries}

    training_data = []

    for odds_info in odds_list:
        entry = entry_map.get(odds_info.horse_number)

        data = TrainingData(
            race_id=race_id,
            race_name=race_info.name,
            race_date=race_info.date,
            venue=race_info.venue,
            distance=race_info.distance,
            course_type=race_info.course_type,
            grade=race_info.grade,
            horse_number=odds_info.horse_number,
            horse_name=entry.horse_name if entry else "",
            jockey_name=entry.jockey_name if entry else "",
            weight=entry.weight if entry else 0.0,
            horse_weight=entry.horse_weight if entry else None,
            odds=odds_info.odds,
            popularity=odds_info.popularity,
            corner_positions="-".join(map(str, odds_info.corner_positions or [])),
            running_style=odds_info.running_style or "",
        )

        training_data.append(data)

    print(f"    Got {len(training_data)} entries")
    return training_data


async def fetch_result_details(fetcher: NetkeibaFetcher, race_id: str) -> dict[int, dict]:
    """Fetch detailed result info (position, time, last_3f, horse_id) from result page."""
    import re
    from bs4 import BeautifulSoup

    url = f"{fetcher.DB_URL}/race/{race_id}/"

    await asyncio.sleep(fetcher.delay)
    response = await fetcher.client.get(url)

    if response.status_code != 200:
        return {}

    html = response.content.decode("euc-jp", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    results = {}
    rows = soup.select("table.race_table_01 tr")

    for row in rows:
        try:
            cols = row.select("td")
            if len(cols) < 14:
                continue

            # 着順 (column 0)
            position_text = cols[0].get_text(strip=True)
            if not position_text.isdigit():
                continue
            position = int(position_text)

            # 馬番 (column 2)
            horse_number_text = cols[2].get_text(strip=True)
            if not horse_number_text.isdigit():
                continue
            horse_number = int(horse_number_text)

            # Horse ID from horse name link (column 3)
            horse_id = None
            horse_link = cols[3].select_one("a[href*='/horse/']")
            if horse_link:
                href = horse_link.get("href", "")
                horse_id_match = re.search(r"/horse/(\d+)", href)
                if horse_id_match:
                    horse_id = horse_id_match.group(1)

            # タイム (column 7)
            time_str = cols[7].get_text(strip=True)
            time_seconds = None
            time_match = re.match(r"(\d):(\d{2})\.(\d)", time_str)
            if time_match:
                time_seconds = (
                    int(time_match.group(1)) * 60
                    + int(time_match.group(2))
                    + int(time_match.group(3)) / 10
                )

            # 上がり3F (column 11)
            last_3f = None
            if len(cols) > 11:
                last_3f_text = cols[11].get_text(strip=True)
                try:
                    last_3f = float(last_3f_text)
                except ValueError:
                    pass

            results[horse_number] = {
                "position": position,
                "time_seconds": time_seconds,
                "last_3f": last_3f,
                "horse_id": horse_id,
            }

        except Exception as e:
            continue

    return results


async def calculate_horse_history(
    fetcher: NetkeibaFetcher,
    horse_id: str,
    race_date: str,
    cache: dict,
) -> dict:
    """
    Calculate horse history features from past race results.

    Args:
        fetcher: NetkeibaFetcher instance
        horse_id: Netkeiba horse ID
        race_date: Current race date (YYYY-MM-DD format) to filter past results
        cache: Cache dict to store/reuse horse results

    Returns:
        Dict with history features
    """
    # Default values for horses with no history
    default = {
        "total_races": 0,
        "total_wins": 0,
        "total_places": 0,
        "grade_wins": 0,
        "win_rate": 0.0,
        "place_rate": 0.0,
        "avg_position_last5": 10.0,
        "best_last_3f": None,
        "avg_last_3f_hist": None,
        "days_since_last_race": 365,
    }

    if not horse_id:
        return default

    # Check cache first
    cache_key = horse_id
    if cache_key not in cache:
        # Fetch horse results (up to 20 past races)
        results = await fetcher.fetch_horse_results(horse_id, limit=20)
        cache[cache_key] = results

    all_results = cache[cache_key]

    if not all_results:
        return default

    # Filter results before the current race date
    # race_date format: YYYY-MM-DD, result.race_date format may vary
    past_results = []
    for r in all_results:
        # Try to parse result date (various formats)
        try:
            # Try format: YYYY/MM/DD
            if "/" in r.race_date:
                parts = r.race_date.split("/")
                result_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            else:
                result_date = r.race_date

            if result_date < race_date:
                past_results.append(r)
        except Exception:
            past_results.append(r)  # Include if can't parse date

    if not past_results:
        return default

    # Calculate features
    total_races = len(past_results)
    total_wins = sum(1 for r in past_results if r.position == 1)
    total_places = sum(1 for r in past_results if 1 <= r.position <= 3)

    # Grade wins (races with G1, G2, G3 in name)
    grade_wins = sum(
        1 for r in past_results
        if r.position == 1 and any(g in r.race_name for g in ["G1", "G2", "G3", "(G"])
    )

    # Win/place rate
    win_rate = total_wins / total_races if total_races > 0 else 0.0
    place_rate = total_places / total_races if total_races > 0 else 0.0

    # Average position in last 5 races
    last_5 = [r for r in past_results[:5] if r.position > 0]
    avg_position_last5 = (
        sum(r.position for r in last_5) / len(last_5)
        if last_5 else 10.0
    )

    # Best and average last 3F
    last_3f_values = [r.last_3f for r in past_results if r.last_3f and r.last_3f > 0]
    best_last_3f = min(last_3f_values) if last_3f_values else None
    avg_last_3f_hist = (
        sum(last_3f_values) / len(last_3f_values)
        if last_3f_values else None
    )

    # Days since last race
    days_since_last_race = 365  # Default
    if past_results:
        try:
            last_race_date = past_results[0].race_date
            if "/" in last_race_date:
                parts = last_race_date.split("/")
                last_race_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"

            from datetime import datetime as dt
            current = dt.strptime(race_date, "%Y-%m-%d")
            last = dt.strptime(last_race_date, "%Y-%m-%d")
            days_since_last_race = (current - last).days
        except Exception:
            pass

    return {
        "total_races": total_races,
        "total_wins": total_wins,
        "total_places": total_places,
        "grade_wins": grade_wins,
        "win_rate": round(win_rate, 3),
        "place_rate": round(place_rate, 3),
        "avg_position_last5": round(avg_position_last5, 2),
        "best_last_3f": best_last_3f,
        "avg_last_3f_hist": round(avg_last_3f_hist, 2) if avg_last_3f_hist else None,
        "days_since_last_race": days_since_last_race,
    }


async def collect_training_data(race_ids: list[str], output_file: str, with_history: bool = False):
    """Collect training data from multiple races."""
    all_data = []
    horse_cache = {}  # Cache for horse history

    async with NetkeibaFetcher() as fetcher:
        for i, race_id in enumerate(race_ids):
            print(f"Processing race {i+1}/{len(race_ids)}: {race_id}")

            try:
                # Get basic training data
                data_list = await fetch_race_result(fetcher, race_id)

                if not data_list:
                    continue

                # Get detailed results (position, time, last_3f, horse_id)
                result_details = await fetch_result_details(fetcher, race_id)

                # Merge detail info and optionally fetch horse history
                for data in data_list:
                    details = result_details.get(data.horse_number, {})
                    data.position = details.get("position", 0)
                    data.time_seconds = details.get("time_seconds")
                    data.last_3f = details.get("last_3f")
                    data.is_win = 1 if data.position == 1 else 0
                    data.is_place = 1 if 1 <= data.position <= 3 else 0

                    # Fetch horse history if requested
                    if with_history:
                        horse_id = details.get("horse_id")
                        if horse_id and data.race_date:
                            history = await calculate_horse_history(
                                fetcher, horse_id, data.race_date, horse_cache
                            )
                            # Update data with history features
                            data.total_races = history["total_races"]
                            data.total_wins = history["total_wins"]
                            data.total_places = history["total_places"]
                            data.grade_wins = history["grade_wins"]
                            data.win_rate = history["win_rate"]
                            data.place_rate = history["place_rate"]
                            data.avg_position_last5 = history["avg_position_last5"]
                            data.best_last_3f = history["best_last_3f"]
                            data.avg_last_3f_hist = history["avg_last_3f_hist"]
                            data.days_since_last_race = history["days_since_last_race"]

                all_data.extend(data_list)

                if with_history:
                    print(f"    Processed {len(data_list)} entries (cache size: {len(horse_cache)})")

            except Exception as e:
                print(f"  Error processing {race_id}: {e}")
                continue

    # Save to CSV
    if all_data:
        print(f"\nSaving {len(all_data)} records to {output_file}")

        fieldnames = list(asdict(all_data[0]).keys())

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for data in all_data:
                writer.writerow(asdict(data))

        print(f"Done! Saved to {output_file}")
    else:
        print("No data collected.")


def load_race_ids(grade: str, data_dir: str) -> list[str]:
    """Load race IDs for the specified grade."""
    if grade == "G1":
        return KNOWN_G1_RACE_IDS
    elif grade in ("G2", "G3"):
        json_file = os.path.join(data_dir, f"{grade.lower()}_race_ids.json")
        if not os.path.exists(json_file):
            print(f"Error: {json_file} not found.")
            print(f"Run: python scripts/fetch_grade_race_ids.py --grade {grade}")
            return []
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("race_ids", [])
    else:
        return []


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Collect historical race data for ML training")
    parser.add_argument(
        "--grade",
        choices=["G1", "G2", "G3", "all"],
        default="G1",
        help="Grade to collect (default: G1)",
    )
    parser.add_argument(
        "--with-history",
        action="store_true",
        help="Fetch horse past race history for additional features (slower)",
    )
    args = parser.parse_args()

    # Determine which grades to process
    grades = ["G1", "G3"] if args.grade == "all" else [args.grade]

    # Base directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    training_dir = os.path.join(data_dir, "training")
    os.makedirs(training_dir, exist_ok=True)

    for grade in grades:
        # Load race IDs for this grade
        race_ids = load_race_ids(grade, data_dir)
        if not race_ids:
            print(f"No race IDs found for {grade}, skipping...")
            continue

        # Output file (add _hist suffix if with history)
        suffix = "_hist" if args.with_history else ""
        output_file = os.path.join(training_dir, f"{grade.lower()}_races{suffix}.csv")

        print(f"\n{'='*60}")
        print(f"Collecting training data from {len(race_ids)} {grade} races...")
        if args.with_history:
            print("Including horse history features (this will take longer)")
        print(f"Output: {output_file}")
        print(f"{'='*60}\n")

        await collect_training_data(race_ids, output_file, with_history=args.with_history)


if __name__ == "__main__":
    asyncio.run(main())
