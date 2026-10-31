// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IV2Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

/// @title MandateVault
/// @notice Holds funds for an AI trading agent. The agent can only trade inside
///         the mandate the owner sets, and every decision (including HOLD) is
///         recorded on-chain: a short rationale plus a hash of the full model output.
contract MandateVault is ReentrancyGuard {
    using SafeERC20 for IERC20;

    enum Action { HOLD, BUY, SELL }

    struct Mandate {
        uint256 maxTradeQuote; // max quote token spent per BUY
        uint256 maxTradeBase;  // max base token sold per SELL
        uint256 dailyCapQuote; // max quote spent per UTC day
        uint256 dailyCapBase;  // max base sold per UTC day
        uint16 maxSlippageBps; // agent's minOut must be within this of its own quote
        bool paused;
    }

    address public owner;
    address public agent;
    IERC20 public immutable base;  // e.g. WHSK
    IERC20 public immutable quote; // e.g. USDT
    IV2Router public router;
    Mandate public mandate;

    uint256 public currentDay;
    uint256 public spentQuoteToday;
    uint256 public soldBaseToday;
    uint256 public decisionCount;

    /// Paper mode: when `router` is unset the vault keeps a virtual book and
    /// fills at the agent-reported price (from a public market feed, recorded
    /// in the event). Used on mainnet while DEX liquidity is too thin.
    uint256 public paperBase;
    uint256 public paperQuote;

    event Decision(
        uint256 indexed id,
        Action action,
        uint256 amountIn,
        uint256 amountOut,
        uint8 confidence,
        int256 priceE8,
        bytes32 rationaleHash,
        string rationale
    );
    event Rejected(uint256 indexed id, Action action, uint256 amountIn, string reason);
    event MandateUpdated(Mandate mandate);
    event AgentUpdated(address agent);
    event RouterUpdated(address router);
    event Withdrawn(address token, uint256 amount);

    error NotOwner();
    error NotAgent();

    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }
    modifier onlyAgent() { if (msg.sender != agent) revert NotAgent(); _; }

    constructor(address _agent, address _base, address _quote, address _router, Mandate memory _m) {
        owner = msg.sender;
        agent = _agent;
        base = IERC20(_base);
        quote = IERC20(_quote);
        router = IV2Router(_router);
        mandate = _m;
        currentDay = block.timestamp / 1 days;
    }

    // ---------- agent ----------

    /// @notice Agent submits a decision. HOLDs and out-of-mandate trades are
    ///         recorded but never revert, so the audit log is complete.
    function decide(
        Action action,
        uint256 amountIn,
        uint256 expectedOut,
        uint256 minOut,
        uint8 confidence,
        int256 priceE8,
        bytes32 rationaleHash,
        string calldata rationale
    ) external onlyAgent nonReentrant returns (uint256 id, uint256 amountOut) {
        id = ++decisionCount;
        _rollDay();

        if (action == Action.HOLD) {
            emit Decision(id, action, 0, 0, confidence, priceE8, rationaleHash, rationale);
            return (id, 0);
        }

        string memory why = _check(action, amountIn, expectedOut, minOut);
        if (bytes(why).length != 0) {
            emit Rejected(id, action, amountIn, why);
            emit Decision(id, Action.HOLD, 0, 0, confidence, priceE8, rationaleHash, rationale);
            return (id, 0);
        }

        if (action == Action.BUY) spentQuoteToday += amountIn; else soldBaseToday += amountIn;

        if (address(router) == address(0)) {
            amountOut = expectedOut;
            if (action == Action.BUY) { paperQuote -= amountIn; paperBase += amountOut; }
            else { paperBase -= amountIn; paperQuote += amountOut; }
            emit Decision(id, action, amountIn, amountOut, confidence, priceE8, rationaleHash, rationale);
            return (id, amountOut);
        }

        (IERC20 tin, IERC20 tout) = action == Action.BUY ? (quote, base) : (base, quote);

        address[] memory path = new address[](2);
        path[0] = address(tin);
        path[1] = address(tout);
        tin.forceApprove(address(router), amountIn);
        uint256[] memory amounts = router.swapExactTokensForTokens(amountIn, minOut, path, address(this), block.timestamp + 300);
        amountOut = amounts[amounts.length - 1];

        emit Decision(id, action, amountIn, amountOut, confidence, priceE8, rationaleHash, rationale);
    }

    function _check(Action action, uint256 amountIn, uint256 expectedOut, uint256 minOut)
        internal view returns (string memory)
    {
        Mandate memory m = mandate;
        if (m.paused) return "paused";
        if (amountIn == 0) return "zero amount";
        if (minOut * 10_000 < expectedOut * (10_000 - m.maxSlippageBps)) return "slippage above mandate";
        if (action == Action.BUY) {
            if (amountIn > m.maxTradeQuote) return "trade size above mandate";
            if (spentQuoteToday + amountIn > m.dailyCapQuote) return "daily cap reached";
            if (_quoteBal() < amountIn) return "insufficient quote balance";
        } else {
            if (amountIn > m.maxTradeBase) return "trade size above mandate";
            if (soldBaseToday + amountIn > m.dailyCapBase) return "daily cap reached";
            if (_baseBal() < amountIn) return "insufficient base balance";
        }
        return "";
    }

    function _paper() internal view returns (bool) { return address(router) == address(0); }
    function _baseBal() internal view returns (uint256) { return _paper() ? paperBase : base.balanceOf(address(this)); }
    function _quoteBal() internal view returns (uint256) { return _paper() ? paperQuote : quote.balanceOf(address(this)); }

    function _rollDay() internal {
        uint256 d = block.timestamp / 1 days;
        if (d != currentDay) {
            currentDay = d;
            spentQuoteToday = 0;
            soldBaseToday = 0;
        }
    }

    // ---------- owner ----------

    function setMandate(Mandate calldata m) external onlyOwner { mandate = m; emit MandateUpdated(m); }
    function setPaused(bool p) external onlyOwner { mandate.paused = p; emit MandateUpdated(mandate); }
    function setAgent(address a) external onlyOwner { agent = a; emit AgentUpdated(a); }
    function setRouter(address r) external onlyOwner { router = IV2Router(r); emit RouterUpdated(r); }

    /// @notice Seed the paper book (paper mode only).
    function setPaperBook(uint256 b, uint256 q) external onlyOwner { paperBase = b; paperQuote = q; }

    function withdraw(address token, uint256 amount) external onlyOwner nonReentrant {
        IERC20(token).safeTransfer(owner, amount);
        emit Withdrawn(token, amount);
    }

    function balances() external view returns (uint256 baseBal, uint256 quoteBal) {
        return (_baseBal(), _quoteBal());
    }
}
