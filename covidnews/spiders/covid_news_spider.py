# Uses scrapy-splash library (instead of 'requests' library) which gives more functionality and flexibility
import scrapy
from scrapy_splash import SplashRequest
from urllib.parse import urljoin
import re
from urllib.parse import urlparse, urlunparse
from dateutil.parser import parse

import base64
from collections import OrderedDict

# For http://web.archive.org/
import internetarchive
import requests

# For domain name
import tldextract


# Define preferred search keywords
#search_keywords = ['covid','virus','pandemic','vaccine','corona','vaccination','circuit breaker','SARS-CoV-2']
search_keywords = ['covid','pandemic','vaccine','coronavirus','vaccination','SARS-CoV-2']

# Define preferred search country scope
search_country = 'singapore'
#search_country = 'philippines'

# Whether to brute-force search across the entire website hierarchy, due to robots.txt restriction
SEARCH_ENTIRE_WEBSITE = 1

# Whether to skip cdx search
SKIP_CDX = True

# Excludes search URL results that renders the following files extensions
excluded_file_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf", ".xls", ".mp3", ".mp4", ".mov",
                            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".webp", ".webm"]

# Only parses URLs within these domains
if search_country == 'singapore':
    allowed_domain_names = ["straitstimes.com", "channelnewsasia.com"]

elif search_country == 'philippines':
    allowed_domain_names = ["mb.com.ph", "inquirer.net"]


# not accessible due to DNS lookup error or the webpage had since migrated to other subdomains
inaccessible_subdomain_names = ["olympianbuilder.straitstimes.com", "ststaff.straitstimes.com", "media.straitstimes.com",
                                "buildsg2065.straitstimes.com", "origin-stcommunities.straitstimes.com",
                                "stcommunities.straitstimes.com", "euro2016.straitstimes.com",
                                "awsstaff.straitstimes.com", "eee.straitstimes.com",
                                "prdstaff.straitstimes.com", "staff.straitstimes.com",
                                "stompcms.straitstimes.com",
                                "inqshop.inquirer.net", "misc.inquirer.net", "nment.inquirer.net",
                                "inqpop.inquirer.net"
                                ]

# these subdomains contains irrelevant contents for region-based, text-based media article scraping
irrelevant_subdomain_names = ["channelnewsasia.com/watch/", "cnaluxury.channelnewsasia.com",
                              "straitstimes.com/multimedia/", "graphics.straitstimes.com/",
                              "cnalifestyle.channelnewsasia.com/interactives/", "channelnewsasia.com/video",
                              "cnalifestyle.channelnewsasia.com/brandstudio/",
                              "channelnewsasia.com/experiences/", "channelnewsasia.com/dining/",
                              "straitstimes.com/video", "channelnewsasia.com/listen/",
                              "straitstimes.com/world/",
                              "straitstimes.com/asia/east-asia/",
                              "channelnewsasia.com/asia/east-asia/", "channelnewsasia.com/asia/south-asia/",
                              "channelnewsasia.com/world/", "channelnewsasia.com/sport/",
                              "channelnewsasia.com/business", "channelnewsasia.com/entertainment",
                              "channelnewsasia.com/author", "straitstimes.com/author",
                              "channelnewsasia.com/women/",
                              "channelnewsasia.com/about-us",
                              "entertainment.inquirer.net",
                              "mb.com.ph/our-company"]

# articles that are published with only a title, and without any body content and publish date
incomplete_articles = ["https://www.straitstimes.com/singapore/education/ask-sandra-jc-mergers",
                       "https://www.straitstimes.com/business/economy/askst-what-benefits-did-budget-2016-offer-entrepreneurs-and-single-women",
                       "https://www.straitstimes.com/singapore/does-getting-zika-infection-once-confer-immunity",
                       "https://www.straitstimes.com/tags/bhumibol-adulyadej",
                       "https://www.straitstimes.com/askst/steely-stand-off",
                       "https://www.straitstimes.com/singapore/environment/askst-is-it-safe-to-eat-spinach-leaves-which-have-white-spots-on-them",
                       "https://mb.com.ph/rss/articles"
                        ]


