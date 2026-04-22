# 代码设计与可测试性审查标准（P1）

## 核心问题：代码能不能测？

在写单元测试前，代码必须满足以下 5 个设计规范。违反任何一个，必须先重构代码。

---

## 5 个设计规范

### 1. 依赖注入
外部依赖（DB、HTTP、缓存）必须通过构造函数传入，不能在类内部创建。

```python
# 反模式：内部创建依赖，无法 Mock
class UserService:
    def __init__(self):
        self.db = Database()  # 硬编码依赖
        self.cache = Redis()

    def get_user(self, user_id):
        return self.db.query(f"SELECT * FROM users WHERE id={user_id}")

# 最佳实践：依赖注入，可轻松 Mock
class UserService:
    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache

    def get_user(self, user_id: int) -> User:
        return self.db.query(User).filter_by(id=user_id).first()
```

### 2. 单一职责
一个类只做一件事，不要混合 DB 操作、业务逻辑、HTTP 响应。

```python
# 反模式：混合多种职责
class OrderHandler:
    def handle(self, request):
        # 解析请求
        data = json.loads(request.body)
        # 业务逻辑
        if data['amount'] > 10000:
            data['discount'] = 0.9
        # 数据库操作
        order = Order(**data)
        db.session.add(order)
        db.session.commit()
        # 构造响应
        return JsonResponse({'id': order.id})

# 最佳实践：职责分离
class OrderService:
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo

    def create_order(self, amount: float) -> Order:
        discount = 0.9 if amount > 10000 else 1.0
        return self.order_repo.create(amount=amount, discount=discount)
```

### 3. 返回值而非副作用
函数返回结果，不要通过 print() 或修改全局状态来表达。

```python
# 反模式：通过副作用表达结果
def process_order(order):
    if order.is_valid():
        print(f"Order {order.id} processed")  # 副作用
        global_stats['processed'] += 1  # 修改全局状态
    else:
        print(f"Order {order.id} failed")

# 最佳实践：返回可验证的结果
def process_order(order: Order) -> ProcessResult:
    if order.is_valid():
        return ProcessResult(success=True, order_id=order.id)
    return ProcessResult(success=False, error="Invalid order")
```

### 4. 显式化依赖
消除 magic numbers、隐藏配置读取，一切都用参数或常量表达。

```python
# 反模式：隐藏依赖
def calculate_tax(amount):
    config = ConfigParser()  # 隐藏的文件读取
    config.read('config.ini')
    rate = float(config.get('tax', 'rate'))  # 隐藏配置
    return amount * rate * 1.05  # magic number

# 最佳实践：显式依赖
TAX_SURCHARGE = 1.05

def calculate_tax(amount: float, tax_rate: float) -> float:
    return amount * tax_rate * TAX_SURCHARGE
```

### 5. 清晰的接口
函数参数少、类型明确，避免过多布尔参数。

```python
# 反模式：参数过多且含义不清
def send_email(to, subject, body, html, attach, cc, bcc, reply, urgent, track):
    pass

# 最佳实践：使用数据类封装参数
@dataclass
class EmailConfig:
    to: str
    subject: str
    body: str
    html: bool = False
    urgent: bool = False

def send_email(config: EmailConfig) -> SendResult:
    pass
```

---

## 快速判断：代码是否可测？

| 检查项 | 通过标准 |
|--------|----------|
| 能否注入 Mock？ | 所有外部依赖都通过构造函数传入 |
| 能否快速运行？ | 不依赖真实 DB/网络/文件系统 |
| 能否验证结果？ | 函数返回可断言的值，而非副作用 |

---

## 测试优先级矩阵：哪些函数值得测？

| 优先级 | 场景 | 测试策略 |
|--------|------|----------|
| P0 | 金额计算、权限检查、状态转移 | 必须写单元+集成测试 |
| P1 | 业务服务（简单逻辑） | 必须写单元测试 |
| P2 | 复杂算法（非关键业务） | 应该写单元测试 |
| P3 | 简单工具函数 | 可选，改到再补 |
| P4 | Getter/Setter、简单格式化 | 可以跳过 |

---

## 快速判断流程

5 个问题，第一个"是"就停止：

1. 涉及钱、权限、数据完整性？ → P0
2. 有 3 个以上分支？ → P2
3. 是 Service/Repository 层？ → P1
4. 以前出过 bug？ → P2
5. 逻辑非常简单且很少改？ → P4

---

## 检查清单

- [ ] **依赖注入**：外部依赖是否通过构造函数传入？
- [ ] **单一职责**：类是否只做一件事？
- [ ] **返回值**：函数是否返回可验证的结果？
- [ ] **显式依赖**：是否消除了 magic numbers 和隐藏配置？
- [ ] **清晰接口**：参数是否少且类型明确？
- [ ] **测试优先级**：是否按照 P0-P4 确定测试策略？
