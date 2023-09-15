# Uses scrapy-splash library (instead of 'requests' library) which gives more functionality and flexibility
import scrapy
from scrapy_splash import SplashRequest
from urllib.parse import urljoin
import re
from urllib.parse import urlparse, urlunparse
from dateutil.parser import parse

# For http://web.archive.org/
import internetarchive
import requests

# Define preferred search keywords
#search_keywords = ['covid','virus','pandemic','vaccine','corona','vaccination','circuit breaker','SARS-CoV-2']
search_keywords = ['covid','pandemic','vaccine','coronavirus','vaccination','SARS-CoV-2']

# Define preferred search countries scope
search_countries = ['Singapore']

# Whether to brute-force search across the entire website hierarchy, due to robots.txt restriction
SEARCH_ENTIRE_WEBSITE = 1

# Whether to skip cdx search
SKIP_CDX = True

# Excludes search URL results that renders the following files extensions
excluded_file_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf", ".xls", ".mp3", ".mp4", ".mov",
                            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"]

# Only parses URLs within these domains
allowed_domain_names = ["archive.org", "straitstimes.com", "channelnewsasia.com"]

# not accessible due to DNA lookup error or the webpage had since migrated to other subdomains
inaccessible_subdomain_names = ["olympianbuilder.straitstimes.com", "ststaff.straitstimes.com", "media.straitstimes.com",
                                "buildsg2065.straitstimes.com", "origin-stcommunities.straitstimes.com",
                                "stcommunities.straitstimes.com", "euro2016.straitstimes.com",
                                "awsstaff.straitstimes.com", "eee.straitstimes.com",
                                "prdstaff.straitstimes.com", "staff.straitstimes.com",
                                "articles.stclassifieds.sg"]

# these subdomains contains irrelevant contents for text-based media article scraping
irrelevant_subdomain_names = ["channelnewsasia.com/watch/", "cnaluxury.channelnewsasia.com",
                              "straitstimes.com/multimedia/graphics/", "graphics.straitstimes.com/",
                              "cnalifestyle.channelnewsasia.com/interactives/", "channelnewsasia.com/video",
                              "straitstimes.com/video", "channelnewsasia.com/listen/",
                              "channelnewsasia.com/author", "straitstimes.com/author",
                              "channelnewsasia.com/about-us"]

# articles that are published with only a title, and without any body content and publish date
incomplete_articles = ["https://www.straitstimes.com/singapore/education/ask-sandra-jc-mergers",
                       "https://www.straitstimes.com/business/economy/askst-what-benefits-did-budget-2016-offer-entrepreneurs-and-single-women",
                       "https://www.straitstimes.com/singapore/does-getting-zika-infection-once-confer-immunity",
                       "https://www.straitstimes.com/tags/bhumibol-adulyadej",
                       "https://www.straitstimes.com/askst/steely-stand-off"]

# Test specific webpages with higher priority
TEST_SPECIFIC = False


