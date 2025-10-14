#!/usr/bin/env python3
"""
全量股票同步脚本 v2

从Flask获取股票列表，循环调用Flask接口同步每只股票的历史行情
支持测试模式：指定单只股票进行同步
"""

import requests
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 配置日志
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f'full_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"📝 日志文件: {log_file}")


class FullSyncClient:
    """全量同步客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Full Sync Script v2/1.0'
        })
    
    def get_all_stocks(self) -> List[Dict[str, Any]]:
        """获取所有股票列表"""
        try:
            response = self.session.get(f"{self.base_url}/stock-info/local")
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                return result['data']['stocks']
            else:
                logger.error(f"获取股票列表失败: {result.get('message')}")
                return []
                
        except Exception as e:
            logger.error(f"获取股票列表异常: {e}")
            return []
    
    def sync_single_stock(self, symbol: str) -> Dict[str, Any]:
        """同步单只股票"""
        try:
            data = {'symbol': symbol}
            
            response = self.session.post(
                f"{self.base_url}/sync/single-stock",
                json=data,
                timeout=300  # 5分钟超时
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"同步股票 {symbol} 失败: {e}")
            return {"success": False, "error": str(e)}
    
    def run_full_sync(self, max_stocks: Optional[int] = None, skip_count: int = 0):
        """运行全量同步"""
        
        logger.info("="*70)
        logger.info("🚀 全量股票同步开始")
        logger.info("="*70)
        
        # 获取股票列表
        logger.info("📊 获取股票列表...")
        stocks = self.get_all_stocks()
        
        if not stocks:
            logger.error("❌ 无法获取股票列表")
            return
        
        total_stocks = len(stocks)
        logger.info(f"✅ 获取到 {total_stocks} 只股票")
        
        # 应用限制
        if skip_count > 0:
            stocks = stocks[skip_count:]
            logger.info(f"⏭️  跳过前 {skip_count} 只股票")
        
        if max_stocks:
            stocks = stocks[:max_stocks]
            logger.info(f"🎯 限制同步数量: {max_stocks} 只")
        
        logger.info(f"📈 实际同步数量: {len(stocks)} 只")
        logger.info("="*70)
        
        # 统计信息
        success_count = 0
        failed_count = 0
        up_to_date_count = 0
        total_inserted = 0
        
        start_time = time.time()
        
        # 逐只同步
        for idx, stock in enumerate(stocks, 1):
            symbol = stock['symbol']
            stock_name = stock.get('stock_name', symbol)
            last_sync = stock.get('last_sync_date', '无')
            
            logger.info(f"\n[{idx}/{len(stocks)}] 正在同步: {symbol} - {stock_name}")
            logger.info(f"          上次同步: {last_sync}")
            
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
            
            # 进度提示
            if idx % 10 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining = (len(stocks) - idx) * avg_time
                logger.info(f"\n{'─'*70}")
                logger.info(f"进度: {idx}/{len(stocks)} ({idx/len(stocks)*100:.1f}%)")
                logger.info(f"成功: {success_count}, 最新: {up_to_date_count}, 失败: {failed_count}")
                logger.info(f"已用时: {elapsed/60:.1f}分钟, 预计剩余: {remaining/60:.1f}分钟")
                logger.info(f"{'─'*70}\n")
        
        # 最终统计
        total_time = time.time() - start_time
        
        logger.info(f"\n{'='*70}")
        logger.info("🎉 全量同步完成！")
        logger.info(f"{'='*70}")
        logger.info(f"✅ 同步成功: {success_count} 只")
        logger.info(f"📌 已是最新: {up_to_date_count} 只")
        logger.info(f"❌ 同步失败: {failed_count} 只")
        logger.info(f"📊 新增记录: {total_inserted:,} 条")
        logger.info(f"⏱️  总用时: {total_time/60:.1f} 分钟 ({total_time/3600:.2f} 小时)")
        if len(stocks) > 0:
            logger.info(f"⚡ 平均速度: {total_time/len(stocks):.1f} 秒/股")
        logger.info(f"{'='*70}\n")
    
    def run_test_mode(self, symbol: str):
        """测试模式：同步单只股票"""
        
        logger.info("="*70)
        logger.info(f"🧪 测试模式：同步单只股票 {symbol}")
        logger.info("="*70)
        
        result = self.sync_single_stock(symbol)
        
        if result.get('task', {}).get('status') == 'success':
            task_result = result['task']['result']
            logger.info(f"\n✅ 同步成功！")
            logger.info(f"   操作: {task_result.get('action')}")
            logger.info(f"   新增记录: {task_result.get('inserted_count', 0)} 条")
            logger.info(f"   总记录数: {task_result.get('total_records', 0)} 条")
            logger.info(f"   最新日期: {task_result.get('latest_sync_date', 'N/A')}")
        else:
            logger.error(f"\n❌ 同步失败")
            logger.error(f"   错误: {result.get('task', {}).get('result', {}).get('error', '未知错误')}")
        
        logger.info(f"{'='*70}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全量股票同步脚本 v2')
    parser.add_argument('--test', type=str, help='测试模式：指定股票代码（如: SH.600519）')
    parser.add_argument('--max', type=int, help='最大同步数量')
    parser.add_argument('--skip', type=int, default=0, help='跳过前N只股票')
    parser.add_argument('--url', type=str, default='http://localhost:8000/api', help='Flask API地址')
    
    args = parser.parse_args()
    
    client = FullSyncClient(base_url=args.url)
    
    if args.test:
        # 测试模式
        client.run_test_mode(args.test)
    else:
        # 全量同步模式
        client.run_full_sync(max_stocks=args.max, skip_count=args.skip)


if __name__ == "__main__":
    main()
