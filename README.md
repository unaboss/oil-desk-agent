# Oil Desk: an AI oil-trading agent with a track record nobody can fake

Built for the **HashKey Chain Horizon Hackathon (AI Agent Trading track)**.

**Live page:** https://unaboss.github.io/oil-desk-agent/ (every on-chain call, the chart, the mandate). Before the mainnet vault has calls, it offers a clearly labelled sample replay ([preview](https://unaboss.github.io/oil-desk-agent/?sample)).

Trading-signal groups sell "track records" made of screenshots. Trading bots get full control of your funds. **Oil Desk fixes both:**

1. **Analyse.** Every cycle the agent runs the Oil Dashboard's **6-signal confluence engine** for WTI crude (volume, CFTC COT positioning, EIA inventories, crack spread, US dollar, Brent-WTI curve). It also runs the engine's own **historical hit-rate audit**.
2. **Ask the crowd.** It reads live **Polymarket** odds on oil-price questions as a sentiment input.
3. **Decide.** An LLM (DeepSeek V4 Flash via Nebius Token Factory) weighs the three inputs and returns BUY, SELL or HOLD with a confidence and a reason that cites the numbers. If the model is unavailable, a deterministic rule set takes over, so the log never stops.
4. **Act within a mandate.** The decision goes to `MandateVault` on **HashKey Chain mainnet**. The contract enforces the max trade size, daily caps, max slippage and a pause switch. The agent physically can't exceed them, and blocked attempts are logged too.
5. **Prove it.** Every call is stamped on-chain *before* the outcome is known, together with the keccak256 hash of the agent's full input and output. The full JSON is published in [`records/`](records/), so anyone can re-hash it and check. The dashboard's **Oil Desk Agent** tab scores every call against what WTI actually did three trading days later.

## Honest scope (v1)
HashKey Chain has no tokenised oil yet, and on-chain DEX liquidity is very thin. So v1 runs a **paper oil book on-chain**: barrels and USD held as contract state, filled at the WTI price the agent records in each event. The mandate, the decision log and the track record are real and on mainnet. Live execution is built in: set a Uniswap V2-style `router` on the vault and the same `decide()` call swaps real tokens (covered by tests with a mock router).

## Layout
| Path | What |
|---|---|
| `site/` | The public Oil Desk page (static, GitHub Pages). `agent/export_site.py` refreshes its data after every agent run |
| `oil_dashboard/` | The Oil Dashboard (Streamlit): data fetchers, confluence engine, audit, 12 tabs including **0. Oil Desk Agent** |
| `agent/` | The agent: `oil_view.py` (confluence + audit), `crowd.py` (Polymarket), `brain.py` (LLM + rules), `chain.py` (web3), `run.py` (one cycle) |
| `contracts/MandateVault.sol` | Mandate enforcement, paper or live execution, on-chain decision log |
| `.github/workflows/` | CI, a one-click vault deploy, the agent on a 3-hour schedule, and the page publisher |
| `records/` | Full JSON record of every decision; its hash is on-chain |
| `deployments/` | Vault address per network |

## Run it
```bash
npm ci --legacy-peer-deps && npx hardhat test            # 9 contract tests
pip install -r oil_dashboard/requirements.txt pytest
python -m pytest -q && (cd oil_dashboard && python -m pytest -q)   # agent + dashboard tests
streamlit run oil_dashboard/app.py                        # dashboard incl. the Agent tab
```
On GitHub: add the secrets `AGENT_KEY`, `EIA_API_KEY` and `LLM_API_KEY`. Then run **Actions → Deploy vault**, then **Actions → Oil Desk agent** (it also runs every 3 hours).

HashKey Chain mainnet: chain ID 177, RPC https://mainnet.hsk.xyz, explorer https://hashkey.blockscout.com

## Roadmap
- Live execution against tokenised commodity / RWA markets on HashKey Chain.
- Per-user vaults: anyone deploys their own mandate and subscribes to the agent's calls.
- Verified signal channels: signal sellers publish through a vault, so their track record is provable. This is the business model.
- Agent-to-agent payments (HSP), letting other agents pay per verified signal.
- A South African fuel-price forecaster (Brent + ZAR) for taxi and fleet operators.
