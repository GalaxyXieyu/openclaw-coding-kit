# 批量任务稳健性（P1）

**适用场景**：本次变更包含批量处理脚本或后台任务

## 批量任务审查清单
- [ ] **验证机制**：任务执行后，如何验证结果正确性？是否有日志或统计数据？
- [ ] **统计机制**：是否统计成功/失败数量？是否有进度展示或定期汇报？
- [ ] **断点续跑机制**：任务中断后能否从断点恢复？是否有幂等性保证？
- [ ] **重试机制**：失败的任务是否会自动重试？重试次数和策略是否合理？
- [ ] **资源保护**：并发度是否可控？是否有超时控制？

**最佳实践示例**：
```python
class BatchProcessor:
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.progress_file = 'progress.json'

    def process_batch(self, items):
        # 断点续跑：从上次中断位置恢复
        processed_ids = self.load_progress()

        for item in items:
            # 幂等性保证：跳过已处理的数据
            if item.id in processed_ids:
                continue

            try:
                self.process_item(item)
                self.success_count += 1
                self.save_progress(item.id)
            except Exception as e:
                self.failure_count += 1
                self.retry_queue.add(item)  # 重试机制
                logger.error(f"Failed: {item.id}, error: {e}")

        # 统计报告
        logger.info(f"Total: {len(items)}, Success: {self.success_count}, Failed: {self.failure_count}")
```
