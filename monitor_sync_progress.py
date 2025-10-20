#!/usr/bin/env python3
"""
实时监控全量同步进度

监控内容:
1. 数据库记录增长
2. Flask服务器日志
3. 同步状态更新
4. 预估完成时间
"""

import requests
import time
import json
from datetime import datetime, timezone, timedelta
import os

CHINA_TZ = timezone(timedelta(hours=8))
API_BASE = "http://localhost:8000/api"

class SyncProgressMonitor:
    def __init__(self):
        self.start_time = datetime.now(CHINA_TZ)
        self.initial_records = 0
        self.initial_stocks = 0
        self.last_records = 0
        self.last_check_time = self.start_time
        
    def get_current_status(self):
        """获取当前同步状态"""
        try:
            response = requests.get(f"{API_BASE}/sync/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                db_info = data['data']['database']
                return {
                    'records': db_info.get('stock_data_count', 0),
                    'stocks': db_info.get('stock_info_count', 0),
                    'latest_date': db_info.get('latest_data_date', 'N/A'),
                    'connected': db_info.get('connected', False)
                }
        except Exception as e:
            return None
    
    def calculate_progress(self, current_records, current_stocks):
        """计算同步进度和速度"""
        now = datetime.now(CHINA_TZ)
        
        if self.initial_records == 0:
            self.initial_records = current_records
            self.initial_stocks = current_stocks
        
        # 总增长
        total_growth = current_records - self.initial_records
        stock_growth = current_stocks - self.initial_stocks
        
        # 时间差
        total_elapsed = (now - self.start_time).total_seconds() / 3600  # 小时
        interval_elapsed = (now - self.last_check_time).total_seconds() / 60  # 分钟
        
        # 速度计算
        if total_elapsed > 0:
            records_per_hour = total_growth / total_elapsed
            stocks_per_hour = stock_growth / total_elapsed
        else:
            records_per_hour = 0
            stocks_per_hour = 0
        
        # 瞬时速度
        interval_growth = current_records - self.last_records
        if interval_elapsed > 0:
            instant_records_per_min = interval_growth / interval_elapsed
        else:
            instant_records_per_min = 0
        
        self.last_records = current_records
        self.last_check_time = now
        
        return {
            'total_growth': total_growth,
            'stock_growth': stock_growth,
            'total_elapsed_hours': total_elapsed,
            'records_per_hour': records_per_hour,
            'stocks_per_hour': stocks_per_hour,
            'instant_records_per_min': instant_records_per_min
        }
    
    def estimate_completion(self, current_stocks, records_per_hour):
        """预估完成时间"""
        target_stocks = 1000  # 第一阶段目标
        remaining_stocks = max(0, target_stocks - current_stocks)
        
        if records_per_hour > 0 and remaining_stocks > 0:
            # 假设每只股票平均6000条记录
            avg_records_per_stock = 6000
            remaining_records = remaining_stocks * avg_records_per_stock
            remaining_hours = remaining_records / records_per_hour
            
            completion_time = datetime.now(CHINA_TZ) + timedelta(hours=remaining_hours)
            return {
                'remaining_stocks': remaining_stocks,
                'remaining_hours': remaining_hours,
                'estimated_completion': completion_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        return None
    
    def display_progress(self):
        """显示进度信息"""
        status = self.get_current_status()
        
        if not status:
            print("❌ 无法获取同步状态")
            return
        
        progress = self.calculate_progress(status['records'], status['stocks'])
        estimation = self.estimate_completion(status['stocks'], progress['records_per_hour'])
        
        # 清屏并显示进度
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🚀 全量同步进度监控")
        print("="*60)
        print(f"⏰ 监控开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 当前时间: {datetime.now(CHINA_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  已运行时间: {progress['total_elapsed_hours']:.1f} 小时")
        print()
        
        print("📈 数据库状态:")
        print(f"   总记录数: {status['records']:,} 条")
        print(f"   股票数量: {status['stocks']:,} 只")
        print(f"   最新日期: {status['latest_date']}")
        print(f"   连接状态: {'✅ 已连接' if status['connected'] else '❌ 未连接'}")
        print()
        
        print("📊 增长统计:")
        print(f"   新增记录: {progress['total_growth']:,} 条")
        print(f"   新增股票: {progress['stock_growth']:,} 只")
        print(f"   记录增速: {progress['records_per_hour']:.0f} 条/小时")
        print(f"   股票增速: {progress['stocks_per_hour']:.1f} 只/小时")
        print(f"   瞬时速度: {progress['instant_records_per_min']:.0f} 条/分钟")
        print()
        
        if estimation:
            print("🎯 预估完成:")
            print(f"   剩余股票: {estimation['remaining_stocks']:,} 只")
            print(f"   剩余时间: {estimation['remaining_hours']:.1f} 小时")
            print(f"   预计完成: {estimation['estimated_completion']}")
        else:
            print("🎯 预估完成: 计算中...")
        
        print()
        print("💡 提示: Ctrl+C 退出监控")
        print("="*60)
    
    def run(self, interval=30):
        """运行监控"""
        print("🔍 启动全量同步进度监控...")
        print(f"📊 每 {interval} 秒更新一次")
        
        try:
            while True:
                self.display_progress()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
            print(f"⏰ 总监控时间: {(datetime.now(CHINA_TZ) - self.start_time).total_seconds() / 3600:.1f} 小时")

def main():
    monitor = SyncProgressMonitor()
    monitor.run(interval=30)  # 每30秒更新一次

if __name__ == "__main__":
    main()