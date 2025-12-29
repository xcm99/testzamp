import os
import time
import re
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ================= 基本配置 =================
SERVER_ID = "2190"
LOGIN_URL = "https://auth.zampto.net/sign-in?app_id=bmhk6c8qdqxphlyscztgl"
DASH_URL = f"https://dash.zampto.net/server?id={SERVER_ID}"
RENEW_API = "https://dash.zampto.net/server/renew"

USERNAME = os.getenv("ZAMPTO_USER")
PASSWORD = os.getenv("ZAMPTO_PASS")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

if not USERNAME or not PASSWORD:
    raise RuntimeError("❌ 缺少 ZAMPTO_USER / ZAMPTO_PASS")


# ================= Telegram 通知 =================
def tg_notify(title, msg, success=True):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return

    emoji = "✅" if success else "❌"
    text = f"{emoji} *{title}*\n\n{msg}"

    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TG_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
    except Exception as e:
        print("Telegram 通知失败:", e)


# ================= Selenium 登录 =================
def selenium_login_get_cookies():
    print("🔐 使用 Selenium 登录 Zampto...")

    options = Options()
    options.binary_location = "/usr/bin/chromium-browser"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(LOGIN_URL)

        wait.until(EC.visibility_of_element_located((By.NAME, "identifier"))).send_keys(USERNAME)
        driver.find_element(By.NAME, "submit").click()

        wait.until(EC.visibility_of_element_located((By.NAME, "password"))).send_keys(PASSWORD)
        driver.find_element(By.NAME, "submit").click()

        wait.until(EC.url_contains("dash.zampto.net"))
        time.sleep(2)

        cookies = driver.get_cookies()
        print(f"🍪 获取到 {len(cookies)} 个 cookies")
        return cookies

    finally:
        driver.quit()


# ================= requests 续期 =================
def renew_with_requests(cookies):
    print("🔁 使用 requests 执行续期...")

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })

    for c in cookies:
        sess.cookies.set(c["name"], c["value"], domain=c["domain"])

    # 打开服务器页面，获取 CSRF
    r = sess.get(DASH_URL, timeout=15)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    if not csrf:
        raise RuntimeError("❌ 未获取 csrf_token")

    # POST renew
    r = sess.post(
        RENEW_API,
        data={
            "server_id": SERVER_ID,
            "csrf_token": csrf.group(1)
        },
        timeout=15
    )

    if r.status_code == 200 and "success" in r.text.lower():
        return True

    raise RuntimeError("❌ renew 请求失败或状态未知")


# ================= 主入口 =================
if __name__ == "__main__":
    print("🚀 Zampto 自动续期【混合终极版】启动")

    try:
        cookies = selenium_login_get_cookies()
        ok = renew_with_requests(cookies)

        if ok:
            print("🎉 续期成功")
            tg_notify(
                "Zampto VPS 续期成功",
                f"服务器 ID: {SERVER_ID}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                True
            )

    except Exception as e:
        print("❌", e)
        tg_notify(
            "Zampto VPS 续期失败",
            str(e),
            False
        )
        raise
