# PRTG 多伺服器監控告警系統

監控多個 PRTG 伺服器狀態頁面，透過 Selenium 自動偵測 PRTG Map 上的狀態色塊，當發現異常時自動發送 Email 通知。

## 狀態偵測邏輯

程式透過 CSS class 偵測 PRTG Map 上的感測器狀態：

| Class | 狀態 | 顏色 | 說明 |
|-------|------|------|------|
| `.sensr` | 錯誤 | 🔴 紅色 | 會觸發告警通知 |
| `.sensy` | 警告 | 🟡 黃色 | 記錄但不告警 |
| `.sensg` | 正常 | 🟢 綠色 | 正常運作 |

## 監控目標

| 伺服器名稱 | Map ID | URL |
|-----------|--------|-----|
| DEVAP | 9927 | |
| erpapec.radium.com.tw | 9952 | |
| radiumdb2019 | 9928 | |

## 安裝步驟

### 1. 安裝 uv（Python 套件管理器）

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安裝完成後，**重新開啟終端機**或執行以下指令重新載入 PATH：

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")
```

### 2. 建立虛擬環境並安裝依賴

```powershell
cd c:\Users\NickJiang\Desktop\CCTV
uv venv --python 3.10
.venv\Scripts\activate
uv pip install -r requirements.txt
```

### 3. 設定 Email

編輯 `config.json`，設定 SMTP：

> **注意**：如果 SMTP server 留空，程式仍可運行但不會發送郵件通知。

## 使用方式

### 啟動監控

```powershell
python prtg_monitor.py
```

### 測試模式（僅檢查一次）

```powershell
python prtg_monitor.py --test
```

### 指定設定檔

```powershell
python prtg_monitor.py --config my_config.json
```

### 測試 Email 發送

```powershell
python -c "import json; from email_sender import send_test_email; config = json.load(open('config.json', 'r', encoding='utf-8')); send_test_email(config)"
```

## 新增/移除監控伺服器

編輯 `config.json` 中的 `servers` 陣列：

```json
{
  "servers": [
    {"name": "伺服器名稱", "map_id": 1234},
    {"name": "另一台伺服器", "map_id": 5678}
  ]
}
```

Map ID 可從 PRTG Map 頁面的 URL 取得，例如：`mapshow.htm?id=9928` 中的 `9928`。

## 停止監控

按下 `Ctrl + C` 即可停止程式。

---

## Docker 部署

### 部署架構

```
┌─────────────────────────────────────────┐
│           Docker Container              │
│  ┌─────────────────────────────────┐   │
│  │  selenium/standalone-chrome     │   │
│  │  ├── Chrome 瀏覽器              │   │
│  │  ├── ChromeDriver               │   │
│  │  └── Python 3 + 你的程式        │   │
│  └─────────────────────────────────┘   │
│                  │                      │
│                  ▼                      │
│         config.json (外部映射)          │
└─────────────────────────────────────────┘
```

### 部署檔案說明

| 檔案 | 用途 |
|------|------|
| `Dockerfile` | 定義如何建立映像檔 |
| `docker-compose.yml` | 定義服務設定（簡化啟動指令） |
| `.dockerignore` | 排除不需要複製的檔案 |

### 快速部署

```bash
# 1. 建置並啟動（首次或程式更新後）
docker-compose up -d --build

# 2. 查看日誌
docker-compose logs -f

# 3. 停止服務
docker-compose down
```

### 常用管理指令

| 指令 | 功能 |
|------|------|
| `docker-compose up -d` | 背景啟動容器 |
| `docker-compose up -d --build` | 重新建置後啟動 |
| `docker-compose down` | 停止並移除容器 |
| `docker-compose restart` | 重新啟動容器 |
| `docker-compose logs -f` | 查看即時日誌 |
| `docker-compose logs --tail 100` | 查看最近 100 行日誌 |
| `docker-compose build --no-cache` | 清除快取重新建置 |

### 更新設定檔

`config.json` 已映射到容器外，修改後只需重啟：

```bash
docker-compose restart
```

### 更新程式碼

修改 Python 程式後需要重新建置：

```bash
docker-compose up -d --build
```

### 疑難排解

#### 1. ChromeDriver 版本不匹配

程式會自動偵測 Docker 環境並使用容器內建的 ChromeDriver，不會出現版本問題。

#### 2. 無法連線到 PRTG

確認：
- `config.json` 中的 PRTG URL 正確
- 容器可以存取該 URL（網路連通性）
- PRTG 帳號密碼正確

#### 3. Email 無法發送

確認：
- SMTP 伺服器設定正確
- 容器可以存取 SMTP 伺服器（防火牆）
