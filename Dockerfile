# 使用精簡的 Python 映像
FROM python:3.10-slim

# 安裝 Chromium 和必要工具（比 Google Chrome 更精簡）
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    # 必要的系統依賴
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 設定 Chromium 路徑
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY *.py .
COPY config.json .

# 執行程式
CMD ["python", "prtg_monitor.py"]
