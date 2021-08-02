"""Readme:
create time: 2021-08-01

1. 请使用pip安装好相应扩展库. lxml、win32api、selenium、pymysql,并配置好ChromeDriver等相关环境
2. 本次使用selenium控制的浏览器为本地Chrome,使用类时请将Chrome安装路径传入参数中
3. 以便更好的抓取相关信息,请提前在Chrome浏览器登录BOSS直聘,如果没有登录会受到反爬限制
4. 执行写入数据库操作时记得提前将 BOSS库和jobs_info表创建好
"""
import os
import time
import random
import pymysql
import win32api
from lxml import etree
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options


class BOSS(object):
    def __init__(self, ChromePath, Keyword, QueryQuantity=30):
        """
        :param ChromePath: chrome安装路径
        :param Keyword: 搜索职位关键字
        :param QueryQuantity: 获取职位的数量,默认获取30条
        """
        self.Url = "https://www.zhipin.com/"
        self.ChromePath = ChromePath
        self.Keyword = Keyword
        self.jobs_quantity = QueryQuantity
        self.Browser = None
        self.xpath = {}
        self.job_info = {}
        self.jobs_list = []

    def start_browser(self):
        """启动本地浏览器并打开页面"""

        # 判断当前Chrome是否在运行
        def is_exe_running(exe="chrome.exe"):
            result = os.popen(f'''tasklist | findstr "{exe}" ''')
            return exe in result.read()

        # 关闭当前Chrome
        def close_exe_program(exe="chrome.exe"):
            if is_exe_running(exe):
                os.popen(f"""taskkill -F /im {exe}""")
                return True
            return False

        # 启动Chrome
        def start_program(path, params=""):
            win32api.ShellExecute(0, 'open', path, params, os.path.split(path)[0], 1)

        # 启用Chrome
        def start_debugging_chrome(url=""):
            if close_exe_program():
                time.sleep(1)
            path = self.ChromePath
            assert path is not None, "获请传入chrome.exe 绝对路径"
            if not path.endswith('chrome.exe'):
                path = path + '\\chrome.exe'
            start_program(path, f"--remote-debugging-port=9222 {url}")

        start_debugging_chrome(url=self.Url)
        option = Options()
        option.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        self.Browser = webdriver.Chrome(options=option)
        self.Browser.maximize_window()
        self.Browser.switch_to.window(self.Browser.window_handles[0])
        try:
            WebDriverWait(driver=self.Browser, timeout=10).until(lambda d: d.find_element_by_id("main"))
        except Exception:
            print("打开页面失败,请检查网络是否正常后重新运行此程序(如果网络正常尝试改变此方法中的element元素或将try语句注释)")
            self.close_browser()
            exit(-1)

    def close_browser(self):
        """关闭浏览器"""
        self.Browser.quit()

    def wait_element_loaded(self, xpath: str, timeout=10, close_browser=True):
        """
        等待页面元素成功加载完成
        :param xpath: xpath表达式
        :param timeout: 最长等待超时时间
        :param close_browser: 元素等待超时后是否关闭浏览器
        :return: Boolean
        """
        now_time = int(time.time())
        while int(time.time()) - now_time < timeout:
            try:
                element = self.Browser.find_element_by_xpath(xpath)
                if element:
                    return True
                time.sleep(1)
            except Exception:
                pass
        else:
            if close_browser:
                self.close_browser()
            print("查找页面元素失败，如果不存在网络问题请尝试修改xpath表达式")
            return False

    def get_element_text(self, xpath, single=True):
        """获取页面中指定元素的文本内容,如果页面中找不到该元素则返回空
        :param xpath: xpath表达式
        :param single: True表示获取单个元素,False表示获取多个元素
        :return: 元素的文本内容
        """
        try:
            if single:
                return self.Browser.find_element_by_xpath(xpath).text
            else:
                return self.Browser.find_elements_by_xpath(xpath)
        except Exception:
            return ''

    def add_xpath_element(self):
        """增加页面中相应的xpath元素"""
        self.xpath['input_box'] = '//input[@name="query"]'                                      # 输入框
        self.xpath['query'] = '//button[@ka="search_box_index"]'                                # 查询按钮
        self.xpath['jobs_div'] = '//div[@class="job-list"]'                                     # 职位展示页面
        self.xpath['jobs_list'] = '//div[@class="job-list"]/ul/li//span[@class="job-name"]/a'   # 职位信息列表
        self.xpath['job_detail'] = '//div[@class="job-banner"]'                                 # 职位详情页面
        self.xpath['next_page'] = '//a[@ka="page-next"]'                                        # 下一页按钮
        self.xpath['company_name'] = '//div[@class="company-info"]/a[2]'                        # 公司名称
        self.xpath['job_name'] = '//div[@class="name"]/h1'                                      # 职位名称
        self.xpath['job_salary'] = '//span[@class="salary"]'                                    # 员工薪水
        self.xpath['job_banner'] = '(//div[@class="info-primary"]/p)[1]'                        # 工作信息栏
        self.xpath['job_content'] = '//div[@class="text"]'                                      # 工作内容
        self.xpath['job_welfare'] = '//div[@class="job-tags"]/span'                             # 员工福利
        self.xpath['company_type'] = '//a[@ka="job-detail-brandindustry"]'                      # 公司行业
        self.xpath['update_date'] = '(//p[@class="gray"])[1]'                                   # 发布职位日期
        self.xpath['update_person'] = '//div[@class="detail-op"]/h2'                            # 发布职位的人员
        self.xpath['company_address'] = '//div[@class="location-address"]'                      # 公司地址
        self.xpath['Financing_stage'] = '//div[@class="sider-company"]/p/i[@class="icon-stage"]/parent::*'   # 公司融资阶段
        self.xpath['company_size'] = '//div[@class="sider-company"]/p/i[@class="icon-scale"]/parent::*'      # 公司规模

    def get_jobs_info(self):
        """处理页面内容"""
        self.Browser.find_element_by_xpath(self.xpath['input_box']).send_keys(self.Keyword)
        time.sleep(1)
        self.Browser.find_element_by_xpath(self.xpath['query']).click()

        while len(self.jobs_list) < self.jobs_quantity:
            if not self.wait_element_loaded(xpath=self.xpath['jobs_div'], timeout=15):
                print("查询职位页面加载失败,请检查网络连接是否正常！")
                exit(-1)
            jobs_links = self.Browser.find_elements_by_xpath(self.xpath['jobs_list'])

            for job_link in jobs_links:
                # 打开单个职位详情页面并将浏览器对象切换到新窗口
                job_link.click()
                self.Browser.switch_to.window(self.Browser.window_handles[-1])
                if not self.wait_element_loaded(xpath=self.xpath['job_detail']):
                    print("职位详情页面加载失败，请检查！")
                    exit(-1)
                job_welfare_list = self.Browser.find_elements_by_xpath(self.xpath['job_welfare'])
                job_banner_HTML = self.Browser.find_element_by_xpath(self.xpath['job_banner']).get_attribute(
                    "outerHTML")
                # 使用etree更好的获取text
                job_banner = etree.fromstring(job_banner_HTML)

                education = job_banner.xpath("./text()")[1]
                work_experience = job_banner.xpath("./text()")[0]
                job_name = self.get_element_text(self.xpath['job_name'])
                job_salary = self.get_element_text(self.xpath['job_salary'])
                update_date = self.get_element_text(self.xpath['update_date'])
                company_size = self.get_element_text(self.xpath['company_size'])
                company_type = self.get_element_text(self.xpath['company_type'])
                company_name = self.get_element_text(self.xpath['company_name'])
                update_person = self.get_element_text(self.xpath['update_person'])
                Financing_stage = self.get_element_text(self.xpath['Financing_stage'])
                company_address = self.get_element_text(self.xpath['company_address'])
                job_content = self.get_element_text(self.xpath['job_content']).replace('\n', '')
                job_welfare = '、'.join([welfare.text for welfare in job_welfare_list if welfare.text])

                self.job_info = {'company_name': company_name, 'job_name': job_name, 'job_salary': job_salary,
                                 'work_experience': work_experience, 'education': education,
                                 'job_content': job_content, 'Financing_stage': Financing_stage,
                                 'company_size': company_size, 'company_type': company_type,
                                 'company_address': company_address, 'update_date': update_date,
                                 'update_person': update_person, 'job_welfare': job_welfare,
                                 }
                print(self.job_info)
                if len(self.jobs_list) < self.jobs_quantity:
                    self.jobs_list.append(self.job_info)
                else:
                    break
                time.sleep(random.randint(2, 5))
                self.Browser.close()
                # 关闭当前所使用的页面后要及时切换到另一个存在的页面，不然会报错
                self.Browser.switch_to.window(self.Browser.window_handles[0])

            if len(self.jobs_list) < self.jobs_quantity:
                try:
                    self.Browser.switch_to.window(self.Browser.window_handles[0])
                    next_page = self.Browser.find_element_by_xpath(self.xpath['next_page'])
                    if "disabled" not in next_page.get_attribute("class"):
                        # 点击下一页
                        next_page.click()
                    else:
                        print("已查询到最后一页...")
                        break
                except Exception as e:
                    print(e)
                    break

        print("已获取职位数量", len(self.jobs_list))

    def run(self):
        """执行程序
        :return: 获取到的结果 -> list
        """
        self.start_browser()
        self.add_xpath_element()
        self.get_jobs_info()
        self.close_browser()
        return self.jobs_list


