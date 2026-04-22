# API 错误处理规范（P1）

## API 错误处理检查清单
- [ ] 错误响应是否包含明确的错误代码、错误消息和建议？
- [ ] 是否避免返回技术细节（如堆栈跟踪）给客户端？
- [ ] 不同类型的错误是否有统一的格式？
- [ ] 错误消息是否清晰易懂，有助于客户端排查问题？

**反模式与最佳实践**：
```python
# 反模式：错误信息不清晰，包含技术细节
@app.get("/users/<id>")
def get_user(id):
    try:
        user = User.objects.get(id=id)
        return jsonify(user), 200
    except Exception as e:
        # 返回模糊的错误信息和技术细节
        return jsonify({"error": f"Failed: {e}"}), 500

# 最佳实践：统一错误响应格式
@app.errorhandler(404)
def not_found_error(e):
    return jsonify({
        "code": "NOT_FOUND",
        "message": f"Resource not found",
        "details": f"The requested resource with id '{request.view_args.get('id')}' does not exist",
        "timestamp": datetime.utcnow().isoformat()
    }), 404

@app.errorhandler(Exception)
def internal_error(e):
    # 记录详细错误日志到服务器
    logger.error(f"Internal error: {str(e)}", exc_info=True)

    return jsonify({
        "code": "INTERNAL_SERVER_ERROR",
        "message": "Internal server error occurred",
        "details": "Please contact the administrator with the request ID: XYZ123",
        "timestamp": datetime.utcnow().isoformat()
    }), 500
```
