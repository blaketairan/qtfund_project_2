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
    
    def __init__(self, 
                 sync_url: str = "http://localhost:7777/api",
                 query_url: str = "http://localhost:8000/api"):
        """
        初始化同步客户端
        
        Args:
            sync_url: 同步服务URL（端口7777）
            query_url: 查询服务URL（端口8000）
        """
        self.sync_url = sync_url
        self.query_url = query_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Full Sync Script v2/1.0'
        })
        logger.info(f"📍 同步服务地址: {self.sync_url}")
        logger.info(f"📍 查询服务地址: {self.query_url}")
    
    def get_all_stocks(self) -> List[Dict[str, Any]]:
        """获取所有股票列表（从查询服务）- 使用大limit获取所有股票"""
        try:
            # 使用足够大的limit值一次性获取所有股票
            params = {
                'limit': 10000,  # API最大支持10000条
                'is_active': 'true'  # 只获取活跃股票
            }
            
            logger.info("📊 开始获取股票列表...")
            response = self.session.get(
                f"{self.query_url}/stock-info/local",
                params=params
            )
            response.raise_for_status()
            result = response.json()

            # 检查API响应格式 (Flask API返回 code=200 表示成功)
            if result.get('code') == 200:
                stocks = result.get('data', [])
                # 转换数据格式，将ticker转换为symbol格式
                converted_stocks = []
                for stock in stocks:
                    # 将API返回的格式转换为脚本期望的格式
                    market_prefix = {
                        'XSHG': 'SH',
                        'XSHE': 'SZ',
                        'BJSE': 'BJ'
                    }.get(stock.get('exchange_code', 'XSHG'), 'SH')

                    converted_stocks.append({
                        'symbol': f"{market_prefix}.{stock.get('ticker', '')}",
                        'stock_name': stock.get('name', ''),
                        'ticker': stock.get('ticker', ''),
                        'exchange_code': stock.get('exchange_code', ''),
                        'is_active': stock.get('is_active', 1),
                        'last_sync_date': stock.get('last_sync_date', '无')
                    })

                logger.info(f"成功获取股票列表: {len(converted_stocks)} 只股票")
                return converted_stocks
            else:
                logger.error(f"API返回错误: code={result.get('code')}, message={result.get('message')}")
                return []

        except Exception as e:
            logger.error(f"获取股票列表异常: {e}")
            return []
    
    def sync_single_stock(self, symbol: str) -> Dict[str, Any]:
        """同步单只股票（调用同步服务）"""
        try:
            data = {'symbol': symbol}
            
            response = self.session.post(
                f"{self.sync_url}/sync/single-stock",
                json=data,
                timeout=300  # 5分钟超时
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"同步股票 {symbol} 失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_etf_list(self) -> List[Dict[str, Any]]:
        """获取ETF列表（从数据库）"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            from database.connection import db_manager
            from models.stock_data import StockInfo
            
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
                        'last_sync_date': str(etf.last_sync_date) if etf.last_sync_date else '无'
                    })
                
                logger.info(f"✅ 成功获取ETF列表: 总计 {len(etf_list)} 只ETF")
                return etf_list
                
        except Exception as e:
            logger.error(f"获取ETF列表失败: {e}")
            return []
    
    def run_etf_sync(self, max_etfs: Optional[int] = None, skip_count: int = 0):
        """运行ETF价格同步（逐只同步模式）"""
        
        logger.info("="*70)
        logger.info("🚀 ETF价格同步开始")
        logger.info("="*70)
        
        # 获取ETF列表
        logger.info("📊 从数据库获取ETF列表...")
        etfs = self.get_etf_list()
        
        if not etfs:
            logger.error("❌ 数据库中没有ETF记录")
            logger.info("   请先执行ETF列表同步:")
            logger.info("   curl -X POST http://localhost:7777/api/sync/etf/lists")
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
        
        # 逐只同步ETF价格（复用现有的sync_single_stock方法）
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
        if len(etfs) > 0:
            logger.info(f"⚡ 平均速度: {total_time/len(etfs):.1f} 秒/ETF")
        logger.info(f"{'='*70}\n")
    
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
    parser.add_argument('--skip', type=int, default=0, help='跳过前N只')
    parser.add_argument('--sync-url', type=str, default='http://localhost:7777/api', 
                        help='同步服务URL（默认: http://localhost:7777/api）')
    parser.add_argument('--etf', action='store_true', 
                        help='同步ETF价格而非股票')
    
    args = parser.parse_args()
    
    client = FullSyncClient(sync_url=args.sync_url)
    
    if args.test:
        # 测试模式
        client.run_test_mode(args.test)
    elif args.etf:
        # ETF价格同步模式（逐只同步）
        client.run_etf_sync(max_etfs=args.max, skip_count=args.skip)
    else:
        # 股票同步模式（原有逻辑）
        client.run_full_sync(max_stocks=args.max, skip_count=args.skip)


if __name__ == "__main__":
    main()
