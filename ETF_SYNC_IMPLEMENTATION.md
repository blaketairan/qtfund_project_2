# ETF同步实现方案

## 需求确认

✅ **用户需求已记录在spec中**：
- ETF价格同步采用逐只同步模式
- 复用 `/api/sync/single-stock` 接口（与股票同步一致）
- 避免批量同步，防止超时
- 每只ETF同步后记录 `last_sync_date`

## 实现方案

### 方案1：扩展 full_sync_v2.py（推荐）

在 `full_sync_v2.py` 中添加ETF同步支持：

```python
class FullSyncClient:
    # ... 现有代码 ...
    
    def get_etf_list(self) -> List[Dict[str, Any]]:
        """获取ETF列表（从数据库）"""
        try:
            from database.connection import db_manager
            from models.stock_data import StockInfo
            from sqlalchemy import and_
            
            with db_manager.get_session() as session:
                # 查询is_etf='Y'的记录
                etfs = session.query(StockInfo).filter(
                    StockInfo.is_etf == 'Y'
                ).all()
                
                etf_list = []
                for etf in etfs:
                    etf_list.append({
                        'symbol': etf.symbol,
                        'stock_name': etf.stock_name,
                        'ticker': etf.ticker,
                        'exchange_code': etf.market_code,
                        'is_active': etf.is_active,
                        'last_sync_date': etf.last_sync_date
                    })
                
                return etf_list
        except Exception as e:
            logger.error(f"获取ETF列表失败: {e}")
            return []
    
    def run_etf_sync(self, max_etfs: Optional[int] = None, skip_count: int = 0):
        """运行ETF价格同步"""
        
        logger.info("="*70)
        logger.info("🚀 ETF价格同步开始")
        logger.info("="*70)
        
        # 获取ETF列表
        logger.info("📊 从数据库获取ETF列表...")
        etfs = self.get_etf_list()
        
        if not etfs:
            logger.error("❌ 数据库中没有ETF记录，请先同步ETF列表")
            logger.info("   执行: curl -X POST http://localhost:7777/api/sync/etf/lists")
            return
        
        total_etfs = len(etfs)
        logger.info(f"✅ 获取到 {total_etfs} 只ETF")
        
        # 应用限制
        if skip_count > 0:
            etfs = etfs[skip_count:]
            logger.info(f"⏭️  跳过前 {skip_count} 只ETF")
        
        if max_etfs:
            etfs = etfs[:max_etfs]
            logger.info(f"🎯 限制同步数量: {max_etfs} 只")
        
        logger.info(f"📈 实际同步数量: {len(etfs)} 只")
        logger.info("="*70)
        
        # 统计信息
        success_count = 0
        failed_count = 0
        up_to_date_count = 0
        total_inserted = 0
        
        start_time = time.time()
        
        # 逐只同步（复用现有的sync_single_stock方法）
        for idx, etf in enumerate(etfs, 1):
            symbol = etf['symbol']
            etf_name = etf.get('stock_name', symbol)
            last_sync = etf.get('last_sync_date', '无')
            
            logger.info(f"\n[{idx}/{len(etfs)}] 正在同步ETF: {symbol} - {etf_name}")
            logger.info(f"          上次同步: {last_sync}")
            
            # 调用相同的single-stock接口
            result = self.sync_single_stock(symbol)
            
            if result.get('task', {}).get('status') == 'success':
                task_result = result['task']['result']
                action = task_result.get('action')
                
                if action == 'up_to_date':
                    up_to_date_count += 1
                    logger.info(f"          ✅ 已是最新")
                elif action == 'completed':
                    success_count += 1
                    inserted = task_result.get('inserted_count', 0)
                    total_inserted += inserted
                    latest_date = task_result.get('latest_sync_date', '')
                    logger.info(f"          ✅ 成功 - 新增 {inserted} 条, 最新日期: {latest_date}")
                else:
                    success_count += 1
                    logger.info(f"          ✅ 完成")
            else:
                failed_count += 1
                error = result.get('task', {}).get('result', {}).get('error', '未知错误')
                logger.info(f"          ❌ 失败 - {error}")
            
            # 进度提示（每10只）
            if idx % 10 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining = (len(etfs) - idx) * avg_time
                logger.info(f"\n{'─'*70}")
                logger.info(f"进度: {idx}/{len(etfs)} ({idx/len(etfs)*100:.1f}%)")
                logger.info(f"成功: {success_count}, 最新: {up_to_date_count}, 失败: {failed_count}")
                logger.info(f"已用时: {elapsed/60:.1f}分钟, 预计剩余: {remaining/60:.1f}分钟")
                logger.info(f"{'─'*70}\n")
        
        # 最终统计
        total_time = time.time() - start_time
        
        logger.info(f"\n{'='*70}")
        logger.info("🎉 ETF价格同步完成！")
        logger.info(f"{'='*70}")
        logger.info(f"✅ 同步成功: {success_count} 只")
        logger.info(f"📌 已是最新: {up_to_date_count} 只")
        logger.info(f"❌ 同步失败: {failed_count} 只")
        logger.info(f"📊 新增记录: {total_inserted:,} 条")
        logger.info(f"⏱️  总用时: {total_time/60:.1f} 分钟")
        logger.info(f"{'='*70}\n")
```

