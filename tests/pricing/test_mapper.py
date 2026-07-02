from wc2026.pricing.mapper import ContractMapper, EventType


def test_kalshi_mapper():
    res = ContractMapper.parse_kalshi_ticker("KXWCADVANCE-MEX")
    assert res["type"] == EventType.ADVANCES
    assert res["team"] == "MEX"
    
    res = ContractMapper.parse_kalshi_ticker("KXWCWIN-ARG")
    assert res["type"] == EventType.WINS_TOURNAMENT
    assert res["team"] == "ARG"
    
    res = ContractMapper.parse_kalshi_ticker("KXWCGRP-ENG")
    assert res["type"] == EventType.WINS_GROUP
    assert res["team"] == "ENG"
    
    res = ContractMapper.parse_kalshi_ticker("KXUNKNOWN-MEX")
    assert res["type"] == EventType.UNKNOWN
