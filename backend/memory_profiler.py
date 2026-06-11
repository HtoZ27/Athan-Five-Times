#!/usr/bin/env python3
"""
Memory Profiler for Athan Five Times Prayer App.
يوفر أدوات لمراقبة وتحليل استهلاك الذاكرة.
"""

import tracemalloc
import gc
import sys
import os
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemorySnapshot:
    """لقطة للذاكرة في وقت معين."""
    timestamp: str
    current_mb: float
    peak_mb: float
    object_count: int
    top_allocations: List[Tuple[str, int, int]]  # (file, line, size_bytes)


class MemoryProfiler:
    """مراقب الذاكرة للتطبيق."""

    def __init__(self, max_frames: int = 25):
        self.max_frames = max_frames  # أقصى عدد من اللقطات قبل الحذف
        self._snapshots: List[MemorySnapshot] = []
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._interval = 5.0  # ثواني

    def start(self, interval: float = 5.0):
        """بدء المراقبة."""
        if self._running:
            return
        self._interval = interval
        self._running = True
        tracemalloc.start(25)  # تخزين 25 إطار
        gc.collect()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print(f"[MemoryProfiler] بدأ المراقبة كل {interval} ثانية")

    def stop(self):
        """إيقاف المراقبة."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        tracemalloc.stop()
        print("[MemoryProfiler] تم إيقاف المراقبة")

    def _monitor_loop(self):
        """حلقة المراقبة الخلفية."""
        while self._running:
            time.sleep(self._interval)
            if not self._running:
                break
            self.take_snapshot()

    def take_snapshot(self) -> MemorySnapshot:
        """أخذ لقطة ذاكرة."""
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()

        # أعلى 10 تخصيصات
        top_stats = snapshot.statistics('lineno')[:10]
        top_allocations = []
        for stat in top_stats:
            frame = stat.traceback[0] if stat.traceback else None
            if frame:
                top_allocations.append((
                    f"{frame.filename}:{frame.lineno}",
                    stat.size,
                    stat.count
                ))

        mem_snapshot = MemorySnapshot(
            timestamp=datetime.now().isoformat(),
            current_mb=current / (1024 * 1024),
            peak_mb=peak / (1024 * 1024),
            object_count=len(gc.get_objects()),
            top_allocations=top_allocations
        )
        self._snapshots.append(mem_snapshot)
        if len(self._snapshots) > self.max_frames:
            self._snapshots.pop(0)
        return mem_snapshot

    def get_summary(self) -> Dict:
        """ملخص الاستهلاك."""
        if not self._snapshots:
            return {"error": "لا توجد لقطات"}

        latest = self._snapshots[-1]
        first = self._snapshots[0]

        return {
            "current_mb": round(latest.current_mb, 2),
            "peak_mb": round(latest.peak_mb, 2),
            "growth_mb": round(latest.current_mb - first.current_mb, 2),
            "object_count": latest.object_count,
            "snapshots_count": len(self._snapshots),
            "top_allocations": latest.top_allocations[:5],
            "monitoring_duration_sec": len(self._snapshots) * self._interval
        }

    def print_report(self):
        """طباعة تقرير مفصل."""
        summary = self.get_summary()
        if "error" in summary:
            print(summary["error"])
            return

        print("\n" + "="*60)
        print("📊 تقرير الذاكرة - Athan Five Times")
        print("="*60)
        print(f"الذاكرة الحالية: {summary['current_mb']} MB")
        print(f"الذروة: {summary['peak_mb']} MB")
        print(f"النمو منذ البداية: {summary['growth_mb']} MB")
        print(f"عدد الكائنات: {summary['object_count']:,}")
        print(f"مدة المراقبة: {summary['monitoring_duration_sec']} ثانية")
        print(f"عدد اللقطات: {summary['snapshots_count']}")
        print("\n🔝 أعلى 5 تخصيصات:")
        for i, (loc, size, count) in enumerate(summary['top_allocations'], 1):
            print(f"  {i}. {loc} - {size/1024:.1f} KB ({count} كائنات)")
        print("="*60 + "\n")

    def save_report(self, filepath: str):
        """حفظ التقرير في ملف JSON."""
        import json
        data = {
            "summary": self.get_summary(),
            "snapshots": [
                {
                    "timestamp": s.timestamp,
                    "current_mb": round(s.current_mb, 2),
                    "peak_mb": round(s.peak_mb, 2),
                    "object_count": s.object_count,
                    "top_allocations": s.top_allocations[:10]
                }
                for s in self._snapshots
            ]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[MemoryProfiler] تم حفظ التقرير في: {filepath}")


# متغير عام للاستخدام السهل
_profiler: Optional[MemoryProfiler] = None


def start_profiling(interval: float = 5.0):
    """بدء المراقبة (دالة مساعدة)."""
    global _profiler
    if _profiler is None:
        _profiler = MemoryProfiler()
    _profiler.start(interval)


def stop_profiling():
    """إيقاف المراقبة."""
    global _profiler
    if _profiler:
        _profiler.stop()
        _profiler.print_report()


def get_memory_usage() -> Tuple[float, float]:
    """الحصول على الاستخدام الحالي (current, peak) بالميجابايت."""
    if tracemalloc.is_tracing():
        current, peak = tracemalloc.get_traced_memory()
        return current / (1024 * 1024), peak / (1024 * 1024)
    return 0.0, 0.0


if __name__ == "__main__":
    # اختبار سريع
    import random
    print("اختبار MemoryProfiler...")
    profiler = MemoryProfiler()
    profiler.start(1.0)

    # محاكاة تخصيص ذاكرة
    data = []
    for i in range(5):
        # تخصيص ~1MB كل مرة
        data.append(bytearray(1024 * 1024))
        time.sleep(1)

    profiler.stop()
    profiler.print_report()
    profiler.save_report("memory_report.json")