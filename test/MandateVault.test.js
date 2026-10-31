const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

const E = (n) => ethers.parseEther(String(n));
const H = ethers.id("rationale");
const HOLD = 0, BUY = 1, SELL = 2;

describe("MandateVault", () => {
  async function setup() {
    const [owner, agent, rando] = await ethers.getSigners();
    const T = await ethers.getContractFactory("MockToken");
    const base = await T.deploy("Wrapped HSK", "WHSK");
    const quote = await T.deploy("Tether", "USDT");
    const R = await ethers.getContractFactory("MockRouter");
    const router = await R.deploy(await base.getAddress(), E(0.5)); // 1 HSK = 0.5 USDT
    const m = { maxTradeQuote: E(10), maxTradeBase: E(20), dailyCapQuote: E(15), dailyCapBase: E(30), maxSlippageBps: 100, paused: false };
    const V = await ethers.getContractFactory("MandateVault");
    const vault = await V.deploy(agent.address, await base.getAddress(), await quote.getAddress(), await router.getAddress(), m);
    await quote.mint(await vault.getAddress(), E(100));
    await base.mint(await vault.getAddress(), E(100));
    return { owner, agent, rando, base, quote, router, vault };
  }

  it("records HOLD decisions", async () => {
    const { vault, agent } = await setup();
    await expect(vault.connect(agent).decide(HOLD, 0, 0, 0, 70, 50_000_000, H, "ipfs://x"))
      .to.emit(vault, "Decision").withArgs(1, HOLD, 0, 0, 70, 50_000_000, H, "ipfs://x");
  });

  it("executes a BUY inside the mandate", async () => {
    const { vault, agent, base } = await setup();
    await expect(vault.connect(agent).decide(BUY, E(5), E(10), E(9.95), 80, 50_000_000, H, ""))
      .to.emit(vault, "Decision").withArgs(1, BUY, E(5), E(10), 80, 50_000_000, H, "");
    expect(await base.balanceOf(await vault.getAddress())).to.equal(E(110));
    expect(await vault.spentQuoteToday()).to.equal(E(5));
  });

  it("executes a SELL", async () => {
    const { vault, agent, quote } = await setup();
    await vault.connect(agent).decide(SELL, E(10), E(5), E(5), 60, 0, H, "");
    expect(await quote.balanceOf(await vault.getAddress())).to.equal(E(105));
  });

  it("rejects oversize trades without reverting", async () => {
    const { vault, agent } = await setup();
    await expect(vault.connect(agent).decide(BUY, E(11), E(22), E(22), 99, 0, H, ""))
      .to.emit(vault, "Rejected").withArgs(1, BUY, E(11), "trade size above mandate");
  });

  it("enforces the daily cap and resets next day", async () => {
    const { vault, agent } = await setup();
    await vault.connect(agent).decide(BUY, E(10), E(20), E(20), 80, 0, H, "");
    await expect(vault.connect(agent).decide(BUY, E(6), E(12), E(12), 80, 0, H, ""))
      .to.emit(vault, "Rejected").withArgs(2, BUY, E(6), "daily cap reached");
    await time.increase(86400);
    await expect(vault.connect(agent).decide(BUY, E(6), E(12), E(12), 80, 0, H, ""))
      .to.emit(vault, "Decision").withArgs(3, BUY, E(6), E(12), 80, 0, H, "");
  });

  it("rejects loose slippage", async () => {
    const { vault, agent } = await setup();
    await expect(vault.connect(agent).decide(BUY, E(5), E(10), E(9), 80, 0, H, ""))
      .to.emit(vault, "Rejected").withArgs(1, BUY, E(5), "slippage above mandate");
  });

  it("pause blocks trades", async () => {
    const { vault, agent, owner } = await setup();
    await vault.connect(owner).setPaused(true);
    await expect(vault.connect(agent).decide(BUY, E(1), E(2), E(2), 80, 0, H, ""))
      .to.emit(vault, "Rejected").withArgs(1, BUY, E(1), "paused");
  });

  it("only the agent decides, only the owner withdraws", async () => {
    const { vault, rando, agent, quote, owner } = await setup();
    await expect(vault.connect(rando).decide(HOLD, 0, 0, 0, 0, 0, H, "")).to.be.revertedWithCustomError(vault, "NotAgent");
    await expect(vault.connect(agent).withdraw(await quote.getAddress(), 1)).to.be.revertedWithCustomError(vault, "NotOwner");
    await vault.connect(owner).withdraw(await quote.getAddress(), E(100));
    expect(await quote.balanceOf(owner.address)).to.equal(E(100));
  });
});

describe("MandateVault paper mode", () => {
  it("fills at the reported price on a virtual book and enforces limits", async () => {
    const [owner, agent] = await ethers.getSigners();
    const T = await ethers.getContractFactory("MockToken");
    const base = await T.deploy("Wrapped HSK", "WHSK");
    const quote = await T.deploy("Tether", "USDT");
    const m = { maxTradeQuote: E(10), maxTradeBase: E(20), dailyCapQuote: E(15), dailyCapBase: E(30), maxSlippageBps: 100, paused: false };
    const V = await ethers.getContractFactory("MandateVault");
    const vault = await V.deploy(agent.address, await base.getAddress(), await quote.getAddress(), ethers.ZeroAddress, m);
    await vault.setPaperBook(E(0), E(100));
    await vault.connect(agent).decide(BUY, E(10), E(20), E(20), 80, 50_000_000, H, "");
    const [b, q] = await vault.balances();
    expect(b).to.equal(E(20));
    expect(q).to.equal(E(90));
    await expect(vault.connect(agent).decide(SELL, E(21), E(10), E(10), 80, 0, H, ""))
      .to.emit(vault, "Rejected").withArgs(2, SELL, E(21), "trade size above mandate");
  });
});
