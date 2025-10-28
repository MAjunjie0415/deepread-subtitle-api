FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（Playwright 需要）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器（只安装 Chromium）
RUN playwright install chromium
# 手动安装依赖，避免 playwright install-deps 的包名问题
RUN apt-get update && apt-get install -y \
    fonts-unifont \
    fonts-ubuntu \
    && rm -rf /var/lib/apt/lists/*

# 复制应用代码
COPY . .

# 暴露端口（Zeabur 默认使用 8080）
EXPOSE 8080

# 使用 gunicorn 运行（生产环境）
# 绑定到 8080 端口
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "main:app"]

