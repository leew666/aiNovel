"""
成本追踪器

追踪LLM API调用成本，实现日预算限制
"""
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from ainovel.llm.exceptions import BudgetExceededError


class CostTracker:
    """
    成本追踪器

    功能：
    1. 追踪每日累计成本
    2. 检查是否超出日预算
    3. 持久化成本记录
    """

    def __init__(
        self,
        daily_budget: float = 5.0,
        storage_path: Optional[str] = None,
    ):
        """
        初始化成本追踪器

        Args:
            daily_budget: 每日预算上限（美元），默认$5
            storage_path: 成本记录存储路径，默认为 data/cost_tracker.json
        """
        self.daily_budget = daily_budget

        # 设置存储路径
        if storage_path is None:
            storage_path = "data/cost_tracker.json"
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载历史记录
        self._load_records()

    def _load_records(self):
        """从磁盘加载成本记录"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
                logger.debug(f"成本记录已加载: {self.storage_path}")
            except Exception as e:
                logger.warning(f"加载成本记录失败: {e}，将创建新记录")
                self.records = {}
        else:
            self.records = {}

    def _save_records(self):
        """保存成本记录到磁盘"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.records, f, indent=2, ensure_ascii=False)
            logger.debug(f"成本记录已保存: {self.storage_path}")
        except Exception as e:
            logger.error(f"保存成本记录失败: {e}")

    def get_today_key(self) -> str:
        """获取今天的日期键"""
        return date.today().isoformat()

    def get_today_cost(self) -> float:
        """
        获取今日累计成本

        Returns:
            今日累计成本（美元）
        """
        today_key = self.get_today_key()
        today_record = self.records.get(today_key, {})
        return today_record.get("total_cost", 0.0)

    def get_today_remaining(self) -> float:
        """
        获取今日剩余预算

        Returns:
            今日剩余预算（美元）
        """
        return max(0.0, self.daily_budget - self.get_today_cost())

    def check_budget(self, estimated_cost: float) -> bool:
        """
        检查是否在预算内

        Args:
            estimated_cost: 预计花费（美元）

        Returns:
            True 如果在预算内，False 如果会超出预算
        """
        today_cost = self.get_today_cost()
        return (today_cost + estimated_cost) <= self.daily_budget

    def add_cost(
        self,
        cost: float,
        usage: Dict[str, int],
        model: str = "unknown",
        task_type: str = "generation",
    ) -> Dict[str, Any]:
        """
        添加一次API调用成本

        Args:
            cost: 本次调用成本（美元）
            usage: Token使用情况
            model: 使用的模型名称
            task_type: 任务类型（如 generation, outline, chapter）

        Returns:
            成本统计信息

        Raises:
            BudgetExceededError: 如果超出日预算
        """
        # 检查预算
        if not self.check_budget(cost):
            remaining = self.get_today_remaining()
            raise BudgetExceededError(
                f"超出日预算限制！日预算: ${self.daily_budget:.2f}, "
                f"今日已用: ${self.get_today_cost():.2f}, "
                f"剩余: ${remaining:.2f}, "
                f"本次需要: ${cost:.2f}"
            )

        # 获取今日记录
        today_key = self.get_today_key()
        if today_key not in self.records:
            self.records[today_key] = {
                "date": today_key,
                "total_cost": 0.0,
                "total_tokens": 0,
                "call_count": 0,
                "calls": [],
            }

        today_record = self.records[today_key]

        # 添加本次调用记录
        call_record = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "task_type": task_type,
            "cost": cost,
            "usage": usage,
        }
        today_record["calls"].append(call_record)

        # 更新统计
        today_record["total_cost"] += cost
        today_record["total_tokens"] += usage.get("total_tokens", 0)
        today_record["call_count"] += 1

        # 保存到磁盘
        self._save_records()

        logger.info(
            f"成本记录已添加: ${cost:.4f} | "
            f"今日累计: ${today_record['total_cost']:.4f} / ${self.daily_budget:.2f} | "
            f"剩余: ${self.get_today_remaining():.4f}"
        )

        return {
            "today_cost": today_record["total_cost"],
            "today_remaining": self.get_today_remaining(),
            "daily_budget": self.daily_budget,
            "call_count": today_record["call_count"],
        }

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            days: 统计最近N天

        Returns:
            统计信息字典
        """
        today = date.today()
        stats = {
            "daily_budget": self.daily_budget,
            "today": self.get_today_key(),
            "today_cost": self.get_today_cost(),
            "today_remaining": self.get_today_remaining(),
            "recent_days": [],
        }

        # 统计最近N天
        for i in range(days):
            day = today - timedelta(days=i)
            day_key = day.isoformat()
            day_record = self.records.get(day_key, {})
            stats["recent_days"].append(
                {
                    "date": day_key,
                    "cost": day_record.get("total_cost", 0.0),
                    "tokens": day_record.get("total_tokens", 0),
                    "calls": day_record.get("call_count", 0),
                }
            )

        return stats

    def reset_budget(self, new_budget: float):
        """
        重置日预算

        Args:
            new_budget: 新的日预算（美元）
        """
        if new_budget <= 0:
            raise ValueError("预算必须大于0")

        self.daily_budget = new_budget
        logger.info(f"日预算已更新为 ${new_budget:.2f}")

    def clear_today(self):
        """清除今日记录（用于测试）"""
        today_key = self.get_today_key()
        if today_key in self.records:
            del self.records[today_key]
            self._save_records()
            logger.warning("今日成本记录已清除")


# 全局单例
_global_tracker: Optional[CostTracker] = None


def get_cost_tracker(
    daily_budget: Optional[float] = None,
    storage_path: Optional[str] = None,
) -> CostTracker:
    """
    获取全局成本追踪器单例

    Args:
        daily_budget: 每日预算（首次调用时有效）
        storage_path: 存储路径（首次调用时有效）

    Returns:
        CostTracker实例
    """
    global _global_tracker

    if _global_tracker is None:
        # 首次创建，使用默认值或传入值
        _global_tracker = CostTracker(
            daily_budget=daily_budget or 5.0,
            storage_path=storage_path,
        )

    return _global_tracker


def reset_cost_tracker():
    """重置全局成本追踪器（用于测试）"""
    global _global_tracker
    _global_tracker = None
