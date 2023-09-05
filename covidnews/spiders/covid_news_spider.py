# Uses scrapy-splash library (instead of 'requests' library) which gives more functionality and flexibility
import scrapy
from scrapy_splash import SplashRequest
from urllib.parse import urljoin

# For http://web.archive.org/
import internetarchive
import requests

# Define preferred search keywords
#search_keywords = ['covid','virus','pandemic','vaccine','corona','vaccination','circuit breaker','SARS-CoV-2']
search_keywords = ['covid','pandemic','vaccine','coronavirus','vaccination','SARS-CoV-2']

# Whether to brute-force search across the entire website hierarchy, due to robots.txt restriction
SEARCH_ENTIRE_WEBSITE = 1

# Whether to skip cdx search
SKIP_CDX = True


class CovidNewsSpider(scrapy.Spider):
    name = 'covid_news_spider'

    start_urls = [
        #'https://web.archive.org/'
        #'https://www.straitstimes.com/'
        'https://www.channelnewsasia.com/'
        #'https://www.channelnewsasia.com/search?q=covid'  # [scrapy.downloadermiddlewares.robotstxt] DEBUG: Forbidden by robots.txt:
        #'https://www.straitstimes.com/search?searchkey=covid'  # Forbidden by https://www.straitstimes.com/robots.txt
    ]

    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'covidnews.middlewares.GzipRetryMiddleware': 543,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': None,
        },
    }

    def search_archives(self, search_keywords, countries, creators, types, languages):

        queries = []
        keyword_queries = []

        # Search by keywords
        for keyword in search_keywords:
            keyword_queries.append(f"subject:{keyword.lower()}")

        # Search by identifier prefix
        for country in countries:
            queries.append(f"identifier:details.{country.lower()}")

        # Limit by creator
        for creator in creators:
            queries.append(f"creator:{creator}")

        # Filter by mediatype
        for type in types:
            queries.append(f"mediatype:{type}")

        # Filter by language
        for lang in languages:
            queries.append(f"language:{lang}")

        # Combine queries
        full_query = " AND ".join(queries) + " AND (" + " OR ".join(keyword_queries) + ")"

        # For ChunkedEncodingError (connection broken issue)
        MAX_RETRIES = 3

        # Search archives
        for i in range(MAX_RETRIES):

            try:
                print(f"full_query for archive.org = {full_query}")
                search = internetarchive.search_items(full_query)
                print(f"archive.org search API returns {len(search)} pieces of search results !!")

                return search

            except internetarchive.exceptions.RequestError as e:
                print(f"Search failed: {e}")

            time.sleep(2 ** i)

        print("Failed after max retries")


    def start_requests(self):
        for url in self.start_urls:
            if "archive.org" in url:
                countries = [] #['SG']
                creators = [] #['CNN', 'CNA']
                types = ['texts']
                languages = ['English']

                search = self.search_archives(search_keywords, countries, creators, types, languages)

                identifiers = [result['identifier'] for result in search]
                unique_identifiers = set(identifiers)
                print(f"len(unique_identifiers) = {len(unique_identifiers)}")

                search_counter = 0

                # Process results
                for result in search:
                    print(f"search_counter = {search_counter}")
                    search_counter = search_counter + 1

                    # Get identifier
                    identifier = result['identifier']

                    if not SKIP_CDX:
                        # Get timestamp from CDX API
                        cdx_url = f'https://web.archive.org/cdx/search/cdx?url={identifier}&output=json'
                        print(f"cdx_url = {cdx_url}")
                        MAX_CDX_RETRIES = 3

                        try:
                            # Request CDX API
                            r = requests.get(cdx_url)

                            # Parse response
                            results = r.json()

                        except ConnectionError as e:
                            print(f"CDX connection error: {e}")

                            if retries < MAX_CDX_RETRIES:
                                time.sleep(1)
                                retries += 1
                                return query_cdx(cdx_url, retries)

                            else:
                                # Max retries reached, skip this identifier
                                print(f"Skipping {identifier} after max retries")
                                continue
                                #raise # reraise error if max retries reached

                        try:
                            # Extract timestamp
                            timestamp = results[-1][1]
                            print(f"timestamp = {timestamp}")
                        except IndexError:
                            print("No results from CDX")

                    # Lookup item metadata
                    try:
                        item = internetarchive.get_item(identifier)
                        metadata = item.metadata
                        #print(f"metadata.keys() = {metadata.keys()}")
                        print(f"metadata = {metadata}")

                    except Exception as e:
                        print("Error retrieving metadata: ", e)

                    timestamp = None

                    if not identifier:
                        print(f"url missing")
                        continue

                    else:
                        # Set the RETRY_TIMES setting to specify how many times to retry failed requests.
                        RETRY_TIMES = 5

                        if timestamp:
                            # Construct Wayback URL
                            wayback_url = f'https://web.archive.org/web/{timestamp}/{identifier}'
                            print(f"wayback_url = {wayback_url}")
                            yield scrapy.Request(wayback_url, callback=self.parse, meta={'retry_times': RETRY_TIMES})

                        else:
                            # Construct url from 'identifier-access' field
                            identifier_url = metadata.get("identifier-access")
                            print(f"identifier_url = {identifier_url}")

                            if identifier_url:
                                yield scrapy.Request(identifier_url, callback=self.parse, meta={'retry_times': RETRY_TIMES})

            else:
                js_script = """
                    function main(splash)

                      -- Go to page
                      splash:go(splash.args.url)

                      -- Wait for 10 seconds
                      splash:wait(10.0)

                      -- Print url
                      print("splash:get_url() = ", splash:get_url())

                      -- Select button
                      local close_btn = splash:select('#pclose-btn')

                      -- Print details
                      print("close_btn = ", close_btn:tostring())

                      -- Click button
                      close_btn:mouse_click()

                      -- Wait 2 seconds
                      splash:wait(2.0)

                      -- Return HTML after waiting
                      return splash:html()

                    end
                    """

                yield SplashRequest(
                        url,
                        callback=self.parse,
                        endpoint='execute',
                        args={'lua_source': js_script, 'adblock': True, 'wait': 10, 'resource_timeout': 10},
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                    )

    def get_next_pages(self, response):
        print("inside get_next_pages(), response.url = ", response.url)

        if 'channelnewsasia' in response.url:
            more_links = response.css('a::attr(href)').getall()  # Replace with the correct CSS selector

        elif 'straitstimes' in response.url:
            if SEARCH_ENTIRE_WEBSITE:
                more_links = response.css('a::attr(href)').getall()
            else:
                # Find all 'a' tags inside 'div' tags with class 'queryly_item_row', 'a' tags with the text 'More', and 'a' tags with class 'stretched-link'
                #more_links = response.css('div.queryly_item_row a::attr(href), a:contains("More")::attr(href), a.stretched-link::attr(href)').getall()
                #more_links = response.css('div.queryly_item_row > a::attr(href)').getall()
                more_links = response.css('a:contains("Next Page")::attr(href)').get()

        elif 'archive.org' in response.url:
            more_links = response.css('a.format-summary:contains("FULL TEXT")::attr(href)').getall()

        else:
            more_links = None

        print("more_links = ", more_links)
        return more_links

    def parse(self, response):
        articles = None
        link = response.url
        print("inside parse(), response.url = ", response.url)

        INTERNETARCHIVE_FULL_TEXT = \
            'https://archive.org/stream/' in response.url or \
            'https://archive.org/compress/' in response.url

        if link:
            if "javascript" in link or "mailto" in link or "play.google.com" in link or "apps.apple.com" in link or \
                "www.channelnewsasia.com/watch" in link or "cnaluxury.channelnewsasia.com" in link or \
                "www.channelnewsasia.com/about-us" in link:
                # Skip links
                print(f"skipped : {link}")

            else:
                if not INTERNETARCHIVE_FULL_TEXT:
                    articles = self.parse_articles(response)
                print("articles = ", articles)

        if articles is not None:
            articles = list(articles)
        else:
            articles = []

        for article in articles:
            yield from self.parse_article(article, response)

        next_pages = None

        if not INTERNETARCHIVE_FULL_TEXT:
            # Get the next pages URLs and yield new requests
            next_pages = self.get_next_pages(response)

        if next_pages is not None:
            next_pages = list(next_pages)
        else:
            next_pages = []

        next_pages_url = []
        for link in next_pages:
            if link.startswith("http"):
                next_pages_url.append(link)
            else:
                next_pages_url.append(urljoin(response.url, link))

        for next_page_url in next_pages_url:
            if next_page_url:
                link = next_page_url
                #print(f"link : {link} is of type : {type(link)}")

                if "javascript" in link or "mailto" in link or "play.google.com" in link or "apps.apple.com" in link or \
                     "www.channelnewsasia.com/watch" in link or "cnaluxury.channelnewsasia.com" in link or \
                    "www.channelnewsasia.com/about-us" in link:
                    # Skip links
                    continue

                print("next_page_url = ", next_page_url)

                yield SplashRequest(
                    #response.urljoin(next_page),
                    next_page_url,
                    self.parse,
                    args={'wait': 0.5},
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                )

        print(f"Found {len(articles)} articles")

    def parse_articles(self, response):
        print("inside parse_articles(), response.url = ", response.url)
        if 'channelnewsasia' in response.url:
            # Extract articles from CNA
            return response.css('div.list-object')

        elif 'straitstimes' in response.url:
            # Extract articles from ST
            #return response.css('div.container > div.grid.cards > div.card')
            print("parse_articles() for straitstimes")
            return response.css('div.card-body')
            #return response.css('div.queryly_item_row')

        elif 'archive.org' in response.url:
            if 'https://archive.org/details/' in response.url:
                # Extract article (only the FULL_TEXT download page) from the summary page
                return response.css('a.format-summary.download-pill:contains("FULL TEXT")::attr(href)')
            else:
                print("Already downloaded and extracted the FULL_TEXT archive.org article")
                # (be aware of compressed zip file format containing multiple djvu.txt.html webpage files,
                # OR Microsoft Word OR Adobe PDF document)
                return response.css('*')


    def get_source(self, response):
        if 'channelnewsasia' in response.url:
            return 'CNA'
        elif 'straitstimes' in response.url:
            return 'ST'
        elif 'archive.org' in response.url:
            return 'archive'


    def parse_article(self, article, response):

        if 'channelnewsasia' in response.url:
            title = article.css('title::text').get() or \
                    article.css('h1.entry-title::text').get() or \
                    article.css('div.quick-link[data-heading]::attr(data-heading)').get() or \
                    article.css('div.quick-link::attr(data-heading)').get() or \
                    article.css('meta[property="og:title"]::attr(content)').get() or \
                    article.css('meta[name="twitter:title"]::attr(content)').get()
            date = article.css('time.entry-date::text').get() or article.css('div.list-object__datetime-duration span::text').get()

            link = article.css('h1.entry-title a::attr(href)').get() or \
                    article.css('h6.list-object__heading a::attr(href)').get() or \
                    article.css('div.quick-link::attr(data-link_absolute)').get()

        elif 'straitstimes' in response.url:
            title = article.css('h5.card-title a::text').get()
            date = article.css('time::text').get()

            link = article.css('a::attr(href)').get()

        elif 'archive.org' in response.url:
            title = article.css('title::text').get()
            date = article.xpath('//meta[@name="date"]/@content').get()

            link = response.css('a.format-summary.download-pill:contains("FULL TEXT")::attr(href)').get()

        #print(f"link : {link} is of type : {type(link)}")

        article_url = link

        yield SplashRequest(
            url=response.urljoin(article_url),
            callback=self.get_article_content,
            meta={'title': title, 'date': date},  # Pass additional data here
            args={'wait': 0.5},
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,      like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        )


    def get_article_content(self, response):
        # retrieves article's detailed title and body properly

        title = response.meta['title']  # Access the additional data here
        date = response.meta['date']  # Access the additional data here

        if 'channelnewsasia' in response.url:
            body = response.xpath('//p[not(@*)]//descendant-or-self::node()/text()').getall()
            body = '\n'.join(body)
            #body = response.css('div.article p::text').getall() or \
            #       response.css('div.text-long').getall() or \
            #       response.css('main#maincontent > div.container.container-ia > pre::text').getall()
            #body = '\n'.join(body)

        elif 'straitstimes' in response.url:
            body = response.xpath('//p[not(@*)]/text()').getall()
            body = '\n'.join(body)

        elif 'archive.org' in response.url:
            body = response.css('div.article p::text').getall() or \
                   response.css('div.text-long').getall() or \
                   response.css('main#maincontent > div.container.container-ia > pre::text').getall()
            body = '\n'.join(body)

        else:
            body = None

        link = response.url

        print(f"inside parse_article(), article_url = {link} , title = {title}, date = {date}, body = {body}")

        self.write_to_local_data(link, title, body, response)

        yield {
            'title': title,
            'link': link,
            'date': date,
            'body': body,
            #'excerpt': article.css('p::text').get(),
            'source': self.get_source(response)
        }


    def write_to_local_data(self, link, title, body, response):
        if (title != None and any(keyword in title.lower() for keyword in search_keywords)) or (body != None and any(keyword in body.lower() for keyword in search_keywords)):
            # Create a unique filename for each URL by removing the 'http://', replacing '/' with '_', and adding '.html'
            filename = link.replace('http://', '').replace('/', '_') + '.html'
            print("filename = ", filename)

            # Write the entire body of the response to a file
            #with open("/home/phung/covidnews_result/"+filename, 'wb') as f:
            with open(filename, 'wb') as f:
                f.write(response.body)

        return None

