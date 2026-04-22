# 性能与资源管理（P0）

## 1. 内存管理
**检查清单**：
- [ ] 大对象或缓存是否及时释放？
- [ ] 是否存在循环引用导致的内存无法回收？
- [ ] 长时间运行的进程是否会不断积累内存占用？
- [ ] 大数据处理是否采用流式处理、分批加载等方式？

**反模式与最佳实践**：
```python
# 反模式：一次性加载所有数据到内存
users = User.objects.all()
for user in users:
    process(user)

# 最佳实践：流式处理，避免内存占用过高
for user in User.objects.all().iterator(chunk_size=1000):
    process(user)
```

## 2. 并发控制
**检查清单**：
- [ ] 是否正确使用锁、信号量或其他同步机制？
- [ ] 并发数是否可配置？是否有上限控制，避免资源耗尽？
- [ ] 是否考虑了线程安全问题（如共享变量的访问）？
- [ ] 数据库连接池、HTTP 连接池等资源池是否合理配置和复用？

**反模式与最佳实践**：
```python
# 反模式：无并发数限制，可能导致资源耗尽
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(task, item) for item in items]
    for future in as_completed(futures):
        future.result()

# 最佳实践：限制并发数，添加超时控制
max_workers = config.get('max_workers', 10)
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(task, item) for item in items]
    for future in as_completed(futures):
        try:
            future.result(timeout=30)
        except TimeoutError:
            logger.error(f"Task timeout")
    pass
```

## 3. 数据库与外部服务压力
**检查清单**：
- [ ] 批量操作或高频请求是否会压垮数据库/外部服务？
- [ ] 是否有限流、分批处理、延迟队列等保护机制？
- [ ] 数据库查询是否优化（索引、避免 N+1 查询）？
- [ ] 是否使用了消息队列来削峰填谷？

**反模式与最佳实践**：
```python
# 反模式：N+1 查询问题
for user in users:
    profile = Profile.objects.get(user_id=user.id)
    process(user, profile)

# 最佳实践：预加载关联数据
users = User.objects.select_related('profile').all()
for user in users:
    process(user, user.profile)
```
