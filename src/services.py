import requests
from typing import List
from .models import LiquidityPool

class PoolRetrievalService:
    """Service to retrieve liquidity pool data from an external API."""

    def __init__(self, api_url: str) -> None:
        self.api_url = api_url

    def get_pools(self, asset_address: str) -> List[LiquidityPool]:
        """Fetch liquidity pools containing the specified asset address."""
        response = requests.get(f"{self.api_url}/pools?asset={asset_address}")
        response.raise_for_status()
        pools_data = response.json()
        return [LiquidityPool(pool['base_token'], pool['quote_token']) for pool in pools_data] 