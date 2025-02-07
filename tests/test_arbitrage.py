import pytest
from src.models import LiquidityPool, ArbitrageOpportunity
from src.controllers import ArbitrageController


def test_find_arbitrage_opportunities() -> None:
    """Test the identification of triangular arbitrage opportunities."""
    pools = [
        LiquidityPool(base_token='A123', quote_token='B123'),
        LiquidityPool(base_token='C123', quote_token='B123'),
        LiquidityPool(base_token='A123', quote_token='C123'),
    ]
    controller = ArbitrageController()
    opportunities = controller.find_arbitrage_opportunities(pools)
    assert len(opportunities) == 1
    assert isinstance(opportunities[0], ArbitrageOpportunity)
    assert opportunities[0].pool_a.base_token == 'A123'
    assert opportunities[0].pool_b.base_token == 'C123'
    assert opportunities[0].pool_c.base_token == 'A123' 