class MysqlPipelines(object):
    """
    实现将数据写入到数据库中
    提前将BOSS库和jobs_info表创建好,创建表结构如下:
        create table BOSS.jobs_info( \
            id int primary key auto_increment, \
            company_name varchar(100) character set utf8, \
            job_name varchar(100) character set utf8, \
            job_salary varchar(100) character set utf8, \
            work_experience varchar(100) character set utf8, \
            education varchar(100) character set utf8, \
            job_content varchar(3000) character set utf8, \
            Financing_stage varchar(100) character set utf8, \
            company_size varchar(100) character set utf8, \
            company_type varchar(100) character set utf8, \
            company_address varchar(100) character set utf8, \
            update_date varchar(100) character set utf8, \
            update_person varchar(100) character set utf8, \
            job_welfare varchar(100) character set utf8);
    """
    def __init__(self, Host, Port, DB, User, Password, Charset):
        """初始化.
        定义连接远程MySQL的IP、端口、库名、用户名、密码、字符格式.
        """
        self.conn = pymysql.connect(
            host=Host,
            port=Port,
            db=DB,
            user=User,
            password=Password,
            charset=Charset,
        )
        self.cur = self.conn.cursor()

    def write_to_mysql(self, values: list or dict):
        """
        将values值进行循环遍历,过滤出字典数据后进行依次写入数据库.
        :param values: 可以是单个字典也可以将字典包含在列表或二维数组中.
        """
        if isinstance(values, list) and len(values) >= 1:
            for value in values:
                if isinstance(value, list):
                    for internal_dict in value:
                        if isinstance(internal_dict, dict):
                            self.insert_value(internal_dict)
                elif isinstance(value, dict):
                    self.insert_value(value)
        elif isinstance(values, dict):
            self.insert_value(values)

        self.conn.close()

    def insert_value(self, dict_value: dict):
        """向MySQL中插入数据
        :param dict_value: 要插入的字典值
        """
        TableName = "BOSS.jobs_info"
        FieldsName = "company_name, job_name, job_salary, work_experience, education, job_content, Financing_stage, " \
                     "company_size, company_type, company_address, update_date, update_person, job_welfare "
        sql = "insert into {}({}) values('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(
            TableName,
            FieldsName,
            dict_value.get('company_name'),
            dict_value.get('job_name'),
            dict_value.get('job_salary'),
            dict_value.get('work_experience'),
            dict_value.get('education'),
            dict_value.get('job_content'),
            dict_value.get('Financing_stage'),
            dict_value.get('company_size'),
            dict_value.get('company_type'),
            dict_value.get('company_address'),
            dict_value.get('update_date'),
            dict_value.get('update_person'),
            dict_value.get('job_welfare')
        )
        try:
            self.cur.execute(sql)
            self.conn.commit()
        except Exception as E:
            print(E)
            self.conn.rollback()


if __name__ == '__main__':
    chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    keyword = "数据分析"
    query_quantity = 40
    main = BOSS(ChromePath=chrome_path, Keyword=keyword, QueryQuantity=query_quantity)
    jobs_info = main.run()

    mysql = MysqlPipelines(Host='192.168.116.128',
                           Port=3306,
                           DB='BOSS',
                           User='root',
                           Password='password123',
                           Charset='utf8')
    mysql.write_to_mysql(values=jobs_info)
