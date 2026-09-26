"""Tests for instrument lookup and caching."""

from pathlib import Path

from data_recorder.instruments import parse_instruments


def test_parse_instruments_from_fixture():
    """Test instrument parsing against hand-made CSV excerpt."""
    fixture_path = Path(__file__).parent / "fixtures" / "scrip_master_excerpt.csv"
    csv_text = fixture_path.read_text()
    
    result = parse_instruments(csv_text)
    
    # Check indices
    assert "NIFTY" in result["indices"]
    assert result["indices"]["NIFTY"] == 13
    assert "BANKNIFTY" in result["indices"]
    assert result["indices"]["BANKNIFTY"] == 25
    assert "SENSEX" in result["indices"]
    assert result["indices"]["SENSEX"] == 51
    
    # Check futures (current month: 2026-09-24)
    assert "NIFTYFUT" in result["futures"]
    assert result["futures"]["NIFTYFUT"]["security_id"] == 42100
    assert result["futures"]["NIFTYFUT"]["expiry"] == "2026-09-24"
    
    assert "BANKNIFTYFUT" in result["futures"]
    assert result["futures"]["BANKNIFTYFUT"]["security_id"] == 42101
    
    assert "SENSEXFUT" in result["futures"]
    assert result["futures"]["SENSEXFUT"]["security_id"] == 42102
    
    # Check heavyweights (all 15)
    expected_heavyweights = {
        "RELIANCE": 55001,
        "TCS": 55002,
        "HDFCBANK": 55003,
        "INFY": 55004,
        "ICICIBANK": 55005,
        "HINDUNILVR": 55006,
        "ITC": 55007,
        "SBIN": 55008,
        "BHARTIARTL": 55009,
        "KOTAKBANK": 55010,
        "LT": 55011,
        "AXISBANK": 55012,
        "ASIANPAINT": 55013,
        "MARUTI": 55014,
        "HCLTECH": 55015,
    }
    
    for symbol, security_id in expected_heavyweights.items():
        assert symbol in result["heavyweights"], f"{symbol} not found in heavyweights"
        assert result["heavyweights"][symbol] == security_id
    
    print(f"✅ Parsed {len(result['indices'])} indices")
    print(f"✅ Parsed {len(result['futures'])} futures")
    print(f"✅ Parsed {len(result['heavyweights'])} heavyweights")


if __name__ == "__main__":
    test_parse_instruments_from_fixture()
    print("\n✅ All instrument tests passed!")