# subdomain_1.subdomain_2.domain.com.eu , 3 if excluding subdomains
MAX_NUM_OF_DOMAIN_TEXT = 3

# Test specific webpages with higher priority
TEST_SPECIFIC = False


class CovidNewsSpider(scrapy.Spider):
    name = 'covid_news_spider'

    if TEST_SPECIFIC:
        start_urls = [
                      "https://www.straitstimes.com/singapore/jobs/government-unions-employer-groups-start-work-on-guidelines-on-flexible-work-arrangements",  # title.lower()
                      "https://www.channelnewsasia.com/advertorial/building-global-healthcare-ecosystem-care-good-2943211",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.channelnewsasia.com/remarkableliving/kausmo-educating-singapore-diners-about-food-wastage-1882711",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.straitstimes.com/singapore/fewer-families-received-comcare-financial-aid-from-the-government-last-year",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.channelnewsasia.com/singapore/new-covid-19-variants-uk-south-africa-strains-b117-explainer-416156",  # AttributeError: 'list' object has no attribute 'encode'
                      "https://www.channelnewsasia.com/singapore/mpa-covid-19-10-000-frontline-workers-vaccinations-415726",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.channelnewsasia.com/singapore/covid19-how-to-choose-masks-filtration-bfe-surgical-1382776",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.channelnewsasia.com/singapore/covid-19-locations-visited-queensway-shopping-masjid-assyakirin-712556",  # part of the sentence text is embedded inside images
                      "https://www.straitstimes.com/singapore/changed-forever-by-one-pandemic-is-singapore-ready-for-the-next"  # irrelevant advertisement paragraph text by SPH Media
                     ]

    else:
        if search_country == 'singapore':
            start_urls = [
                #'https://web.archive.org/',
                'https://www.straitstimes.com/',
                'https://www.channelnewsasia.com/'
                #'https://www.channelnewsasia.com/search?q=covid'  # [scrapy.downloadermiddlewares.robotstxt] DEBUG: Forbidden by robots.txt:
                #'https://www.straitstimes.com/search?searchkey=covid'  # Forbidden by https://www.straitstimes.com/robots.txt
            ]

        elif search_country == 'philippines':
            start_urls = [
                #'https://www.pna.gov.ph/',  # webite server seems to block scraping activity
                #'https://www.manilatimes.net/search?query=covid',  # forbidden by the /search rule in robots.txt
                #'https://www.manilatimes.net/',  # almost all articles requires digital subscription fees
                #'https://mb.com.ph/search-results?s=covid',  # splash is not working yet
                'https://www.inquirer.net/'
            ]


    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            #'scrapy_splash.SplashCookiesMiddleware': 723,
            #'scrapy_splash.SplashMiddleware': 725,
            'covidnews.middlewares.GzipRetryMiddleware': 543,
            'covidnews.middlewares.ForgivingHttpCompressionMiddleware': 810,
        },

        'SPIDER_MIDDLEWARES': {
            #'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
    }

    js_script = """
        function main(splash, args)

            -- Go to page
            splash:go(splash.args.url)

            -- Wait for 7 seconds
            splash:wait(7.0)

            -- Print url
            print("splash:url() = ", splash:url())

            -- Return HTML after waiting
            return splash:html()

        end
        """

    js_script_test_specific = """
        function main(splash, args)

            -- Go to page
            splash:go(splash.args.url)

            -- Wait for 7 seconds
            splash:wait(7.0)

            -- Print url
            print("splash:url() = ", splash:url())

            -- for visual debugging purpose
            splash:set_viewport_full()
            local png = splash:png()

            return {
                url = splash:url(),
                png = png,
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
                                  'adblock': True,
                                  'wait': 10,
                                  'resource_timeout': 10,
                                  'timeout': 60  # limit the total time the Lua script can run (optional)
                                 },
                            splash_headers={'X-Splash-Render-HTML': 1},  # for non-pure html with javascript
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                        )

                else:
                    yield SplashRequest(
                            url,
                            callback=self.parse,
                            endpoint='execute',  # for closing advertising overlay page to get to desired page
                            args={'lua_source': self.js_script,
                                  'lua_source_isolated': False,  # for showing self.js_script print() output
                                  'adblock': True,
                                  'wait': 10,
                                  'resource_timeout': 10,
                                  'timeout': 60  # limit the total time the Lua script can run (optional)
                                 },
                            splash_headers={'X-Splash-Render-HTML': 1},  # for non-pure html with javascript
                            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                        )


    def extract_domain_name(self, link):
        extracted = tldextract.extract(link)

        # Concatenates the domain and the suffix (TLD)
        domain_name = f"{extracted.domain}.{extracted.suffix}"
        return domain_name


    def get_next_pages(self, response):
        print("inside get_next_pages(), response.url = ", response.url)

        link = response.url.lower()

        domain_name = self.extract_domain_name(link)

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

        elif 'inquirer.net' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'mb.com.ph' in response.url:
            if SEARCH_ENTIRE_WEBSITE:
                more_links = response.css('a::attr(href)').getall()
            else:
                # need to figure out how to click the "MORE+" button, and then execute the css() selector code again
                #more_links = response.css('.mb-font-more-button::text').get()
                return None

        elif 'archive.org' in response.url:
            more_links = response.css('a.format-summary:contains("FULL TEXT")::attr(href)').getall()

        else:
            more_links = None

        #print("more_links = ", more_links)
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
        url = re.sub(r"^tps?://", "https://", url)
        url = re.sub(r"^ps?://", "https://", url)
        url = re.sub(r"^s?://", "https://", url)
        url = re.sub(r"^vhttps?://", "https://", url)
        url = re.sub(r"^xhttps?://", "https://", url)
        url = re.sub(r"^ttps?://", "https://", url)
        url = re.sub(r"https://ww\.", "https://www.", url)
        url = re.sub(r"https?://www\.\.", "https://www.", url)
        url = re.sub(r'^https?://wwww', 'https://www', url)
        url = re.sub(r"https?://taff\.straitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://wwwf\.straitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://wwwstraitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://lifestyle\.inq@inquirer\.net", "https://lifestyle.inquirer.net", url)
        url = re.sub(r"https?://usiness\.inquirer\.net", "https://business.inquirer.net", url)

        if not url.startswith("http"):
            url = urljoin(default_url, url)

        # Removes any whitespace characters
        url = url.strip()

        # If the URL is fine, return it as is
        return url


    def parse(self, response):
        articles = None
        link = response.url.lower()
        print("inside parse(), response.url = ", response.url)

        INTERNETARCHIVE_FULL_TEXT = \
            'https://archive.org/stream/' in response.url or \
            'https://archive.org/compress/' in response.url

        domain_name = self.extract_domain_name(link)

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
            #print("articles = ", articles)

        if articles is not None:
            articles = list(articles)
        else:
            articles = []

        print(f"len(articles) = {len(articles)}")

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
            #print(f"Before fix_url(), link : {link} is of type : {type(link)}")
            link = self.fix_url(link, response.url)
            #print(f"After fix_url(), link : {link} is of type : {type(link)}")
            next_pages_url.append(link)

        for next_page_url in next_pages_url:
            if next_page_url:
                link = next_page_url.lower()
                domain_name = self.extract_domain_name(link)

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

                #print("response.url = ", response.url)
                #print("next_page_url = ", next_page_url)

                yield SplashRequest(
                    #response.urljoin(next_page),
                    url=next_page_url,
                    callback=self.parse,
                    #endpoint='render.html',  # for non-pure html with javascript
                    endpoint='execute',  # for closing advertising overlay page to get to desired page
                    args={'lua_source': self.js_script,
                          'lua_source_isolated': False,  # for showing self.js_script print() output
                          'adblock': True,
                          'wait': 10,
                          'resource_timeout': 10,
                          'timeout': 60  # limit the total time the Lua script can run (optional)
                         },
                    splash_headers={'X-Splash-Render-HTML': 1},  # for non-pure html with javascript
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

        elif 'inquirer.net' in response.url:
            print("parse_articles() for inquirer.net")

            if response.url == 'https://cebudailynews.inquirer.net/':

                body = response.css('*').getall()

                if body:
                    body = [s.strip() for s in body]
                    body = '\n'.join(body)
                    body = body.strip()

                    body = self.remove_photograph_credit(body)
                    body = self.remove_footnote(body)


                # Write the scraped html response to local file for debugging purpose
                self.write_to_local_data(
                                            link = response.url,
                                            title = 'cebudailynews_inquirer_net_debug',
                                            body = body,
                                            date = '1 October 2020',
                                            response = response,
                                        )

            return response.css('.flx-leftbox, .flx-m-box, #tr_boxs3, #fv-ed-box, #op-columns-box, .image-with-text, #buzz-box, #inqf-box, div[data-tb-region-item], div.items[data-tb-region-item], #cmr-bg, #cmr-box, #ncg-box, #cdn-col-box, #cdn-g-box, .list-head, #trend_title, #usa-add-gallery > a, #cdn-cat-wrap > a, #ch-ls-head')

        elif 'mb.com.ph' in response.url:
            print("parse_articles() for mb.com.ph")

            if response.url == 'https://mb.com.ph/category/specials':

                body = response.css('*').getall()

                if body:
                    body = [s.strip() for s in body]
                    body = '\n'.join(body)
                    body = body.strip()

                    body = self.remove_photograph_credit(body)
                    body = self.remove_footnote(body)


                # Write the scraped html response to local file for debugging purpose
                self.write_to_local_data(
                                            link = response.url,
                                            title = 'manila_bulletin_debug',
                                            body = body,
                                            date = '1 October 2020',
                                            response = response,
                                        )

            return response.css('div.row.mb-16, div.row.mb-5, .custom-article-text, .mb-font-article-title, .mb-font-live-update-article-title, div.videoCube.trc_spotlight_item.origin-undefined')

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
        elif 'mb.com.ph' in response.url:
            return 'MB'
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
            title = article.css('h5.card-title a::text').get() or \
                    article.css('.node-header.h1::text').get()
            date = article.css('time::text').get() or \
                    article.css('time::attr(datetime)').get() or \
                    article.css('.story-postdate::text').get()

            link = article.css('a::attr(href)').get()

        elif 'inquirer.net' in response.url:
            title = article.css('.flx-m-head::text, .flx-l-head::text, #tr_boxs3 h2 a::text, #inqf-info h2::text, #fv-ed-box h2 a::text, #buzz-info h2::text, div.items[data-tb-region-item] h3 a::text, div[data-tb-region-item] h3 a::text, #cmr-info h1 a::text, #cmr-info h2 a::text, #cmr-info h2::text, #ncg-info h1 a::text, #cgb-head h1::text, #cdn-col-box h2 a::text, #cdn-cat-box h2::text, #cat-info h2::text, .list-head a::text, #trend_title h2 a::text, h1.entry-title::text, #ch-ls-head h2 a::text').get()
            date = article.css('#tr_boxs3 h6 ::text').get() or \
                    article.css('#cmr-info h3::text').get() or \
                    article.css('#ch-ls-head #ch-postdate span:first-child::text').get() or \
                    article.css('#ncg-info #ncg-postdate::text').get() or \
                    article.css('#cdn-col-box #col-post-date::text').get() or \
                    article.css('#cat-info #cat-pt::text').get() or \
                    article.css('#cdn-cat-box #cb-pt::text').get() or \
                    article.css('#trend_title h3::text').get() or \
                    article.css('div[data-tb-region-item] h4::text').get() or \
                    article.css('div.items[data-tb-region-item] h4::text').get()

            # Get onclick url
            onclick_url = response.css('#cmr-box::attr(onclick)').get()

            # Extract url from onclick attribute
            if onclick_url:
                link = re.search(r"window.open\('(.*?)'", onclick_url).group(1)
            else:
                link = article.css('a::attr(href)').get() or \
                        article.css('#cgb-head h1::attr(data-vr-contentbox-url)').get()


        elif 'mb.com.ph' in response.url:
            title = article.css('.mb-font-article-title a::text').get() or \
                    article.css('div.mb-font-article-title a span::text').get() or \
                    article.css('span.mb-font-live-update-article-title::attr(title)').get()
            date = article.css('.mb-font-article-date::text').get()

            link = article.css('a::attr(href)').get()

        elif 'archive.org' in response.url:
            title = article.css('title::text').get()
            date = article.xpath('//meta[@name="date"]/@content').get()

            link = response.css('a.format-summary.download-pill:contains("FULL TEXT")::attr(href)').get()

        else:
            title = None
            date = None
            link = None

        if title:
            title = title.strip()  # to remove unnecessary whitespace or newlines characters

        if date:
            date = date.strip()  # to remove unnecessary whitespace or newlines characters

        if link:
            link = self.fix_url(link, response.url)
            link = link.lower()
            domain_name = self.extract_domain_name(link)
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
            print("departing to get_article_content()")

            yield SplashRequest(
                url=article_url,
                callback=self.get_article_content,
                meta={'title': title, 'date': date, 'article_url': article_url},  # Pass additional data here
                #endpoint='render.html',  # for non-pure html with javascript
                endpoint='execute',  # for closing advertising overlay page to get to desired page
                args={'lua_source': self.js_script,
                      'lua_source_isolated': False,  # for showing self.js_script print() output
                      'adblock': True,
                      'wait': 10,
                      'resource_timeout': 10,
                      'timeout': 60  # limit the total time the Lua script can run (optional)
                     },
                splash_headers={'X-Splash-Render-HTML': 1},  # for non-pure html with javascript
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,      like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            )


    def remove_photograph_credit(self, text):
        text = re.sub(r"\(Image: .+?\)", "", text)
        text = re.sub(r"\(Photo: .+?\)", "", text)
        text = re.sub(r"\(Photo by .+?\)", "", text)
        text = re.sub(r"\(AP Photo.+?\)", "", text)
        text = re.sub(r"\(File photo: .+?\)", "", text)
        text = re.sub(r"File photo of .+?", "", text)
        text = re.sub(r"FILE PHOTO: .+?File Photo", "", text)
        return text


    def remove_footnote(self, text, window_size=3):
        # cleans up some strange character
        text = text.replace('\xa0', ' ')

        # splits into multiple tokens using newline characters
        lines = text.split('\n')
        lines = [l.strip() for l in lines]

        # list of phrases to search for
        search_phrases = [
            "join st's telegram channel",
            "join st's whatsapp channel",
            "download our app",
            "read this story in",
            "is an editor at",
            "is a journalist at",
            "is a journalist based in",
            "is a senior journalist at",
            "is associate fellow",
            "is a phd candidate",
            "is a doctoral candidate",
            "is Research Fellow",
            "is Associate Professor",
            "is Professor",
            "is a lecturer",
            "is a senior lecturer",
            "is President of",
            "Editor's note",
            "this article originally appear",
            "© The New York Times",
            "© 2023 the new york times",
            "© The Financial Times",
            "© 2021 The Financial Times",
            "© 2022 The Financial Times",
            "© 2023 The Financial Times",
            "(Source: AP)",
            "catch the olympics games",
            "cna women is a section on cna",
            "Write to us at",
            "Subscribe to",
            "copyright© mediacorp 2023"
        ]

        # Initialize an empty buffer
        buffer = []

        for i, line in enumerate(lines):
            # add line to buffer
            buffer.append(line)

            # ensure buffer doesn't exceed window size
            if len(buffer) > window_size:
                buffer.pop(0)

            #print(f"inside remove_footnote(), buffer = {buffer}, i = {i}")

            # Check if phrases are in the buffer
            buffer_string = ' '.join(buffer).lower()

            for phrase in search_phrases:
                phrase = phrase.lower()

                if phrase in buffer_string:
                    # Find the position of the phrase in the buffer string
                    phrase_start = buffer_string.find(phrase)
                    phrase_end = phrase_start + len(phrase)
                    #print(f"inside remove_footnote(), phrase_start = {phrase_start}, phrase_end = {phrase_end}")

                    # Determine which lines those positions correspond to in the buffer
                    line_lengths = [len(line) + 1 for line in buffer]  # +1 for '\n'
                    line_start_positions = [sum(line_lengths[:i]) for i in range(len(buffer))]
                    line_end_positions = [sum(line_lengths[:i+1]) for i in range(len(buffer))]
                    #print(f"inside remove_footnote(), line_lengths = {line_lengths}, line_start_positions = {line_start_positions}, line_end_positions = {line_end_positions}")

                    # Remove all lines that are part of the phrase
                    for start, end in reversed(list(zip(line_start_positions, line_end_positions))):
                        if start <= phrase_start < end or start < phrase_end <= end:
                            if buffer:  # Check if buffer is not empty before popping
                                buffer.pop(line_start_positions.index(start))
                                #print(f"inside remove_footnote(), after pop(), buffer = {buffer}")
                            else:
                                break

                        else:
                            # Replace lines in the original text with the modified buffer
                            #print(f"inside remove_footnote(), before cleaning the footnote phrase, lines[{i-window_size+1}:{i-window_size+len(buffer)+1}] = {lines[i-window_size:i-window_size+len(buffer)+1]}")
                            lines[i-window_size+1:i-window_size+len(buffer)+1] = buffer
                            #print(f"inside remove_footnote(), after cleaning the footnote phrase, lines[{i-window_size+1}:{i-window_size+len(buffer)+1}] = {lines[i-window_size+1:i-window_size+len(buffer)+1]}")

                            # Remove all subsequent text after footnote phrase
                            #print(f"inside remove_footnote(), before cleaning the subsequent text, lines[{i-window_size+len(buffer)+1}:] = {lines[i-window_size+len(buffer)+1:]}")
                            lines[i-window_size+len(buffer)+1:] = ''
                            #print(f"inside remove_footnote(), after cleaning the subsequent text, lines[{i-window_size+len(buffer)+1}:] = {lines[i-window_size+len(buffer)+1:]}")

                            # Join the lines back into a single string
                            cleaned_text = "\n".join(lines)
                            #print(f"inside remove_footnote(), cleaned_text = {cleaned_text}")
                            return self.remove_footnote(cleaned_text)  # to make sure ALL footnote phrases are removed completely

        # return the original text if no footnote was found
        return text


    def get_article_content(self, response):
        # retrieves article's detailed title and body properly
        print("arrived at get_article_content()")
        # Access the additional data here
        title = response.meta['title']
        date = response.meta['date']
        article_url = response.meta['article_url']

        link = response.url.lower()
        domain_name = self.extract_domain_name(link)

        if article_url != link:
            print(f"url redirection occurs from {article_url} to {link}")
            url_had_redirected = True
        else:
            url_had_redirected = False

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
            if 'channelnewsasia' in response.url:
                body = response.xpath('//blockquote//p//text() | //p[not(@*) and not(ancestor::figcaption)]/descendant-or-self::node()/text() | //ul/li[not(@*)]/span[not(@*)]/span[not(@*)]/text()').getall()
                if date is None:
                    date = response.css('.article-publish::text').get() or \
                            response.css('.article-publish span::text').get()

            elif 'straitstimes' in response.url:
                #body = response.css('p ::text, h2:not(.visually-hidden) ::text').getall()
                body = response.xpath('//p[not(ancestor::blockquote[contains(@class, "instagram-media")]) and not(ancestor::div[contains(@class, "fb-post")])]//text() | //h2[not(contains(@class, "visually-hidden"))]/text()').getall()

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

            elif 'inquirer.net' in response.url:
                print("get_article_content for inquirer")
                if title is None:
                    title = response.css('h1.entry-title::text, h1[class="elementor-heading-title elementor-size-default"]::text, div[id="landing-headline"] h1::text, div[class="single-post-banner-inner"] h1::text').get()

                body = response.css('p ::text').getall()

                if date is None:
                    print("inquirer.net date is None !!!")

                    # sometimes there could a meaningless <span> with a single text character
                    if response.css('div#m-pd2 > span:nth-child(2)::text').get() and len(response.css('div#m-pd2 > span:nth-child(2)::text').get()) > 1:
                        date = response.css('div#m-pd2 > span:nth-child(2)::text').get()
                    elif response.css('div#m-pd2 > span:nth-child(3)::text').get() and len(response.css('div#m-pd2 > span:nth-child(3)::text').get()) > 1:
                        date = response.css('div#m-pd2 > span:nth-child(3)::text').get()

                    date = date or \
                            response.css('div.art-byline span:last-child::text').get() or \
                            response.css('ul.blog-meta-list > li:nth-child(3) a::text').get() or \
                            response.css('div.bpdate::text').get() or \
                            response.css('li[itemprop="datePublished"] span::text').get() or \
                            response.css('div[id="art_plat"]::text').getall()[-1]

            elif 'mb.com.ph' in response.url:
                body = response.css('p ::text').getall()
                if date is None:
                    print("mb.com.ph date is None !!!")
                    date = response.css('.mb-font-article-date::text').get()

            elif 'archive.org' in response.url:
                body = response.css('div.article p::text').getall() or \
                       response.css('div.text-long').getall() or \
                       response.css('main#maincontent > div.container.container-ia > pre::text').getall()

            else:
                body = None


            if body:
                body = [s.strip() for s in body]
                body = '\n'.join(body)
                body = body.strip()

                body = self.remove_photograph_credit(body)
                body = self.remove_footnote(body)

            if date:
                date = ''.join(c for c in date if c.isprintable())  # to remove erroneous non-ASCII printable character
                date = date.strip()  # to remove unnecessary whitespace or newlines characters

            print(f"inside get_article_content(), article_url = {link} , title = {title}, date = {date}, body = {body}")
            # This is an early sign that the current page after url redirection
            # is pointing to a new page containing multiple articles
            if url_had_redirected and self.parse_articles(response) is not None:
                    print(f"going back to parse() for {link}")
                    yield self.parse(response)

            else:
                self.write_to_local_data(link, title, body, date, response)

                # for the purpose of debugging js_script_test_specific
                if TEST_SPECIFIC:
                    print(f"for debug, type(response) = {type(response)}")

                    # The webpage HTML is in data['html']
                    html = response.data['html']

                    # The screenshot is in data['png']
                    png = response.data['png']

                    # You can now save the debug screenshot to a file, like so:
                    file_parent_directory = ''
                    filename = file_parent_directory + link.replace('http://', '').replace('/', '_') + '_screenshot.png'
                    print("filename = ", filename)
                    with open(filename, 'wb') as f:
                        f.write(base64.b64decode(png))

                yield {
                    'title': title,
                    'link': link,
                    'date': date,
                    'body': body,
                    #'excerpt': article.css('p::text').get(),
                    'source': self.get_source(response)
                }


    def write_to_local_data(self, link, title, body, date, response):
        if "day ago" in date.lower() or "days ago" in date.lower() or \
            "hour ago" in date.lower() or "hours ago" in date.lower() or \
            "minute ago" in date.lower() or "minutes ago" in date.lower() or \
            "min ago" in date.lower() or "mins ago" in date.lower() or \
            "second ago" in date.lower() or "seconds ago" in date.lower() or \
            "sec ago" in date.lower() or "secs ago" in date.lower():
            published_year = 2023
        else:
            date = parse(date)
            published_year = date.year


        if TEST_SPECIFIC:
            date_is_within_covid_period = published_year >= 2019
        else:
            # Jan 2020 till Jan 2022
            date_is_within_covid_period = ((published_year >= 2020) and (published_year <= 2021))

        print(f"date = {date}, and published_year = {published_year}, and date_is_within_covid_period = {date_is_within_covid_period}")

        if ((title != None and any(keyword in title.lower() for keyword in search_keywords)) or \
            (body != None and any(keyword in body.lower() for keyword in search_keywords))) and \
            (date_is_within_covid_period):
            # Create a unique filename for each URL by removing the 'http://', replacing '/' with '_', and adding '.html'
            file_parent_directory = ''
            filename = file_parent_directory + link.replace('http://', '').replace('/', '_') + '.html'
            print("filename = ", filename)

            # Write the entire body of the response to a file
            with open(filename, 'wb') as f:
                f.write(body.encode('utf-8'))

        return None

