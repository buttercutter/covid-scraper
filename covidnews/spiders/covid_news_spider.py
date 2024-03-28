# Uses scrapy-splash library (instead of 'requests' library) which gives more functionality and flexibility
import scrapy
from scrapy_splash import SplashRequest
from urllib.parse import urljoin
import re
from urllib.parse import urlparse, urlunparse

from dateutil.parser import parse
from datetime import datetime

import os
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

# For javascript handling
USE_SPLASH = 0
USE_SELENIUM = 0
USE_PLAYWRIGHT = 0
USE_PUPPETEER = 0

# The status code 429 stands for "Too Many Requests".
# It is an HTTP response status code indicating that the user has sent too many requests in a given amount of time ("rate limiting").
USE_RATE_LIMIT = 0

# Whether to skip cdx search
SKIP_CDX = True

# Excludes search URL results that renders the following files extensions
excluded_file_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf", ".xls", ".mp3", ".mp4", ".mov", ".flv",
                            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".webp", ".webm", ".m4v"]

# Only parses URLs within these domains
if search_country == 'singapore':
    allowed_domain_names = ["straitstimes.com", "channelnewsasia.com"]

elif search_country == 'philippines':
    allowed_domain_names = ["mb.com.ph", "inquirer.net", "philstar.com"]

elif search_country == 'malaysia':
    allowed_domain_names = ["nst.com.my", "thestar.com.my", "bernama.com/en/", "malaysianow.com", "malaymail.com", "freemalaysiatoday.com", "malaysiakini.com"]

elif search_country == 'vietnam':
    allowed_domain_names = ["vnanet.vn/en/", "vietnamnews.vn", "en.vietnamplus.vn"]

elif search_country == 'thailand':
    allowed_domain_names = ["bangkokpost.com"]

elif search_country == 'indonesia':
    allowed_domain_names = ["thejakartapost.com"]

# not accessible due to DNS lookup error or the webpage had since migrated to other subdomains
inaccessible_subdomain_names = ["olympianbuilder.straitstimes.com", "ststaff.straitstimes.com", "media.straitstimes.com",
                                "buildsg2065.straitstimes.com", "origin-stcommunities.straitstimes.com",
                                "stcommunities.straitstimes.com", "euro2016.straitstimes.com",
                                "awsstaff.straitstimes.com", "eee.straitstimes.com",
                                "prdstaff.straitstimes.com", "staff.straitstimes.com",
                                "stompcms.straitstimes.com",
                                "classifieds.thestar.com.my", "starnie@thestar.com.my",
                                "news.mb.com.ph",
                                "live.inquirer.net",
                                "inqshop.inquirer.net", "misc.inquirer.net", "nment.inquirer.net",
                                "inqpop.inquirer.net", "newyorktimes.inquirer.net", "showbizandstyle.inquirer.net",
                                "vouchers.inquirer.net", "blogs.inquirer.net", "apec.inquirer.net",
                                "newsinafo.inquirer.net", "yass.inquirer.net", "yasss.inquirer.net"
                                ]

# these subdomains contains irrelevant contents for non-subscription-based, region-based, text-based media article scraping
irrelevant_subdomain_names = ["channelnewsasia.com/watch/", "cnaluxury.channelnewsasia.com",
                              "straitstimes.com/multimedia/", "graphics.straitstimes.com/",
                              "cnalifestyle.channelnewsasia.com/interactives/", "channelnewsasia.com/video",
                              "cnalifestyle.channelnewsasia.com/brandstudio/",
                              "channelnewsasia.com/experiences/", "channelnewsasia.com/dining/",
                              "straitstimes.com/video", "channelnewsasia.com/listen/",
                              "straitstimes.com/sport/", "straitstimes.com/business/",
                              "straitstimes.com/world/",
                              "straitstimes.com/life/", "straitstimes.com/lifestyle/entertainment/",
                              "straitstimes.com/asia/south-asia/", "straitstimes.com/asia/east-asia/",
                              "straitstimes.com/asia/australianz/", "ge2015social.straitstimes.com",
                              "channelnewsasia.com/asia/east-asia/", "channelnewsasia.com/asia/south-asia/",
                              "channelnewsasia.com/world/", "channelnewsasia.com/sport/",
                              "channelnewsasia.com/business", "channelnewsasia.com/entertainment",
                              "channelnewsasia.com/author", "straitstimes.com/author",
                              "channelnewsasia.com/women/",
                              "channelnewsasia.com/about-us",
                              "nst.com.my/lifestyle", "nst.com.my/news-cars-bikes-trucks", "nst.com.my/property",
                              "nst.com.my/business", "nst.com.my/videos", "nst.com.my/sports",
                              "nst.com.my/podcast", "nst.com.my/flyfm", "nst.com.my/buletinfm",
                              "nst.com.my/hotfm", "nst.com.my/8fm", "nst.com.my/molekfm",
                              "nst.com.my/photos", "nst.com.my/nst175", "vouchers.nst.com.my",
                              "thestar.com.my/privacy/", "thestar.com.my/Privacy", "thestar.com.my/ContactUs",
                              "thestar.com.my/lifestyle/", "thestar.com.my/sport", "events.thestar.com.my",
                              "thestar.com.my/FAQs", "thestar.com.my/terms/", "advertising.thestar.com.my",
                              "thestar.com.my/AboutUs", "thestar.com.my/Terms", "mystarauth.thestar.com.my",
                              "sso.thestar.com.my", "newsstand.thestar.com.my", "login.thestar.com.my",
                              "thestar.com.my/faqs", "thestar.com.my/subscribe", "thestar.com.my/subscription",
                              "thestar.com.my/business/", "ads.thestar.com.my",
                              "thestar.com.my/food", "thestar.com.my/lifestyle",
                              "thestar.com.my/news/world", "thestar.com.my/world/world",
                              "thestar.com.my/tag/forex", "thestar.com.my/tag/banking", "thestar.com.my/tag/cryptocurrency",
                              "thestar.com.my/tag/energy", "thestar.com.my/tag/smartphones",
                              "bangkokpost.com/video", "bangkokpost.com/photo", "bangkokpost.com/business",
                              "bangkokpost.com/learning/course/",
                              "thejakartapost.com/election-2024", "thejakartapost.com/business", "thejakartapost.com/longform",
                              "thejakartapost.com/epost", "thejakartapost.com/culture/entertainment",
                              "thejakartapost.com/multimedia/video", "thejakartapost.com/multimedia/photo",
                              "thejakartapost.com/longform/", "thejakartapost.com/business/",
                              "bernama.com/en/videos/", "bernama.com/tv/", "bernama.com/radio/", "images.bernama.com",
                              "entertainment.inquirer.net", "business.inquirer.net", "opinion.inquirer.net",
                              "sports.inquirer.net", "technology.inquirer.net", "usa.inquirer.net",
                              "pop.inquirer.net", "inquirer.net/inqpop", "lifestyle.inquirer.net",
                              "philstar.com/sports", "philstar.com/lifestyle", "philstar.com/business",
                              "philstar.com/entertainment",
                              "news.vnanet.vn/en/",  # only works for paid login subscription
                              "vnanet.vn/en/anh/vna-photos", "seagames-en.vnanet.vn",
                              "vietnamnews.vn/Economy", "vietnamnews.vn/Life - Style", "vietnamnews.vn/life-style",
                              "vietnamnews.vn/Sports", "vietnamnews.vn/economy", "vietnamnews.vn/travel",
                              "special.vietnamplus.vn",  # articles inside this subdomain is very general, does not contain any date
                              "vietnamplus.vn/region/",  # international region subdomain section
                              "mb.com.ph/our-company"]

if SEARCH_ENTIRE_WEBSITE:
    irrelevant_subdomain_names += ["search.bangkokpost.com"]