### 在main函数中添加参数

```python
def main():
    parser = argparse.ArgumentParser(description='全量股票同步脚本 v2')
    parser.add_argument('--test', type=str, help='测试模式：指定股票代码')
    parser.add_argument('--max', type=int, help='最大同步数量')
    parser.add_argument('--skip', type=int, default=0, help='跳过前N只')
    parser.add_argument('--sync-url', type=str, default='http://localhost:7777/api')
    parser.add_argument('--etf', action='store_true', help='同步ETF价格（而非股票）')
    
    args = parser.parse_args()
    client = FullSyncClient(sync_url=args.sync_url)
    
    if args.etf:
        # ETF同步模式
        client.run_etf_sync(max_etfs=args.max, skip_count=args.skip)
    elif args.test:
        # 测试模式
        client.run_test_mode(args.test)
    else:
        # 股票同步模式（原有逻辑）
        client.run_full_sync(max_stocks=args.max, skip_count=args.skip)
```

## 使用方式

### 1. 首次同步：同步ETF列表到数据库

```bash
# 通过API同步ETF列表
curl -X POST http://localhost:7777/api/sync/etf/lists \
  -H "Content-Type: application/json" \
  -d '{"exchange_codes": ["XSHG", "XSHE"]}'
```

### 2. 同步ETF价格（逐只同步）

```bash
# 同步所有ETF价格
python full_sync_v2.py --etf

# 限制数量
python full_sync_v2.py --etf --max 10

# 跳过前N只
python full_sync_v2.py --etf --skip 50

# 测试单只ETF
python full_sync_v2.py --etf --test SH.510050
```

## 数据流程

### 完整流程

```
1. ETF列表同步（一次性）
   POST /api/sync/etf/lists
   ↓
   数据库中ETF记录（is_etf='Y'）

2. ETF价格同步（定期执行）
   python full_sync_v2.py --etf
   ↓
   逐只调用 /api/sync/single-stock
   ↓
   每只完成后记录last_sync_date

3. 增量同步
   下次运行时检查last_sync_date
   只同步缺失的日期
```

## 优势

✅ **复用现有接口**：使用相同的`/api/sync/single-stock`接口  
✅ **避免超时**：逐只同步，不会因数据量大而超时  
✅ **增量同步**：利用`last_sync_date`支持增量更新  
✅ **统一模式**：与股票同步完全一致的逻辑  
✅ **容错性强**：某只ETF失败不影响其他ETF  
✅ **进度跟踪**：实时显示同步进度

## 与现有批量API的对比

| 特性 | 批量API | 逐只同步（新方案） |
|------|---------|------------------|
| 超时风险 | 高（数据量大） | 低（单只执行） |
| 进度可见 | 不可见 | 实时可见 |
| 容错性 | 差（整体失败） | 好（单只失败不影响） |
| 维护成本 | 高（需要后台任务） | 低（同股票同步） |
| 实现复杂度 | 高 | 低 |

## 实施建议

### 优先级：高

这个方案是最佳实践，因为：
1. **安全**：不会因数据量大而超时
2. **一致**：与股票同步逻辑完全一致
3. **简单**：复用现有接口，无需额外开发
4. **可靠**：成熟的股票同步逻辑已验证可用

### 需要修改的文件

1. `full_sync_v2.py` - 添加 `get_etf_list()` 和 `run_etf_sync()` 方法
2. `full_sync_v2.py` - 在 `main()` 中添加 `--etf` 参数

### 无需修改

- Flask API端点（复用现有的 `/api/sync/single-stock`）
- 数据库schema（已有 `last_sync_date` 字段）
- ETF同步服务（仅用于列表同步）

## 总结

✅ **Spec已更新**：记录了逐只同步的需求  
✅ **实现方案**：扩展现有的`full_sync_v2.py`  
✅ **优势明确**：安全、简单、可靠  
⏳ **待实施**：修改`full_sync_v2.py`添加ETF支持
