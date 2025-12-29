import os
import time
import re
import requests

# ================= 配置 =================
SERVER_ID = "2190"

LOGIN_URL = "https://auth.zampto.net/sign-in?app_id=bmhk6c8qdqxphlyscztgl"
DASH_URL = f"https://dash.zampto.net/server?id={SERVER_ID}"
RENEW_API = f"https://dash.zampto.net/server/renew"

USERNAME = os.getenv("ZAMPTO_USER")
PASSWORD = os.getenv("ZAMPTO_PASS")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

if not USERNAME or not PASSWORD:
    raise RuntimeError("❌ 缺少 ZAMPTO_USER / ZAMPTO_PASS")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ================= Telegram =================
def tg_notify(title, msg, success=True):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    emoji = "✅" if success else "❌"
    text = f"{emoji} *{title}*\n\n{msg}"

    requests.post(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        data={
            "chat_id": TG_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        },
        timeout=10
    )

# ================= 主流程 =================
def main():
    print("🚀 Zampto renew (requests-only) 启动")

    sess = requests.Session()
    sess.headers.update(HEADERS)

    # 1️⃣ 访问登录页
    r = sess.get(LOGIN_URL, timeout=15)
    if r.status_code != 200:
        raise RuntimeError("无法访问登录页")

    # 2️⃣ 提交账号
    auth_state = re.search(r'name="state" value="([^"]+)"', r.text)
    if not auth_state:
        raise RuntimeError("未获取 auth state")

    payload_user = {
        "state": auth_state.group(1),
        "username": USERNAME,
        "action": "default"
    }

    r = sess.post(LOGIN_URL, data=payload_user, timeout=15)

    # 3️⃣ 提交密码
    payload_pass = {
        "state": auth_state.group(1),
        "username": USERNAME,
        "password": PASSWORD,
        "action": "default"
    }

    r = sess.post(LOGIN_URL, data=payload_pass, timeout=15)

    if "dash.zampto.net" not in r.text:
        raise RuntimeError("登录失败（可能触发 MFA / 风控）")

    print("✅ 登录成功")

    # 4️⃣ 打开服务器页，提取 CSRF
    r = sess.get(DASH_URL, timeout=15)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    if not csrf:
        raise RuntimeError("未获取 CSRF token")

    csrf_token = csrf.group(1)

    # 5️⃣ POST renew
    renew_payload = {
        "server_id": SERVER_ID,
        "csrf_token": csrf_token
    }

    r = sess.post(RENEW_API, data=renew_payload, timeout=15)

    if r.status_code == 200 and "success" in r.text.lower():
        print("🎉 续期成功")
        tg_notify(
            "Zampto VPS 续期成功",
            f"服务器 ID: {SERVER_ID}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            True
        )
    else:
        raise RuntimeError("续期失败 / 状态未知")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌", e)
        tg_notify(
            "Zampto VPS 续期失败",
            str(e),
            False
        )
        raise
