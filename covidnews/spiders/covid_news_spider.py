# Uses scrapy-splash library (instead of 'requests' library) which gives more functionality and flexibility
import scrapy
from scrapy_splash import SplashRequest
from urllib.parse import urljoin
import re
from urllib.parse import urlparse, urlunparse
from dateutil.parser import parse

import base64
from collections import OrderedDict
from parsel import Selector
from bs4 import BeautifulSoup

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
excluded_file_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf", ".xls", ".mp3", ".mp4", ".mov", ".flv",
                            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".webp", ".webm", ".m4v"]

# Only parses URLs within these domains
if search_country == 'singapore':
    allowed_domain_names = ["straitstimes.com", "channelnewsasia.com"]

elif search_country == 'philippines':
    allowed_domain_names = ["mb.com.ph", "inquirer.net"]

elif search_country == 'malaysia':
    allowed_domain_names = ["nst.com.my", "thestar.com.my"]


# not accessible due to DNS lookup error or the webpage had since migrated to other subdomains
inaccessible_subdomain_names = ["olympianbuilder.straitstimes.com", "ststaff.straitstimes.com", "media.straitstimes.com",
                                "buildsg2065.straitstimes.com", "origin-stcommunities.straitstimes.com",
                                "stcommunities.straitstimes.com", "euro2016.straitstimes.com",
                                "awsstaff.straitstimes.com", "eee.straitstimes.com",
                                "prdstaff.straitstimes.com", "staff.straitstimes.com",
                                "stompcms.straitstimes.com",
                                "news.mb.com.ph",
                                "inqshop.inquirer.net", "misc.inquirer.net", "nment.inquirer.net",
                                "inqpop.inquirer.net", "newyorktimes.inquirer.net", "showbizandstyle.inquirer.net",
                                "vouchers.inquirer.net", "blogs.inquirer.net", "apec.inquirer.net",
                                "newsinafo.inquirer.net", "yass.inquirer.net", "yasss.inquirer.net"
                                ]

