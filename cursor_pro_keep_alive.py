import os

os.environ["PYTHONVERBOSE"] = "0"
os.environ["PYINSTALLER_VERBOSE"] = "0"

import time
import random
import traceback
from tqdm import tqdm
from cursor_auth_manager import CursorAuthManager
import os
import logging
from browser_utils import BrowserManager
from get_email_code import EmailVerificationHandler
from logo import print_logo

# 在文件开头设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cursor_keep_alive.log", encoding="utf-8"),
    ],
)


def show_progress(message, seconds):
    """显示进度条"""
    with tqdm(total=100, desc=message, ncols=100) as pbar:
        for _ in range(seconds):
            time.sleep(1)
            pbar.update(100/seconds)


def handle_turnstile(tab):
    print("\n🔄 开始验证...")
    try:
        with tqdm(total=100, desc="验证进行中", ncols=100) as pbar:
            for i in range(30):
                try:
                    challengeCheck = (
                        tab.ele("@id=cf-turnstile", timeout=2)
                        .child()
                        .shadow_root.ele("tag:iframe")
                        .ele("tag:body")
                        .sr("tag:input")
                    )

                    if challengeCheck:
                        print("✨ 开始突破")
                        time.sleep(random.uniform(1, 3))
                        challengeCheck.click()
                        pbar.update(100 - pbar.n)  # 更新到100%
                        time.sleep(2)
                        print("✅ 突破成功")
                        return True
                except:
                    pass

                if any(tab.ele(selector) for selector in ["@name=password", "@data-index=0", "Account Settings"]):
                    pbar.update(100 - pbar.n)  # 更新到100%
                    print("✅ 验证通过")
                    break

                time.sleep(0.5)
                pbar.update(100/30)  # 每次更新大约3.33%
            
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
        return False


def get_cursor_session_token(tab, max_attempts=3, retry_interval=2):
    """
    获取Cursor会话token，带有重试机制
    :param tab: 浏览器标签页
    :param max_attempts: 最大尝试次数
    :param retry_interval: 重试间隔(秒)
    :return: session token 或 None
    """
    print("开始获取cookie")
    attempts = 0

    while attempts < max_attempts:
        try:
            cookies = tab.cookies()
            for cookie in cookies:
                if cookie.get("name") == "WorkosCursorSessionToken":
                    return cookie["value"].split("%3A%3A")[1]

            attempts += 1
            if attempts < max_attempts:
                print(
                    f"第 {attempts} 次尝试未获取到CursorSessionToken，{retry_interval}秒后重试..."
                )
                time.sleep(retry_interval)
            else:
                print(f"已达到最大尝试次数({max_attempts})，获取CursorSessionToken失败")

        except Exception as e:
            print(f"获取cookie失败: {str(e)}")
            attempts += 1
            if attempts < max_attempts:
                print(f"将在 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)

    return None


def update_cursor_auth(email=None, access_token=None, refresh_token=None):
    """
    更新Cursor的认证信息的便捷函数
    """
    auth_manager = CursorAuthManager()
    return auth_manager.update_auth(email, access_token, refresh_token)


def sign_up_account(browser, tab):
    print("开始执行...")
    tab.get(sign_up_url)

    try:
        if tab.ele("@name=first_name"):
            tab.actions.click("@name=first_name").input(first_name)
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=last_name").input(last_name)
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=email").input(account)
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@type=submit")

    except Exception as e:
        print("打开注册页面失败")
        return False

    handle_turnstile(tab)

    try:
        if tab.ele("@name=password"):
            tab.ele("@name=password").input(password)
            time.sleep(random.uniform(1, 3))

            tab.ele("@type=submit").click()
            print("请稍等...")

    except Exception as e:
        print("执行失败")
        return False

    time.sleep(random.uniform(1, 3))
    if tab.ele("This email is not available."):
        print("执行失败")
        return False

    handle_turnstile(tab)

    while True:
        try:
            if tab.ele("Account Settings"):
                break
            if tab.ele("@data-index=0"):
                code = email_handler.get_verification_code(account)
                if not code:
                    return False

                i = 0
                for digit in code:
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                    i += 1
                break
        except Exception as e:
            print(e)

    handle_turnstile(tab)
    wait_time = random.randint(3, 6)
    for i in range(wait_time):
        print(f"等待中... {wait_time-i}秒")
        time.sleep(1)
    tab.get(settings_url)
    try:
        usage_selector = (
            "css:div.col-span-2 > div > div > div > div > "
            "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
            "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
        )
        usage_ele = tab.ele(usage_selector)
        if usage_ele:
            usage_info = usage_ele.text
            total_usage = usage_info.split("/")[-1].strip()
            print("可用上限: " + total_usage)
    except Exception as e:
        print("获取可用上限失败")
    print("注册完成")
    account_info = f"\nCursor 账号： {account}  密码： {password}"
    logging.info(account_info)
    time.sleep(5)
    return True


class EmailGenerator:
    def __init__(
        self,
        domain="mailto.plus",
        password="".join(
            random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
                k=12,
            )
        ),
        first_name="yuyan",
        last_name="peng",
    ):
        self.domain = domain
        self.default_password = password
        self.default_first_name = first_name
        self.default_last_name = last_name

    def generate_email(self, length=8):
        """生成随机邮箱地址"""
        random_str = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=length))
        timestamp = str(int(time.time()))[-6:]  # 使用时间戳后6位
        return f"{random_str}{timestamp}@{self.domain}"

    def get_account_info(self):
        """获取完整的账号信息"""
        return {
            "email": self.generate_email(),
            "password": self.default_password,
            "first_name": self.default_first_name,
            "last_name": self.default_last_name,
        }


if __name__ == "__main__":
    print_logo()
    print("\n" + "="*50)
    browser_manager = None
    
    try:
        print("\n🚀 初始化程序...")
        show_progress("初始化浏览器", 3)
        
        browser_manager = BrowserManager()
        browser = browser_manager.init_browser()
        
        show_progress("配置验证环境", 2)
        email_handler = EmailVerificationHandler(browser)

        # 固定的 URL 配置
        login_url = "https://authenticator.cursor.sh"
        sign_up_url = "https://authenticator.cursor.sh/sign-up"
        settings_url = "https://www.cursor.com/settings"
        mail_url = "https://tempmail.plus"

        # 生成随机邮箱
        email_generator = EmailGenerator()
        account = email_generator.generate_email()
        password = email_generator.default_password
        first_name = email_generator.default_first_name
        last_name = email_generator.default_last_name

        print(f"\n📧 使用邮箱: {account}")
        
        tab = browser.latest_tab
        tab.run_js("try { turnstile.reset() } catch(e) { }")
        tab.get(login_url)

        if sign_up_account(browser, tab):
            show_progress("完成注册", 2)
            token = get_cursor_session_token(tab)
            if token:
                update_cursor_auth(email=account, access_token=token, refresh_token=token)
                print("\n✅ 账号注册成功！")
            else:
                print("\n❌ 账户注册失败")

        print("\n🎉 执行完毕!")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        if browser_manager:
            browser_manager.quit()
        input("\n按回车键退出...")
