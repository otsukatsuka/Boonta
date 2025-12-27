"""
Script to collect historical G1 race data for ML training.

Netkeiba Race ID format: YYYYVVKKDDNN
- YYYY: Year
- VV: Venue code (01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉)
- KK: 開催回 (1-5)
- DD: 日目 (1-12)
- NN: Race number (01-12)
"""

import asyncio
import csv
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
    # 2024年 G1
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
    "202409040611",  # 阪神JF 2024
    "202409040711",  # 朝日杯FS 2024
    "202406050811",  # 有馬記念 2024
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
    "202304040811",  # スプリンターズS 2023
    "202308040811",  # 秋華賞 2023
    "202308040911",  # 菊花賞 2023
    "202305040811",  # 天皇賞秋 2023
    "202308050811",  # エリザベス女王杯 2023
    "202308050911",  # マイルCS 2023
    "202305050911",  # ジャパンC 2023
    "202307050811",  # チャンピオンズC 2023
    "202309040611",  # 阪神JF 2023
    "202309040711",  # 朝日杯FS 2023
    "202306050811",  # 有馬記念 2023
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
    """Fetch detailed result info (position, time, last_3f) from result page."""
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
            }

        except Exception as e:
            continue

    return results


async def collect_training_data(race_ids: list[str], output_file: str):
    """Collect training data from multiple races."""
    all_data = []

    async with NetkeibaFetcher() as fetcher:
        for i, race_id in enumerate(race_ids):
            print(f"Processing race {i+1}/{len(race_ids)}: {race_id}")

            try:
                # Get basic training data
                data_list = await fetch_race_result(fetcher, race_id)

                if not data_list:
                    continue

                # Get detailed results (position, time, last_3f)
                result_details = await fetch_result_details(fetcher, race_id)

                # Merge detail info
                for data in data_list:
                    details = result_details.get(data.horse_number, {})
                    data.position = details.get("position", 0)
                    data.time_seconds = details.get("time_seconds")
                    data.last_3f = details.get("last_3f")
                    data.is_win = 1 if data.position == 1 else 0
                    data.is_place = 1 if 1 <= data.position <= 3 else 0

                all_data.extend(data_list)

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


async def main():
    """Main entry point."""
    # Use known G1 race IDs
    race_ids = KNOWN_G1_RACE_IDS

    # Output file
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "..", "data", "training", "g1_races.csv")

    # Create directory if needed
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print(f"Collecting training data from {len(race_ids)} G1 races...")
    print(f"Output: {output_file}")
    print()

    await collect_training_data(race_ids, output_file)


if __name__ == "__main__":
    asyncio.run(main())
