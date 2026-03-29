FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装依赖（利用缓存，依赖不变就不重新安装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "app.py"]