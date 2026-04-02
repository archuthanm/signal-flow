from datetime import UTC, datetime, timedelta

from market_monitor.app.collectors.rss_collector import RSSCollector


def test_collector_rejects_low_signal_title() -> None:
    collector = RSSCollector()

    assert collector._is_low_signal_title("Top Fintech Stocks Redefining Banking, Payments and Investing") is True
    assert collector._is_low_signal_title("ECB signals caution on further rate cuts") is False


def test_collector_rejects_stale_articles() -> None:
    collector = RSSCollector()
    old_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=40)

    assert collector._is_stale(old_date) is True
    assert collector._is_stale(datetime.now(UTC).replace(tzinfo=None)) is False


def test_collector_allows_formal_publishers_only() -> None:
    collector = RSSCollector()

    assert collector._is_allowed_source("Professional Markets", "Reuters") is True
    assert collector._is_allowed_source("Nasdaq FinTech", "Nasdaq") is False


def test_collector_extracts_source_from_google_news_title() -> None:
    collector = RSSCollector()

    assert collector._extract_source_from_title("Fed signals caution on rates - Reuters") == "Reuters"
    assert collector._strip_source_suffix("Fed signals caution on rates - Reuters", "Reuters") == "Fed signals caution on rates"
