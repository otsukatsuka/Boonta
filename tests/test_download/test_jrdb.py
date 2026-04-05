"""Tests for JRDB downloader with mock HTTP responses."""
import io
import zipfile
from unittest.mock import MagicMock, patch

import httpx
import pytest

from config.settings import Settings
from src.download.jrdb import FILE_TYPES, JRDBDownloader


@pytest.fixture
def tmp_output_dir(tmp_path):
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    return raw_dir


@pytest.fixture
def settings(tmp_output_dir):
    s = Settings(
        jrdb_user="testuser",
        jrdb_pass="testpass",
        data_raw_dir=tmp_output_dir,
    )
    return s


@pytest.fixture
def downloader(settings):
    return JRDBDownloader(settings)


def _make_zip_bytes(filename: str, content: bytes) -> bytes:
    """Create a ZIP archive in memory with a single file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, content)
    return buf.getvalue()


class TestBuildURL:
    def test_kyi_url(self, downloader):
        url = downloader._build_url("KYI", "260405")
        assert url == "http://www.jrdb.com/member/datazip/Kyi/KYI260405.zip"

    def test_sed_url(self, downloader):
        url = downloader._build_url("SED", "260405")
        assert url == "http://www.jrdb.com/member/datazip/Sed/SED260405.zip"

    def test_hjc_url(self, downloader):
        url = downloader._build_url("HJC", "260405")
        assert url == "http://www.jrdb.com/member/datazip/Hjc/HJC260405.lzh"


class TestFileTypes:
    def test_all_types_defined(self):
        assert set(FILE_TYPES.keys()) == {"KYI", "SED", "HJC"}

    def test_invalid_type(self, downloader):
        with pytest.raises(ValueError, match="Unknown file type"):
            downloader.download_file("INVALID", "260405")


class TestDownloadFile:
    def test_download_and_extract_zip(self, downloader, tmp_output_dir):
        """Test downloading and extracting a ZIP file."""
        sample_content = b"test KYI data " * 50
        zip_bytes = _make_zip_bytes("KYI260405.txt", sample_content)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        extracted = downloader.download_file("KYI", "260405", client=mock_client)

        assert len(extracted) == 1
        assert extracted[0].name == "KYI260405.txt"
        assert extracted[0].exists()
        assert extracted[0].read_bytes() == sample_content

        # Archive should be cleaned up
        archive_path = tmp_output_dir / "KYI260405.zip"
        assert not archive_path.exists()

    def test_download_uses_auth(self, downloader):
        """Test that HTTP Basic auth credentials are passed."""
        zip_bytes = _make_zip_bytes("KYI260405.txt", b"data")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        downloader.download_file("KYI", "260405", client=mock_client)

        call_args = mock_client.get.call_args
        assert call_args.kwargs["auth"] == ("testuser", "testpass")

    def test_creates_output_dir(self, settings, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        new_dir = tmp_path / "new" / "dir"
        settings.data_raw_dir = new_dir
        dl = JRDBDownloader(settings)

        zip_bytes = _make_zip_bytes("KYI260405.txt", b"data")
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        dl.download_file("KYI", "260405", client=mock_client)
        assert new_dir.exists()

    def test_http_error_raises(self, downloader):
        """Test that HTTP errors are propagated."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            downloader.download_file("KYI", "260405", client=mock_client)


class TestDownloadDateRange:
    def test_multiple_dates(self, downloader):
        """Test downloading multiple dates."""
        zip_bytes = _make_zip_bytes("KYI260405.txt", b"data")
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx.Client, "get", return_value=mock_response):
            with patch.object(httpx.Client, "close"):
                results = downloader.download_date_range(
                    "KYI", ["260405", "260406"], delay=0
                )

        assert len(results) == 2

    def test_failed_date_continues(self, downloader):
        """Test that a failed download doesn't stop the batch."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mock = MagicMock()
                mock.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "404", request=MagicMock(), response=MagicMock()
                )
                return mock
            mock = MagicMock()
            mock.content = _make_zip_bytes("KYI260406.txt", b"data")
            mock.raise_for_status = MagicMock()
            return mock

        with patch.object(httpx.Client, "get", side_effect=side_effect):
            with patch.object(httpx.Client, "close"):
                results = downloader.download_date_range(
                    "KYI", ["260405", "260406"], delay=0
                )

        assert results["260405"] == []
        assert len(results["260406"]) == 1
