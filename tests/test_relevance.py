from market_monitor.app.filters.relevance import RelevanceScorer
from market_monitor.app.models import ArticlePayload


def test_relevance_scores_macro_story_highest() -> None:
    scorer = RelevanceScorer()
    article = ArticlePayload(
        title="Fed signals slower pace of rate cuts as inflation remains sticky",
        source="Reuters",
        url="https://example.com/macro-story",
        description="Bond yields rise after the Federal Reserve points to tighter monetary policy.",
    )

    result = scorer.score(article)

    assert result.sector == "macro_rates"
    assert result.score >= 7
    assert "fed" in [keyword.lower() for keyword in result.matched_keywords]


def test_relevance_rejects_non_market_moving_finance_story() -> None:
    scorer = RelevanceScorer()
    article = ArticlePayload(
        title="Top banking apps to watch this year",
        source="CNBC",
        url="https://example.com/soft-story",
        description="A broad look at consumer trends in digital finance and app design.",
    )

    result = scorer.score(article)

    assert result.sector is None
    assert result.score == 0.0


def test_relevance_keeps_major_bank_earnings_story() -> None:
    scorer = RelevanceScorer()
    article = ArticlePayload(
        title="JPMorgan earnings beat forecasts as net interest income rises",
        source="Reuters",
        url="https://example.com/jpm-earnings",
        description="The bank raised guidance after stronger-than-expected quarterly results.",
    )

    result = scorer.score(article)

    assert result.sector == "banking"
    assert result.score >= 9
