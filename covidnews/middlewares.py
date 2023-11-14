# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
from scrapy.http import HtmlResponse

# For javascript handling
from selenium import webdriver
import asyncio
from scrapy.utils.defer import mustbe_deferred
from scrapy.utils.python import to_bytes
from playwright.async_api import async_playwright

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter

# For solving the gzip decompression issue
import gzip
from scrapy.utils.response import response_status_message
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.downloadermiddlewares.httpcompression import HttpCompressionMiddleware


class GzipRetryMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if response.status in [500, 502, 503, 504, 400, 408]:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response

        if response.headers is not None and b'Content-Encoding' in response.headers:
            content_encoding = response.headers[b'Content-Encoding']

            if content_encoding is not None and b'gzip' in content_encoding:
                try:
                    body = gzip.decompress(response.body)
                    return response.replace(body=body)
                except (OSError, EOFError) as e:
                    return self._retry(request, e, spider) or response

        return response


class ForgivingHttpCompressionMiddleware(HttpCompressionMiddleware):
    def process_response(self, request, response, spider):
        try:
            return super().process_response(request, response, spider)
        except gzip.BadGzipFile:
            return response  # Return uncompressed response if decompression fails


class SeleniumMiddleware:
    def __init__(self):
        self.driver = webdriver.Firefox()

    def __del__(self):
        self.driver.quit()

    def process_request(self, request, spider):
        self.driver.get(request.url)
        return HtmlResponse(self.driver.current_url, body=self.driver.page_source, encoding='utf-8', request=request)


from twisted.internet import defer

class PlaywrightMiddleware:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.launch_browser())

    async def launch_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def process_request(self, request, spider):
        page = await self.browser.new_page()
        response = await page.goto(request.url)
        body = await response.text()
        await page.close()
        return HtmlResponse(url=request.url, body=to_bytes(body), encoding='utf-8', request=request)

    def spider_closed(self, spider):
        self.loop.run_until_complete(self.browser.close())
        self.loop.run_until_complete(self.playwright.stop())


class CovidnewsSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class CovidnewsDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
