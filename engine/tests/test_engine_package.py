import cloverproof_engine


def test_engine_exposes_version() -> None:
    assert cloverproof_engine.__version__ == "0.3.0"