# articles that are 404 broken links, or published with only a title, and without any body content and publish date
incomplete_articles = ["https://www.straitstimes.com/singapore/education/ask-sandra-jc-mergers",
                       "https://www.straitstimes.com/business/economy/askst-what-benefits-did-budget-2016-offer-entrepreneurs-and-single-women",
                       "https://www.straitstimes.com/singapore/does-getting-zika-infection-once-confer-immunity",
                       "https://www.straitstimes.com/tags/bhumibol-adulyadej",
                       "https://www.straitstimes.com/askst/steely-stand-off",
                       "https://www.straitstimes.com/singapore/environment/askst-is-it-safe-to-eat-spinach-leaves-which-have-white-spots-on-them",
                       "https://www.thestar.com.my/metro/metro-news/2020/07/20/",
                       "https://www.thestar.com.my/news/nation/2022/10/19/",
                       "https://www.thestar.com.my/aseanplus/aseanplus-news/2021/09/07/",
                       "https://www.thestar.com.my/2003/06/09/all-dried-out",
                       "https://www.thestar.com.my/tech/tech-news/2023/06/13/stock-list.asp",
                       "https://www.thestar.com.my/news/nation/2023/09/01/malaysian-aviation-group-announces-three-new-routes-to-india",
                       "https://www.thestar.com.my/news/nation/2022/04/26/toll-free-travel-and-discounts-to-make-a-merrier-raya",
                       "https://www.thestar.com.my/2004/10/03/umno-in-her-blood",
                       "https://www.thestar.com.my/opinion/columnists/analysis/2022/10/15/an-election-like-no-other",
                       "https://www.thestar.com.my/2006/02/19/the-bard-brickfields-style",
                       "https://www.thestar.com.my/tech/tech/tech-news/2023/12/15/the-last-of-us-online-game-cancelled-by-sonys-naughty-dog-studio",
                       "https://www.thestar.com.my/tech/tech/tech-news/2023/12/15/chinas-weibo-asks-bloggers-to-avoid-badmouthing-the-economy",
                       "https://www.thestar.com.my/tech/tech/tech-news/2023/12/15/heartless-selfish-woman-in-china-cancels-ride-hail-car-after-cabbie-drove-40km-waited-half-hour-but-failed-to-help-with-bags",
                       "https://www.thestar.com.my/metro/metro/metro-news/2023/12/15/rm2bil-project-to-rejuvenate-shah-alam-starting-next-year",
                       "https://www.thestar.com.my/metro/metro/metro-news/2023/12/15/dbkl-high-rise-project-has-met-all-conditions",
                       "https://www.thestar.com.my/metro/metro/metro-news/2023/12/15/drain-in-low-lying-area-upgraded",
                       "https://www.thestar.com.my/metro/metro/metro-news/2023/12/15/cruise-into-the-sunset",
                       "https://www.thestar.com.my/metro/metro/metro-news/2023/12/15/loud-tweets-ruffle-feathers",
                       "https://www.thestar.com.my/aseanplus/2022/11/30/chance-for-every-malaysian-to-save",
                       "https://www.thestar.com.my/tech/tech/tech-news/2023/12/18/outrage-as-man-drags-wife-out-of-car-leaving-crying-toddler-son-on-busy-road-in-china-during-row-over-boys-education",
                       "https://www.thestar.com.my/news/nation/2022/10/13/tommy-thomas-was-not-cut-out-to-be-ag-reads-task-force-report",
                       "https://www.thestar.com.my/news/nation/2023/09/06/wisma-pertahanan-names-new-armed-forces-chief",
                       "https://www.thestar.com.my/aseanplus/aseanplus-news/2022/04/22/75-year-old-lost-us1-million-in-china-officials-impersonation-scam",
                       "https://www.thestar.com.my/2003/07/27/one-big-shopping-spree--for-carnival",
                       "https://vnanet.vn/Frontend/TrackingView.aspx?IID=7155206",
                       "https://vnanet.vn/Frontend/TrackingView.aspx?IID=7167889",
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
                      "https://www.bangkokpost.com/learning/easy/2105639/wear-mask-or-pay-20-000-baht-fine",  # for testing xpath() on <li> tags
                      "https://www.bangkokpost.com/life/social-and-lifestyle/2283058/owed-a-real-debt-of-gratitude",  # for testing xpath() on <li> tags
                      "https://www.bangkokpost.com/thailand/pr/2331868/manufacturing-expo-2022-kicks-off-the-most-comprehensive-exhibition-for-the-manufacturing-and-supporting-industries-bringing-in-ground-breaking-machinery-and-technologies-across-9-shows-in-one-mega-event-as-well-as-30-seminars-aimed-to-deep-dive-into-the-industry",  # filename too long
                      "https://www.bangkokpost.com/thailand/pr/2121403/central-world-joins-hands-with-king-chulalongkorn-memorial-hospital-of-the-thai-red-cross-society-to-open-a-vaccination-centre-to-help-authorities-fight-the-pandemic-reinforcing-central-pattanas-position-as-the-private-sectors-leader-in-mass-vaccinations",  # filename too long
                      "https://www.bangkokpost.com/thailand/pr/2123287/central-pattana-joins-hands-with-partners-in-national-mission-reaffirming-central-shopping-centers-as-the-model-of-safe-vaccination-centres-nationwide-launching-im-vaccinated-campaign-in-23-central-shopping-centres",  # filename too long
                      "https://www.bangkokpost.com/thailand/pr/2143763/frasers-property-industrial-thailand-and-strategic-partner-mitsui-fudosan-asia-thailand-celebrates-the-start-of-the-first-warehouse-construction-at-bang-na-2-logistics-park-in-the-eastern-economic-corridor",  # filename too long
                      "https://www.thestar.com.my/aseanplus/aseanplus-news/2022/03/16/food-aid-delivered-to-54393-homes-since-onset-of-second-covid-wave-in-brunei",  # empty article
                      "https://www.thestar.com.my/tech/tech-news/2022/11/08/amazon-sets-up-warehouse-in-eastern-china-for-faster-overseas-ecommerce-signalling-confidence-in-consumer-spending",  # javacript rendering is wrong
                      "https://www.thestar.com.my/news/regional/2020/05/17/south-east-asia---caught-in-the-middle-of-a-new-us-china-cold-war",  # javacript rendering is wrong
                      "https://www.thestar.com.my/tech/tech-news/2020/10/01/covid-19-controls-turn-asia-into-global-surveillance-hotspot-analysts-say",  # javacript rendering is wrong
                      "https://www.thestar.com.my/tech/tech-news/2021/03/02/beijing-dismisses-alleged-chinese-hacking-of-indian-vaccine-makers",  # javacript rendering is wrong
                      "https://www.thestar.com.my/news/education/2022/05/22/we-give-it-all-we-got",  # javacript rendering is wrong
                      "https://www.thestar.com.my/tech/tech-news/2022/08/24/anti-work-redditors-say-quiet-quittingreally-means-just-doing-your-job",  # javacript rendering is wrong
                      "https://www.thestar.com.my/opinion/columnists/on-your-side/2020/08/21/a-second-chance-to-keep-hopes-alive",  # javacript rendering is wrong
                      "https://www.thestar.com.my/opinion/columnists/on-your-side/2020/05/01/share-profits-to-save-the-industry",  # javacript rendering is wrong
                      "https://www.thestar.com.my/tech/tech-news/2022/06/13/making-a-difference-in-the-digital-age",  # javacript rendering is wrong
                      "https://www.thestar.com.my/opinion/columnists/search-scholar-series/2022/08/01/advancing-the-esg-agenda-in-china-and-malaysia",  # javacript rendering is wrong
                      "https://www.thestar.com.my/opinion/columnists/search-scholar-series/2022/03/28/digital-silk-road-potential-benefits-for-malaysias-digital-economy",  # javacript rendering is wrong
                      "https://www.thestar.com.my/aseanplus/aseanplus-news/2022/10/04/asean-news-headlines-at-9pm-on-tuesday-oct-4-2022",  # javacript rendering is wrong
                      "https://www.thestar.com.my/news/nation/2022/07/15/16th-pkr-national-congress-begins-today",  # need to check whether to ignore all <strong> tags for `ALSO READ:` in the middle of paragraph during `body` extraction since it is also a part of footnote phrase
                      "https://www.straitstimes.com/singapore/consumer/spores-nightlife-industry-remains-shut-out-despite-easing-of-curbs",  # need to manually scrape due to multiple articles and multiple footnotes
                      "https://www.straitstimes.com/singapore/community/domestic-workers-long-for-visits-home-amid-covid-19-restrictions",  # need to manually scrape due to multiple articles and multiple footnotes
                      "https://www.straitstimes.com/singapore/seniors-in-spore-find-it-hard-to-stay-home-in-order-to-stay-safe-amid-covid-19",  # need to manually scrape due to multiple articles and multiple footnotes
                      "https://newsinfo.inquirer.net/1580989/no-new-covid-19-cases-recorded-in-pateros-for-fourth-consecutive-day",  # need to manually scrape due to limitation in how I could code the xpath() for 'body' especially for <li> tags
                      "https://www.channelnewsasia.com/singapore/sinovac-covid-19-vaccine-national-vaccination-programme-three-dose-singapore-2263787",  # need to manually scrape due to limitation in how I could code the xpath() for 'body' especially for <li> tags
                      "https://globalnation.inquirer.net/187527/dfa-records-21-new-covid-19-cases-of-filipinos-abroad-total-now-at-1922",  # need to manually scrape due to limitation in how I could code the xpath() for 'body' especially for <p><b> tags
                      "https://newsinfo.inquirer.net/1456244/duque-reminds-lgus-to-prioritize-health-workers-elderly-in-covid-19-vax-drive",  # body is empty, need to debug futher
                      "https://newsinfo.inquirer.net/1477559/vigan-city-extends-stricter-curbs-under-mecq-due-to-virus-surge",  # need to manually remove footnote
                      "https://globalnation.inquirer.net/153570/sen-cayetano-confirms-wikipedia-report",  # new_article_url variable is not working yet
                      "https://globalnation.inquirer.net/153864/duterte-looking-better-trump",  # new_article_url variable is not working yet
                      "https://www.straitstimes.com/singapore/jobs/government-unions-employer-groups-start-work-on-guidelines-on-flexible-work-arrangements",  # title.lower()
                      "https://www.channelnewsasia.com/advertorial/building-global-healthcare-ecosystem-care-good-2943211",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.channelnewsasia.com/remarkableliving/kausmo-educating-singapore-diners-about-food-wastage-1882711",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.straitstimes.com/singapore/fewer-families-received-comcare-financial-aid-from-the-government-last-year",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.channelnewsasia.com/singapore/new-covid-19-variants-uk-south-africa-strains-b117-explainer-416156",  # AttributeError: 'list' object has no attribute 'encode'
                      "https://www.channelnewsasia.com/singapore/mpa-covid-19-10-000-frontline-workers-vaccinations-415726",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://www.channelnewsasia.com/singapore/covid19-how-to-choose-masks-filtration-bfe-surgical-1382776",  # AttributeError: 'list' object has no attribute 'lower'
                      "https://newsinfo.inquirer.net/1459925/octa-notes-increasing-covid-19-cases-in-cebu-city-lapu-lapu",  # part of the sentence text is embedded inside images
                      "https://www.channelnewsasia.com/singapore/covid-19-locations-visited-queensway-shopping-masjid-assyakirin-712556",  # part of the sentence text is embedded inside images
                      "https://www.channelnewsasia.com/singapore/places-visited-by-covid-19-cases-moh-novena-square-fairprice-1851511",  # part of the sentence text is embedded inside images
                      "https://www.straitstimes.com/singapore/health/high-vaccination-rate-risk-of-hospitals-being-swamped-cited-as-reasons-for-and",  # part of the sentence text is embedded inside images
                      "https://www.straitstimes.com/singapore/changed-forever-by-one-pandemic-is-singapore-ready-for-the-next"  # irrelevant advertisement paragraph text by SPH Media
                     ]

        # Try to open the file in read mode
        try:
            # opening the file in read mode
            my_file = open("manual_scrape.txt", "r")

            # reading the file
            data = my_file.read()

            # splitting the text it when '\n' is seen.
            lines = data.split("\n")
            print(f"len(lines) = {len(lines)}")

            start_urls = start_urls + lines
            print(f"len(start_urls) = {len(start_urls)}")

            # close the file
            my_file.close()

        except FileNotFoundError:
            print("The file manual_scrape.txt does not exist.")

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
                #'https://www.inquirer.net/',  # already finished the entire scraping process
                'https://www.philstar.com/'
            ]

        elif search_country == 'malaysia':
            start_urls = [
                #'https://www.nst.com.my/',  # does not work with Selenium library
                #'https://www.bernama.com/en/',  # only contains article for the most recent 2 months
                'https://www.malaysianow.com/',
                'https://www.malaymail.com/',
                'https://www.freemalaysiatoday.com/',
                'https://www.malaysiakini.com/',
                'https://www.thestar.com.my/'
            ]

        elif search_country == 'vietnam':
            start_urls = [
                'https://vnanet.vn/en/',
                'https://vietnamnews.vn',
                'https://en.vietnamplus.vn'
            ]

        elif search_country == 'thailand':
            if SEARCH_ENTIRE_WEBSITE:
                start_urls = [
                    'https://www.bangkokpost.com'
                ]
            else:
                start_urls = [
                    #'https://search.bangkokpost.com/search/result_advanced?q=covid&searchedField=all&category=all&xNewsSection=&xChannel=&xColumn=covid&author=&xDate2=past60Days&xDate=&xDateSearchRadio=range&xDateFrom=01%2F01%2F2020&xDateTo=01%2F01%2F2023',
                    'https://search.bangkokpost.com/search/result_advanced?q=covid&category=archive&refinementFilter=&sort=newest&publishedDate=%5B2020-01-01T00%3A00%3A00Z%3B2022-12-31T23%3A59%3A59Z%5D&searchedField=all&xNewsSection=&xChannel=&xColumn=&author='
                ]

        elif search_country == 'indonesia':
            start_urls = [
                'https://www.thejakartapost.com'
            ]

    # settings for Javacript handling
    if USE_SPLASH:  # scrapy-splash
        custom_settings = {
            'DOWNLOADER_MIDDLEWARES': {
                'covidnews.middlewares.GzipRetryMiddleware': 543,
                'covidnews.middlewares.ForgivingHttpCompressionMiddleware': 810,
            },

            'SPIDER_MIDDLEWARES': {
                'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
                'scrapy_splash.SplashCookiesMiddleware': 723,
                'scrapy_splash.SplashMiddleware': 725,
            },
        }

    elif USE_PLAYWRIGHT:
        os.system('playwright install')

        custom_settings = {
            'DOWNLOADER_MIDDLEWARES': {
                'covidnews.middlewares.GzipRetryMiddleware': 543,
                'covidnews.middlewares.ForgivingHttpCompressionMiddleware': 810,
                'covidnews.middlewares.PlaywrightMiddleware': 800,
            },

            'SPIDER_MIDDLEWARES': {
            },
        }

    elif USE_PUPPETEER:
        from scrapypuppeteer import PuppeteerRequest

        custom_settings = {
            'DOWNLOADER_MIDDLEWARES': {
                'covidnews.middlewares.GzipRetryMiddleware': 543,
                'covidnews.middlewares.ForgivingHttpCompressionMiddleware': 810,
                'scrapypuppeteer.middleware.PuppeteerServiceDownloaderMiddleware': 1042,
            },

            'SPIDER_MIDDLEWARES': {
            },
        }
        PUPPETEER_SERVICE_URL = 'http://localhost:3000'

    elif USE_SELENIUM:
        custom_settings = {
            'DOWNLOADER_MIDDLEWARES': {
                'covidnews.middlewares.GzipRetryMiddleware': 543,
                'covidnews.middlewares.ForgivingHttpCompressionMiddleware': 810,
                'covidnews.middlewares.SeleniumMiddleware': 800,
            },

            'SPIDER_MIDDLEWARES': {
            },
        }

    else:  # just scrapy
        custom_settings = {
            'DOWNLOADER_MIDDLEWARES': {
                'covidnews.middlewares.GzipRetryMiddleware': 543,
                'covidnews.middlewares.ForgivingHttpCompressionMiddleware': 810,
            },

            'SPIDER_MIDDLEWARES': {
            },
        }

    if USE_RATE_LIMIT:
        custom_settings['DOWNLOAD_DELAY'] = 0.5


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
                    if USE_PUPPETEER:
                        yield PuppeteerRequest(
                                url,
                                callback=self.get_article_content,
                                meta={'title': None, 'date': None, 'article_url': url},  # Pass additional data here, assigned None here for testing purpose
                        )

                    else:
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

        if (search_country == 'malaysia' and domain_name == 'bernama.com') or \
           (search_country == 'vietnam' and domain_name == 'vnanet.vn'):
            # for specific use case only
            domain_name = domain_name + "/en/"

        elif (search_country == 'vietnam' and domain_name == 'vietnamplus.vn'):
            # for specific use case only
            domain_name = "en." + domain_name

        return domain_name


    def get_next_pages(self, response):
        print("inside get_next_pages(), response.url = ", response.url)

        link = response.url.strip().lower()

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

        elif 'philstar.com' in response.url:
            more_links = response.css('a::attr(href)').getall()

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

        elif 'bernama.com/en/' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'malaysianow.com' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'freemalaysiatoday.com' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'vnanet.vn/en/' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'vietnamnews.vn' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'en.vietnamplus.vn' in response.url:
            more_links = response.css('a::attr(href)').getall()

        elif 'bangkokpost.com' in response.url:
            if SEARCH_ENTIRE_WEBSITE:
                more_links = response.css('a::attr(href)').getall()
            else:
                more_links = response.css('p.page-Navigation > a::attr(href)').getall()

        elif 'thejakartapost.com' in response.url:
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
        url = re.sub(r"https?://globnalnation\.inquirer\.net", "https://globalnation.inquirer.net", url)
        url = re.sub(r"https?://www\.bandera\.inquirer\.net", "https://bandera.inquirer.net", url)
        url = re.sub(r"https?://www\.newsinfo\.inquirer\.net", "https://newsinfo.inquirer.net", url)
        url = re.sub(r"https?://nwsinfo\.inquirer\.net", "https://newsinfo.inquirer.net", url)
        url = re.sub(r"https?://www\.cebudailynews\.inquirer\.net", "https://cebudailynews.inquirer.net", url)
        url = re.sub(r"https?://events\@thestar\.com\.my/", "https://events.thestar.com.my/", url)

        if not url.startswith("http"):
            url = urljoin(default_url, url)

        # Removes any whitespace characters
        url = url.strip()

        # If the URL is fine, return it as is
        return url


    def parse(self, response):
        # The HTTP 202 status code generally means that the request has been received but not yet acted upon.
        if response.status == 202:
            yield None

        articles = None
        link = response.url.strip().lower()
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

        print(f"Found {len(articles)} articles")

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
                link = next_page_url.strip()
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

        elif 'philstar.com' in response.url:
            print("parse_articles() for philstar.com")
            return response.css(
                    'div.carousel__item__title h2 a, \
                    div.theContent div#news_main div.jscroll-inner div.news_column.latest div.tiles.late.ribbon-cont div.ribbon div.ribbon_content div.ribbon_title h2 a, \
                    div.theContent div#news_main div.jscroll-inner div#home_columnists div#home_columnists_content div#home_columnists_actual.owl-carousel.owl-theme.owl-loaded.owl-drag div.owl-stage-outer div.owl-stage div.owl-item.active div.home_columnists_cell div.home_columnists_cell_details h3 a, \
                    div.theContent div#news_main div.jscroll-inner div#inside_philstar table#inside_philstar_cells tbody tr td.inside_cell div.inside_cell_title_main h3 a, \
                    div.theContent div#news_main div.jscroll-inner div#inside_philstar table#inside_philstar_cells tbody tr td.inside_cell ul li h3 a, \
                    div.news_title h2 a, \
                    div.news_title a'
                    )

        elif 'inquirer.net' in response.url:
            print("parse_articles() for inquirer.net")

            if response.url == 'https://cebudailynews.inquirer.net/':

                body = response.css('*').getall()

                if body:
                    body = [s.strip() for s in body]
                    body = '\n'.join(body)
                    body = body.strip()

                    body = self.remove_media_credit(body)
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

                    body = self.remove_media_credit(body)
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
                    'div.row.mb-4 div.col-md-4.col-lg-3.order-2.order-sm-1.mb-4.mb-sm-0 div.mb-4 div.block.block-article-image-row-listing div.d-flex.flex-row.mb-3, \
                    \
                    div.block.block-breaking-news div.d-flex.mb-3, \
                    div.block.block-breaking-news div.row div.col-12.col-sm.mb-4.mb-sm-0, \
                    div.block.block-breaking-news div.row div.col.col-sm.align-items-center.article-listing div.d-flex.flex-column.h-100.justify-content-between a.d-flex.article.listing.mb-2 div.content.pl-2 div.field-title, \
                    \
                    div.most-popular.block div#__BVID__12.tabs div#__BVID__12__BV_tab_container_.tab-content.pt-2 div#__BVID__13.tab-pane.active div.timeline.pt-3 ul li.d-flex.pb-3, \
                    div.most-popular.block div#__BVID__12.tabs div#__BVID__12__BV_tab_container_.tab-content.pt-2 div#__BVID__15.tab-pane.active div.ranked-listing div.ranked-item.d-flex.px-3.pb-2.mb-2.align-items-center.timeline, \
                    div.most-popular.block div#__BVID__9.tabs div#__BVID__9__BV_tab_container_.tab-content.pt-2 div#__BVID__10.tab-pane.active div.timeline.pt-3 ul li.d-flex.pb-3, \
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
                    div.col-sm-3.in-sec-story div.row div.col-xs-7.left.col-sm-12 h2, \
                    div.row.story-set div.col-xs-12.col-sm-3.mob-bot-20 div.col-wrap div.col-content h2, \
                    div.col-sm-6.in-sec-story div.row div.col-xs-7.left.col-sm-12 h2, \
                    ul#MoreNews-Second.story-set.col-sm-4.col-md-3 li.row.hidden-visual, \
                    div.row.list-listing div.col-xs-7.col-sm-9 h2, \
                    ul#justInListing.timeline.vTicker li.row div.col-xs-8.col-sm-10.col-md-9.tm-content-wrap div.timeline-content p a, \
                    div.focus section.latest-news div.sub-section-list div.row.list-listing, \
                    div.featuredDiv div.focus-story div.row div div.col-xs-12.col-sm-4.featuredContent div.content h2, \
                    div.row ul.story-set.col-sm-3.story3 li.row.hidden-visual div.col-xs-7.left.col-sm-12 h2 a, \
                    div.story-set-group.story2 div.col-sm-6.in-sec-story div.row div.col-xs-7.left.col-sm-12 a, \
                    div#section1.story-set-group div.col-sm-3.in-sec-story div.row div.col-xs-7.left.col-sm-12 h2, \
                    div#section2.sub-section-list div.row.list-listing div.col-xs-7.col-sm-9 h2, \
                    div#story-recom-list.desc-wrap div.desc div.col-xs-7.col-sm-9.col-md-7.left, \
                    div#divOpinionWidget section.side-combo-2 div.desc-wrap div.row.desc div.col-xs-9.col-sm-10.right p a, \
                    div.focus-story.focus-lifestyle div.row div.col-xs-12.col-sm-4, \
                    div.sub-section-list.story-set-lifestyle div.col-xs-12.col-sm-6.bot-20.lifemain div.row div.col-xs-12.left, \
                    div.thumb__container.viewpoints__stories.row div.col-sm-6.thumb__item div.thumb.thumb--vp div.thumb__inner, \
                    div.opinion-content div div.row.story-set div.col-xs-12.col-sm-4.bot-20 div.col-wrap div.col-content h2, \
                    div#story-recom-list.desc-wrap div.desc, div.row.panel-content'
            )

        elif 'bernama.com/en/' in response.url:
            print("parse_articles() for bernama.com/en/")
            return response.css(
                'div#topstory.carousel.slide.mt-2 div.carousel-inner div.carousel-item div.carousel-caption h1.h3 a, \
                div#skroll div.ji-timeline div.ji-container.ji-right div.ji-content h6, \
                div#main.container-fluid.px-0 div.row div.col-lg-6 div#spcl2news.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div.row div.col-lg-12 div#spcl3news.row div.col-12.col-sm-12.col-md-3.col-lg-3.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div.row div.col-sm-12.col-md-12.col-lg-12 div.row div.col-12 div#latestnews.owl-carousel.owl-theme.owl-loaded.owl-drag div.owl-stage-outer div.owl-stage div.owl-item.active div h6 a, \
                div#main.container-fluid.px-0 div#twonewsonly.row div.col-lg-6 div#generalnews.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div#twonewsonly.row div.col-lg-6 div#worldnews.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div#twonewsonly.row div.col-lg-6 div#businessnews.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div#twonewsonly.row div.col-lg-6 div#politicsnews.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div#twonewsonly.row div.col-lg-6 div#sportnews.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div#twonewsonly.row div.col-lg-6 div#featuresnews.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#main.container-fluid.px-0 div#twonewsonly.row div.col-lg-6 div#thoughtsnews.row div.col-12.col-sm-12.col-md-6.col-lg-6.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12 h6 a, \
                div#body-row.row.oku_font div.col.pt-3 div.container-fluid.px-0 div.row div.col-sm-12.col-md-12.col-lg-12 div.row div.col-sm-12.col-md-4.col-lg-4.mt-3.mt-md-0.mt-lg-0 h1.h3 a, \
                div#body-row.row.oku_font div.col.pt-3 div.container-fluid.px-0 div.row div.col-sm-12.col-md-12.col-lg-12 div.row div.col-12.col-sm-12.col-md-3.col-lg-3.mb-3.mb-md-0.mb-lg-0 div.row div.col-7.col-md-12.col-lg-12.mb-3 h6 a, \
                div#body-row.row.oku_font div.col.pt-3 div.container-fluid.px-0 div.row div.col-12.col-sm-12.col-md-8.col-lg-8 div.row div.p-2.pl-3 div.row div.col-7.col-sm-7.col-md-8.col-lg-8 h6 a'
            )

        elif 'malaysianow.com' in response.url:
            print("parse_articles() for malaysianow.com")
            return response.css(
                'div#__next main div.bg-white div.mx-auto.max-w-7xl.px-4.pt-10.pb-8.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.px-4.pt-10.pb-8.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 div.space-y-8.sm\:grid.sm\:grid-cols-2.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:gap-x-6.lg\:gap-y-6 div.group a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.border-t-2.border-gray-100.py-8 div.space-y-8 div ul.space-y-8.sm\:grid.sm\:grid-cols-2.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:grid-cols-3.lg\:gap-x-8 li a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.items-stretch.space-y-8.lg\:flex.lg\:flex-1.lg\:space-x-6.lg\:space-y-0 div.w-full.space-y-8.lg\:sticky.lg\:top-40.lg\:h-full.lg\:w-\[300px\] div.space-y-8.sm\:grid.sm\:grid-cols-1.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:gap-x-6.lg\:gap-y-6 div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.items-stretch.space-y-8.lg\:flex.lg\:flex-1.lg\:space-x-6.lg\:space-y-0 div.flex-1 div.space-y-12.sm\:-mt-8.sm\:space-y-0.sm\:divide-y.sm\:divide-gray-200.lg\:gap-x-8.lg\:space-y-0 div.sm\:py-8 a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 div.space-y-8.sm\:grid.sm\:grid-cols-2.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:gap-x-6.lg\:gap-y-6 div.group a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.px-4.pt-8.pb-10.sm\:px-6 div.mx-auto.grid.gap-5.sm\:grid-cols-2.lg\:max-w-none.lg\:grid-cols-4 div.group.flex.flex-col.overflow-hidden.rounded-md.border-2.border-gray-100 div.flex.flex-1.flex-col.justify-between.bg-white.p-6 div.flex-1 a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1 div.mx-auto.grid.gap-5.sm\:grid-cols-2.lg\:max-w-none.lg\:grid-cols-3 div.group.flex.flex-col.overflow-hidden.rounded-md.border-2.border-gray-100 div.flex.flex-1.flex-col.justify-between.bg-white.p-6 div.flex-1 a, \
                div#__next main div.bg-white div.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.space-y-8.lg\:sticky.lg\:top-40.lg\:h-full.lg\:w-\[300px\] div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a, \
                div#__next main div.bg-white article.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1.space-y-6 div.space-y-4 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.hidden.space-y-8.lg\:sticky.lg\:top-40.lg\:block.lg\:h-full.lg\:w-\[300px\] div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a, \
                div#__next main div.bg-white article.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1.space-y-6 div.space-y-4 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1.space-y-6 div.space-y-6 div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a, \
                div#__next main div.bg-white article.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.space-y-8.lg\:sticky.lg\:top-40.lg\:h-full.lg\:w-\[300px\] div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a'
            )

        elif 'freemalaysiatoday.com' in response.url:
            print("parse_articles() for freemalaysiatoday.com")
            return response.css(
                'main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-3 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-12.col-sm-7.col-lg-5.order-1.order-sm-2.mb-4.mb-lg-0 article div.col-12 h1.sc-aXZVg.jiTbBU.fw-bold a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-3 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-12.col-lg-4.order-2.order-sm-3 div.row.align-items-stretch.gx-3 article.col-6.mb-4 blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.iBuEiq div.sc-eqUAAy.fgprtA.container-xxl div.row section.col-lg-8 div.sc-fPXMVe.lmAJDv.col-12 div.home-topnews-listing.row.gx-3 div.row.g-1.home-lifestyle-listing.gallery-listing div.col-6 div.featured.mb-5 article div.col-12 blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.iBuEiq div.sc-eqUAAy.fgprtA.container-xxl div.row section.col-lg-8 div.sc-fPXMVe.lmAJDv.col-12 div.home-topnews-listing.row.gx-3 div.row.g-1.home-lifestyle-listing.gallery-listing article.col-12.col-sm-6.px-2.row.gx-2.mb-4.fs-12.align-items-stretch div.col blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.iBuEiq div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-lg-4 aside.col-lg div.home-mostpopular-listing ol li div a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-md-7.mb-4.mb-md-0 article.position-relative.h-md-100 div.sc-jEACwC.eyfswQ.summary-wrapper.position-absolute.bottom-0.w-100.px-4.px-sm-5 div.summary-title-wrapper.mb-4.mb-sm-3 blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-md div.row.align-items-stretch.gx-3 div.sc-gFqAkR.KXNUP div.row.g-1.home-lifestyle-listing.gallery-listing div.col-6.mb-4 article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-prev article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-next article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-active article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate.swiper-slide-duplicate-prev article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate.swiper-slide-duplicate-active article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate.swiper-slide-duplicate-next article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-12.col-md-7 article div.col-12 blockquote.sc-aXZVg.jiTbBU.fw-bold a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-12.col-md-5 div.row.gx-3 div.sc-ikkxIA.bklVyq div.row.g-1.home-lifestyle-listing.gallery-listing div.col-6.mb-4 article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.sc-dAbbOL.delONt.col-12 div.row.gx-3.home-lifestyle-listing div.col-6.col-md-3.mb-4.mb-md-0 article.position-relative.h-100 div.sc-jEACwC.eyfswQ.summary-wrapper.position-absolute.bottom-0.w-100.px-3 div.summary-title-wrapper.pb-28-px blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.mb-5 div.sc-eqUAAy.fgprtA.container-xxl div.sc-feUZmu.beTCqT.col-12 div.row.gx-3 div.col-6.col-md-3 article blockquote a, \
                main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row section.col-12.col-md-4.mostviewed-listing article.row.gx-3.mb-4.fs-12.align-items-stretch div.col blockquote a, \
                main.sc-hzhJZQ.gqYvvz.d-flex.flex-column.flex-grow-1 div.sc-gEvEer.iBuEiq.flex-grow-1 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-md-4 div aside.col-lg div.home-mostpopular-listing ol li div a, \
                div#__next div.fixed-top.jumpslider.d-none.d-md-block div.fade.bg-light.alert-border.alert.alert-success.show div div div a.m__story, \
                div#__next main.sc-hzhJZQ.gqYvvz.d-flex.flex-column.flex-grow-1 div.sc-gEvEer.iBuEiq.flex-grow-1 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-md-8 section.sc-gEvEer.iBuEiq.p-4 section.sc-gEvEer.iBuEiq.pt-5.pb-3.px-0.fs-16 div.row.gx-3 article.col-6.col-sm-3.mb-3 blockquote a'
            )

        elif 'vnanet.vn/en' in response.url:
            return response.css(
                'div.col-big-news.fl-left div.title-big-news h2 > a, \
                div.list-box-rows.list-box-rows-2.scrollbar.divTopNews ul li.parentMenuItem a, \
                li.act-cate-main div.sub-cate-main div.big-news-cate-main div.title-bg-grd.title-big-news-main > a, \
                li.act-cate-main div.sub-cate-main div.list-box-rows.list-box-rows-4.cf ul li > a, \
                div.list-box-rows.list-box-rows-5.scrollbar ul#divOtherNews li > a, \
                div.ct-post-details div.feature-list-news ul li div.grp-panel > a, \
                div.ct-post-details div.grp-list-news-2 ul li div.grp-panel > a, \
                div.sidebar-rows.fix-sidebar-rows div#divServiceNews.list-news-dv ul li div.grp-panel > a, \
                div.divTextView.newsListForm div.flex-container div.flex-item.meta-data-port a'
            )

        elif 'vietnamnews.vn' in response.url:
            return response.css(
                'html body div.site-content div.l-grid div.l-content div#spotlight_slick.spotlight-slick.slick-initialized.slick-slider div.slick-list.draggable div.slick-track div.d-flex.slick-slide div.slick-meta h2 a, \
                html body div.site-content div.l-grid div.l-content div.row.feature div.col article.story.story--focus div.story__meta h2 a, \
                html body div.site-content div.l-grid div.l-content div.row.feature div.col article.story h2 a, \
                html body div.site-content div.l-grid div.l-content div.highlight section.zone.zone--highlight div.row.zone__content article.col.story h2 a, \
                html body div.site-content div.l-grid div.l-content section.zone.zone--cate.has-thumb div.zone__content div.focus-col article.story h2 a, \
                html body div.site-content div.l-grid div.l-content section.zone.zone--cate.has-thumb div.zone__content article.story.story--focus h2 a, \
                html body div.site-content div.l-grid div.l-content section.zone.zone--cate.has-thumb div.zone__content div.focus-col article.story h2 a, \
                html body div.site-content div.l-grid div.sidebar section.aside.aside--latest div.tab-content div#latest.tab-pane.fade.show.active article.story h2 a, \
                html body div.site-content div.l-grid div.sidebar div.event ul.event-list li a, \
                html body div.site-content div.l-grid div.l-content section.zone.zone--column div.zone__content div.row article.col.story h2 a, \
                html body div.site-content div.l-grid div.l-content section.zone.zone--cate.has-text div.zone__content article.story.story--focus h2 a, \
                html body div.site-content div.l-grid div.l-content section.zone.zone--cate.has-text div.zone__content div.row article.col.story h2 a, \
                html body div.site-content div.area.area--dark div.l-grid section.zone.zone--opinion div.zone__content div.row div.col article.story div.story__meta h2 a, \
                html body div.site-content div.l-grid.cate-col div.row div.col section.zone div.zone__content article.story h2 a, \
                html body div.site-content div.l-grid div.l-content.category section.zone.zone--cate.has-thumb div.zone__content article.story.story--focus h2 a, \
                html body div.site-content div.l-grid div.l-content.category section.zone.zone--cate.has-thumb div.zone__content div.focus-col article.story h2 a, \
                html body div.site-content div.l-grid div.l-content.category div.d-flex div.timeline article.story h2 a'
            )

        elif 'en.vietnamplus.vn' in response.url:
            return response.css(
                'section.latest-news div.clearfix article.story--text h2 a, \
                div.spotlight article.story.story--horizontal h2 a, \
                div.highlight div.l-content div.focus article.story h2 a, \
                div.highlight div.l-content div.feature.cols-3 article.story h2 a, \
                div.l-content section.zone--timeline div.clearfix article.story h2 a, \
                div.clearfix article.story.story--horizontal h2 a, \
                div.clearfix ul.story--list li a, \
                div.zone--region__list ul.story--list li a, \
                div.clearfix article.story.story--large h2 a, \
                div.clearfix div.right article.story.story--horizontal h2 a, \
                div.l-content section.zone--cate div.feature.cols-3 article.story h2 a, \
                div#wrapper-popular section.zone.zone--popular div.clearfix article.story h2 a, \
                div.clearfix article.story.story--split h2 a, \
                div.clearfix article.story--large h2 a, \
                div.clearfix ul li article.story h2 a'
            )

        elif 'bangkokpost.com' in response.url:
            return response.css(
                'body > div.divbody-container > div.divsection-container > section.section-highlight > div > div.row.no-gutters-sm > div.col-15.col-lg-11.ctrl-height > div.divnews-highlight > div > div.owl-stage-outer.owl-height > div > div.owl-item.active > div > div > figure > figcaption > h3 > a, \
                body > div.divbody-container > div.divsection-container > section.section-highlight > div > div.row.no-gutters-sm > div.col-15.col-lg-11.ctrl-height > div.news--slide222 > div > div.owl-stage-outer > div > div > div > div > h3 > a, \
                body > div.divbody-container > div.divsection-container > section.section-highlight > div > div.row.no-gutters-sm > div.col-15.col-lg-4 > div > div.div-timeline--list > div > h3 > a, \
                body > div.divbody-container > div.divsection-container > section.section-highlight > div > div.row.no-gutters-sm > div.col-15.col-lg-4 > div > div.div-timeline--list > ul > li > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div > div.news--slide > div > div.owl-stage-outer > div > div > div > div > h3 > a, \
                div.section-news > div.container > #news-tabContent > div > div > div > div.col-15.col-lg-9 > div > figure > figcaption > h3 > a, \
                div.section-news > div.container > #news-tabContent > div > div > div > div.col-15.col-lg-6 > div > ul > li > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div > div > div.col-15.col-lg-10 > div.row > div > div > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div > div > div.col-15.col-lg-10 > div.row > div > div > ul > li > h3 > a, \
                body > div.divbody-container > div.divsection-container > section.section-leaning > div > div.boxnews--container.learning--slide > div > div.owl-stage-outer > div > div > div > div > a, \
                body > div.divbody-container > div.divsection-container > section > div > div.topics--slide > div > div.owl-stage-outer > div > div > div > div > div.col-15.col-lg-9.col-xl-50 > div > a, \
                body > div.divbody-container > div.divsection-container > section > div > div.topics--slide > div > div.owl-stage-outer > div > div > div > div > div.col-15.col-lg-6.col-xl-50 > div > ul > li > h3 > a, \
                body > div.divbody-container > div.divsection-container > section.section-highlight.news--highlight > div > div > div.col-15.col-lg-10 > div > div > div.owl-stage-outer > div > div.owl-item.active > div > div > figure > figcaption > h3 > a, \
                body > div.divbody-container > div.divsection-container > section.section-highlight.news--highlight > div > div > div.col-15.col-lg-5 > div > div.div-mostview--list > ul > li > h3 > a, \
                div.news--slide > div#recommended > div.owl-stage-outer > div > div > div > div > h3 > a, \
                body > div > div.divsection-container > section > section.section-page > div > div.row.topics-news > div > div > div > h3 > a, \
                div > div > div > div.col-15.col-lg-6 > div > ul > li > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div.container > div > div.col-15.col-lg-5 > div.articl--aside > div.div-recommended.mb-30 > div.div-recommended--list > ul > li > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div.container > div > div.col-15.col-lg-5 > div.articl--aside > div.box-topic--bg > div.row > div > div > ul > li > h3 > a, \
                body > section.section-learning > section > div.div-learning-listdetail > div > div > div.col-15.col-md-15.col-lg-10 > div.row.lea-commu > div > article > div > div > h3 > a, \
                li#primary-slider-slide01 > div > a, \
                body > section.section-learning > section > div > div > div.col-15.col-md-15.col-lg-10 > div.section-learning--article > div > div > article > div > div > h3 > a, \
                body > div > div.divsection-container > section.section-page > div > div > div > div > div > h3 > a, \
                #trending-widget > div > div.news--slide > div > div > div > div > a, \
                div > div.videoCube.trc_spotlight_item.origin-default.thumbnail_top.textItem.videoCube_2_child.trc_excludable > a, \
                body > div > div.divsection-container > section.section-page > div > div > div > div.owl-stage-outer > div > div > div > div > div.col-15.col-lg-9.col-xl-50 > div > a, \
                #alphabet-a > div.mt-5 > div.news--slide > div > div.owl-stage-outer > div > div > div > div > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div > div > div > div.div-section--main.mb-5 > div.news--list.border-bottom.mb-4.pb-3 > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div > div > div > div.div-section--main.mb-5 > div.news--list-noimg > ul > li > h3 > a, \
                div > div.videoCube.trc_spotlight_item.origin-default.thumbnail_top.textItem.videoCube_1_child.trc-first-recommendation.trc-spotlight-first-recommendation.trc_excludable > a, \
                body > div.divbody-container > div.divsection-container > section.section-highlight.news--highlight > div > div > div.col-15.boxnews--notshow-mobi.mt-md-5 > div > div > div > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div > div.row.page--link > div > div > div > h3 > a, \
                body > div.divbody-container > div.divsection-container > section > div > div.subsect--latest > div.row.page--link > div > div > div > h3 > a, \
                body > div.divbody-container.life-container > div.divsection-container > section > div > div.subsect--latest.divlife--latest > div.row.page--link > div > div > div > h3 > a, \
                #content > div.content-right > ul > li > div > h3 > a, \
                #content > div.content-right > ul > div > h3 > a'
            )

        elif 'thejakartapost.com' in response.url:
            return response.css(
                'body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__headline > div > div > div.tjp-homepage__headline-main.outlined > div > div > a, \
                body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__headline > div > div > div.tjp-homepage__headline-third.outlined > div > div > a, \
                body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__section.tjp-homepage__section--popular > div > div > div > div.tjp-grid.tjp-grid--1-2 > div > div > a, \
                #swiper-wrapper-61071fce948872ee1 > div.swiper-slide.swiper-slide-active > a, \
                body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__section.tjp-homepage__section--popular > div > div > div > div.tjp-grid.tjp-grid--2 > div > div > a, \
                body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__section.tjp-homepage__section--opinion > div.tjp-grid.tjp-grid--2 > div > a, \
                body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__section.tjp-homepage__section--opinion > div.tjp-grid.tjp-grid--2 > div > div > div > div > a, \
                body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__section.tjp-homepage__section--indonesia > div.tjp-grid.tjp-grid--2 > div > div > div > a, \
                body > div.tjp-wrapper > div.col-xs-12.tjpcontainer > div.container.borderGrid > div > div > div > div > div > div.tjp-homepage__section.tjp-homepage__section--indonesia > div.tjp-grid.tjp-grid--2 > div > div > div > div > a, \
                body > div.col-xs-12.tjpcontainer > div > div > div > div.jpRow.mainNews.lineSection.channelTwoSided.subCanal > div.containerLeft.col-xs-12 > div > div.theLatest.mb-20 > div.columns.tjp-newsListing > div > div > div.latestDetail > a, \
                body > div.col-xs-12.tjpcontainer > div > div > div > div.jpRow.mainNews.headLineChannel.channelTwoSided > div > div.smallHeadline.channel > div > div > a'
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
        title = None
        date = None
        link = None

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

        elif 'philstar.com' in response.url:
            title = article.css('a ::text').get()
            date = article.css('div.article__date-published').get()
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

        elif 'nst.com.my' in response.url:
            title = article.css('h6.field-title::text').get()

            if article.css('div.d-block.article-meta span.created-ago::text').get():
                date = article.css('div.d-block.article-meta span.created-ago::text').get().split(' @ ')[0]

            if date is None and article.css('div.article-meta > div::text').get():
                date = article.css('div.article-meta > div::text').get().split(' @ ')[0]

            link = article.css('a::attr(href)').get()

        elif 'thestar.com.my' in response.url:
            title = article.css('h2 a ::text').get() or \
                    article.css('a ::text').get()

            if article.css('span.timestamp ::text').get():
                date = article.css('span.timestamp ::text').get().split(' | ')[0]

            if date is None and article.css('label.timestamp ::text').get():
                date = article.css('label.timestamp ::text').get().split(' | ')[0]

            link = article.css('a::attr(href)').get()

        elif 'bernama.com/en/' in response.url:
            title = article.css('a ::text').get()
            link = article.css('a::attr(href)').get()

        elif 'malaysianow.com' in response.url:
            title = article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.px-4.pt-10.pb-8.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 a div.group.space-y-4 div.space-y-1 h3 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.px-4.pt-10.pb-8.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 div.space-y-8.sm\:grid.sm\:grid-cols-2.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:gap-x-6.lg\:gap-y-6 div.group a div.space-y-3 div.space-y-1 h3 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.border-t-2.border-gray-100.py-8 div.space-y-8 div ul.space-y-8.sm\:grid.sm\:grid-cols-2.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:grid-cols-3.lg\:gap-x-8 li a.group div.group.grid.grid-cols-3.items-start.gap-6.space-y-0 div.col-span-2.flex.h-full.flex-col.justify-center.space-y-1.align-middle h3 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.items-stretch.space-y-8.lg\:flex.lg\:flex-1.lg\:space-x-6.lg\:space-y-0 div.w-full.space-y-8.lg\:sticky.lg\:top-40.lg\:h-full.lg\:w-\[300px\] div.space-y-8.sm\:grid.sm\:grid-cols-1.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:gap-x-6.lg\:gap-y-6 div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a div.space-y-3 div.space-y-1 h3 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.items-stretch.space-y-8.lg\:flex.lg\:flex-1.lg\:space-x-6.lg\:space-y-0 div.flex-1 div.space-y-12.sm\:-mt-8.sm\:space-y-0.sm\:divide-y.sm\:divide-gray-200.lg\:gap-x-8.lg\:space-y-0 div.sm\:py-8 a div.group.space-y-4.sm\:grid.sm\:grid-cols-5.sm\:items-start.sm\:gap-6.sm\:space-y-0 div.sm\:col-span-3 div.space-y-4 div.space-y-1 h3 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 a div.group.space-y-4 div.space-y-1 h3 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.py-8.px-4.sm\:px-6 div.space-y-8.lg\:grid.lg\:grid-cols-4.lg\:gap-8.lg\:space-y-0 div.lg\:col-span-2 div.space-y-8.sm\:grid.sm\:grid-cols-2.sm\:gap-x-6.sm\:gap-y-8.sm\:space-y-0.lg\:gap-x-6.lg\:gap-y-6 div.group a div.space-y-3 div.space-y-1 h3 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.px-4.pt-8.pb-10.sm\:px-6 div.mx-auto.grid.gap-5.sm\:grid-cols-2.lg\:max-w-none.lg\:grid-cols-4 div.group.flex.flex-col.overflow-hidden.rounded-md.border-2.border-gray-100 div.flex.flex-1.flex-col.justify-between.bg-white.p-6 div.flex-1 a.mt-2.block p.font-georgia.text-xl.leading-6.text-gray-900.transition.duration-200.group-hover\:text-brand-red-900 ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1 div.mx-auto.grid.gap-5.sm\:grid-cols-2.lg\:max-w-none.lg\:grid-cols-3 div.group.flex.flex-col.overflow-hidden.rounded-md.border-2.border-gray-100 div.flex.flex-1.flex-col.justify-between.bg-white.p-6 div.flex-1 a.mt-2.block div.space-y-1 p ::text').get() or \
                    article.css('div#__next main div.bg-white div.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.space-y-8.lg\:sticky.lg\:top-40.lg\:h-full.lg\:w-\[300px\] div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a div.space-y-3 div.space-y-1 h3 ::text').get() or \
                    article.css('div#__next main div.bg-white article.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1.space-y-6 div.space-y-4 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.hidden.space-y-8.lg\:sticky.lg\:top-40.lg\:block.lg\:h-full.lg\:w-\[300px\] div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a div.space-y-3 div.space-y-1 h3 ::text') or \
                    article.css('div#__next main div.bg-white article.mx-auto.max-w-7xl.py-10.px-4.sm:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1.space-y-6 div.space-y-4 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.flex-1.space-y-6 div.space-y-6 div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a div.grid.grid-cols-3.items-start.gap-6.space-y-0 div.col-span-2 div.space-y-1 div.space-y-1.font-georgia.text-xl.font-medium.leading-6.transition.duration-200.group-hover\:text-brand-red-900 h3 ::text') or \
                    article.css('div#__next main div.bg-white article.mx-auto.max-w-7xl.py-10.px-4.sm\:px-6 div.items-stretch.space-y-6.lg\:flex.lg\:flex-1.lg\:space-y-0.lg\:space-x-6 div.space-y-8.lg\:sticky.lg\:top-40.lg\:h-full.lg\:w-\[300px\] div.rounded-md.border-2.border-gray-100.p-6 div.space-y-4 div.divide-y.divide-gray-200 div.group.py-4 a div.space-y-3 div.space-y-1 h3 ::text')


            date = article.css('time ::text').get()
            link = article.css('a::attr(href)').get()

        elif 'freemalaysiatoday.com' in response.url:
            title = article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-3 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-12.col-sm-7.col-lg-5.order-1.order-sm-2.mb-4.mb-lg-0 article div.col-12 h1.sc-aXZVg.jiTbBU.fw-bold a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-3 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-12.col-lg-4.order-2.order-sm-3 div.row.align-items-stretch.gx-3 article.col-6.mb-4 blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.iBuEiq div.sc-eqUAAy.fgprtA.container-xxl div.row section.col-lg-8 div.sc-fPXMVe.lmAJDv.col-12 div.home-topnews-listing.row.gx-3 div.row.g-1.home-lifestyle-listing.gallery-listing div.col-6 div.featured.mb-5 article div.col-12 blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.iBuEiq div.sc-eqUAAy.fgprtA.container-xxl div.row section.col-lg-8 div.sc-fPXMVe.lmAJDv.col-12 div.home-topnews-listing.row.gx-3 div.row.g-1.home-lifestyle-listing.gallery-listing article.col-12.col-sm-6.px-2.row.gx-2.mb-4.fs-12.align-items-stretch div.col blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.iBuEiq div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-lg-4 aside.col-lg div.home-mostpopular-listing ol li div a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-md-7.mb-4.mb-md-0 article.position-relative.h-md-100 div.sc-jEACwC.eyfswQ.summary-wrapper.position-absolute.bottom-0.w-100.px-4.px-sm-5 div.summary-title-wrapper.mb-4.mb-sm-3 blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-md div.row.align-items-stretch.gx-3 div.sc-gFqAkR.KXNUP div.row.g-1.home-lifestyle-listing.gallery-listing div.col-6.mb-4 article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-prev article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-next article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-active article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate.swiper-slide-duplicate-prev article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate.swiper-slide-duplicate-active article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row.mb-4 div.col-12.col-lg-8 div div.position-relative div.swiper.swiper-initialized.swiper-horizontal.swiper-pointer-events div.swiper-wrapper div.swiper-slide.swiper-slide-duplicate.swiper-slide-duplicate-next article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-12.col-md-7 article div.col-12 blockquote.sc-aXZVg.jiTbBU.fw-bold a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.home-beritautama-listing.row.gx-3 div.col-12.col-md-5 div.row.gx-3 div.sc-ikkxIA.bklVyq div.row.g-1.home-lifestyle-listing.gallery-listing div.col-6.mb-4 article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.sc-dAbbOL.delONt.col-12 div.row.gx-3.home-lifestyle-listing div.col-6.col-md-3.mb-4.mb-md-0 article.position-relative.h-100 div.sc-jEACwC.eyfswQ.summary-wrapper.position-absolute.bottom-0.w-100.px-3 div.summary-title-wrapper.pb-28-px blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq section.sc-gEvEer.iBuEiq.mb-5 div.sc-eqUAAy.fgprtA.container-xxl div.sc-feUZmu.beTCqT.col-12 div.row.gx-3 div.col-6.col-md-3 article blockquote a ::text').get() or \
                    article.css('main.sc-dLMFU.dEogEu.d-flex.flex-column.flex-grow-1 div.sc-fHjqPf.cqruwq div.sc-gEvEer.BiNyN.py-5 div.sc-eqUAAy.fgprtA.container-xxl div.row section.col-12.col-md-4.mostviewed-listing article.row.gx-3.mb-4.fs-12.align-items-stretch div.col blockquote a ::text').get() or \
                    article.css('main.sc-hzhJZQ.gqYvvz.d-flex.flex-column.flex-grow-1 div.sc-gEvEer.iBuEiq.flex-grow-1 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-md-4 div aside.col-lg div.home-mostpopular-listing ol li div a ::text').get() or \
                    article.css('div#__next div.fixed-top.jumpslider.d-none.d-md-block div.fade.bg-light.alert-border.alert.alert-success.show div div div a.m__story b ::text').get() or \
                    article.css('div#__next main.sc-hzhJZQ.gqYvvz.d-flex.flex-column.flex-grow-1 div.sc-gEvEer.iBuEiq.flex-grow-1 div.sc-eqUAAy.fgprtA.container-xxl div.row div.col-md-8 section.sc-gEvEer.iBuEiq.p-4 section.sc-gEvEer.iBuEiq.pt-5.pb-3.px-0.fs-16 div.row.gx-3 article.col-6.col-sm-3.mb-3 blockquote a ::text').get()

            date = article.css('time ::text').get()
            link = article.css('a::attr(href)').get()

        elif 'vnanet.vn/en/' in response.url:
            title = article.css('a ::text').get()
            date = article.css('div.article__date-published').get()
            link = article.css('a::attr(href)').get()

        elif 'vietnamnews.vn' in response.url:
            title = article.css('a ::text').get()
            date = article.css('div.article__date-published').get()
            link = article.css('a::attr(href)').get()

        elif 'en.vietnamplus.vn' in response.url:
            title = article.css('a ::text').get()
            date = article.css('div.article__date-published').get()
            link = article.css('a::attr(href)').get()

        elif 'bangkokpost.com' in response.url:
            title = article.css('a ::text').get()
            date = article.css('div.article__date-published').get()
            link = article.css('a::attr(href)').get()

        elif 'thejakartapost.com' in response.url:
            title = article.css('a ::text').get()
            date = article.css('div.article__date-published').get()
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
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                )


    def remove_media_credit(self, text):
        text = re.sub(r"\([^()]*first of two parts[^()]*\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\([^()]*Second of two parts[^()]*\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\([^()]*pic[^()]*\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\(Image: .+?\)", "", text, flags=re.DOTALL)
        text = re.sub(r"\(Photo.+?\)", "", text, flags=re.DOTALL)
        text = re.sub(r".+?Photo from.+?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".+?Screenshot from.+?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".+?FIle photo.+?\n", "", text, flags=re.DOTALL)
        text = re.sub(r"\(AP Photo.+?\)", "", text, flags=re.DOTALL)
        text = re.sub(r"\(File photo: .+?\)", "", text, flags=re.DOTALL)
        text = re.sub(r"File photo of .+?\n", "", text, flags=re.DOTALL)
        text = re.sub(r"FILE-.+?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?file photo.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?File photo.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?FILE PHOTO.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?PHOTO:.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?PVL PHOTO.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?UAAP PHOTO.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?INQUIRER PHOTO.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?\/INQUIRER\.net.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?PHOTO FROM.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?REUTERS\/.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r".*?CONTRIBUTED PHOTO.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r"FILE PHOTO-.+?", "", text, flags=re.DOTALL)
        text = re.sub(r"FILE PHOTO: .+?File Photo", "", text, flags=re.DOTALL)

        text = re.sub(r"WATCH THE LIVESTREAM HERE:", "", text, flags=re.DOTALL)
        text = re.sub(r"Watch the full speech:", "", text, flags=re.DOTALL)
        return text


    def remove_footnote(self, text, window_size=3, previous_search_footnote_phrase=None):
        # cleans up some strange character
        text = text.replace('\xa0', ' ')
        text = text.replace('<200b>', ' ')

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
            "is Dean of",
            "is the Dean of",
            "Note:",
            "Editor's note",
            "Editor’s Note:",
            "Editorial note:",
            "Correction note:",
            "Clarification note:",
            "Terence Fernandez is a",
            "Brian Martin is the managing editor of The Star",
            "About the author:",
            "The article was edited",
            "This story was produced",
            "The story has been updated",
            "This story has been updated",
            "This article has been updated",
            "this article originally appear",
            "This story came from",
            "© The New York Times",
            "© 2023 the new york times",
            "© The Financial Times",
            "© 2021 The Financial Times",
            "© 2022 The Financial Times",
            "© 2023 The Financial Times",
            "©2020 Bloomberg",
            "©2021 Bloomberg",
            "©2022 Bloomberg",
            "©2020 Project Syndicate",
            "©2021 Project Syndicate",
            "©2022 project syndicate",
            "©1995-2022 Project Syndicate",
            "©Project Syndicate",
            "Project Syndicate",
            "©2022",
            "© 2022",
            "©2021",
            "© 2021",
            "©2020",
            "© 2020",
            "© 2016 - 2024 PT. Bina Media Tenggara",
            "©CNN",
            "TSB",
            "lzb",
            "/lzb",
            "[atm]",
            "/atm",
            "(Source: AP)",
            "(Reporting by",
            "Additional reporting by",
            "Edited by",  # Comment this out for manual scraping due to truncated words for "accrEdited by"
            "Produced by:",
            "Brought to you by",
            "WITH REPORT FROM", "—REPORTS FROM",
            "—With a report from", "—WITH REPORTS FROM",
            "— By YEE XIANG YUN", "— By M. SIVANANTHA SHARMA", "— By FARID WAHAB", "— By ANDY CHUA",
            "— By REBECCA RAJAENDRAM",
            "— By GRACE CHEN", "— By PAUL GABRIEL", "— By JEREMY TAN", "— By IMRAN HILMY", "— By SANDHYA MENON",
            "—Jerome",
            "–Jaime Laude",
            "—Julie",
            "–Helen Flores",
            "–Elizabeth Marcelo",
            "—MA. APRIL MIER-MANJARES",
            "—Jovic",
            "—JOANNA",
            "—JUN A. MALIG",
            "—DONA",
            "—Nikka",
            "–Rudy Santos",
            "—Leila B. Salaverria",
            "—NESTLE SEMILLA",
            "—NESTOR",
            "—Patricia",
            "—Tina",
            "— Bella Perez-Rubio",
            "— KHIRTHNADHEVI KUMAR",
            "— Christian Deiparine",
            "— Kaycee Valmonte with Agence France-Presse",
            "- Jakarta Post",
            "— Jakarta Post",
            "– AP",
            "- AFP",
            "– AFP",
            "— AFP",
            "– dpa",
            "- Reuters",
            "— Reuters",
            "– Reuters",
            "- Bloomberg",
            "– Bloomberg",
            "— Bloomberg",
            "- Bernama",
            "– Bernama",
            "— Bernama",
            "-- Bernama",
            "- Xinhua",
            "— VNS", "VNS Copyrights 2012",
            "-VNA", "./. VNA", "./.  VNA", "./.   VNA", "./.    VNA",
            "- The Straits Times/ANN",
            "– The Straits Times (Singapore)/Asia News Network",
            "- The Nation Thailand/ANN",
            "— The Nation Thailand/ANN",
            "- Philippines Daily Inquirer/ANN",
            "— Vietnam News",
            "- Vietnam News/ANN",
            "- Phnom Penh Post/ANN",
            "– South China Morning Post",
            "– Thomson Reuters Foundation",
            "– Los Angeles Times/Tribune News Service",
            "– Hartford Courant/Tribune News Service",
            "– Bangkok Post, Thailand/Tribune News Service",
            "– Khaleej Times, Dubai/Tribune News Service",
            "burs/",
            "burs-",
            "bangkok post/",
            "Email karnjanak@bangkokpost.co.th",
            "CONTACT: BANGKOK POST BUILDING",
            "MCI (P)",
            "[ac]",
            "-- More to follow --",
            "Click below to watch",
            "Click here for more",
            "Click here to read more",
            "View More",
            "READ:",
            "READ MORE:",
            "Read next",
            "READ NEXT:",
            "READ MORE HERE",
            "Read more from",
            "Read more stories",
            "READ FULL STORY:",
            "Read more Global Nation stories",
            "More from South China Morning Post:",
            ". Learn more about",
            "For more news like this",
            "For more information about",
            "For the latest news from",
            "Watch the full news",
            "RELATED:",
            "RELATED STORIES",
            "RELATED STORY",
            "RELATED VIDEO",
            "TOPIC:",
            "Reference:",
            "Source:",
            "Visit https://spoti.fi",
            "catch the olympics games",
            "cna women is a section on cna",
            "Write to us at",
            "Subscribe now to",
            ". Subscribe to",
            "Already a subscriber?",
            "We use cookies",
            "Tags / Keywords:",
            "By registering, you agree with",
            "All letter writers must provide full name and address",
            "All letter writers must provide a full name and address",
            "To be updated with all the latest news and analyses daily.",
            "For more news about the novel coronavirus click here",
            "Follow INQUIRER.net",
            "The Inquirer Foundation",
            "Philstar.com is one of the most ",
            "ADVT",
            "Best viewed on",
            "Report it to us",
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


    def is_a_valid_date(self, date_string):
        try:
            # Attempt to parse the date string
            datetime.strptime(date_string, '%B %d, %Y - %I:%M %p')
            return True
        except ValueError:
            # If a ValueError is raised, the date string is not in the expected format
            return False


    def get_article_content(self, response):
        # The HTTP 202 status code generally means that the request has been received but not yet acted upon.
        if response.status == 202:
            yield None

        # retrieves article's detailed title and body properly
        #print("arrived at get_article_content()")
        # Access the additional data here
        title = response.meta['title']
        date = response.meta['date']
        article_url = response.meta['article_url']

        link = response.url.strip()
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

            elif 'philstar.com' in response.url:
                print("get_article_content for philstar")
                body = response.xpath('//p[not(ancestor::div[@class="twitter-tweet"])]//text()').getall()

                if title is None:
                    title = response.css('div.article__title h1 ::text').get()

                if date is None and response.css('div.article__date-published ::text').get():
                    date = response.css('div.article__date-published ::text').get().split(' | ')[0]

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
                    if ((date and not self.is_a_valid_date(date)) or date is None) and response.css('div#m-pd2 > span:nth-child(3)::text').get() and len(response.css('div#m-pd2 > span:nth-child(3)::text').get()) > 1:
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

            elif 'nst.com.my' in response.url:
                body = response.css('p ::text').getall()

                if title is None:
                    title = response.css('h1.page-title.mb-2 span.d-inline-block.mr-1::text').get()

                if date is None and response.css('div.article-meta > div::text').get():
                    date = response.css('div.article-meta > div::text').get().split(' @ ')[0]

            elif 'thestar.com.my' in response.url:
                #body = response.css('p:not(.caption):not(.date) ::text').getall()
                body = response.xpath('//p[not(contains(@class, "caption")) and not(contains(@class, "date")) and not(contains(@class, "reactions__desc")) and not(contains(@class, "footer-bottom")) and not(contains(., "Do you have question")) and not(ancestor::div[@class="plan-temp_desc relative"]) and not(ancestor::div[@class="klci"]) and not(ancestor::div[@class="sponsored-panel"]) and not(ancestor::div[@class="for-side api-widget"]) and not(.//span[contains(@class, "inline-caption")]) and not(contains(., "ALSO READ:"))]//text() | //li[not(*)]/text()').getall()

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

                        #if text in t and j == len(li_texts) - 1:
                            # replace the matching part of the text with t (which has a fullstop added)
                            #body[i] = text.replace(t, t + '.')

                if title is None:
                    title = response.css('.headline.story-pg h1::text').get()

                if date is None:
                    date = response.css('p.date::text').get()

            elif 'bernama.com/en/' in response.url:
                body = response.css('p ::text').getall()

                if title is None:
                    title = response.css('div#body-row.row.oku_font div.col.pt-3 div.container-fluid.px-0 div.row div.col-12.col-sm-12.col-md-12.col-lg-8 h1.h2::text').get()

                date = response.css('div#body-row.row.oku_font div.col.pt-3 div.container-fluid.px-0 div.row div.col-12.col-sm-12.col-md-12.col-lg-8 div.row div.col-6.mt-3 div.text-right::text').get()

            elif 'malaysianow.com' in response.url:
                body = response.css('p ::text').getall()

                if title is None:
                    title = response.css('h1 ::text').get()

                if date is None:
                    date = response.css('time ::text').get()

            elif 'freemalaysiatoday.com' in response.url:
                body = response.css('p ::text').getall()

                if title is None:
                    title = response.css('h1 ::text').get()

                if date is None:
                    print("date is None for freemalaysiatoday")
                    date = response.css('time ::text').get()
                    print("date is still None for freemalaysiatoday")

            elif 'vnanet.vn/en/' in response.url:
                body = response.css('p ::text').getall()

                if title is None:
                    title = response.css('div.details__header h1::text').get()

                date = response.css('time::text').get()

                if date is None:
                    print("date is None for vnanet")

            elif 'vietnamnews.vn' in response.url:
                body = response.css('p ::text').getall()

                if title is None:
                    title = response.css('div.detail__header h1.headline::text').get()

                date = response.css('div.datetime::text').get()

                if date is None:
                    print("date is None for vietnamnews.vn")

            elif 'en.vietnamplus.vn' in response.url:
                body = response.xpath('//p//text() | //div[contains(@class, "content") and contains(@class, "article-body")]//text()[not(ancestor::div[contains(@class, "article-photo")])]').getall()

                if title is None:
                    title = response.css('div.details__header h1.details__headline.cms-title::text').get()

                date = response.css('time::text').get()

                if date is None:
                    print("date is None for vietnamplus")

            elif 'bangkokpost.com' in response.url:
                print("get_article_content for bangkokpost")

                body = response.xpath('//p[not(contains(@class, "Footnote")) and not(contains(@class, "footnote")) and not(ancestor::div[@class="footer"]) and not(ancestor::div[@class="article-info"]) and not(ancestor::div[@class="article-info--col"]) and not(ancestor::div[@class="article--columnist-history"]) and not(ancestor::div[@class="articlePhotoCenter"]) and not(ancestor::div[@class="embed-responsive-content"]) and not(ancestor::div[@class="PostbagName"])]//text() | //article/div[@class="articl-content"]/ul/li//text() | //article/div[@class="article-content"]/ul/li//text() | //article/div[@class="article-content"]/h2//text()').getall()

                if title is None:
                    title = response.css('div.article-headline > h1::text').get()

                original_date_str = response.css('div.article-info--col:nth-child(1) > p:nth-child(1)::text').get() or \
                                    response.css('div.article-info > div.row > div > p::text').get() or \
                                    response.css('div.postbag-info-date > a#calendar > span::text').get() or \
                                    response.css('div.article-news > article > div.article-info.has-columnnist > div:nth-child(1) > div > div:nth-child(2) > p::text').get()

                if original_date_str is None:
                    print("original_date_str is None for bangkokpost")

                # Original date string
                # original_date_str = "PUBLISHED : 12 Mar 2024 at 12:42"

                # Preprocess the string to remove unnecessary parts
                date = original_date_str.split("PUBLISHED :")[-1].split("published :")[-1].split(" at ")[0].strip()

            elif 'thejakartapost.com' in response.url:
                body = response.xpath('//p[not(ancestor::div[@class="tjp-newsletter-box"])]//text()').getall()

                if title is None:
                    title = response.css('div.tjp-single__head-item.tjp-single__head-item--detail > h1::text').get()

                date = response.css('div.tjp-meta > div > div.tjp-meta__content-list > div:nth-child(2)::text').get()

                if date is None:
                    print("date is None for thejakartapost")

            elif 'archive.org' in response.url:
                body = response.css('div.article p::text').getall() or \
                       response.css('div.text-long').getall() or \
                       response.css('main#maincontent > div.container.container-ia > pre::text').getall()

            else:
                body = None


            if title:
                title = title.strip()  # to remove unnecessary whitespace or newlines characters

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
                         callback=self.get_article_content,
                         meta={'title': title, 'date': date, 'article_url': new_article_url, 'body': body},  # Pass additional data here
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

            # This is an early sign that the current page after url redirection
            # is pointing to a new page containing multiple articles
            if url_had_redirected and self.parse_articles(response) is not None and \
                    (domain_name != "vietnamnews.vn" and domain_name != "en.vietnamplus.vn" and domain_name != "bangkokpost.com"):
                # these domains have articles list even in the actual article
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
        # The HTTP 202 status code generally means that the request has been received but not yet acted upon.
        if response.status == 202:
            print("response.status == 202")
            return None

        if "month ago" in date.lower() or "months ago" in date.lower() or \
            "week ago" in date.lower() or "weeks ago" in date.lower() or \
            "day ago" in date.lower() or "days ago" in date.lower() or \
            "h ago" in date.lower() or "m ago" in date.lower() or "s ago" in date.lower() or \
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

            elif search_country == 'malaysia':
                # https://en.wikipedia.org/wiki/Malaysian_movement_control_order
                date_is_within_covid_period = ((published_year >= 2020) and (published_year <= 2022))

            elif search_country == 'vietnam':
                # https://en.wikipedia.org/wiki/Timeline_of_the_COVID-19_pandemic_in_Vietnam
                date_is_within_covid_period = ((published_year >= 2020) and (published_year <= 2022))

            elif search_country == 'thailand':
                # https://en.wikipedia.org/wiki/Timeline_of_the_COVID-19_pandemic_in_Thailand
                date_is_within_covid_period = ((published_year >= 2020) and (published_year <= 2022))

            elif search_country == 'indonesia':
                # https://en.wikipedia.org/wiki/COVID-19_pandemic_in_Indonesia
                date_is_within_covid_period = ((published_year >= 2020) and (published_year <= 2023))

        print(f"date = {date}, and published_year = {published_year}, and date_is_within_covid_period = {date_is_within_covid_period}")

        # we had already retried to re-fetch the new_article_url inside get_article_content(), so if body is still an empty list,
        # this means there is either no new_article_url or the newly redirected page also had no body paragraph text
        if body == []:
            return None

        if body:
            body = [s.strip() for s in body]
            body = '\n'.join(body)
            body = body.strip()

            body = self.remove_media_credit(body)
            body = self.remove_footnote(body)

        print(f"inside write_to_local_data(), article_url = {link} , title = {title}, date = {date}, body = {body}")

        if (((title != None and any(keyword in title.lower() for keyword in search_keywords)) or \
            (body != None and any(keyword in body.lower() for keyword in search_keywords))) and \
            (date_is_within_covid_period)) or \
            (TEST_SPECIFIC and link in self.start_urls):
            # Create a unique filename for each URL by removing the 'http://', replacing '/' with '_', and adding '.html'
            file_parent_directory = ''
            original_filename = file_parent_directory + link.replace('http://', '').replace('/', '_') + '.html'
            print("filename = ", original_filename)

            # Solution to OSError: [Errno 63] File name too long : Truncate the filename
            filename_max_length = 255  # Adjust based on the filesystem's limits
            if len(original_filename) > filename_max_length:
                filename = original_filename[:filename_max_length]
            else:
                filename = original_filename

            # Write the entire body of the response to a file
            with open(filename, 'wb') as f:
                if len(original_filename) > filename_max_length:
                    f.write(original_filename.encode('utf-8'))
                    f.write('\n'.encode('utf-8'))

                f.write(body.encode('utf-8'))

        return None

