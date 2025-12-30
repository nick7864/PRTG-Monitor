# -*- coding: utf-8 -*-
"""
Email 發送模組
用於發送 PRTG 監控異常告警郵件
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    """Email 發送器類別"""
    
    def __init__(self, config: dict):
        """
        初始化 Email 發送器
        
        Args:
            config: 包含 smtp 和 email 設定的字典
        """
        self.smtp_config = config.get('smtp', {})
        self.email_config = config.get('email', {})
        self.enabled = bool(self.smtp_config.get('server'))
        
        if not self.enabled:
            logger.warning("SMTP 設定未填寫，Email 通知功能已停用")
    
    def send_alert(self, server_name: str, map_url: str, status: str = "錯誤") -> bool:
        """
        發送異常告警郵件
        
        Args:
            server_name: 伺服器名稱
            map_url: PRTG Map 頁面 URL
            status: 狀態描述
            
        Returns:
            是否發送成功
        """
        if not self.enabled:
            logger.warning(f"[{server_name}] Email 通知功能未啟用，跳過發送")
            return False
        
        try:
            # 建立郵件內容
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 PRTG 伺服器異常警報 - {server_name}"
            msg['From'] = self.email_config.get('sender', '')
            msg['To'] = ', '.join(self.email_config.get('recipients', []))
            
            # 純文字內容
            text_content = self._create_text_content(server_name, map_url, status)
            
            # HTML 內容
            html_content = self._create_html_content(server_name, map_url, status)
            
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 發送郵件
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                if self.smtp_config.get('use_tls', True):
                    server.starttls()
                
                if self.smtp_config.get('username') and self.smtp_config.get('password'):
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                
                server.send_message(msg)
            
            logger.info(f"[{server_name}] 告警郵件已成功發送至 {msg['To']}")
            return True
            
        except Exception as e:
            logger.error(f"[{server_name}] 發送郵件失敗: {e}")
            return False
    
    def _create_text_content(self, server_name: str, map_url: str, status: str) -> str:
        """建立純文字郵件內容"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 偵測到伺服器異常！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

伺服器名稱: {server_name}
監控頁面: {map_url}
偵測時間: {now}
狀態: {status} (紅色 #e30613)

請立即登入 PRTG 檢查伺服器狀態！

---
此郵件由 PRTG 監控系統自動發送
"""
    
    def _create_html_content(self, server_name: str, map_url: str, status: str) -> str:
        """建立 HTML 郵件內容"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="background-color: #e30613; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">🚨 伺服器異常警報</h1>
        </div>
        <div style="padding: 30px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">伺服器名稱</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; color: #e30613; font-weight: bold;">{server_name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">監控頁面</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><a href="{map_url}" style="color: #0066cc;">{map_url}</a></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">偵測時間</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{now}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">狀態</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">
                        <span style="background-color: #e30613; color: white; padding: 3px 10px; border-radius: 3px;">{status}</span>
                    </td>
                </tr>
            </table>
            <div style="margin-top: 30px; padding: 15px; background-color: #fff3cd; border-radius: 5px; border-left: 4px solid #ffc107;">
                <strong>⚠️ 請立即登入 PRTG 檢查伺服器狀態！</strong>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666;">
            此郵件由 PRTG 監控系統自動發送
        </div>
    </div>
</body>
</html>
"""


def send_test_email(config: dict) -> bool:
    """
    發送測試郵件
    
    Args:
        config: 完整設定字典
        
    Returns:
        是否發送成功
    """
    sender = EmailSender(config)
    if not sender.enabled:
        print("❌ SMTP 設定未填寫，無法發送測試郵件")
        return False
    
    return sender.send_alert(
        server_name="測試伺服器",
        map_url="https://example.com/test",
        status="測試"
    )
