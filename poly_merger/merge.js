/**
 * Poly-Merger: Polymarket持仓合并工具
 *
 * 此脚本处理Polymarket预测市场中YES和NO持仓的合并以回收抵押品。
 * 它适用于常规市场和负风险市场。
 *
 * 合并器通过safe-helpers.js工具支持Gnosis Safe钱包。
 *
 * 使用方法:
 *   node merge.js [要合并的数量] [条件ID] [是否为负风险市场]
 *
 * 示例:
 *   node merge.js 1000000 12345 true
 */

const { ethers } = require('ethers');
const { resolve } = require('path');
const { existsSync } = require('fs');
const { signAndExecuteSafeTransaction } = require('./safe-helpers');
const { safeAbi } = require('./safeAbi');

// 加载环境变量
const localEnvPath = resolve(__dirname, '.env');
const parentEnvPath = resolve(__dirname, '../.env');
const envPath = existsSync(localEnvPath) ? localEnvPath : parentEnvPath;
require('dotenv').config({ path: envPath })

// 连接到Polygon网络
const provider = new ethers.providers.JsonRpcProvider("https://polygon-rpc.com");
const privateKey = process.env.PK;
const wallet = new ethers.Wallet(privateKey, provider);

// Polymarket合约地址
const addresses = {
  // 负风险市场的适配器合约
  neg_risk_adapter: '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296',
  // Polygon上的USDC代币合约
  collateral: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
  // 预测市场的主条件代币合约
  conditional_tokens: '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045'
};

// 我们交互的合约的最小ABI
const negRiskAdapterAbi = [
  "function mergePositions(bytes32 conditionId, uint256 amount)"
];

const conditionalTokensAbi = [
  "function mergePositions(address collateralToken, bytes32 parentCollectionId, bytes32 conditionId, uint256[] partition, uint256 amount)"
];

/**
 * 合并Polymarket预测市场中的YES和NO持仓以回收USDC抵押品。
 *
 * 此函数通过不同的合约调用处理常规市场和负风险市场。
 * 它使用Gnosis Safe钱包基础设施进行安全的交易执行。
 *
 * @param {string|number} amountToMerge - 要合并的原始代币数量（通常以原始单位表示，例如1000000 = 1 USDC）
 * @param {string|number} conditionId - 市场的条件ID
 * @param {boolean} isNegRiskMarket - 是否为负风险市场（使用不同的合约）
 * @returns {string} 合并操作的交易哈希
 */
async function mergePositions(amountToMerge, conditionId, isNegRiskMarket) {
    // 记录参数以便调试
    console.log(amountToMerge, conditionId, isNegRiskMarket);

    // 准备交易参数
    const nonce = await provider.getTransactionCount(wallet.address);
    const gasPrice = await provider.getGasPrice();
    const gasLimit = 10000000;  // 设置高gas限制以确保交易完成

    let tx;
    // 不同市场类型的不同合约调用
    if (isNegRiskMarket) {
      // 对于负风险市场，使用适配器合约
      const negRiskAdapter = new ethers.Contract(addresses.neg_risk_adapter, negRiskAdapterAbi, wallet);
      tx = await negRiskAdapter.populateTransaction.mergePositions(conditionId, amountToMerge);
    } else {
      // 对于常规市场，直接使用条件代币合约
      const conditionalTokens = new ethers.Contract(addresses.conditional_tokens, conditionalTokensAbi, wallet);
      tx = await conditionalTokens.populateTransaction.mergePositions(
        addresses.collateral,        // USDC合约
        ethers.constants.HashZero,   // 父集合ID（顶级市场为0）
        conditionId,                 // 市场ID
        [1, 2],                      // 分区（要合并的结果索引）
        amountToMerge                // 要合并的数量
      );
    }

    // 准备完整的交易对象
    const transaction = {
      ...tx,
      chainId: 137,       // Polygon链ID
      gasPrice: gasPrice,
      gasLimit: gasLimit,
      nonce: nonce
    };

    // 从环境变量获取Safe地址
    const safeAddress = process.env.BROWSER_ADDRESS;
    const safe = new ethers.Contract(safeAddress, safeAbi, wallet);

    // 通过Safe执行交易
    console.log("正在签名交易")
    const txResponse = await signAndExecuteSafeTransaction(
      wallet,
      safe,
      transaction.to,
      transaction.data,
      {
        gasPrice: transaction.gasPrice,
        gasLimit: transaction.gasLimit
      }
    );

    console.log("已发送交易。等待响应")
    const txReceipt = await txResponse.wait();

    console.log("合并持仓 " + txReceipt.transactionHash);
    return txReceipt.transactionHash;
}

// 解析命令行参数
const args = process.argv.slice(2);

// 要合并的代币数量（原始单位，例如1000000 = 1 USDC）
const amountToMerge = args[0];

// 市场的条件ID
const conditionId = args[1];

// 是否为负风险市场（true/false）
const isNegRiskMarket = args[2] === 'true';

// 执行合并操作并处理任何错误
mergePositions(amountToMerge, conditionId, isNegRiskMarket)
  .catch(error => {
    console.error("合并持仓时出错:", error);
    process.exit(1);
  });