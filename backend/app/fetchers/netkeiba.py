"""Netkeiba.com data fetcher."""

import asyncio
import re

from bs4 import BeautifulSoup

from app.fetchers.base import DataFetcher, EntryInfo, OddsInfo, RaceInfo, ResultInfo


class NetkeibaFetcher(DataFetcher):
    """
    Data fetcher for netkeiba.com.

    Note: Scraping logic based on netkeiba HTML structure as of Dec 2024.
    Always respect robots.txt and terms of service.
    """

    BASE_URL = "https://race.netkeiba.com"
    DB_URL = "https://db.netkeiba.com"

    async def fetch_race_info(self, race_id: str) -> RaceInfo | None:
        """
        Fetch race information from netkeiba.

        Args:
            race_id: Netkeiba race ID (e.g., "202406050811")

        Returns:
            RaceInfo or None if not found
        """
        url = f"{self.BASE_URL}/race/shutuba.html?race_id={race_id}"

        try:
            await asyncio.sleep(self.delay)
            response = await self.client.get(url)

            if response.status_code != 200:
                return None

            # Decode EUC-JP
            html = response.content.decode("euc-jp", errors="ignore")
            soup = BeautifulSoup(html, "lxml")

            # Parse race name from title
            title_elem = soup.select_one("title")
            if not title_elem:
                return None

            title_text = title_elem.get_text()
            # Title format: "レース名(G1) 出馬表 | 2024年12月22日 中山11R..."
            race_name_match = re.match(r"(.+?)\s*出馬表", title_text)
            race_name = race_name_match.group(1).strip() if race_name_match else "Unknown"

            # Parse race data from RaceData01
            race_data = soup.select_one(".RaceData01")
            race_data_text = race_data.get_text() if race_data else ""

            # Extract distance
            distance = 2000
            distance_match = re.search(r"(\d{4})m", race_data_text)
            if distance_match:
                distance = int(distance_match.group(1))

            # Extract course type
            course_type = "芝"
            if "ダート" in race_data_text or "ダ" in race_data_text:
                course_type = "ダート"

            # Parse venue and date from RaceData02
            race_data2 = soup.select_one(".RaceData02")
            venue = "東京"
            race_date = ""

            if race_data2:
                data2_text = race_data2.get_text()
                # Extract venue (e.g., "中山", "東京", "阪神")
                venue_match = re.search(r"(東京|中山|阪神|京都|中京|小倉|新潟|福島|札幌|函館)", data2_text)
                if venue_match:
                    venue = venue_match.group(1)

                # Extract date
                date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", data2_text)
                if date_match:
                    race_date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"

            # Extract grade
            grade = "OP"
            if "G1" in race_name or "(G1)" in title_text:
                grade = "G1"
            elif "G2" in race_name or "(G2)" in title_text:
                grade = "G2"
            elif "G3" in race_name or "(G3)" in title_text:
                grade = "G3"

            return RaceInfo(
                external_id=race_id,
                name=race_name,
                date=race_date,
                venue=venue,
                course_type=course_type,
                distance=distance,
                grade=grade,
            )

        except Exception as e:
            print(f"Error fetching race info: {e}")
            return None

    async def fetch_entries(self, race_id: str) -> list[EntryInfo]:
        """
        Fetch entry information for a race.

        Args:
            race_id: Netkeiba race ID

        Returns:
            List of EntryInfo
        """
        url = f"{self.BASE_URL}/race/shutuba.html?race_id={race_id}"

        try:
            await asyncio.sleep(self.delay)
            response = await self.client.get(url)

            if response.status_code != 200:
                return []

            # Decode EUC-JP
            html = response.content.decode("euc-jp", errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            entries = []

            # Find all horse rows
            rows = soup.select("tr.HorseList")

            for row in rows:
                try:
                    # Skip cancelled horses
                    if "Cancel" in row.get("class", []):
                        continue

                    # Extract horse number from Umaban cell
                    umaban_cell = row.select_one("td[class*='Umaban']")
                    horse_number = 0
                    if umaban_cell:
                        horse_number = int(umaban_cell.get_text(strip=True))

                    # Extract post position (waku) from Waku cell
                    waku_cell = row.select_one("td[class*='Waku'] span")
                    post_position = 1
                    if waku_cell:
                        post_position = int(waku_cell.get_text(strip=True))

                    # Extract horse name
                    horse_name_elem = row.select_one("span.HorseName a")
                    horse_name = ""
                    if horse_name_elem:
                        horse_name = horse_name_elem.get("title", "") or horse_name_elem.get_text(strip=True)

                    if not horse_name:
                        continue

                    # Extract jockey name
                    jockey_cell = row.select_one("td.Jockey a")
                    jockey_name = ""
                    if jockey_cell:
                        jockey_name = jockey_cell.get("title", "") or jockey_cell.get_text(strip=True)

                    # Extract weight (斤量)
                    # It's in a td after Barei, usually 6th td
                    tds = row.select("td")
                    weight = 55.0
                    for i, td in enumerate(tds):
                        if "Barei" in td.get("class", []):
                            # Next td should be weight
                            if i + 1 < len(tds):
                                weight_text = tds[i + 1].get_text(strip=True)
                                try:
                                    weight = float(weight_text)
                                except ValueError:
                                    pass
                            break

                    # Extract horse weight from Weight cell
                    weight_cell = row.select_one("td.Weight")
                    horse_weight = None
                    horse_weight_diff = None
                    if weight_cell:
                        weight_text = weight_cell.get_text(strip=True)
                        # Format: "520(-2)" or "520"
                        hw_match = re.match(r"(\d+)\s*(?:\(([+-]?\d+)\))?", weight_text)
                        if hw_match:
                            horse_weight = int(hw_match.group(1))
                            if hw_match.group(2):
                                horse_weight_diff = int(hw_match.group(2))

                    # Extract trainer
                    trainer_cell = row.select_one("td.Trainer a")
                    trainer = ""
                    if trainer_cell:
                        trainer = trainer_cell.get("title", "") or trainer_cell.get_text(strip=True)

                    entry = EntryInfo(
                        horse_name=horse_name,
                        horse_number=horse_number,
                        post_position=post_position,
                        jockey_name=jockey_name,
                        weight=weight,
                        horse_weight=horse_weight,
                        horse_weight_diff=horse_weight_diff,
                        trainer=trainer,
                    )
                    entries.append(entry)

                except Exception as e:
                    print(f"Error parsing entry row: {e}")
                    continue

            return entries

        except Exception as e:
            print(f"Error fetching entries: {e}")
            return []

    async def fetch_horse_results(
        self, horse_id: str, limit: int = 10
    ) -> list[ResultInfo]:
        """
        Fetch past race results for a horse.

        Args:
            horse_id: Netkeiba horse ID
            limit: Maximum number of results to fetch

        Returns:
            List of ResultInfo
        """
        url = f"{self.DB_URL}/horse/result/{horse_id}/"

        try:
            await asyncio.sleep(self.delay)
            response = await self.client.get(url)

            if response.status_code != 200:
                return []

            html = response.content.decode("euc-jp", errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            results = []

            # Parse result table
            rows = soup.select(".db_h_race_results tr")

            count = 0
            for row in rows:
                if count >= limit:
                    break
                try:
                    cols = row.select("td")
                    if len(cols) < 20:
                        continue

                    # Column structure:
                    # 0: 日付, 1: 競馬場, 2: 天気, 3: R, 4: レース名
                    # 5: (映像), 6: 頭数, 7: 枠, 8: 馬番, 9: オッズ, 10: 人気, 11: 着順
                    # 12: (騎手), 13: 斤量, 14: 距離, 15: (馬場指数), 16: 馬場
                    # 17: (なにか), 18: タイム, 19: 着差, 20: (なにか), 21: 通過順
                    # 22: ペース, 23: 上がり3F, 24: 馬体重

                    race_date = cols[0].get_text(strip=True)
                    venue = cols[1].get_text(strip=True)
                    race_name_elem = cols[4].select_one("a")
                    race_name = race_name_elem.get("title", "") if race_name_elem else cols[4].get_text(strip=True)

                    # 着順
                    position_text = cols[11].get_text(strip=True)
                    position = 0
                    if position_text.isdigit():
                        position = int(position_text)
                    elif position_text in ["取", "除", "中"]:
                        continue  # 取消・除外・中止はスキップ

                    # 人気
                    popularity = None
                    pop_text = cols[10].get_text(strip=True)
                    if pop_text.isdigit():
                        popularity = int(pop_text)

                    # 距離
                    distance_text = cols[14].get_text(strip=True)
                    distance = 2000
                    course_type = "芝"
                    dist_match = re.search(r"(芝|ダ)(\d+)", distance_text)
                    if dist_match:
                        course_type = "芝" if dist_match.group(1) == "芝" else "ダート"
                        distance = int(dist_match.group(2))

                    # 馬場状態
                    track_condition = cols[16].get_text(strip=True) if len(cols) > 16 else None

                    # タイム
                    time_str = cols[18].get_text(strip=True) if len(cols) > 18 else ""
                    time_seconds = None
                    if time_str:
                        time_match = re.match(r"(\d):(\d{2})\.(\d)", time_str)
                        if time_match:
                            time_seconds = (
                                int(time_match.group(1)) * 60
                                + int(time_match.group(2))
                                + int(time_match.group(3)) / 10
                            )

                    # 通過順
                    corner_text = cols[21].get_text(strip=True) if len(cols) > 21 else ""
                    corner_positions = self._parse_corner_positions(corner_text)

                    # 上がり3F
                    last_3f = None
                    if len(cols) > 23:
                        last_3f_text = cols[23].get_text(strip=True)
                        try:
                            last_3f = float(last_3f_text)
                        except ValueError:
                            pass

                    result = ResultInfo(
                        race_name=race_name,
                        race_date=race_date,
                        venue=venue,
                        distance=distance,
                        course_type=course_type,
                        position=position,
                        time=time_seconds,
                        last_3f=last_3f,
                        track_condition=track_condition,
                        corner_positions=corner_positions,
                        popularity=popularity,
                    )
                    results.append(result)
                    count += 1

                except Exception as e:
                    print(f"Error parsing result row: {e}")
                    continue

            return results

        except Exception as e:
            print(f"Error fetching horse results: {e}")
            return []

    async def fetch_odds_from_result(self, race_id: str) -> list[OddsInfo]:
        """
        Fetch odds and running style from race result page.

        Args:
            race_id: Netkeiba race ID

        Returns:
            List of OddsInfo with odds, popularity, and estimated running style
        """
        url = f"{self.DB_URL}/race/{race_id}/"

        try:
            await asyncio.sleep(self.delay)
            response = await self.client.get(url)

            if response.status_code != 200:
                return []

            html = response.content.decode("euc-jp", errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            odds_list = []

            # Find result table rows
            rows = soup.select("table.race_table_01 tr")

            for row in rows:
                try:
                    cols = row.select("td")
                    if len(cols) < 14:
                        continue

                    # Column indices (0-indexed):
                    # 0: 着順, 1: 枠, 2: 馬番, 3: 馬名, 4: 性齢, 5: 斤量
                    # 6: 騎手, 7: タイム, 8: 着差, 9: スピード指数, 10: 通過順
                    # 11: 上がり3F, 12: 単勝オッズ, 13: 人気

                    # Extract horse number
                    horse_number_text = cols[2].get_text(strip=True)
                    if not horse_number_text.isdigit():
                        continue
                    horse_number = int(horse_number_text)

                    # Extract odds (column 12)
                    odds_text = cols[12].get_text(strip=True)
                    try:
                        odds = float(odds_text)
                    except ValueError:
                        odds = 99.9

                    # Extract popularity (column 13)
                    popularity_text = cols[13].get_text(strip=True)
                    try:
                        popularity = int(popularity_text)
                    except ValueError:
                        popularity = 99

                    # Extract corner positions (column 10)
                    corner_text = cols[10].get_text(strip=True)
                    corner_positions = self._parse_corner_positions(corner_text)

                    # Estimate running style from corner positions
                    running_style = self._estimate_running_style(corner_positions)

                    odds_list.append(OddsInfo(
                        horse_number=horse_number,
                        odds=odds,
                        popularity=popularity,
                        corner_positions=corner_positions,
                        running_style=running_style,
                    ))

                except Exception as e:
                    print(f"Error parsing odds row: {e}")
                    continue

            return odds_list

        except Exception as e:
            print(f"Error fetching odds: {e}")
            return []

    def _parse_corner_positions(self, corner_text: str) -> list[int]:
        """Parse corner positions from text like '6-5-5-3'."""
        positions = []
        # Remove parentheses and asterisks
        clean = re.sub(r"[\(\)\*]", "", corner_text)
        parts = clean.split("-")
        for part in parts:
            try:
                positions.append(int(part.strip()))
            except ValueError:
                continue
        return positions

    def _estimate_running_style(self, corner_positions: list[int]) -> str:
        """
        Estimate running style from corner positions.

        ESCAPE: 逃げ - Usually in 1st-2nd position at first corner
        FRONT: 先行 - Usually in 3rd-5th position
        STALKER: 差し - Usually in 6th-10th position
        CLOSER: 追込 - Usually in 11th+ position
        """
        if not corner_positions:
            return "VERSATILE"

        first_corner = corner_positions[0]

        if first_corner <= 2:
            return "ESCAPE"
        elif first_corner <= 5:
            return "FRONT"
        elif first_corner <= 10:
            return "STALKER"
        else:
            return "CLOSER"
