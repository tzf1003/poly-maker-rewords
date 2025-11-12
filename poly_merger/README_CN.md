# Poly-Merger（持仓合并工具）

一个用于高效合并Polymarket持仓的实用工具。此工具帮助合并同一市场中的相反持仓，使您能够：

1. 降低gas费用
2. 释放资金
3. 简化持仓管理

## 工作原理

合并工具与Polymarket的智能合约交互，以合并二元市场中的相反持仓。当您在同一市场中同时持有YES和NO份额时，此工具将合并它们以回收您的USDC。

## 使用方法

当满足持仓合并条件时，合并器通过主Poly-Maker机器人调用，但您也可以独立使用它：

```
node merge.js [要合并的数量] [条件ID] [是否为负风险市场]
```

示例：
```
node merge.js 1000000 0xasdasda true
```

这将在市场0xasdasda中合并价值1 USDC的相反持仓，该市场是负风险市场。0xasdasda应该是condition_id

## 前置要求

- Node.js
- ethers.js v5.x
- 包含您的Polygon网络私钥的.env文件

## 注意事项

此实现基于开源的Polymarket代码，但已针对自动化做市操作进行了优化。

