from market_monitor.app.models import ArticlePayload
from market_monitor.app.processors.investor_analysis import InvestorAnalyzer


def test_investor_analysis_classifies_positive_bank_earnings_story() -> None:
    analyzer = InvestorAnalyzer()
    article = ArticlePayload(
        title="JPMorgan earnings beat expectations and raises guidance",
        source="Reuters",
        url="https://example.com/jpm",
        sector="banking",
        relevance_score=8.0,
        description="Shares rise after stronger revenue and resilient net interest income.",
    )

    analysis = analyzer.analyse(article)

    assert analysis.event_type == "earnings"
    assert analysis.direction == "positive"
    assert "JPMorgan" in analysis.impacted_assets
    assert analysis.importance_score >= 8


def test_investor_analysis_classifies_negative_regulation_story() -> None:
    analyzer = InvestorAnalyzer()
    article = ArticlePayload(
        title="PayPal faces antitrust lawsuit over payments practices",
        source="Bloomberg",
        url="https://example.com/paypal",
        sector="fintech",
        relevance_score=7.0,
        description="The case increases regulatory pressure on digital payments providers.",
    )

    analysis = analyzer.analyse(article)

    assert analysis.event_type == "regulation"
    assert analysis.direction == "negative"
    assert "PayPal" in analysis.impacted_assets
