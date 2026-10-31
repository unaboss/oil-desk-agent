// Deploys the Oil Desk MandateVault.
// Paper mode (ROUTER unset): an on-chain book of barrels (base) and USD (quote),
// filled at the WTI price the agent reports and records in every Decision event.
const fs = require("fs");
const path = require("path");
const { ethers, network } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  const E = (n) => ethers.parseEther(String(n));
  const agent = process.env.AGENT_ADDRESS || deployer.address;
  const router = process.env.ROUTER || ethers.ZeroAddress;
  const mandate = {
    maxTradeQuote: E(process.env.MAX_TRADE_USD || 2500),
    maxTradeBase: E(process.env.MAX_TRADE_BBL || 40),
    dailyCapQuote: E(process.env.DAILY_CAP_USD || 5000),
    dailyCapBase: E(process.env.DAILY_CAP_BBL || 80),
    maxSlippageBps: Number(process.env.MAX_SLIPPAGE_BPS || 50),
    paused: false,
  };
  console.log(`network=${network.name} deployer=${deployer.address} agent=${agent}`);
  const V = await ethers.getContractFactory("MandateVault");
  const vault = await V.deploy(agent, process.env.BASE_TOKEN || ethers.ZeroAddress, process.env.QUOTE_TOKEN || ethers.ZeroAddress, router, mandate);
  await vault.waitForDeployment();
  const addr = await vault.getAddress();
  const deployBlock = (await vault.deploymentTransaction().wait()).blockNumber;
  console.log(`MandateVault: ${addr} (block ${deployBlock})`);
  if (router === ethers.ZeroAddress) {
    await (await vault.setPaperBook(0, E(process.env.PAPER_USD || 10000))).wait();
    console.log(`Paper book seeded with $${process.env.PAPER_USD || 10000}`);
  }
  const dir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  const out = { network: network.name, chainId: Number((await ethers.provider.getNetwork()).chainId), vault: addr, agent, deployBlock, paper: router === ethers.ZeroAddress, deployedAt: new Date().toISOString() };
  fs.writeFileSync(path.join(dir, `${network.name}.json`), JSON.stringify(out, null, 2) + "\n");
  console.log(JSON.stringify(out));
}
main().catch((e) => { console.error(e); process.exit(1); });
