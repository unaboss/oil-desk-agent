// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockToken is ERC20 {
    constructor(string memory n, string memory s) ERC20(n, s) {}
    function mint(address to, uint256 a) external { _mint(to, a); }
}

/// Fixed-price router: 1 base = priceE18 quote.
contract MockRouter {
    uint256 public priceE18;
    address public base;
    constructor(address _base, uint256 _p) { base = _base; priceE18 = _p; }
    function setPrice(uint256 p) external { priceE18 = p; }
    function swapExactTokensForTokens(uint256 amountIn, uint256 minOut, address[] calldata path, address to, uint256)
        external returns (uint256[] memory amounts)
    {
        uint256 out = path[0] == base ? amountIn * priceE18 / 1e18 : amountIn * 1e18 / priceE18;
        require(out >= minOut, "slippage");
        ERC20(path[0]).transferFrom(msg.sender, address(this), amountIn);
        MockToken(path[1]).mint(to, out);
        amounts = new uint256[](2);
        amounts[0] = amountIn;
        amounts[1] = out;
    }
}
