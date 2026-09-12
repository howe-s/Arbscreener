# Arbitrage Contract Finder

***Work in progress***

A Flask-based application that detects and analyzes arbitrage opportunities across cryptocurrency trading pairs and decentralized exchange in real-time. 

<!-- ![image](https://github.com/user-attachments/assets/ac8d58c4-5d32-4a73-a79e-5e417c57f4cb) -->


https://github.com/user-attachments/assets/7c92e9a7-4685-47dc-bdd7-7f81f5b96f49 




## Run and test

Use Python 3.12. Create a virtual environment, activate it, then run:

```sh
python -m pip install -r requirements.txt
python app.py
```

Open http://localhost:8080. `PORT` overrides the port. `/health` is the
health endpoint. Run `python -m pytest -q` for the offline regression suite.
The Flask app is the maintained entry point; the Firebase folders and
`old_files` contain earlier experiments.

Search accepts a token or pool address (blank uses the example token).
Investment is USD. Slippage and fee inputs are fractions: `0.001` means 0.1%.
Results include same-chain two-pool routes and three-pool cycles, sorted by
estimated net profit. Triangles apply slippage and fees on every trade;
two-pool routes use a liquidity-scaled slippage estimate. These are screening
estimates, excluding gas, transfer costs, execution timing, and pool-specific
price impact. The app does not execute trades. API searches are not exhaustive.

Market data uses the public [DEX Screener API](https://docs.dexscreener.com/api/reference)
with bounded request timeouts and retries for rate limits. External failures
return an error instead of a successful empty scan. Logs are bounded and
process-local; the log panel is a development aid, not a multi-user audit trail.

Docker uses Python 3.12 and defaults to port 8080. Build with
`docker build -t arbscreener .` and run with
`docker run --rm -p 8080:8080 arbscreener`.

## Profitability dashboard

The dashboard shows estimated proceeds, known costs, net profit and margin.
Scan inputs display fee and slippage as percentages and convert them to the
backend's fractional rates. Expand a route to enter gas/network and
transfer/other costs in USD. Blank costs stay unknown; enter zero explicitly
only when no cost applies. Assumptions reset on a new scan or page reload.

PROFITABLE means entered costs leave a positive return meeting the visible
minimum margin (default 1%). REVIEW means missing economics, break-even, or
margin below the chosen target. NOT PROFITABLE means known costs already
exceed proceeds. All results remain estimates, including green results.
Margin is net profit divided by expected proceeds, not return on investment.
Potential profit includes only cost-complete profitable estimates and is not
an executable total because routes may overlap.

The UI requests `include_unprofitable=true` so loss-making and break-even
routes remain inspectable; existing API callers retain the positive-only
default. Three-pool cycles display their best direction. Run
`node tests/test_frontend.js` for calculation, missing-data, sorting and
HTML-escaping checks, alongside the Python suite.
