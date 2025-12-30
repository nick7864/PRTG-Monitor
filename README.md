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
