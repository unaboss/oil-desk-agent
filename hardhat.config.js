require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-chai-matchers");
const KEY = process.env.DEPLOYER_KEY || process.env.AGENT_KEY;
const PK = KEY ? [KEY] : [];
module.exports = {
  solidity: { version: "0.8.24", settings: { optimizer: { enabled: true, runs: 200 }, viaIR: true } },
  networks: {
    hashkeyTestnet: { url: process.env.HSK_TESTNET_RPC || "https://testnet.hsk.xyz", chainId: 133, accounts: PK },
    hashkey: { url: process.env.HSK_RPC || "https://mainnet.hsk.xyz", chainId: 177, accounts: PK },
  },
};

// Use the npm solc-js build when binaries.soliditylang.org is unreachable.
const { subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require("hardhat/builtin-tasks/task-names");
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD, async (args, hre, runSuper) => {
  if (process.env.USE_SOLCJS !== "1") return runSuper();
  const solcPath = require.resolve("solc/soljson.js");
  return { compilerPath: solcPath, isSolcJs: true, version: args.solcVersion, longVersion: require("solc/package.json").version };
});
