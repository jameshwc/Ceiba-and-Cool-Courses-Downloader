import logging
import os
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import strings
from exceptions import NotFound
import util


class Crawler():

    crawled_urls = {}  # TODO: use set
    crawled_static_files = {
    }  # css/img: use path to avoid repetitive downloads.

    # TODO: we should move css/img to root folder instead of download them every time in each course

    def __init__(self,
                 session: requests.Session,
                 url: str,
                 path: str,
                 filename: str,
                 text: str = ""):
        self.session = session
        self.url = url
        self.path = path
        self.filename = util.get_valid_filename(filename)
        self.text = text

    def crawl(self) -> bool:
        '''
        Return True if the url is file, and return False if the url is html.
        '''
        response = util.get(self.session, self.url)
        if response.status_code == 404:
            raise NotFound(self.text, response.url)

        if not response.url.startswith('https://ceiba.ntu.edu.tw'):
            logging.warn(strings.skip_external_href.format(response.url))
            return  # TODO: download (optionally) external documents (.pdf, .docx, etc.) (may limit the domain names)

        if self.url in Crawler.crawled_urls:
            return Crawler.crawled_urls[self.url]
        if (self.path, self.url) in Crawler.crawled_static_files:
            return True

        if str.encode(
                'The requested URL was rejected. Please consult with your administrator.'
        ) in response.content:
            logging.error(
                strings.crawler_download_fail.format(self.text, response.url))
            return False

        if len(self.text) > 0:
            logging.info(strings.crawler_download_info.format(self.text))

        if 'text/html' not in response.headers[
                'content-type']:  # files (e.g. pdf, docs)
            if self.filename.endswith('.html'):
                self.filename = self.filename.removesuffix('.html')
            dir = os.path.join(os.path.join(self.path, "files"))
            os.makedirs(dir, exist_ok=True)
            path = Path(os.path.join(dir, self.filename))
            path.write_bytes(response.content)
            Crawler.crawled_static_files[(self.path, response.url)] = True
            return True

        soup = BeautifulSoup(response.content, 'html.parser')
        Crawler.crawled_urls[response.url] = False

        for css in soup.find_all('link'):
            url = urljoin(self.url, css.get('href'))
            if url.startswith('http') and 'ceiba' not in url:
                continue  # skip downloading external css
            filename = url.split('/')[-1]
            css['href'] = "static/" + filename
            static_dir = os.path.join(self.path, 'static')
            os.makedirs(static_dir, exist_ok=True)
            Crawler(self.session, url, static_dir, filename,
                    css['href']).crawl_css_and_resources()

        for img in soup.find_all('img'):
            url = urljoin(self.url, img.get('src'))
            img['src'] = url.split('/')[-1]
            img_response = util.get(self.session, url)
            path = Path(os.path.join(self.path, img['src']))
            if path.exists():  # TODO: check if filename exists
                pass
            path.write_bytes(img_response.content)

        for op in soup.find_all('option'):
            op.extract()

        hrefs = soup.find_all('a')

        skip_href_texts = ['作業列表', '友善列印']
        skip_href_texts.extend([
            '看板列表', '最新張貼', '排行榜', '推薦文章', '搜尋文章', '發表紀錄', ' 新增主題', '引用',
            ' 回覆', '分頁顯示', '上個主題', '下個主題', '修改'
        ])
        # '修改' may be an indicator to download the owner's article?
        skip_href_texts.extend(['上頁', '下頁', '上一頁', '下一頁', ' 我要評分'])

        # special case for board
        is_board = False
        board_dir = {}
        for caption in soup.find_all('caption'):
            caption_text: str = caption.get_text()
            if caption_text.startswith('看板列表'):
                rows = caption.parent.find('tbody').find_all('tr')
                for row in rows:
                    a_tag = row.find("p", {"class": "fname"}).find('a')
                    dir_name = util.get_valid_filename(a_tag.text)
                    board_dir[a_tag.text] = os.path.join(self.path, dir_name)
                    os.makedirs(board_dir[a_tag.text], exist_ok=True)
                is_board = True
                break

        for a in hrefs:
            if a.text in skip_href_texts:
                a.replaceWithChildren()
                continue
            if len(a.text) > 0 and not a['href'].startswith('mailto'):
                if not a['href'].startswith('http') or a['href'].startswith(
                        'https://ceiba.ntu.edu.tw'):
                    # TODO: refactor the following code
                    url = urljoin(response.url, a.get('href'))
                    filename = util.get_valid_filename(a.text)
                    if not filename.endswith('.html'):
                        filename += ".html"
                    if is_board and a.text in board_dir:
                        a['href'] = os.path.join(board_dir[a.text], filename)
                        os.makedirs(os.path.join(board_dir[a.text], "files"),
                                    exist_ok=True)
                        is_file = Crawler(self.session, url, board_dir[a.text],
                                          filename, a.text).crawl()
                    else:
                        try:
                            is_file = Crawler(self.session, url, self.path,
                                              filename, a.text).crawl()
                        except NotFound as e:
                            logging.warning(e)
                            a.string = a.text + " [404 not found]"
                            a['href'] = urljoin(self.url, a['href'])
                            # a.replaceWithChildren()  # discuss: when 404 happens, should it link to original url?
                            continue
                        a['href'] = filename
                    if is_file:  # TODO: avoid duplicate filenames?
                        a['href'] = os.path.join(
                            "files",
                            filename.removesuffix('.htm').removesuffix(
                                '.html'))

        with open(os.path.join(self.path, self.filename),
                  'w',
                  encoding='utf-8') as html:
            html.write(str(soup))
        return False

    def crawl_css_and_resources(self):
        response = util.get(self.session, self.url)
        path = Path(os.path.join(self.path, self.filename))
        if path.exists():  # TODO: check if filename exists
            pass
        new_content = response.content
        resources = re.findall(r'url\((.*?)\)', str(response.content))
        if len(resources) > 0:
            resources_path = os.path.join(self.path, "resources")
            os.makedirs(resources_path, exist_ok=True)
            for res in resources:
                resp = util.get(self.session, urljoin(self.url, res))
                res_filename = res.split('/')[-1]
                with open(os.path.join(resources_path, res_filename),
                          'wb') as resource_file:
                    resource_file.write(resp.content)
                new_content = new_content.replace(
                    bytes('url(' + res, encoding='utf-8'),
                    bytes('url(resources/' + res_filename, encoding='utf-8'))
        path.write_bytes(new_content)