class CovidNewsSpider(scrapy.Spider):
    name = 'covid_news_spider'

    if TEST_SPECIFIC:
        start_urls = ["https://www.straitstimes.com/singapore/parenting-education/st-smart-parenting-read-more-stories"]

    else:
        start_urls = [
            #'https://web.archive.org/',
            'https://www.straitstimes.com/',
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

    js_script = """
        function main(splash)

            -- Go to page
            splash:go(splash.args.url)

            -- Wait for 5 seconds
            splash:wait(5.0)

            -- Print url
            print("splash:url() = ", splash:url())

            -- Select button
            local close_ads_btn = splash:select('#pclose-btn')
            local expand_btn = splash:select('a.article__read-full-story-button')

            -- Print details
            print("close_ads_btn = ", close_ads_btn:outerHtml())
            print("expand_btn = ", expand_btn:outerHtml())

            -- Click button
            close_ads_btn:mouse_click()
            expand_btn:mouse_click()

            -- Wait 5 seconds
            splash:wait(5.0)

            -- Reload final url
            splash:go(splash:url())

            -- Return HTML after waiting
            return splash:html()

        end
        """

    js_script_test_specific = """
        function main(splash)

            -- Go to page
            splash:go(splash.args.url)

            -- Wait for 5 seconds
            splash:wait(5.0)

            -- Print url
            print("splash:url() = ", splash:url())

            -- Select button
            local close_ads_btn = splash:select('#pclose-btn')
            local expand_btn = splash:select('a.article__read-full-story-button')

            -- Print details
            print("close_ads_btn = ", close_ads_btn:outerHtml())
            print("expand_btn = ", expand_btn:outerHtml())

            -- Click button
            close_ads_btn:mouse_click()
            expand_btn:mouse_click()

            -- Wait 5 seconds
            splash:wait(5.0)

            -- Reload final url
            splash:go(splash:url())

            return {
                url = splash:url(),
                html = splash:html(),
            }

        end
        """

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
                if TEST_SPECIFIC:
                    yield SplashRequest(
                            url,
                            callback=self.get_article_content,
                            meta={'title': None, 'date': None, 'article_url': url},  # Pass additional data here, assigned None here for testing purpose
                            endpoint='execute',  # for closing advertising overlay page to get to desired page
                            args={'lua_source': self.js_script_test_specific,
                                  'lua_source_isolated': False,  # for showing self.js_script print() output
                                  'adblock': True, 'wait': 10, 'resource_timeout': 10},
                            splash_headers={'X-Splash-Render-HTML': 1},  # for non-pure html with javascript
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                        )

                else:
                    yield SplashRequest(
                            url,
                            callback=self.parse,
                            endpoint='execute',  # for closing advertising overlay page to get to desired page
                            args={'lua_source': self.js_script, 'adblock': True, 'wait': 10, 'resource_timeout': 10},
                            splash_headers={'X-Splash-Render-HTML': 1},  # for non-pure html with javascript
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                        )

    def get_next_pages(self, response):
        print("inside get_next_pages(), response.url = ", response.url)

        link = response.url

        # Extract domain name from link
        match = re.search(r'^https?://([\w\.-]+)', link)
        if match:
            domain_name = match.group(1)
            domain_name = domain_name.lstrip('www.')
        else:
            domain_name = None

        if not link or "javascript" in link or "mailto" in link or "whatsapp://" in link or \
            "play.google.com" in link or "apps.apple.com" in link or \
            any(article_url in link for article_url in incomplete_articles) or \
            any(file_extension in link for file_extension in excluded_file_extensions) or \
            any(subdomain_name in link for subdomain_name in irrelevant_subdomain_names) or \
            any(subdomain_name in link for subdomain_name in inaccessible_subdomain_names) or \
            domain_name not in allowed_domain_names:
            # skipping urls
            # This is a workaround to avoid scraping url links inside irrelevant pages redirected from other urls
            print(f"skipped {link} inside get_next_pages()")
            return None

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


    def fix_url(self, url, default_url='https://www.example.com/'):
        # Remove repeated protocols
        url = re.sub(r'^http://link%20to%20microsite%20', '', url)
        url = re.sub(r"https?://https?://", "https://", url)
        url = re.sub(r"https?://\(https?:?//?", "https://", url)
        url = re.sub(r"https?://ttps?//?", "https://", url)
        url = re.sub(r'^http://%22https/', 'https:/', url)
        url = re.sub(r'^https?://www.https?/', 'https://', url)
        url = re.sub(r'^https?://www.straitsthttps?/', 'https://', url)

        # Fix common typo in domain name
        url = re.sub(r"https://ww\.", "https://www.", url)
        url = re.sub(r"https?://www\.\.", "https://www.", url)
        url = re.sub(r'^https?://wwww', 'https://www', url)
        url = re.sub(r"https?://taff\.straitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://wwwf\.straitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://wwwstraitstimes\.com/", "https://www.straitstimes.com/", url)

        if not url.startswith("http"):
            url = urljoin(default_url, url)

        # Removes any whitespace characters
        url = url.strip()

        # If the URL is fine, return it as is
        return url


    def parse(self, response):
        articles = None
        link = response.url
        print("inside parse(), response.url = ", response.url)

        INTERNETARCHIVE_FULL_TEXT = \
            'https://archive.org/stream/' in response.url or \
            'https://archive.org/compress/' in response.url

        # Extract domain name from link
        match = re.search(r'^https?://([\w\.-]+)', link)
        if match:
            domain_name = match.group(1)
            domain_name = domain_name.lstrip('www.')
        else:
            domain_name = None

        if not link or "javascript" in link or "mailto" in link or "whatsapp://" in link or \
            "play.google.com" in link or "apps.apple.com" in link or \
            any(article_url in link for article_url in incomplete_articles) or \
            any(file_extension in link for file_extension in excluded_file_extensions) or \
            any(subdomain_name in link for subdomain_name in irrelevant_subdomain_names) or \
            any(subdomain_name in link for subdomain_name in inaccessible_subdomain_names) or \
            domain_name not in allowed_domain_names:
            # Skip links
            print(f"skipped {link} inside parse() A")

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
            # Fix wrong links that are already wrong at the source
            # For example:
            # https://https://www.domain.com/subdirectory
            # https://ww.domain.com/subdirectory
            # https://https://subdirectory
            print(f"Before fix_url(), link : {link} is of type : {type(link)}")
            link = self.fix_url(link, response.url)
            print(f"After fix_url(), link : {link} is of type : {type(link)}")
            next_pages_url.append(link)

        for next_page_url in next_pages_url:
            if next_page_url:
                link = next_page_url

                # Extract domain name from link
                match = re.search(r'^https?://([\w\.-]+)', link)
                if match:
                    domain_name = match.group(1)
                    domain_name = domain_name.lstrip('www.')
                else:
                    domain_name = None

                if "javascript" in link or "mailto" in link or "whatsapp://" in link or \
                    "play.google.com" in link or "apps.apple.com" in link or \
                    any(article_url in link for article_url in incomplete_articles) or \
                    any(file_extension in link for file_extension in excluded_file_extensions) or \
                    any(subdomain_name in link for subdomain_name in irrelevant_subdomain_names) or \
                    any(subdomain_name in link for subdomain_name in inaccessible_subdomain_names) or \
                    domain_name not in allowed_domain_names:
                    # Skip links
                    print(f"skipped {link} inside parse() B")
                    continue

                print("response.url = ", response.url)
                print("next_page_url = ", next_page_url)

                yield SplashRequest(
                    #response.urljoin(next_page),
                    url=next_page_url,
                    callback=self.parse,
                    #endpoint='render.html',  # for non-pure html with javascript
                    endpoint='execute',  # for closing advertising overlay page to get to desired page
                    args={'lua_source': self.js_script, 'adblock': True, 'wait': 0.5, 'resource_timeout': 10},
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
                    article.css('.h1.h1--page-title::text').get() or \
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
            date = article.css('time::text').get() or \
                    article.css('time::attr(datetime)').get() or \
                    article.css('.story-postdate::text').get()

            link = article.css('a::attr(href)').get()

        elif 'archive.org' in response.url:
            title = article.css('title::text').get()
            date = article.xpath('//meta[@name="date"]/@content').get()

            link = response.css('a.format-summary.download-pill:contains("FULL TEXT")::attr(href)').get()

        else:
            title = None
            date = None
            link = None

        if date:
            date = date.strip()  # to remove unnecessary whitespace or newlines characters

        if link:
            link = self.fix_url(link, response.url)

            # Extract domain name from link
            match = re.search(r'^https?://([\w\.-]+)', link)
            if match:
                domain_name = match.group(1)
                domain_name = domain_name.lstrip('www.')
            else:
                domain_name = None
        else:
            domain_name = None

        print(f"inside parse_article(), parent_url = {response.url} , article_url = {link} , title = {title}, date = {date}")

        if not link or "javascript" in link or "mailto" in link or "whatsapp://" in link or \
            "play.google.com" in link or "apps.apple.com" in link or \
            any(article_url in link for article_url in incomplete_articles) or \
            any(file_extension in link for file_extension in excluded_file_extensions) or \
            any(subdomain_name in link for subdomain_name in irrelevant_subdomain_names) or \
            any(subdomain_name in link for subdomain_name in inaccessible_subdomain_names) or \
            domain_name not in allowed_domain_names:
            # skipping urls
            print(f"skipped {link} inside parse_article()")
            yield None

        else:
            article_url = link

            yield SplashRequest(
                url=article_url,
                callback=self.get_article_content,
                meta={'title': title, 'date': date, 'article_url': article_url},  # Pass additional data here
                #endpoint='render.html',  # for non-pure html with javascript
                endpoint='execute',  # for closing advertising overlay page to get to desired page
                args={'lua_source': self.js_script, 'adblock': True, 'wait': 0.5, 'resource_timeout': 10},
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,      like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            )


    def get_article_content(self, response):
        # retrieves article's detailed title and body properly

        # Access the additional data here
        title = response.meta['title']
        date = response.meta['date']
        article_url = response.meta['article_url']

        link = response.url

        if article_url != link:
            print(f"url redirection occurs from {article_url} to {link}")
            url_had_redirected = True
        else:
            url_had_redirected = False

        # Extract domain name from link
        match = re.search(r'^https?://([\w\.-]+)', link)
        if match:
            domain_name = match.group(1)
            domain_name = domain_name.lstrip('www.')
        else:
            domain_name = None

        if 'channelnewsasia' in response.url:
            body = response.xpath('//p[not(@*)]//descendant-or-self::node()/text()').getall()
            body = '\n'.join(body)

            if date is None:
                date = response.css('.article-publish::text').get() or \
                        response.css('.article-publish span::text').get()

        elif 'straitstimes' in response.url:
            body = response.xpath('//p[not(@*)]/text()').getall()
            body = '\n'.join(body)

            if date is None:
                print("straitstimes date is None !!!")
                date = response.css('.group-story-changedate .story-changeddate::text').get() or \
                        response.css('.group-story-postdate .story-postdate::text').get() or \
                        response.css('div.story-postdate::text').get() or \
                        response.css('.byline::text').get() or \
                        response.css('.st-byline::text').get() or \
                        response.css('time::text').get() or \
                        response.css('time::attr(datetime)').get() or \
                        response.css('.lb24-default-list-item-date::text').get() or \
                        response.css('time[itemprop="datePublished"]::attr(datetime)').get()

                if response.css('.byline::text').get() is not None and 'PUBLISHED: ' in date:
                    date = date.split('PUBLISHED: ')[-1]

                if response.css('.st-byline::text').get() is not None and 'Published: ' in date:
                    date = date.split('Published: ')[-1]

        elif 'archive.org' in response.url:
            body = response.css('div.article p::text').getall() or \
                   response.css('div.text-long').getall() or \
                   response.css('main#maincontent > div.container.container-ia > pre::text').getall()
            body = '\n'.join(body)

        else:
            body = None

        if date:
            date = date.strip()  # to remove unnecessary whitespace or newlines characters

        if not link or "javascript" in link or "mailto" in link or "whatsapp://" in link or \
            "play.google.com" in link or "apps.apple.com" in link or \
            any(article_url in link for article_url in incomplete_articles) or \
            any(file_extension in link for file_extension in excluded_file_extensions) or \
            any(subdomain_name in link for subdomain_name in irrelevant_subdomain_names) or \
            any(subdomain_name in link for subdomain_name in inaccessible_subdomain_names) or \
            domain_name not in allowed_domain_names:
            # skipping urls
            print(f"skipped {link} inside get_article_content()")
            yield None

        else:
            print(f"inside get_article_content(), article_url = {link} , title = {title}, date = {date}, body = {body}")
            # This is an early sign that the current page after url redirection
            # is pointing to a new page containing multiple articles
            # since the scraping css() selector code could not retrieve any date information from article.
            if url_had_redirected and date is None:
                    print(f"going back to parse() for {link}")
                    yield self.parse(response)

            else:
                self.write_to_local_data(link, title, body, date, response)

                yield {
                    'title': title,
                    'link': link,
                    'date': date,
                    'body': body,
                    #'excerpt': article.css('p::text').get(),
                    'source': self.get_source(response)
                }


    def write_to_local_data(self, link, title, body, date, response):
        if "hour ago" in date.lower() or "hours ago" in date.lower() or \
            "min ago" in date.lower() or "mins ago" in date.lower() or \
            "sec ago" in date.lower() or "secs ago" in date.lower():
            published_year = 2023
        else:
            date = parse(date)
            published_year = date.year

        date_is_within_covid_period = published_year >= 2019
        print(f"date = {date}, and published_year = {published_year}, and date_is_within_covid_period = {date_is_within_covid_period}")

        if ((title != None and any(keyword in title.lower() for keyword in search_keywords)) or \
            (body != None and any(keyword in body.lower() for keyword in search_keywords) and \
             any(country in body.lower() for country in search_countries))) and \
            (date_is_within_covid_period):
            # Create a unique filename for each URL by removing the 'http://', replacing '/' with '_', and adding '.html'
            filename = link.replace('http://', '').replace('/', '_') + '.html'
            print("filename = ", filename)

            # Write the entire body of the response to a file
            #with open("/home/phung/covidnews_result/"+filename, 'wb') as f:
            with open(filename, 'wb') as f:
                f.write(body.encode('utf-8'))

        return None

