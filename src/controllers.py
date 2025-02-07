from typing import List
from .models import LiquidityPool, ArbitrageOpportunity

class ArbitrageController:
    """Controller to handle the logic for identifying triangular arbitrage opportunities."""

    def find_arbitrage_opportunities(self, pools: List[LiquidityPool]) -> List[ArbitrageOpportunity]:
        """Identify sets of three pools that form a valid triangular arbitrage structure."""
        opportunities = []
        for pool_a in pools:
            for pool_b in pools:
                if pool_a.quote_token == pool_b.quote_token and pool_a.base_token != pool_b.base_token:
                    for pool_c in pools:
                        if pool_c.base_token == pool_a.base_token and pool_c.quote_token == pool_b.base_token:
                            opportunities.append(ArbitrageOpportunity(pool_a, pool_b, pool_c))
        return opportunities 