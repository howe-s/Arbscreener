from typing import List, Tuple

class LiquidityPool:
    """Represents a liquidity pool with base and quote token addresses."""
    def __init__(self, base_token: str, quote_token: str) -> None:
        self.base_token = base_token
        self.quote_token = quote_token

    def __repr__(self) -> str:
        return f"LiquidityPool(base_token={self.base_token}, quote_token={self.quote_token})"


class ArbitrageOpportunity:
    """Represents a triangular arbitrage opportunity consisting of three liquidity pools."""
    def __init__(self, pool_a: LiquidityPool, pool_b: LiquidityPool, pool_c: LiquidityPool) -> None:
        self.pool_a = pool_a
        self.pool_b = pool_b
        self.pool_c = pool_c

    def __repr__(self) -> str:
        return (f"ArbitrageOpportunity(\n"
                f"  pool_a={self.pool_a},\n"
                f"  pool_b={self.pool_b},\n"
                f"  pool_c={self.pool_c}\n"
                f")") 