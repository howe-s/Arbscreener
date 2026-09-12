import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.main_utils import (
    calculate_arbitrage_profit,
    process_token_pairs,
    find_arbitrage_opportunities,
    safe_get,
    calculate_price_discrepancies,
    check_price_compatibility
)

@pytest.fixture
def sample_pair():
    """
    Fixture that creates a mock trading pair with base and quote tokens.

    Returns:
        Mock: A mock object representing a trading pair with the following attributes:
            - base_token: Mock token with name='Token1' and address='0x123'
            - quote_token: Mock token with name='Token2' and address='0x456'
            - pair_address: '0x789'
            - price_usd: '100.0'
            - price_native: '1.0'
            - liquidity: Dict containing usd, base, and quote values
            - url: 'https://example.com'
            - chain_id: 'ethereum'
            - dex_id: 'uniswap'
    """
    base_token = Mock()
    base_token.name = 'Token1'
    base_token.address = '0x123'
    base_token.configure_mock(**{'name': 'Token1', 'address': '0x123'})

    quote_token = Mock()
    quote_token.name = 'Token2'
    quote_token.address = '0x456'
    quote_token.configure_mock(**{'name': 'Token2', 'address': '0x456'})

    pair = Mock()
    pair.base_token = base_token
    pair.quote_token = quote_token
    pair.pair_address = '0x789'
    pair.price_usd = '100.0'
    pair.price_native = '1.0'
    pair.liquidity = {'usd': 1000000.0, 'base': 5000.0, 'quote': 500000.0}
    pair.url = 'https://example.com'
    pair.chain_id = 'ethereum'
    pair.dex_id = 'uniswap'
    return pair

@pytest.fixture
def sample_token_pairs():
    """
    Fixture that provides a list of sample token pairs for testing.

    Returns:
        List[Dict]: A list of two token pairs with complete trading information including:
            - Trading pair names
            - Pool addresses
            - Prices in USD and native currency
            - Liquidity information
            - Token addresses
            - Chain and DEX identifiers
            - URLs
    """
    return [
        {
            'pair': 'Token1/Token2',
            'pool_address': '0x123',
            'price_usd': 100.0,
            'price_native': 1.0,
            'liquidity_usd': 1000000.0,
            'liquidity_base': 5000.0,
            'liquidity_quote': 500000.0,
            'baseToken_address': '0xabc',
            'quoteToken_address': '0xdef',
            'chain_id': 'ethereum',
            'dex_id': 'uniswap',
            'pool_url': 'https://example.com',
            'url': 'https://example.com'
        },
        {
            'pair': 'Token2/Token3',
            'pool_address': '0x456',
            'price_usd': 200.0,
            'price_native': 2.0,
            'liquidity_usd': 2000000.0,
            'liquidity_base': 10000.0,
            'liquidity_quote': 1000000.0,
            'baseToken_address': '0xdef',
            'quoteToken_address': '0xghi',
            'chain_id': 'ethereum',
            'dex_id': 'uniswap',
            'pool_url': 'https://example.com',
            'url': 'https://example.com'
        }
    ]

def test_safe_get():
    """
    Test the safe_get helper function's ability to safely access object attributes.

    Test cases:
        1. Accessing existing attribute returns correct value
        2. Accessing non-existent attribute returns None
        3. Accessing non-existent attribute with default value returns default
        4. Accessing attribute on None object returns None

    Side effects: None

    Assertions:
        - Existing attribute returns expected value
        - Non-existent attribute returns None
        - Non-existent attribute with default returns default value
        - None object attribute access returns None
    """
    class TestObj:
        def __init__(self):
            self.attribute = 'value'

    obj = TestObj()

    assert safe_get(obj, 'attribute') == 'value'
    assert safe_get(obj, 'nonexistent') is None
    assert safe_get(obj, 'nonexistent', 'default') == 'default'
    assert safe_get(None, 'attribute') is None

