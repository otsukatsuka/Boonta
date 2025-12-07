"""Netkeiba.com data fetcher."""

import asyncio
import re
from datetime import datetime

from bs4 import BeautifulSoup

from app.fetchers.base import DataFetcher, EntryInfo, RaceInfo, ResultInfo


class NetkeibaFetcher(DataFetcher):
    """
    Data fetcher for netkeiba.com.

    Note: This implementation is a template. Actual scraping logic
    needs to be adjusted based on the current website structure.
    Always respect robots.txt and terms of service.
    """

    BASE_URL = "https://race.netkeiba.com"
    DB_URL = "https://db.netkeiba.com"

    async def fetch_race_info(self, race_id: str) -> RaceInfo | None:
        """
        Fetch race information from netkeiba.

        Args:
            race_id: Netkeiba race ID (e.g., "202405020811")

        Returns:
            RaceInfo or None if not found
        """
        url = f"{self.BASE_URL}/race/{race_id}/"

        try:
            await asyncio.sleep(self.delay)
            response = await self.client.get(url)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "lxml")

            # Parse race info
            # Note: Selectors need to be updated based on actual HTML structure
            race_name = self._extract_text(soup, ".RaceName")
            race_data = self._extract_text(soup, ".RaceData01")

            if not race_name:
                return None

            # Parse race data (distance, course type, etc.)
            distance = 2000  # Default
            course_type = "芝"
            venue = "東京"
            grade = "G1"

            # Extract distance from race data
            distance_match = re.search(r"(\d{4})m", race_data or "")
            if distance_match:
                distance = int(distance_match.group(1))

            # Extract course type
            if "ダート" in (race_data or ""):
                course_type = "ダート"

            # Parse date
            date_elem = soup.select_one(".RaceData02")
            race_date = datetime.now().strftime("%Y-%m-%d")
            if date_elem:
                date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_elem.text)
                if date_match:
                    race_date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"

            return RaceInfo(
                external_id=race_id,
                name=race_name,
                date=race_date,
                venue=venue,
                course_type=course_type,
                distance=distance,
                grade=grade,
            )

        except Exception:
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

            soup = BeautifulSoup(response.text, "lxml")
            entries = []

            # Parse entry table
            # Note: Selectors need to be updated based on actual HTML structure
            rows = soup.select(".HorseList tr")

            for row in rows:
                try:
                    horse_number = self._extract_text(row, ".Waku span")
                    horse_name = self._extract_text(row, ".HorseName a")
                    jockey_name = self._extract_text(row, ".Jockey a")
                    weight = self._extract_text(row, ".Weight")

                    if not horse_name or not horse_number:
                        continue

                    entry = EntryInfo(
                        horse_name=horse_name,
                        horse_number=int(horse_number) if horse_number.isdigit() else 0,
                        post_position=1,  # TODO: Extract from HTML
                        jockey_name=jockey_name or "",
                        weight=float(weight) if weight and weight.replace(".", "").isdigit() else 55.0,
                    )
                    entries.append(entry)

                except Exception:
                    continue

            return entries

        except Exception:
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
        url = f"{self.DB_URL}/horse/{horse_id}/"

        try:
            await asyncio.sleep(self.delay)
            response = await self.client.get(url)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "lxml")
            results = []

            # Parse result table
            # Note: Selectors need to be updated based on actual HTML structure
            rows = soup.select(".db_h_race_results tr")[1:limit + 1]  # Skip header

            for row in rows:
                try:
                    cols = row.select("td")
                    if len(cols) < 10:
                        continue

                    race_date = self._extract_text(cols[0], "a")
                    venue = self._extract_text(cols[1], "a")
                    race_name = self._extract_text(cols[4], "a")
                    position = self._extract_text(cols[5], None)
                    time_str = self._extract_text(cols[7], None)
                    last_3f = self._extract_text(cols[11], None)

                    # Parse time
                    time_seconds = None
                    if time_str:
                        time_match = re.match(r"(\d):(\d{2})\.(\d)", time_str)
                        if time_match:
                            time_seconds = (
                                int(time_match.group(1)) * 60
                                + int(time_match.group(2))
                                + int(time_match.group(3)) / 10
                            )

                    result = ResultInfo(
                        race_name=race_name or "",
                        race_date=race_date or "",
                        venue=venue or "",
                        distance=2000,  # TODO: Extract from race name/link
                        course_type="芝",  # TODO: Extract
                        position=int(position) if position and position.isdigit() else 0,
                        time=time_seconds,
                        last_3f=float(last_3f) if last_3f else None,
                    )
                    results.append(result)

                except Exception:
                    continue

            return results

        except Exception:
            return []

    def _extract_text(self, element, selector: str | None) -> str | None:
        """Extract text from element or its child."""
        if element is None:
            return None

        if selector:
            child = element.select_one(selector)
            if child:
                return child.get_text(strip=True)
            return None

        return element.get_text(strip=True)
