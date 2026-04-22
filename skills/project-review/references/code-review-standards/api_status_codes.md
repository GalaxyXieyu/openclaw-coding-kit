# API 状态码规范（P1）

## API 状态码检查清单
- [ ] 是否使用了标准的 HTTP 状态码（如 2xx、4xx、5xx）？
- [ ] 客户端错误是否返回 4xx 状态码，服务器错误是否返回 5xx 状态码？
- [ ] 是否避免了自定义状态码？如果必须使用，是否有明确的映射关系？
- [ ] 不同的操作类型是否使用了对应的状态码（如 POST 创建成功返回 201，删除成功返回 204）？

**反模式与最佳实践**：
```python
# 反模式：状态码与实际操作不符
@app.post("/users")
def create_user():
    # 成功创建用户却返回 200
    return jsonify({"id": 123, "name": "test"}), 200

# 最佳实践：使用标准状态码
@app.post("/users")
def create_user():
    # 成功创建返回 201 Created
    return jsonify({"id": 123, "name": "test", "url": "/users/123"}), 201
```

**常用标准状态码推荐**：
- 200 OK - GET/POST 请求成功返回资源
- 201 Created - POST/PUT 请求成功创建资源
- 204 No Content - DELETE 请求成功删除资源
- 400 Bad Request - 请求参数错误
- 401 Unauthorized - 未授权访问
- 403 Forbidden - 禁止访问
- 404 Not Found - 资源不存在
- 500 Internal Server Error - 服务器内部错误
- 502 Bad Gateway - 网关错误
