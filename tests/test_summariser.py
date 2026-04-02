from market_monitor.app.models import ArticlePayload
from market_monitor.app.processors.summariser import RuleBasedSummariser


def test_summariser_includes_title_context_and_description_detail() -> None:
    summariser = RuleBasedSummariser()
    article = ArticlePayload(
        title="JPMorgan earnings beat forecasts as net interest income rises",
        source="Reuters",
        url="https://example.com/story",
        sector="banking",
        description="The bank raised guidance after stronger-than-expected quarterly results and highlighted resilient consumer credit trends.",
    )

    summary, why_it_matters = summariser.summarise(
        article,
        matched_keywords=["jpmorgan", "net interest income"],
    )

    assert "JPMorgan earnings beat forecasts" in summary
    assert "raised guidance" in summary
    assert "jpmorgan" in why_it_matters.lower()
    assert "net interest income" in why_it_matters.lower()
