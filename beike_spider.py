import time
import random
import pandas as pd
import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
import os
import json
import getpass
import os.path

class BeikeSpider:
    def __init__(self):
        self.base_url = "https://sz.ke.com/chengjiao/"
        self.data = []
        self.setup_driver()
        self.target_date = None  # 存储目标日期(T日)
        
    def setup_driver(self):
        """设置Chrome浏览器"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            chromedriver_path = os.path.join(current_dir, "chromedriver.exe")
            
            print(f"正在初始化Chrome驱动，路径: {chromedriver_path}")
            
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-features=NetworkService')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-save-password-bubble')
            options.add_argument('--disable-single-click-autofill')
            options.add_argument('--disable-translate')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-breakpad')
            options.add_argument('--disable-component-extensions-with-background-pages')
            options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--enable-features=NetworkService,NetworkServiceInProcess')
            options.add_argument('--force-color-profile=srgb')
            options.add_argument('--metrics-recording-only')
            options.add_argument('--no-first-run')
            options.add_argument('--password-store=basic')
            options.add_argument('--use-mock-keychain')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            
            options.page_load_strategy = 'eager'
            
            service = Service(executable_path=chromedriver_path)
            service.start()
            
            self.driver = webdriver.Chrome(service=service, options=options)
            
            self.driver.set_page_load_timeout(30)
            self.driver.set_script_timeout(30)
            self.driver.implicitly_wait(10)
            
            self.wait = WebDriverWait(self.driver, 20)
            
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-CN', 'zh']
                    });
                '''
            })
            
            print("Chrome驱动初始化成功！")
            
        except Exception as e:
            print(f"Chrome驱动初始化失败: {e}")
            raise

    def wait_for_login(self):
        """等待用户手动登录"""
        print("\n请在打开的浏览器中手动登录贝壳找房网站。")
        print("登录后请按回车键继续...")
        input()
        print("继续执行爬虫程序...")

    def handle_verification(self):
        """处理验证码"""
        print("\n检测到需要进行人机验证，请在浏览器中完成验证。")
        print("完成验证后请按回车键继续...")
        input()
        print("继续执行爬虫程序...")

    def save_page_source(self, page):
        """保存页面源码用于调试"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'debug_page_{page}_{timestamp}.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"页面源码已保存到: {filename}")
        except Exception as e:
            print(f"保存页面源码失败: {e}")

    def parse_house_info(self, house_element):
        """解析单个房源信息"""
        try:
            # 获取基本信息（楼盘名称、户型、面积）
            basic_info = house_element.find_element(By.XPATH, ".//div/div[1]").text
            # 使用正则表达式分离数据
            name = re.search(r'(.+?)\s+(\d+室\d+厅)\s+(\d+\.?\d*平米)', basic_info)
            if name:
                house_name = name.group(1)
                house_type = name.group(2)
                area = name.group(3)
            else:
                house_name = house_type = area = ""

            # 获取成交日期
            deal_date = house_element.find_element(By.XPATH, ".//div/div[2]/div[2]").text

            # 检查是否已设置目标日期，若未设置，则将第一条数据的日期设为目标日期
            if self.target_date is None and deal_date:
                self.target_date = deal_date
                print(f"目标日期(T日)设置为: {self.target_date}")
            
            # 获取成交价格
            price = house_element.find_element(By.XPATH, ".//div/div[2]/div[3]/span").text

            # 获取楼层和楼龄信息（尝试多种方式）
            floor_info = ""
            try:
                # 尝试直接获取
                floor_info = house_element.find_element(By.XPATH, ".//div/div[3]/div[1]").text
            except NoSuchElementException:
                try:
                    # 尝试其他可能的XPath
                    floor_info = house_element.find_element(By.XPATH, ".//div/div[3]").text
                except NoSuchElementException:
                    try:
                        # 尝试通过文本内容查找
                        floor_info = house_element.find_element(By.XPATH, ".//*[contains(text(), '层')]").text
                    except NoSuchElementException:
                        print(f"注意：{house_name} 没有楼层信息")

            # 解析楼层信息
            current_floor = ""
            total_floor = ""
            building_age = ""
            building_type = ""

            # 尝试匹配楼层信息
            floor_match = re.search(r'([高|中|低]楼层)\(共(\d+)层\)', floor_info)
            if floor_match:
                current_floor = floor_match.group(1)
                total_floor = floor_match.group(2)
            else:
                # 尝试其他可能的格式
                floor_match = re.search(r'(\d+)层/(\d+)层', floor_info)
                if floor_match:
                    current_floor = f"{floor_match.group(1)}层"
                    total_floor = floor_match.group(2)

            # 尝试匹配楼龄和建筑类型
            age_match = re.search(r'(\d{4})年(.*?)(?:\s|$)', floor_info)
            if age_match:
                building_age = age_match.group(1)
                building_type = age_match.group(2)

            # 获取成交周期（尝试多种方式）
            cycle = ""
            try:
                # 尝试直接获取成交周期
                cycle_element = house_element.find_element(By.XPATH, ".//div/div[5]/span[2]/span[2]")
                cycle = cycle_element.text
            except NoSuchElementException:
                try:
                    # 尝试其他可能的XPath
                    cycle_element = house_element.find_element(By.XPATH, ".//div/div[5]/span[2]")
                    cycle = cycle_element.text
                except NoSuchElementException:
                    try:
                        # 尝试通过文本内容查找
                        cycle_element = house_element.find_element(By.XPATH, ".//*[contains(text(), '成交周期')]")
                        cycle = cycle_element.text
                    except NoSuchElementException:
                        print(f"注意：{house_name} 没有成交周期信息")

            # 提取天数
            cycle_days = re.search(r'(\d+)天', cycle)
            if cycle_days:
                cycle = cycle_days.group(1)
            else:
                cycle = ""

            # 获取朝向
            direction = house_element.find_element(By.XPATH, ".//div/div[2]/div[1]").text
            direction = re.search(r'(.+?)$', direction)
            if direction:
                direction = direction.group(1)
            else:
                direction = ""

            house_data = {
                '成交楼盘': house_name,
                '户型': house_type,
                '面积(平米)': area,
                '成交时间': deal_date,
                '成交价格': price,
                '当前楼层': current_floor,
                '总楼层': total_floor,
                '楼龄': building_age,
                '建筑类型': building_type,
                '朝向': direction,
                '成交周期(天)': cycle,
                '爬取时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return house_data

        except Exception as e:
            print(f"解析房源信息出错: {e}")
            return None

    def get_page(self, first_page=False):
        """获取页面数据"""
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                if first_page:
                    print("\n正在访问首页...")
                    self.driver.get(self.base_url)
                
                time.sleep(5)
                
                # 检查是否需要登录或验证
                page_source = self.driver.page_source.lower()
                if "登录" in page_source:
                    print("检测到需要登录...")
                    self.save_page_source("login")
                    self.wait_for_login()
                    continue
                
                if "验证" in page_source or "安全验证" in page_source:
                    print("检测到需要验证...")
                    self.save_page_source("verify")
                    self.handle_verification()
                    continue
                
                # 等待房源列表加载
                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='beike']/div[1]/div[5]/div[1]/div[4]/ul")))
                    return True
                except TimeoutException:
                    print("等待房源列表超时，正在保存页面源码...")
                    self.save_page_source("timeout")
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"等待15秒后重试第{retry_count + 1}次...")
                        time.sleep(15)
                    continue
                
            except Exception as e:
                print(f"访问页面出错: {e}")
                self.save_page_source("error")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"等待15秒后重试第{retry_count + 1}次...")
                    time.sleep(15)
                continue
        
        return False

    def parse_page(self):
        """解析当前页面的房源信息"""
        try:
            # 获取所有房源元素
            houses = self.driver.find_elements(By.XPATH, "//*[@id='beike']/div[1]/div[5]/div[1]/div[4]/ul/li")
            
            if not houses:
                print("未找到房源信息")
                return False
            
            print(f"找到{len(houses)}个房源")
            
            # 标记是否发现非目标日期的数据
            found_non_target_date = False
            
            for idx, house in enumerate(houses, 1):
                try:
                    # 先检查日期，不解析完整数据
                    try:
                        deal_date = house.find_element(By.XPATH, ".//div/div[2]/div[2]").text
                        
                        # 设置目标日期（如果尚未设置）
                        if self.target_date is None and deal_date:
                            self.target_date = deal_date
                            print(f"目标日期(T日)设置为: {self.target_date}")
                        
                        # 检查日期是否为目标日期
                        if self.target_date and deal_date != self.target_date:
                            print(f"发现非目标日期数据: {deal_date}，目标日期为: {self.target_date}")
                            found_non_target_date = True
                            break
                    except NoSuchElementException:
                        print(f"第{idx}个房源无法获取日期信息")
                        continue
                    
                    # 日期匹配目标日期，解析完整数据
                    house_data = self.parse_house_info(house)
                    if house_data:
                        print(f"成功解析第{idx}个房源: {house_data['成交楼盘']}")
                        self.data.append(house_data)
                except Exception as e:
                    print(f"解析第{idx}个房源出错: {e}")
                    continue
            
            # 如果发现非目标日期的数据，返回False表示应停止爬取
            return not found_non_target_date
                    
        except Exception as e:
            print(f"解析页面出错: {e}")
            self.save_page_source("parse_error")
            return False

    def click_next_page(self):
        """点击下一页按钮"""
        try:
            # 获取当前页码
            try:
                # 尝试从URL中获取页码
                current_url = self.driver.current_url
                if "pg" in current_url:
                    page_num = int(re.search(r'pg(\d+)', current_url).group(1))
                else:
                    page_num = 1
            except:
                # 如果无法从URL获取，默认为第1页
                page_num = 1
            
            print(f"当前页码: {page_num}")
            
            # 根据页码选择对应的XPath
            if page_num == 1:
                xpath = "//*[@id='beike']/div[1]/div[5]/div[1]/div[5]/div[2]/div/a[5]"
            elif page_num == 2:
                xpath = "//*[@id='beike']/div[1]/div[5]/div[1]/div[5]/div[2]/div/a[7]"
            elif page_num == 3:
                xpath = "//*[@id='beike']/div[1]/div[5]/div[1]/div[5]/div[2]/div/a[8]"
            else:  # 第4页及之后
                xpath = "//*[@id='beike']/div[1]/div[5]/div[1]/div[5]/div[2]/div/a[9]"
            
            # 增加备用XPath
            backup_xpaths = [
                "//a[contains(text(), '下一页')]",
                "//div[contains(@class, 'page-box')]//a[last()]",
                f"//div[contains(@class, 'page-box')]//a[contains(@data-page, '{page_num + 1}')]"
            ]
            
            # 尝试主要的XPath
            try:
                print(f"尝试使用XPath: {xpath}")
                
                next_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                
                # 滚动到按钮可见位置
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(2)
                
                # 检查是否是"下一页"按钮
                button_text = next_button.text
                if "下一页" not in button_text and ">" not in button_text and page_num + 1 != int(button_text):
                    print(f"警告：找到的按钮文本是 '{button_text}'，可能不是下一页按钮")
                    # 尝试改用备用方法
                    raise Exception("可能不是下一页按钮")
                
                # 点击下一页
                next_button.click()
                time.sleep(3)
                
                # 验证是否成功翻页
                new_url = self.driver.current_url
                if "登录" in self.driver.page_source:
                    print("检测到需要登录，登录状态可能已失效")
                    return False
                    
                # 检查是否成功翻页
                if "pg" in new_url:
                    new_page = int(re.search(r'pg(\d+)', new_url).group(1))
                    if new_page > page_num:
                        print(f"成功翻到第{new_page}页")
                        return True
                else:
                    # 首页到第二页的特殊情况
                    if page_num == 1 and "pg2" in new_url:
                        print("成功从首页翻到第2页")
                        return True
                
            except Exception as e:
                print(f"主要XPath方法失败: {e}")
                
                # 尝试备用XPath方法
                for bak_xpath in backup_xpaths:
                    try:
                        print(f"尝试备用XPath: {bak_xpath}")
                        
                        next_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, bak_xpath)))
                        
                        # 滚动到按钮可见位置
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(2)
                        
                        # 点击下一页
                        next_button.click()
                        time.sleep(3)
                        
                        # 验证是否成功翻页
                        new_url = self.driver.current_url
                        if "登录" in self.driver.page_source:
                            print("检测到需要登录，登录状态可能已失效")
                            return False
                            
                        # 检查是否成功翻页
                        if "pg" in new_url:
                            new_page = int(re.search(r'pg(\d+)', new_url).group(1))
                            if new_page > page_num:
                                print(f"使用备用方法成功翻到第{new_page}页")
                                return True
                        else:
                            # 首页到第二页的特殊情况
                            if page_num == 1 and "pg2" in new_url:
                                print("使用备用方法成功从首页翻到第2页")
                                return True
                                
                    except Exception as e2:
                        print(f"备用XPath {bak_xpath} 失败: {e2}")
                        continue
            
            # 如果以上方法都失败，尝试直接修改URL
            try:
                if page_num == 1:
                    next_url = self.base_url + "pg2/"
                else:
                    next_url = re.sub(r'pg\d+', f'pg{page_num+1}', self.driver.current_url)
                
                print(f"尝试直接访问下一页URL: {next_url}")
                self.driver.get(next_url)
                time.sleep(3)
                
                # 验证是否成功翻页
                if "pg" in self.driver.current_url:
                    new_page = int(re.search(r'pg(\d+)', self.driver.current_url).group(1))
                    if new_page > page_num:
                        print(f"使用直接URL访问成功翻到第{new_page}页")
                        return True
            except Exception as e:
                print(f"直接URL访问失败: {e}")
            
            print("所有翻页方式都失败了")
            return False
            
        except Exception as e:
            print(f"点击下一页按钮失败: {e}")
            return False

    def save_data(self):
        """保存数据到Excel文件"""
        try:
            if not self.data:
                print("没有收集到任何数据！")
                return
                
            # 获取当前脚本所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 创建data文件夹（如果不存在）
            data_dir = os.path.join(current_dir, 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                
            # 生成文件名，包含时间戳
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(data_dir, f'贝壳二手房成交数据_{timestamp}.xlsx')
            
            # 转换为DataFrame并保存
            df = pd.DataFrame(self.data)
            df.to_excel(filename, index=False, engine='openpyxl')
            
            print(f"\n数据已保存到: {filename}")
            print(f"共保存{len(self.data)}条记录")
            print("\n数据预览:")
            print(df.head())
            
        except Exception as e:
            print(f"保存数据时出错: {e}")
            # 尝试使用备用方式保存
            try:
                backup_file = os.path.join(data_dir, f'贝壳二手房成交数据_backup_{timestamp}.csv')
                df.to_csv(backup_file, index=False, encoding='utf-8-sig')
                print(f"数据已备份保存为CSV格式: {backup_file}")
            except Exception as e2:
                print(f"备份保存也失败了: {e2}")

    def save_cookies(self):
        """保存cookies到文件"""
        try:
            cookies = self.driver.get_cookies()
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cookie_path = os.path.join(current_dir, 'beike_cookies.json')
            with open(cookie_path, 'w') as f:
                json.dump(cookies, f)
            print("登录状态已保存，下次运行将自动登录")
        except Exception as e:
            print(f"保存cookies失败: {e}")

    def load_cookies(self):
        """从文件加载cookies"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cookie_path = os.path.join(current_dir, 'beike_cookies.json')
            if not os.path.exists(cookie_path):
                return False
            
            with open(cookie_path, 'r') as f:
                cookies = json.load(f)
            
            # 必须先访问网站域名，才能添加cookie
            self.driver.get("https://sz.ke.com")
            time.sleep(2)
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    continue
                
            print("已加载登录状态")
            return True
        except Exception as e:
            print(f"加载cookies失败: {e}")
            return False

    def handle_login(self):
        """处理登录流程"""
        # 先尝试使用保存的cookies登录
        if self.load_cookies():
            # 刷新页面，应用cookies
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # 检查是否登录成功
            if "登录" not in self.driver.page_source:
                print("自动登录成功！")
                return True
        
        # 如果没有cookies或cookies已失效，需要手动登录
        print("\n请在浏览器中手动登录...")
        print("登录完成后请按回车键继续...")
        input()
        
        # 保存新的登录状态
        self.save_cookies()
        return True

    def run(self):
        """运行爬虫"""
        try:
            # 访问第一页
            if not self.get_page(first_page=True):
                print("获取首页失败，程序退出")
                return
            
            # 检查是否有保存的cookies
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cookie_path = os.path.join(current_dir, 'beike_cookies.json')
            if os.path.exists(cookie_path):
                print("检测到已保存的登录状态，正在尝试自动登录...")
                if self.load_cookies():
                    self.driver.refresh()
                    time.sleep(3)
                    if "登录" not in self.driver.page_source:
                        print("自动登录成功！")
                    else:
                        print("自动登录失败，需要手动登录")
                        self.wait_for_login()
                        self.save_cookies()
                else:
                    print("加载cookies失败，需要手动登录")
                    self.wait_for_login()
                    self.save_cookies()
            else:
                print("未检测到保存的登录状态，需要手动登录")
                self.wait_for_login()
                self.save_cookies()
            
            current_page = 1
            while current_page <= 100:  # 最多爬取100页
                print(f"\n正在爬取第{current_page}页...")
                
                # 解析当前页面的房源信息，并检查是否应继续爬取
                should_continue = self.parse_page()
                
                # 如果发现了非目标日期的数据，停止爬取
                if not should_continue:
                    print(f"已发现非目标日期(T-1日)的数据，停止爬取")
                    break
                
                # 每爬取10页保存一次数据
                if current_page % 10 == 0:
                    self.save_data()
                
                # 随机延时
                delay = random.uniform(2, 4)
                print(f"等待{delay:.2f}秒后继续...")
                time.sleep(delay)
                
                # 尝试翻到下一页
                if not self.click_next_page():
                    print("无法继续翻页，可能已到最后一页")
                    break
                
                current_page += 1
                
        except KeyboardInterrupt:
            print("\n检测到用户中断，正在保存数据...")
            self.save_data()
        except Exception as e:
            print(f"爬虫运行出错: {e}")
        finally:
            self.save_data()
            self.driver.quit()
            print("爬虫已完成，浏览器已关闭。")

if __name__ == "__main__":
    spider = BeikeSpider()
    spider.run() 