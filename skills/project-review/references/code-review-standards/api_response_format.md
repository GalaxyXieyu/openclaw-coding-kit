# API 响应格式规范（P1）

## API 响应格式检查清单
- [ ] 是否有统一的响应结构（如包含 status、data/error、message 字段）？
- [ ] 分页接口是否包含总条数、当前页、每页数量等元信息？
- [ ] 响应字段是否有清晰的命名和文档？
- [ ] 是否避免了不必要的嵌套和冗余字段？
- [ ] 是否使用了合适的字段类型和格式（如时间使用 ISO 8601 格式）？

**成功响应格式示例**：
```json
{
  "status": "success",
  "data": {
    "id": 123,
    "name": "test user",
    "email": "test@example.com",
    "created_at": "2023-10-01T12:00:00Z",
    "updated_at": "2023-10-05T15:30:00Z"
  },
  "meta": {
    "timestamp": "2023-10-06T08:30:00Z",
    "request_id": "XYZ123"
  }
}
```

**分页响应格式示例**：
```json
{
  "status": "success",
  "data": [
    {"id": 123, "name": "user1"},
    {"id": 456, "name": "user2"}
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "total_pages": 5,
    "timestamp": "2023-10-06T08:30:00Z",
    "request_id": "XYZ123"
  }
}
```

**错误响应格式示例**（与成功响应结构一致）：
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {"field": "email", "message": "Email format is invalid"},
      {"field": "password", "message": "Password must be at least 8 characters"}
    ]
  },
  "meta": {
    "timestamp": "2023-10-06T08:30:00Z",
    "request_id": "XYZ123"
  }
}
```
