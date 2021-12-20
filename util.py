import logging
import re
import time

import requests
# import appdirs
from bs4 import BeautifulSoup

import strings

# from pathlib import Path

home_url = 'https://ceiba.ntu.edu.tw'
login_url = 'https://ceiba.ntu.edu.tw/ChkSessLib.php'
module_url = 'https://ceiba.ntu.edu.tw/modules/main.php'
courses_url = 'https://ceiba.ntu.edu.tw/student/index.php?seme_op=all'
button_url = 'https://ceiba.ntu.edu.tw/modules/button.php'
banner_url = 'https://ceiba.ntu.edu.tw/modules/banner.php'
homepage_url = 'https://ceiba.ntu.edu.tw/modules/index.php'
skip_courses_list = ['中文系大學國文網站']
# data_dir = Path(appdirs.user_data_dir('ceiba-downloader', 'jameshwc'))
# data_dir.mkdir(parents=True, exist_ok=True)

# crawled_courses = json.load(os.path.join(data_dir, 'courses.json'))


def get_valid_filename(name: str):
    s = str(name).strip().replace(' ', '_').replace('/', '-')
    s = re.sub(r'(?u)[^-\w.]', '_', s)
    return s


def progress_decorator():
    def decorator(func):
        def wrap(self, *args):
            logging.info(
                strings.object_download_info.format(self.cname, args[1]))
            ret = func(self, *args)
            logging.info(strings.object_finish_info.format(
                self.cname, args[1]))
            return ret

        return wrap

    return decorator


def get(session: requests.Session, url: str):
    while True:
        try:
            response = session.get(url)
        # except (TimeoutError, ConnectionResetError):
        except Exception as e:
            print(type(e))
            if type(e) == TimeoutError or type(e) == ConnectionResetError:
                logging.error(strings.crawler_timeour_error)
            else:
                logging.error(e)
                logging.info('五秒後重新連線...')
            time.sleep(5)
            continue
        return response
