# -*- coding: utf-8 -*-
"""
PRTG 多伺服器監控告警系統
監控多個 PRTG Map 頁面的狀態色塊，當偵測到異常時發送 Email 通知
"""

import json
import time
import sys
import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore, Style

from email_sender import EmailSender

# 初始化 colorama (Windows 終端機顏色支援)
init()

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class PRTGMonitor:
    """PRTG 監控器類別"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化監控器
        
        Args:
            config_path: 設定檔路徑
        """
        self.config = self._load_config(config_path)
        self.driver: Optional[webdriver.Chrome] = None
        self.email_sender = EmailSender(self.config)
        
        # 追蹤每個伺服器的上一次狀態，避免重複告警
        self.last_status: Dict[int, str] = {}
        
        # 顏色設定
        self.normal_color = self.config['monitoring']['normal_color'].lower()
        self.error_color = self.config['monitoring']['error_color'].lower()
    
    def _load_config(self, config_path: str) -> dict:
        """載入設定檔"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"找不到設定檔: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _init_browser(self) -> None:
        """初始化瀏覽器"""
        logger.info("正在初始化瀏覽器...")
        
        options = Options()
        options.add_argument('--headless')  # 無頭模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--ignore-certificate-errors')  # 忽略 SSL 憑證錯誤
        options.add_argument('--ignore-ssl-errors')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(10)
        
        logger.info("瀏覽器初始化完成")
    
    def _login(self) -> bool:
        """
        登入 PRTG 系統
        
        Returns:
            是否登入成功
        """
        prtg_config = self.config['prtg']
        login_url = f"{prtg_config['base_url']}/public/login.htm"
        
        logger.info(f"正在登入 PRTG: {prtg_config['base_url']}")
        
        try:
            self.driver.get(login_url)
            
            # 等待登入表單載入
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "loginusername"))
            )
            
            # 輸入帳號密碼
            username_input = self.driver.find_element(By.ID, "loginusername")
            password_input = self.driver.find_element(By.ID, "loginpassword")
            
            username_input.clear()
            username_input.send_keys(prtg_config['username'])
            
            password_input.clear()
            password_input.send_keys(prtg_config['password'])
            
            # 點擊登入按鈕 (使用 CSS Selector，因為按鈕是 class 而非 id)
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button.loginbutton")
            login_button.click()
            
            # 等待登入完成
            time.sleep(3)
            
            # 檢查是否登入成功 (透過 URL 變化)
            if "login" not in self.driver.current_url.lower():
                logger.info("✅ 登入成功")
                return True
            else:
                logger.error("❌ 登入失敗，請檢查帳號密碼")
                return False
                
        except TimeoutException:
            logger.error("❌ 登入頁面載入超時")
            return False
        except Exception as e:
            logger.error(f"❌ 登入過程發生錯誤: {e}")
            return False
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """將 HEX 顏色轉換為 RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _parse_color(self, color_str: str) -> str:
        """
        解析顏色字串，統一轉換為小寫 HEX 格式
        
        Args:
            color_str: CSS 顏色值 (可能是 rgb(), rgba(), 或 hex)
            
        Returns:
            小寫 HEX 格式顏色 (例如: #e30613)
        """
        color_str = color_str.strip().lower()
        
        # 如果已經是 HEX 格式
        if color_str.startswith('#'):
            return color_str
        
        # 解析 rgb() 或 rgba() 格式
        rgb_match = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color_str)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            return f'#{r:02x}{g:02x}{b:02x}'
        
        return color_str
    
    def _check_server_status(self, server: dict) -> Tuple[str, bool]:
        """
        檢查單一伺服器的狀態
        
        透過偵測 class 名稱判斷狀態:
        - .sensr = 錯誤 (紅色)
        - .sensy = 警告 (黃色)  
        - .sensg = 正常 (綠色)
        
        Args:
            server: 伺服器設定 (包含 name 和 map_id)
            
        Returns:
            (狀態描述, 是否為異常狀態)
        """
        map_id = server['map_id']
        # 直接開啟 maponly.htm 避免 iframe 問題
        map_url = f"{self.config['prtg']['base_url']}/controls/maponly.htm?id={map_id}"
        
        try:
            self.driver.get(map_url)
            
            # 等待頁面載入
            time.sleep(3)
            
            # 偵測紅色錯誤狀態 (.sensr)
            sensr_elements = self.driver.find_elements(By.CSS_SELECTOR, ".sensr")
            if sensr_elements:
                error_count = len(sensr_elements)
                # 取得錯誤數量 (元素內的文字)
                try:
                    total_errors = sum(int(el.text) for el in sensr_elements if el.text.isdigit())
                    if total_errors == 0:
                        total_errors = error_count
                except:
                    total_errors = error_count
                logger.info(f"[{server['name']}] 偵測到 {total_errors} 個錯誤狀態 (紅色)")
                return f"錯誤 ({total_errors}個)", True
            
            # 偵測黃色警告狀態 (.sensy)
            sensy_elements = self.driver.find_elements(By.CSS_SELECTOR, ".sensy")
            warning_count = 0
            if sensy_elements:
                try:
                    warning_count = sum(int(el.text) for el in sensy_elements if el.text.isdigit())
                    if warning_count == 0:
                        warning_count = len(sensy_elements)
                except:
                    warning_count = len(sensy_elements)
            
            # 偵測綠色正常狀態 (.sensg)
            sensg_elements = self.driver.find_elements(By.CSS_SELECTOR, ".sensg")
            ok_count = 0
            if sensg_elements:
                try:
                    ok_count = sum(int(el.text) for el in sensg_elements if el.text.isdigit())
                    if ok_count == 0:
                        ok_count = len(sensg_elements)
                except:
                    ok_count = len(sensg_elements)
            
            # 沒有錯誤，回報正常狀態
            status = f"正常 ({ok_count}個"
            if warning_count > 0:
                status += f", 警告 {warning_count}個"
            status += ")"
            
            return status, False
            
        except Exception as e:
            logger.error(f"[{server['name']}] 檢查狀態時發生錯誤: {e}")
            return "檢查失敗", False
    
    def check_all_servers(self) -> Dict[str, dict]:
        """
        檢查所有伺服器的狀態
        
        Returns:
            各伺服器的狀態結果
        """
        results = {}
        
        for server in self.config['servers']:
            name = server['name']
            map_id = server['map_id']
            map_url = f"{self.config['prtg']['base_url']}/mapshow.htm?id={map_id}"
            
            color, is_error = self._check_server_status(server)
            
            # 記錄結果
            results[name] = {
                'map_id': map_id,
                'map_url': map_url,
                'color': color,
                'is_error': is_error,
                'timestamp': datetime.now().isoformat()
            }
            
            # 輸出狀態
            if is_error:
                print(f"{Fore.RED}🚨 [{name}] 異常 - 顏色: {color}{Style.RESET_ALL}")
                
                # 檢查是否為新的異常 (避免重複告警)
                if self.last_status.get(map_id) != 'error':
                    logger.warning(f"[{name}] 偵測到新的異常狀態，準備發送告警...")
                    self.email_sender.send_alert(name, map_url, "錯誤")
                    self.last_status[map_id] = 'error'
                else:
                    logger.info(f"[{name}] 異常狀態持續中，不重複發送告警")
            else:
                print(f"{Fore.GREEN}✅ [{name}] 正常 - 顏色: {color}{Style.RESET_ALL}")
                self.last_status[map_id] = 'normal'
        
        return results
    
    def run(self) -> None:
        """執行監控主迴圈"""
        try:
            self._init_browser()
            
            if not self._login():
                logger.error("登入失敗，程式終止")
                return
            
            interval = self.config['monitoring']['check_interval_seconds']
            logger.info(f"開始監控，檢查間隔: {interval} 秒")
            logger.info(f"監控伺服器數量: {len(self.config['servers'])}")
            
            print("\n" + "=" * 50)
            print("PRTG 多伺服器監控系統已啟動")
            print("=" * 50)
            print(f"監控目標:")
            for server in self.config['servers']:
                print(f"  - {server['name']} (Map ID: {server['map_id']})")
            print("=" * 50 + "\n")
            
            # 監控主迴圈
            cycle = 0
            while True:
                cycle += 1
                print(f"\n--- 第 {cycle} 輪檢查 ({datetime.now().strftime('%H:%M:%S')}) ---")
                
                self.check_all_servers()
                
                print(f"下次檢查: {interval} 秒後...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("收到中斷訊號，正在關閉...")
        except Exception as e:
            logger.error(f"監控過程發生錯誤: {e}")
        finally:
            self.close()
    
    def test(self) -> None:
        """測試模式：僅檢查一次並顯示結果"""
        try:
            self._init_browser()
            
            if not self._login():
                logger.error("登入失敗")
                return
            
            print("\n" + "=" * 50)
            print("測試模式 - 單次檢查")
            print("=" * 50 + "\n")
            
            results = self.check_all_servers()
            
            print("\n" + "=" * 50)
            print("測試完成")
            print("=" * 50)
            
        finally:
            self.close()
    
    def close(self) -> None:
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()
            logger.info("瀏覽器已關閉")


def main():
    """主程式進入點"""
    parser = argparse.ArgumentParser(description='PRTG 多伺服器監控告警系統')
    parser.add_argument('--config', '-c', default='config.json', help='設定檔路徑')
    parser.add_argument('--test', '-t', action='store_true', help='測試模式（僅檢查一次）')
    
    args = parser.parse_args()
    
    try:
        monitor = PRTGMonitor(config_path=args.config)
        
        if args.test:
            monitor.test()
        else:
            monitor.run()
            
    except FileNotFoundError as e:
        print(f"{Fore.RED}錯誤: {e}{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}發生錯誤: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
