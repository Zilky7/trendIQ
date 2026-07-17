from pathlib import Path


def test_example_environment_never_contains_a_secret() -> None:
    text = Path("../../.env.example").read_text()
    assert "AI_API_KEY=" in text
    assert "TF7" not in text
