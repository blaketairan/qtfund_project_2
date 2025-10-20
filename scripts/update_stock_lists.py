#!/usr/bin/env python3
"""
股票清单日更新脚本

用于定期更新交易所股票清单，识别新增和变更的股票
"""

import sys
import os
from datetime import datetime, timedelta
import argparse

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_fetcher.exchange_stocks import fetch_all_chinese_exchange_stocks
from constants.stock_lists_loader import StockListsManager


def update_stock_lists(output_dir: str = "constants/stock_lists") -> dict:
    """
    更新股票清单
    
    Args:
        output_dir: 输出目录
        
    Returns:
        dict: 更新结果统计
    """
    print(f"🔄 开始更新股票清单...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 获取更新前的统计
    print("📊 更新前统计:")
    manager = StockListsManager(output_dir)
    if manager.load_all_stock_lists():
        old_stats = manager.get_statistics()
        print(f"   总股票数: {old_stats['total_stocks']}")
        for exchange, info in old_stats['exchanges'].items():
            print(f"   {exchange}: {info['total']} 只")
    else:
        old_stats = {'total_stocks': 0, 'exchanges': {}}
        print("   未找到现有数据")
    
    # 执行更新
    print(f"\n🚀 执行更新...")
    results = fetch_all_chinese_exchange_stocks(output_dir=output_dir)
    
    # 获取更新后的统计
    print(f"\n📈 更新后统计:")
    manager.load_all_stock_lists()
    new_stats = manager.get_statistics()
    print(f"   总股票数: {new_stats['total_stocks']}")
    
    # 计算变化
    total_change = new_stats['total_stocks'] - old_stats['total_stocks']
    
    update_summary = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'old_total': old_stats['total_stocks'],
        'new_total': new_stats['total_stocks'],
        'total_change': total_change,
        'successful_exchanges': len([r for r in results if r['success']]),
        'failed_exchanges': len([r for r in results if not r['success']]),
        'exchange_details': []
    }
    
    print(f"\n📋 更新结果:")
    print(f"   总变化: {total_change:+d} 只股票")
    print(f"   成功更新: {update_summary['successful_exchanges']} 个交易所")
    
    if update_summary['failed_exchanges'] > 0:
        print(f"   更新失败: {update_summary['failed_exchanges']} 个交易所")
    
    # 详细的交易所变化
    for result in results:
        if result['success']:
            exchange_code = result['exchange_code']
            old_count = old_stats['exchanges'].get(exchange_code, {}).get('total', 0)
            new_count = result['total_stocks']
            change = new_count - old_count
            
            detail = {
                'exchange_code': exchange_code,
                'exchange_name': result['exchange_name_cn'],
                'old_count': old_count,
                'new_count': new_count,
                'change': change,
                'new_stocks': result['new_stocks']
            }
            update_summary['exchange_details'].append(detail)
            
            print(f"   {result['exchange_name_cn']}: {old_count} -> {new_count} ({change:+d})")
            if result['new_stocks'] > 0:
                print(f"     新增股票: {result['new_stocks']} 只")
    
    return update_summary


def show_new_stocks(days: int = 7):
    """
    显示最近新增的股票
    
    Args:
        days: 天数
    """
    print(f"\n🆕 最近 {days} 天新增股票:")
    
    manager = StockListsManager()
    if not manager.load_all_stock_lists():
        print("   ❌ 无法加载股票清单")
        return
    
    new_stocks = manager.get_newly_added_stocks(days)
    
    if not new_stocks:
        print(f"   最近 {days} 天无新增股票")
        return
    
    print(f"   找到 {len(new_stocks)} 只新增股票:")
    
    # 按交易所分组显示
    by_exchange = {}
    for stock in new_stocks:
        if stock.exchange_code not in by_exchange:
            by_exchange[stock.exchange_code] = []
        by_exchange[stock.exchange_code].append(stock)
    
    for exchange_code, stocks in by_exchange.items():
        print(f"   {exchange_code} ({len(stocks)} 只):")
        for stock in stocks[:10]:  # 最多显示10只
            print(f"     {stock.symbol}: {stock.name} ({stock.first_fetch_time})")
        if len(stocks) > 10:
            print(f"     ... 还有 {len(stocks) - 10} 只")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='更新交易所股票清单')
    parser.add_argument('--output-dir', default='constants/stock_lists',
                       help='输出目录 (默认: constants/stock_lists)')
    parser.add_argument('--show-new', type=int, default=7, metavar='DAYS',
                       help='显示最近N天新增股票 (默认: 7)')
    parser.add_argument('--no-update', action='store_true',
                       help='跳过更新，仅显示统计信息')
    
    args = parser.parse_args()
    
    try:
        if not args.no_update:
            # 执行更新
            summary = update_stock_lists(args.output_dir)
            
            # 显示最近新增股票
            if args.show_new > 0:
                show_new_stocks(args.show_new)
            
            print(f"\n✅ 更新完成!")
            
            # 如果有重大变化，给出提醒
            if abs(summary['total_change']) > 100:
                print(f"⚠️  注意: 股票总数变化较大 ({summary['total_change']:+d})")
                print("   建议检查数据源或网络连接状况")
            
        else:
            # 仅显示统计信息
            print("📊 当前股票清单统计:")
            manager = StockListsManager(args.output_dir)
            if manager.load_all_stock_lists():
                stats = manager.get_statistics()
                print(f"   总股票数: {stats['total_stocks']}")
                print(f"   更新时间: {stats['loaded_at']}")
                for exchange, info in stats['exchanges'].items():
                    print(f"   {exchange}: {info['total']} 只 (活跃: {info['active']})")
                
                if args.show_new > 0:
                    show_new_stocks(args.show_new)
            else:
                print("   ❌ 无法加载股票清单")
    
    except KeyboardInterrupt:
        print(f"\n\n⏹️  更新被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()