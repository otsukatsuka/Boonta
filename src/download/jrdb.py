"""JRDB file downloader with HTTP Basic auth, ZIP/LZH extraction."""
from __future__ import annotations

import time
import zipfile
from pathlib import Path

import httpx
import lhafile

from config.settings import Settings

# File type configuration: (URL path prefix, archive format, file prefix)
FILE_TYPES = {
    "KYI": ("Kyi/", "zip", "KYI"),
    "SED": ("Sed/", "zip", "SED"),
    "HJC": ("Hjc/", "lzh", "HJC"),
}


class JRDBDownloader:
    """Downloads and extracts JRDB data files."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.output_dir = self.settings.data_raw_dir

    def _build_url(self, file_type: str, date_str: str) -> str:
        """Build download URL for a given file type and date.

        Args:
            file_type: One of "KYI", "SED", "HJC".
            date_str: Date in YYMMDD format (e.g. "260405").
        """
        path_prefix, archive_fmt, file_prefix = FILE_TYPES[file_type]
        filename = f"{file_prefix}{date_str}.{archive_fmt}"
        return f"{self.settings.jrdb_base_url}{path_prefix}{filename}"

    def _extract_zip(self, archive_path: Path) -> list[Path]:
        """Extract ZIP archive, return list of extracted file paths."""
        extracted = []
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                zf.extract(name, self.output_dir)
                extracted.append(self.output_dir / name)
        return extracted

    def _extract_lzh(self, archive_path: Path) -> list[Path]:
        """Extract LZH archive using lhafile, return list of extracted file paths."""
        extracted = []
        lha = lhafile.Lhafile(str(archive_path))
        for name in lha.namelist():
            data = lha.read(name)
            out_path = self.output_dir / name
            out_path.write_bytes(data)
            extracted.append(out_path)
        return extracted

    def download_file(
        self,
        file_type: str,
        date_str: str,
        client: httpx.Client | None = None,
    ) -> list[Path]:
        """Download and extract a single JRDB file.

        Args:
            file_type: One of "KYI", "SED", "HJC".
            date_str: Date in YYMMDD format.
            client: Optional httpx.Client (for testing/reuse).

        Returns:
            List of extracted file paths.
        """
        if file_type not in FILE_TYPES:
            raise ValueError(f"Unknown file type: {file_type}. Must be one of {list(FILE_TYPES)}")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        url = self._build_url(file_type, date_str)
        _, archive_fmt, file_prefix = FILE_TYPES[file_type]
        archive_path = self.output_dir / f"{file_prefix}{date_str}.{archive_fmt}"

        own_client = client is None
        if own_client:
            client = httpx.Client()

        try:
            auth = (self.settings.jrdb_user, self.settings.jrdb_pass)
            response = client.get(url, auth=auth, follow_redirects=True)
            response.raise_for_status()

            archive_path.write_bytes(response.content)

            if archive_fmt == "zip":
                extracted = self._extract_zip(archive_path)
            else:
                extracted = self._extract_lzh(archive_path)

            # Clean up archive
            archive_path.unlink()
            return extracted

        finally:
            if own_client:
                client.close()

    def download_date_range(
        self,
        file_type: str,
        dates: list[str],
        delay: float = 1.0,
    ) -> dict[str, list[Path]]:
        """Download files for multiple dates.

        Args:
            file_type: One of "KYI", "SED", "HJC".
            dates: List of dates in YYMMDD format.
            delay: Seconds to wait between requests (rate limiting).

        Returns:
            Dict mapping date_str to list of extracted paths.
        """
        results: dict[str, list[Path]] = {}

        with httpx.Client() as client:
            for i, date_str in enumerate(dates):
                try:
                    extracted = self.download_file(file_type, date_str, client=client)
                    results[date_str] = extracted
                except httpx.HTTPStatusError as e:
                    print(f"Failed to download {file_type} for {date_str}: {e}")
                    results[date_str] = []

                if i < len(dates) - 1:
                    time.sleep(delay)

        return results