def test_calculate_arbitrage_profit():
    """
    Test the arbitrage profit calculation function with different market conditions.

    Inputs:
        - Investment amount: 10000
        - Entry/exit prices: Various scenarios
        - Slippage rate: 0.001 (0.1%)
        - Fee rate: 0.003 (0.3%)
        - Liquidity: 1,000,000 for both entry and exit

    Test cases:
        1. Profitable trade (price increases)
        2. Unprofitable trade (price decreases)

    Expected outputs:
        - Profitable scenario returns positive profit
        - Unprofitable scenario returns negative profit (loss)

    Side effects: None
    """
    profit = calculate_arbitrage_profit(
        investment_amount=10000,
        entry_price=100,
        exit_price=110,
        slippage_rate=0.001,
        fee_rate=0.003,
        entry_liquidity=1000000,
        exit_liquidity=1000000
    )
    assert profit > 0

    loss = calculate_arbitrage_profit(
        investment_amount=10000,
        entry_price=100,
        exit_price=99,
        slippage_rate=0.001,
        fee_rate=0.003,
        entry_liquidity=1000000,
        exit_liquidity=1000000
    )
    assert loss < 0

@patch('utils.main_utils.safe_get')
def test_process_token_pairs(mock_safe_get, sample_pair):
    """
    Test the processing of token pairs into a standardized format.

    Args:
        mock_safe_get (MagicMock): Mocked safe_get function
        sample_pair (Mock): Fixture providing a sample trading pair

    Test cases:
        1. Processing a single token pair with complete information

    Expected outputs:
        - List containing one processed pair with all required fields
        - Correct formatting of pair name, addresses, and numerical values

    Mock behavior:
        - safe_get is mocked to return appropriate values based on input
        - Returns mock values for token names, addresses, and liquidity

    Assertions:
        - Output list has correct length
        - Pair name is correctly formatted
        - Pool address matches input
        - Price and liquidity values are correctly converted
    """
    def side_effect(obj, attr, default=None):
        if attr == 'name' and obj in [sample_pair.base_token, sample_pair.quote_token]:
            return obj.name
        if attr == 'liquidity':
            return sample_pair.liquidity
        if attr == 'usd' and isinstance(obj, dict) and obj == sample_pair.liquidity:
            return 1000000.0
        if hasattr(sample_pair, attr):
            return getattr(sample_pair, attr)
        return default

    mock_safe_get.side_effect = side_effect

    pairs = [sample_pair]
    processed = process_token_pairs(pairs)

    assert len(processed) == 1
    assert processed[0]['pair'] == 'Token1/Token2'
    assert processed[0]['pool_address'] == sample_pair.pair_address
    assert float(processed[0]['price_usd']) == float(sample_pair.price_usd)
    assert float(processed[0]['liquidity_usd']) == 1000000.0

def test_check_price_compatibility():
    """
    Test the price compatibility checker for arbitrage opportunities.

    Test cases:
        1. Favorable price movement (profitable arbitrage opportunity)
        2. Unfavorable price movement (unprofitable arbitrage opportunity)

    Inputs:
        - Opportunity dictionaries with price information
        - Initial investment: 10000
        - Slippage: 0.001 (0.1%)
        - Fee percentage: 0.003 (0.3%)

    Expected outputs:
        - True for favorable price movements
        - False for unfavorable price movements

    Side effects: None
    """
    opportunity = {
        'pair1_price': '100.0',
        'pair2_price': '110.0',
        'pair3_price': '90.0',
        'pair1_priceNative': '1.0',
        'pair2_priceNative': '1.1',
        'pair3_priceNative': '0.9'
    }

    opportunity.update(pair1_baseToken_address='A', pair1_quoteToken_address='B',
                       pair2_baseToken_address='A', pair2_quoteToken_address='C',
                       pair3_baseToken_address='B', pair3_quoteToken_address='C')
    result = check_price_compatibility(
        opportunity=opportunity,
        initial_investment=10000,
        slippage=0.001,
        fee_percentage=0.003
    )
    assert result is True

    bad_opportunity = {
        'pair1_price': '100.0',
        'pair2_price': '90.0',
        'pair3_price': '110.0',
        'pair1_priceNative': '1.0',
        'pair2_priceNative': '0.9',
        'pair3_priceNative': '1.1'
    }
    bad_opportunity.update({key: value for key, value in opportunity.items() if key.endswith('Token_address')})
    result = check_price_compatibility(
        opportunity=bad_opportunity,
        initial_investment=10000,
        slippage=0.001,
        fee_percentage=0.003
    )
    assert result is False

