"""
后台任务管理模块

使用多线程实现后台任务执行，支持启动、停止、查询状态
"""

import threading
import logging
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 运行中
    STOPPING = "stopping"    # 停止中
    STOPPED = "stopped"      # 已停止
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败


class BackgroundTask:
    """后台任务类"""
    
    def __init__(self, task_id: str, task_name: str, task_func: Callable, **kwargs):
        self.task_id = task_id
        self.task_name = task_name
        self.task_func = task_func
        self.kwargs = kwargs
        
        self.status = TaskStatus.PENDING
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        self.progress = {
            'current': 0,
            'total': 0,
            'percentage': 0,
            'message': ''
        }
        
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
    
    def start(self):
        """启动任务"""
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"任务状态为{self.status.value}，无法启动")
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
        self.thread.start()
        
        logger.info(f"后台任务已启动: {self.task_name} (ID: {self.task_id})")
    
    def _run(self):
        """执行任务的内部方法"""
        try:
            # 将stop_flag传递给任务函数
            self.kwargs['stop_flag'] = self.stop_flag
            self.kwargs['progress_callback'] = self._update_progress
            
            result = self.task_func(**self.kwargs)
            
            if self.stop_flag.is_set():
                self.status = TaskStatus.STOPPED
                self.result = {'message': '任务已被用户停止'}
                logger.info(f"任务已停止: {self.task_name}")
            else:
                self.status = TaskStatus.COMPLETED
                self.result = result
                logger.info(f"任务已完成: {self.task_name}")
                
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            logger.error(f"任务执行失败: {self.task_name}, 错误: {e}")
        finally:
            self.completed_at = datetime.now()
    
    def stop(self):
        """停止任务"""
        if self.status != TaskStatus.RUNNING:
            raise ValueError(f"任务状态为{self.status.value}，无法停止")
        
        logger.info(f"请求停止任务: {self.task_name}")
        self.status = TaskStatus.STOPPING
        self.stop_flag.set()
    
    def _update_progress(self, current: int, total: int, message: str = ''):
        """更新进度"""
        self.progress['current'] = current
        self.progress['total'] = total
        self.progress['percentage'] = round(current / total * 100, 2) if total > 0 else 0
        self.progress['message'] = message
    
    def get_info(self) -> Dict[str, Any]:
        """获取任务信息"""
        duration = None
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            duration = (end_time - self.started_at).total_seconds()
        
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'status': self.status.value,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'started_at': self.started_at.strftime('%Y-%m-%d %H:%M:%S') if self.started_at else None,
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else None,
            'duration_seconds': round(duration, 2) if duration else None,
            'progress': self.progress,
            'result': self.result,
            'error': self.error
        }


class BackgroundTaskManager:
    """后台任务管理器（单例）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.tasks: Dict[str, BackgroundTask] = {}
        self._initialized = True
        logger.info("后台任务管理器已初始化")
    
    def create_task(self, task_name: str, task_func: Callable, **kwargs) -> str:
        """创建并启动后台任务"""
        task_id = f"{task_name}_{int(time.time() * 1000)}"
        
        task = BackgroundTask(task_id, task_name, task_func, **kwargs)
        self.tasks[task_id] = task
        task.start()
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """获取任务对象"""
        return self.tasks.get(task_id)
    
    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        try:
            task.stop()
            return True
        except ValueError as e:
            logger.warning(f"停止任务失败: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        return task.get_info()
    
    def list_tasks(self, status_filter: Optional[str] = None) -> list:
        """列出所有任务"""
        tasks = []
        for task in self.tasks.values():
            if status_filter and task.status.value != status_filter:
                continue
            tasks.append(task.get_info())
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x['created_at'], reverse=True)
        return tasks
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        now = datetime.now()
        to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.completed_at:
                age_hours = (now - task.completed_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个旧任务")
        
        return len(to_remove)


# 全局任务管理器实例
task_manager = BackgroundTaskManager()