# these subdomains contains irrelevant contents for region-based, text-based media article scraping
irrelevant_subdomain_names = ["channelnewsasia.com/watch/", "cnaluxury.channelnewsasia.com",
                              "straitstimes.com/multimedia/", "graphics.straitstimes.com/",
                              "cnalifestyle.channelnewsasia.com/interactives/", "channelnewsasia.com/video",
                              "cnalifestyle.channelnewsasia.com/brandstudio/",
                              "channelnewsasia.com/experiences/", "channelnewsasia.com/dining/",
                              "straitstimes.com/video", "channelnewsasia.com/listen/",
                              "straitstimes.com/sport/", "straitstimes.com/business/",
                              "straitstimes.com/world/",
                              "straitstimes.com/life/", "straitstimes.com/lifestyle/entertainment/",
                              "straitstimes.com/asia/east-asia/", "ge2015social.straitstimes.com",
                              "channelnewsasia.com/asia/east-asia/", "channelnewsasia.com/asia/south-asia/",
                              "channelnewsasia.com/world/", "channelnewsasia.com/sport/",
                              "channelnewsasia.com/business", "channelnewsasia.com/entertainment",
                              "channelnewsasia.com/author", "straitstimes.com/author",
                              "channelnewsasia.com/women/",
                              "channelnewsasia.com/about-us",
                              "entertainment.inquirer.net", "business.inquirer.net", "opinion.inquirer.net",
                              "sports.inquirer.net", "technology.inquirer.net", "usa.inquirer.net",
                              "pop.inquirer.net", "inquirer.net/inqpop", "lifestyle.inquirer.net",
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
                      "https://opinion.inquirer.net/",  # date is None
                      "https://business.inquirer.net/column/for-laws-sake",  # date is None
                      "https://lifestyle.inquirer.net/478043/bounty-fresh-chickens-chicky-stars-in-bgcs-3d-billboard/",  # dateutil.parser._parser.ParserError: Unknown string format: lifestyle
                      "https://technology.inquirer.net/126933/how-to-use-free-chatgpt-custom-instructions",  # dateutil.parser._parser.ParserError: String does not contain a date:
                      "https://technology.inquirer.net/126943/gptbot-web-crawler",  # dateutil.parser._parser.ParserError: String does not contain a date
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

        elif search_country == 'malaysia':
            start_urls = [
                'https://www.nst.com.my/',
                'https://www.thestar.com.my/'
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

    if TEST_SPECIFIC:

        js_script = """
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

    else:

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
            #print(f"skipped {link} inside get_next_pages()")
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

        elif 'nst.com.my' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'thestar.com.my' in response.url:
            more_links = response.css('a::attr(href)').getall()

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
        url = re.sub(r'^https?https?://', 'https://', url)
        url = re.sub(r'^https?://www.https?/', 'https://', url)
        url = re.sub(r'^https?://www.straitsthttps?/', 'https://', url)

        # Fix common typo in domain name
        url = re.sub(r"^htps?://", "https://", url)
        url = re.sub(r"^tps?://", "https://", url)
        url = re.sub(r"^ps?://", "https://", url)
        url = re.sub(r"^s?://", "https://", url)
        url = re.sub(r"^.*https?://", "https://", url)
        url = re.sub(r"^ttps?://", "https://", url)
        url = re.sub(r"https://ww\.", "https://www.", url)
        url = re.sub(r"https?://www\.\.", "https://www.", url)
        url = re.sub(r'^https?://wwww', 'https://www', url)
        url = re.sub(r"https?://taff\.straitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://wwwf\.straitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://wwwstraitstimes\.com/", "https://www.straitstimes.com/", url)
        url = re.sub(r"https?://lifestyle\.inq@inquirer\.net", "https://lifestyle.inquirer.net", url)
        url = re.sub(r"https?://usiness\.inquirer\.net", "https://business.inquirer.net", url)
        url = re.sub(r"https?://ebudailynews\.inquirer\.net", "https://cebudailynews.inquirer.net", url)
        url = re.sub(r"https?://www\.bandera\.inquirer\.net", "https://bandera.inquirer.net", url)
        url = re.sub(r"https?://www\.newsinfo\.inquirer\.net", "https://newsinfo.inquirer.net", url)
        url = re.sub(r"https?://nwsinfo\.inquirer\.net", "https://newsinfo.inquirer.net", url)
        url = re.sub(r"https?://www\.cebudailynews\.inquirer\.net", "https://cebudailynews.inquirer.net", url)

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
            #print(f"skipped {link} inside parse() A")
            pass

        else:
            if not INTERNETARCHIVE_FULL_TEXT:
                articles = self.parse_articles(response)
            #print("articles = ", articles)

        if articles is not None:
            articles = list(articles)
        else:
            articles = []

        print(f"len(articles) = {len(articles)}")

        if TEST_SPECIFIC and response.url in self.start_urls:
            yield from self.parse_article(response.css('*'), response)

        else:
            for article in articles:
                yield from self.parse_article(article, response)

        next_pages = None

        if not INTERNETARCHIVE_FULL_TEXT and not TEST_SPECIFIC:
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
                    #print(f"skipped {link} inside parse() B")
                    continue

                else:
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

            return response.css('.flx-leftbox, .flx-m-box, #tr_boxs3, #fv-ed-box, #op-columns-box, .image-with-text, #buzz-box, #inqf-box, div[data-tb-region-item]:not(#fview-cap), div.items[data-tb-region-item], #cmr-bg, #cmr-box, #ncg-box, #cdn-col-box, #cdn-g-box, .list-head, #trend_title, #usa-add-gallery > a, #cdn-cat-wrap > a, #op-sec h3, #ch-ls-head')

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

        elif 'nst.com.my' in response.url:
            print("parse_articles() for nst.com.my")
            return response.css(
                    'div.row.mb-4 div.col-md-4.col-lg-3.order-2.order-sm-1.mb-4.mb-sm-0 div.mb-4, \
                    div.row.mb-4 div.col-md-4.col-lg-3.order-2.order-sm-1.mb-4.mb-sm-0 div div.block.block-article-image-row-listing, \
                    \
                    div.block.block-breaking-news div.d-flex.mb-3, \
                    div.block.block-breaking-news div.row div.col-12.col-sm.mb-4.mb-sm-0, \
                    div.block.block-breaking-news div.row div.col.col-sm.align-items-center.article-listing div.d-flex.flex-column.h-100.justify-content-between a.d-flex.article.listing.mb-2, \
                    \
                    div.most-popular.block div#__BVID__12.tabs div#__BVID__12__BV_tab_container_.tab-content.pt-2 div#__BVID__13.tab-pane.active div.timeline.pt-3 ul li.d-flex.pb-3, \
                    div.most-popular.block div#__BVID__12.tabs div#__BVID__12__BV_tab_container_.tab-content.pt-2 div#__BVID__15.tab-pane.active div.ranked-listing div.ranked-item.d-flex.px-3.pb-2.mb-2.align-items-center.timeline, \
                    div.most-popular.block div#__BVID__8.tabs div#__BVID__8__BV_tab_container_.tab-content.pt-2 div#__BVID__11.tab-pane.active div.ranked-listing div.ranked-item.d-flex.px-3.pb-2.mb-2.align-items-center.timeline, \
                    div.most-popular.block div#__BVID__8.tabs div#__BVID__8__BV_tab_container_.tab-content.pt-2 div#__BVID__9.tab-pane.active div.timeline.pt-3 ul li.d-flex.pb-3, \
                    div.most-popular.block div#__BVID__8.tabs div#__BVID__8__BV_tab_container_.tab-content.pt-2 div#__BVID__9.tab-pane.active div.timeline.pt-3 ul li.d-flex.pb-4, \
                    \
                    div.block.block-opinions div.row div.col-12.col-sm.mb-4.mb-sm-0, \
                    div.owl-stage div.owl-item.cloned, \
                    div.owl-stage div.owl-item.active, \
                    div.owl-stage div.owl-item.cloned.active, \
                    div.owl-stage div.owl-item, \
                    \
                    div.block.block-left-featured-right-listing div.row.no-gutter div.col-12.col-lg a, \
                    div.block.block-left-featured-right-listing div.row.no-gutter div.col-12.col-lg div.inner-wrapper.h-100.p-3.d-flex.flex-column.justify-content-between a.d-flex.article.listing.mb-2, \
                    div.col-12.col-lg.article-listing div.inner-wrapper.h-100.p-3.d-flex.flex-column.justify-content-between a.d-flex.article.listing.mb-2, \
                    div.col-12.col-lg div.inner-wrapper.h-100.p-3.d-flex.flex-column.justify-content-between a.d-flex.article.listing.mb-2, \
                    \
                    div.article-listing div.article-teaser, \
                    div#trending-block.block.my-4 div.block-content.d-block.position-relative a.d-flex.article.listing.mb-2.pb-2.border-bottom, \
                    \
                    div.block.block-single-listing, \
                    div.collection-listing-latest div.latest-featured div.row, \
                    div.collection-listing-latest div.latest-listing.mt-4 div.row div.col-12.col-sm.mb-3.mb-sm-0'
            )

        elif 'thestar.com.my' in response.url:
            print("parse_articles() for thestar.com.my")
            return response.css(
                    'div.content.main-desktop-headline, \
                    div.content > u1 > li, \
                    div.col-sm-3.in-sec-story, \
                    div.row.story-set div.col-xs-12.col-sm-3.mob-bot-20, \
                    div.col-sm-6.in-sec-story, \
                    ul#MoreNews-Second.story-set.col-sm-4.col-md-3 li.row.hidden-visual, \
                    div.row.list-listing, \
                    ul#justInListing.timeline.vTicker li, \
                    div.focus section.latest-news div.sub-section-list div.row.list-listing, \
                    div.featuredDiv div.focus-story div.row div div.col-xs-12.col-sm-4.featuredContent, \
                    div.row ul.story-set.col-sm-3.story3 li.row.hidden-visual, \
                    div.story-set-group.story2 div.col-sm-6.in-sec-story div.row div.col-xs-7.left.col-sm-12, \
                    div#section1.story-set-group div.col-sm-3.in-sec-story div.row div.col-xs-7.left.col-sm-12, \
                    div#section2.sub-section-list div.row.list-listing div.col-xs-7.col-sm-9, \
                    div.timeline-content, \
                    div#story-recom-list.desc-wrap div.desc div.col-xs-7.col-sm-9.col-md-7.left, \
                    div#divOpinionWidget section.side-combo-2 div.desc-wrap div.row.desc div.col-xs-9.col-sm-10.right, \
                    div.focus-story.focus-lifestyle div.row div.col-xs-12.col-sm-4, \
                    div.sub-section-list.story-set-lifestyle div.col-xs-12.col-sm-6.bot-20.lifemain div.row div.col-xs-12.left, \
                    div#story-recom-list.desc-wrap div.desc, div.row.panel-content'
            )

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
        elif 'inquirer.net' in response.url:
            return 'INQ'
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
            title = article.css('.flx-m-head::text, .flx-l-head::text, #tr_boxs3 h2 a::text, #inqf-info h2::text, #fv-ed-box h2 a::text, #buzz-info h2::text, div.items[data-tb-region-item] h3 a::text, div[data-tb-region-item] h3 a::text, #cmr-info h1 a::text, #cmr-info h2 a::text, #cmr-info h2::text, #ncg-info h1 a::text, #cgb-head h1::text, #cdn-col-box h2 a::text, #cdn-cat-box h2::text, #cat-info h2::text, .list-head a::text, #trend_title a::text, #trend_title h2 a::text, h1.entry-title::text, #ch-ls-head h2 a::text, #op-sec h3 a::text').get()
            date = article.css('.elementor-post-info__item--type-date::text').get() or \
                    article.css('#tr_boxs3 h6 ::text').get() or \
                    article.css('#cmr-info h3::text').get() or \
                    article.css('#ch-ls-head #ch-postdate span:first-child::text').get() or \
                    article.css('#cdn-col-box #col-post-date::text').get() or \
                    article.css('#cat-info #cat-pt::text').get() or \
                    article.css('#cdn-cat-box #cb-pt::text').get() or \
                    article.css('#trend_title h3::text').get() or \
                    article.css('div[data-tb-region-item] h4::text').get() or \
                    article.css('div.items[data-tb-region-item] h4::text').get()

            if date is None and article.css('#ncg-info #ncg-postdate::text').get() and not article.css('#ncg-info #ncg-postdate::text').get().isspace():
                date = date or article.css('#ncg-info #ncg-postdate::text').get()

            link = None  # just for initialization

            # Get onclick url
            onclick_url = response.css('#cmr-box::attr(onclick)').get()

            # Extract url from onclick attribute
            if onclick_url:
                link = re.search(r"window.open\('(.*?)'", onclick_url).group(1)

            if article.css('a::attr(href)').get() and not article.css('a::attr(href)').get().startswith("?utm_source=(direct)&utm_medium=gallery"):
                link = article.css('a::attr(href)').get()

            link = link or article.css('#cgb-head h1::attr(data-vr-contentbox-url)').get()


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

        if TEST_SPECIFIC and response.url in self.start_urls:
            link = response.url

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
            #print(f"skipped {link} inside parse_article()")
            yield None

        else:
            article_url = link

            if TEST_SPECIFIC and article_url not in self.start_urls:
                print("for testing, do not even scrape the children articles")
                yield None

            else:
                #print("departing to get_article_content()")

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
        text = re.sub(r"\(Photo.+?\)", "", text)
        text = re.sub(r".+?Photo from.+?\n", "", text)
        text = re.sub(r".+?Screenshot from.+?\n", "", text)
        text = re.sub(r".+?FIle photo.+?\n", "", text)
        text = re.sub(r"\(AP Photo.+?\)", "", text)
        text = re.sub(r"\(File photo: .+?\)", "", text)
        text = re.sub(r"File photo of .+?\n", "", text)
        text = re.sub(r"FILE-.+?\n", "", text)
        text = re.sub(r".*?file photo.*?\n", "", text)
        text = re.sub(r".*?File photo.*?\n", "", text)
        text = re.sub(r".*?FILE PHOTO.*?\n", "", text)
        text = re.sub(r".*?PHOTO:.*?\n", "", text)
        text = re.sub(r".*?PVL PHOTO.*?\n", "", text)
        text = re.sub(r".*?UAAP PHOTO.*?\n", "", text)
        text = re.sub(r".*?INQUIRER PHOTO.*?\n", "", text)
        text = re.sub(r".*?\/INQUIRER\.net.*?\n", "", text)
        text = re.sub(r".*?PHOTO FROM.*?\n", "", text)
        text = re.sub(r".*?REUTERS\/.*?\n", "", text)
        text = re.sub(r".*?CONTRIBUTED PHOTO.*?\n", "", text)
        text = re.sub(r"FILE PHOTO-.+?", "", text)
        text = re.sub(r"FILE PHOTO: .+?File Photo", "", text)
        return text


    def remove_footnote(self, text, window_size=3, previous_search_footnote_phrase=None):
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
            "(Reporting by",
            "Edited by",
            "Brought to you by",
            "—With a report from",
            "—WITH REPORTS FROM",
            "—Jerome",
            "[ac]",
            "Click here for more",
            "Click here to read more",
            "READ:",
            "READ MORE:",
            "Read next",
            "Read more stories",
            "Read more Global Nation stories",
            ". Learn more about",
            "For more information about",
            "RELATED STORIES",
            "RELATED STORY",
            "RELATED VIDEO",
            "catch the olympics games",
            "cna women is a section on cna",
            "Write to us at",
            ". Subscribe to",
            "We use cookies",
            "For more news about the novel coronavirus click here",
            "Follow INQUIRER.net",
            "The Inquirer Foundation",
            "ADVT",
            "COPYRIGHT ©",
            "copyright© mediacorp 2023"
        ]

        # Initialize an empty buffer
        buffer = []
        """
        all_buffer = []

        for i, line in enumerate(lines):
            all_buffer.append(line)
            all_buffer_string = ' '.join(all_buffer).lower()
        #print(f"inside remove_footnote(), all_buffer_string = {all_buffer_string}")
        """

        if previous_search_footnote_phrase:
            search_phrases_in_lowercase = []
            for search_phrase in search_phrases:
                search_phrases_in_lowercase.append(search_phrase.lower())

        for i, line in enumerate(lines):
            # add line to buffer
            buffer.append(line)

            # ensure buffer doesn't exceed window size
            if len(buffer) > window_size:
                buffer.pop(0)

            #print(f"inside remove_footnote(), buffer = {buffer}, i = {i}")

            # Check if phrases are in the buffer
            buffer_string = ' '.join(buffer).lower()
            #print(f"inside remove_footnote(), buffer_string = {buffer_string}")

            for phrase in search_phrases:
                phrase = phrase.lower()

                if previous_search_footnote_phrase:
                    previous_search_footnote_phrase_index = search_phrases_in_lowercase.index(previous_search_footnote_phrase)
                    current_search_footnote_phrase_index = search_phrases_in_lowercase.index(phrase)

                    if current_search_footnote_phrase_index < previous_search_footnote_phrase_index:
                        continue

                if phrase in buffer_string:
                    # Find the position of the phrase in the buffer string
                    phrase_start = buffer_string.find(phrase)
                    phrase_end = phrase_start + len(phrase)
                    #print(f"inside remove_footnote(), phrase = {phrase}, phrase_start = {phrase_start}, phrase_end = {phrase_end}")

                    # Determine which lines those positions correspond to in the buffer
                    line_lengths = [len(line) + 1 for line in buffer]  # +1 for '\n'
                    line_start_positions = [sum(line_lengths[:i]) for i in range(len(buffer))]
                    line_end_positions = [sum(line_lengths[:i+1]) for i in range(len(buffer))]
                    #print(f"inside remove_footnote(), line_lengths = {line_lengths}, line_start_positions = {line_start_positions}, line_end_positions = {line_end_positions}")

                    # Remove all lines that are part of the phrase
                    for start, end in list(zip(line_start_positions, line_end_positions)):
                        #print(f"inside remove_footnote(), start = {start}, end = {end}")

                        if start <= phrase_start < end or start < phrase_end <= end:
                            phrase_is_located_at_this_buffer_index = line_start_positions.index(start)

                            if buffer:  # Check if buffer is not empty before popping
                                orig_buf_len = len(buffer)
                                #print(f"inside remove_footnote(), before pop(), buffer = {buffer}")
                                #print(f"inside remove_footnote(), before pop(), orig_buf_len = {orig_buf_len}, phrase_is_located_at_this_buffer_index = {phrase_is_located_at_this_buffer_index}")
                                # pop() for 'line_with_the_footnote_phrase' only removes 1 single element, but not the subsequent elements
                                line_with_the_footnote_phrase = buffer.pop(phrase_is_located_at_this_buffer_index)

                                # removes subsequent element in 'buffer'
                                for ws_i in range(phrase_is_located_at_this_buffer_index, len(buffer)):
                                    #print(f"inside remove_footnote(), before pop(), len(buffer) = {len(buffer)}, phrase_is_located_at_this_buffer_index = {phrase_is_located_at_this_buffer_index}, buffer = {buffer}")
                                    if phrase_is_located_at_this_buffer_index > 0:
                                        removed_string_item = buffer.pop(ws_i)
                                        #print(f"inside remove_footnote(), ws_i = {ws_i}, removed_string_item = {removed_string_item}")
                                    else:
                                        #removed_string_item = buffer.pop(len(buffer)-ws_i-1)
                                        buffer = []

                                #print(f"inside remove_footnote(), after pop(), buffer = {buffer}")

                                # Replace line in the original text with the modified line
                                #print(f"inside remove_footnote(), line_with_the_footnote_phrase = {line_with_the_footnote_phrase}")
                                line_without_the_footnote_phrase = line_with_the_footnote_phrase[:phrase_start-start]
                                #print(f"inside remove_footnote(), line_without_the_footnote_phrase = {line_without_the_footnote_phrase}")

                            else:
                                break

                            footnote_is_spread_across_multiple_buffer_items = \
                                (len(phrase) > end - start) or \
                                (phrase_end > end)

                            #print(f"footnote_is_spread_across_multiple_buffer_items = {footnote_is_spread_across_multiple_buffer_items}, len({phrase}) = {len(phrase)}")

                            # Remove the exact line containing footnote phrase as well as all other subsequent lines
                            if phrase_is_located_at_this_buffer_index == 0:
                                #print(f"inside remove_footnote(), before cleaning the subsequent text, lines[{i-orig_buf_len+1}:] = {lines[i-orig_buf_len+1:]}")
                                lines[i-orig_buf_len+1:] = ''
                                #print(f"inside remove_footnote(), after cleaning the subsequent text, lines[{i-orig_buf_len+1}:] = {lines[i-orig_buf_len+1:]}")
                            else:
                                if not footnote_is_spread_across_multiple_buffer_items:
                                    #print(f"inside remove_footnote(), before cleaning the subsequent text, lines[{i}:] = {lines[i:]}")
                                    lines[i:] = ''
                                    #print(f"inside remove_footnote(), after cleaning the subsequent text, lines[{i}:] = {lines[i:]}")
                                else:
                                    #print(f"inside remove_footnote(), before cleaning the subsequent text, lines[{i-len(buffer)}:] = {lines[i-len(buffer):]}")
                                    lines[i-len(buffer):] = ''
                                    #print(f"inside remove_footnote(), after cleaning the subsequent text, lines[{i-len(buffer)}:] = {lines[i-len(buffer):]}")

                            # Combines lines that have no footnote phrase
                            lines.append(line_without_the_footnote_phrase)

                            # Join the lines back into a single string
                            cleaned_text = "\n".join(lines)
                            #print(f"inside remove_footnote(), cleaned_text = {cleaned_text}")

                            # to make sure ALL footnote phrases are removed completely
                            return self.remove_footnote(cleaned_text, window_size=3, previous_search_footnote_phrase=phrase)

        # return the original text if no footnote was found
        return text


    def get_article_content(self, response):
        # retrieves article's detailed title and body properly
        #print("arrived at get_article_content()")
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
            #print(f"skipped {link} inside get_article_content()")
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

                #body = response.css('p:not(.footertext):not(.headertext):not(.wp-caption-text) ::text').getall()
                #body = response.xpath('//p[not(.//strong) and not(.//b) and not(contains(@class, "wp-caption-text")) and not(contains(@class, "footertext")) and not(contains(@class, "headertext")) and not(ancestor::div[@class="qni-cookmsg"]) and not(ancestor::blockquote[@class="twitter-tweet"]) and not(./iframe)]//text() | //li[not(*)]/text() | //p//text()[contains(.,"ADVT")] | //p//text()[contains(.,"READ MORE")]').getall()


                """
                The following logic using BeautifulSoup is trying to work around the limitation of
                response.xpath('//p[not(.//strong) and not(.//b)]//text()').getall() , where this xpath() will
                exclude html such as:   <p>relevant_text<strong>irrelevant_text</strong>relevant_text</p>
                """

                # Get HTML content
                html_content = response.xpath('//body').get()

                # Parse HTML content with BeautifulSoup
                soup = BeautifulSoup(html_content, 'lxml')

                # Find all <strong> and <b> tags
                tags = soup.find_all(['strong', 'b'])

                # Remove each tag
                for tag in tags:
                    tag.decompose()

                # Get the modified HTML
                html_content = str(soup)
                #print(f"html_content after removing <strong> and <b> tags = {html_content}")

                # Convert the resulting text into a Selector object
                response_without_strong_and_b_tags = Selector(text=html_content)

                # Extract the rest of the data
                body = response_without_strong_and_b_tags.xpath('//p[not(contains(@class, "wp-caption-text")) and not(contains(@class, "footertext")) and not(contains(@class, "headertext")) and not(ancestor::div[@class="qni-cookmsg"]) and not(ancestor::blockquote[@class="twitter-tweet"]) and not(./iframe)]//text() | //li[not(*)]/text() | //p//text()[contains(.,"ADVT")] | //p//text()[contains(.,"READ MORE")]').getall()
                #print(f"body after removing <strong> and <b> tags = {body}")


                # Get the text of the <li> tags without any child tags
                li_texts = response.xpath('//li[not(*)]/text()').getall()
                #print(f"li_texts = {li_texts}")

                # Replace <li> texts with comma separated
                for i, text in enumerate(body):
                    for j, t in enumerate(li_texts):
                        #print(f"text = {text}, t = {t}")
                        if text in t and j < len(li_texts) - 1:
                            # replace the matching part of the text with t (which has a comma added)
                            body[i] = text.replace(t, t + ',')

                        if text in t and j == len(li_texts) - 1:
                            # replace the matching part of the text with t (which has a fullstop added)
                            body[i] = text.replace(t, t + '.')

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
                            response.css('li[itemprop="datePublished"] span::text').get() or \
                            response.css('div[id="art_plat"]::attr(data-timezone)').get() or \
                            response.css('#spl-byline span:last-child::text').get()

                    if date is None and response.css('div[id="art_plat"]::text').getall():
                        date = date or \
                                response.css('div[id="art_plat"]::text').getall()[-1].replace("Updated as of:", "")

                    if response.css('div.bpdate::text').getall():
                        date = date or \
                                response.css('div.bpdate::text').getall()[-1]

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


            if date:
                date = ''.join(c for c in date if c.isprintable())  # to remove erroneous non-ASCII printable character
                date = date.strip()  # to remove unnecessary whitespace or newlines characters

            #print(f"inside get_article_content(), article_url = {link} , title = {title}, date = {date}, body = {body}")

            if body == []:
                print(f"empty body list for {link}, search for any url link redirection text")
                url_redirection_html_elements = response.css('a')
                new_article_url = None

                for url_redirection_html_element in url_redirection_html_elements:
                    url_redirection_text = url_redirection_html_element.css('::text').get()
                    url_redirection_link = url_redirection_html_element.css('::attr(href)').get()

                    if url_redirection_text and url_redirection_text.lower() == 'click here for article':
                        new_article_url = url_redirection_link
                        print(f"new_article_url = {new_article_url}")
                        break

                link = new_article_url

                if not link or "javascript" in link or "mailto" in link or "whatsapp://" in link or \
                    "play.google.com" in link or "apps.apple.com" in link or \
                    any(article_url in link for article_url in incomplete_articles) or \
                    any(file_extension in link for file_extension in excluded_file_extensions) or \
                    any(subdomain_name in link for subdomain_name in irrelevant_subdomain_names) or \
                    any(subdomain_name in link for subdomain_name in inaccessible_subdomain_names) or \
                    domain_name not in allowed_domain_names:
                    # skipping urls
                    #print(f"skipped {link} inside get_article_content()")
                    yield None

                else:
                    yield SplashRequest(
                         url=new_article_url,
                         callback=self.write_to_local_data,
                         meta={'link': new_article_url, 'title': title, 'body': body, 'date': date},  # Pass additional data here
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

            # This is an early sign that the current page after url redirection
            # is pointing to a new page containing multiple articles
            if url_had_redirected and self.parse_articles(response) is not None:
                    print(f"going back to parse() for {link}")
                    yield self.parse(response)

            else:
                self.write_to_local_data(response, link, title, body, date)

                '''
                # for the purpose of debugging js_script
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
                '''

                yield {
                    'title': title,
                    'link': link,
                    'date': date,
                    'body': body,
                    #'excerpt': article.css('p::text').get(),
                    'source': self.get_source(response)
                }


    def write_to_local_data(self, response, link=None, title=None, body=None, date=None):
        # Access the additional data here
        if not link and not title and not date:
            link = response.meta['link']
            title = response.meta['title']
            body = response.meta['body']
            date = response.meta['date']

        if "month ago" in date.lower() or "months ago" in date.lower() or \
            "week ago" in date.lower() or "weeks ago" in date.lower() or \
            "day ago" in date.lower() or "days ago" in date.lower() or \
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
            if search_country == 'singapore':
                # Jan 2020 till Jan 2022
                date_is_within_covid_period = ((published_year >= 2020) and (published_year <= 2021))

            elif search_country == 'philippines':
                # https://en.wikipedia.org/wiki/COVID-19_community_quarantines_in_the_Philippines
                date_is_within_covid_period = ((published_year >= 2020) and (published_year <= 2022))

        print(f"date = {date}, and published_year = {published_year}, and date_is_within_covid_period = {date_is_within_covid_period}")

        # we had already retried to re-fetch the new_article_url inside get_article_content(), so if body is still an empty list,
        # this means there is either no new_article_url or the newly redirected page also had no body paragraph text
        if body == []:
            return None

        if body:
            body = [s.strip() for s in body]
            body = '\n'.join(body)
            body = body.strip()

            body = self.remove_photograph_credit(body)
            body = self.remove_footnote(body)

        print(f"inside write_to_local_data(), article_url = {link} , title = {title}, date = {date}, body = {body}")

        if (((title != None and any(keyword in title.lower() for keyword in search_keywords)) or \
            (body != None and any(keyword in body.lower() for keyword in search_keywords))) and \
            (date_is_within_covid_period)) or \
            (TEST_SPECIFIC and link in self.start_urls):
            # Create a unique filename for each URL by removing the 'http://', replacing '/' with '_', and adding '.html'
            file_parent_directory = ''
            filename = file_parent_directory + link.replace('http://', '').replace('/', '_') + '.html'
            print("filename = ", filename)

            # Write the entire body of the response to a file
            with open(filename, 'wb') as f:
                f.write(body.encode('utf-8'))

        return None