@patch('utils.main_utils.logger')
def test_find_arbitrage_opportunities(mock_logger, sample_token_pairs):
    """
    Test the arbitrage opportunity finder functionality.

    Args:
        mock_logger (MagicMock): Mocked logger instance
        sample_token_pairs (List[Dict]): Fixture providing sample token pairs

    Test cases:
        1. Finding arbitrage opportunities in a set of token pairs

    Inputs:
        - List of token pairs
        - Slippage: 0.001 (0.1%)
        - Fee percentage: 0.003 (0.3%)
        - Initial investment: 10000
        - Empty user purchases list

    Expected outputs:
        - List of arbitrage opportunities (may be empty)
        - Logger called with appropriate messages

    Mock behavior:
        - Logger is mocked to verify logging calls

    Assertions:
        - Result is a list
        - Logger info method was called
    """
    opportunities = find_arbitrage_opportunities(
        token_pairs=sample_token_pairs,
        slippage=0.001,
        fee_percentage=0.003,
        initial_investment=10000,
        user_purchases=[]
    )

    assert isinstance(opportunities, list)
    mock_logger.info.assert_called()

def test_calculate_price_discrepancies():
    """
    Test the calculation of price discrepancies between trading pairs.

    Test cases:
        1. Calculate price discrepancies between three trading pairs

    Inputs:
        - Opportunity dictionary containing:
            - Prices in USD and native currency
            - Token addresses
            - Price information for all pairs

    Expected outputs:
        - Opportunity dictionary updated with discrepancy calculations
        - All discrepancy fields present and properly formatted

    Side effects:
        - Modifies the input opportunity dictionary

    Assertions:
        - All expected discrepancy fields are present
        - All discrepancy values are strings
        - All discrepancy values end with '%'
    """
    opportunity = {
        'pair1_price': '100.0',
        'pair2_price': '110.0',
        'pair3_price': '105.0',
        'pair1_priceNative_round': '1.0',
        'pair2_priceNative_round': '1.1',
        'pair3_priceNative_round': '1.05',
        'quote_price_usd_1': '$100.0',
        'quote_price_usd_2': '$110.0',
        'quote_price_usd_3': '$105.0',
        'pair1_baseToken_address': '0x123',
        'pair1_quoteToken_address': '0x456',
        'pair2_baseToken_address': '0x456',
        'pair2_quoteToken_address': '0x789',
        'pair3_baseToken_address': '0x789',
        'pair3_quoteToken_address': '0x123'
    }

    calculate_price_discrepancies(opportunity)

    expected_fields = [
        'baseToken_difference_12',
        'baseToken_difference_13',
        'baseToken_difference_23',
        'quoteToken_difference_12',
        'quoteToken_difference_13',
        'quoteToken_difference_23'
    ]

    for field in expected_fields:
        assert field in opportunity
        assert isinstance(opportunity[field], str)
        assert opportunity[field].endswith('%')

@pytest.mark.integration
def test_end_to_end_arbitrage_flow():
    """
    Integration test for the complete arbitrage detection flow.

    Test cases:
        1. Complete flow from fetching pairs to processing arbitrage opportunities

    Mock behavior:
        - fetch_and_cache_pairs is mocked to return a predefined pair
        - Mock pair includes complete trading information

    Expected outputs:
        - List of arbitrage opportunities

    Side effects:
        - None (all external calls are mocked)

    Assertions:
        - Result is a list
    """
    with patch('utils.main_utils.fetch_and_cache_pairs') as mock_fetch:
        mock_pair = Mock()

        base_token = Mock()
        base_token.configure_mock(**{'name': 'Token1', 'address': '0x456'})

        quote_token = Mock()
        quote_token.configure_mock(**{'name': 'Token2', 'address': '0x789'})

        mock_pair.configure_mock(**{
            'base_token': base_token,
            'quote_token': quote_token,
            'pair_address': '0x123',
            'price_usd': '100.0',
            'price_native': '1.0',
            'liquidity': {'usd': 1000000.0, 'base': 5000.0, 'quote': 500000.0},
            'url': 'https://example.com',
            'chain_id': 'ethereum',
            'dex_id': 'uniswap'
        })

        mock_fetch.return_value = [mock_pair]

        from utils.main_utils import process_arbitrage_data

        result = process_arbitrage_data(
            user_purchases=[],
            initial_investment=10000,
            slippage=0.001,
            fee_percentage=0.003,
            search_address='0x123'
        )

        assert isinstance(result, list)
