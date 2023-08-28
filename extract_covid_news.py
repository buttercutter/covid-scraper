import newspaper
from newspaper import Article
import json
from json import JSONDecodeError
import requests
import feedparser
import googleapiclient.discovery
from gnews import GNews
from bs4 import BeautifulSoup


# Define preferred sources and search keywords
preferred_sources = ['The Straits Times', 'CNA', 'channelnewsasia', 'The New Paper']
search_keywords = ['covid','virus','pandemic','vaccine','corona','vaccination','circuit breaker','SARS-CoV-2']

# GNews
google_news = GNews()
covid_news = google_news.get_news('Singapore covid vaccine')[:1000]
filtered_gnews = [item for item in covid_news if item['publisher']['title'] in preferred_sources]

# News API
api_key = '8b0c825ef9bf44e79efc486f980afe68'
newsapi_url = 'https://newsapi.org/v2/everything?q=covid&sortBy=publishedAt&apiKey='+api_key
newsapi_response = requests.get(newsapi_url)
newsapi_data = newsapi_response.json()['articles']
#print("newsapi_data = ", newsapi_data)
filtered_newsapi_data = []
filtered_newsapi_data += [item for item in newsapi_data if item['source']['name'] in preferred_sources]
filtered_newsapi_data += [item for item in newsapi_data
                          if any(keyword in item['title'].lower()
                                for keyword in search_keywords)]
filtered_newsapi_data += [item for item in newsapi_data
                          if any(keyword in item['description'].lower()
                                for keyword in search_keywords)]

# Feedly/RSS
#feed = feedparser.parse("https://www.channelnewsasia.com/topics/covid-19")
feed = feedparser.parse("https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=10416")
rss_articles = feed['entries']
#print("rss_articles = ", rss_articles)
filtered_rss_articles = []
filtered_rss_articles += [article for article in rss_articles
                        if any(keyword in article['title'].lower()
                               for keyword in search_keywords)]
filtered_rss_articles += [article for article in rss_articles
                        if any(keyword in article['summary'].lower()
                               for keyword in search_keywords)]

# Google custom search API
api_key = 'AIzaSyCQbrv_4LC9VgP-rL4AgAjt9AGnXZbODTo'
customsearch = googleapiclient.discovery.build(
  "customsearch", "v1", developerKey=api_key)  # https://developers.google.com/custom-search/v1/introduction

search_params = {'q': 'covid',
                 'cx': 'b2efcfd5bcdc54e2b'} # Search engine ID, https://cse.google.com/cse?cx=b2efcfd5bcdc54e2b

results = customsearch.cse().list(**search_params).execute()
articles = results['items']
#print("google custom search articles = ", articles)
filtered_google_custom_search = []
preferred = ['straitstimes', 'channelnewsasia']

for article in articles:
    source = article['pagemap']['metatags'][0].get('og:site_name', '')
    #if source in preferred:
    filtered_google_custom_search.append(article)

#for article in filtered_google_custom_search:
  #print(article['title'])


# Newspaper3k
paper = newspaper.build('https://www.straitstimes.com', memoize_articles=False)
paper = newspaper.build('https://www.channelnewsasia.com', memoize_articles=False)
articles = paper.articles
#print("newspaper3k articles = ", articles)
filtered_newspaper3k = []
filtered_newspaper3k += [article for article in articles
                       if any(keyword in article.title
                              for keyword in search_keywords)]
#for article in filtered_newspaper3k:
#    print("filtered newspaper3k articles = ", article.title)

# GDELT API
# keywords : circuit breaker, vaccine, corona virus, SARS covid
gdelt_url = 'https://api.gdeltproject.org/api/v2/doc/doc?query=%22vaccine%20Covid%22&mode=artlist&maxrecords=250&format=json&startdate=2020-08-01&enddate=2022-08-01'
gdelt_response = requests.get(gdelt_url)

if gdelt_response.status_code != 200:
    print("GDELT request failed:", gdelt_response.status_code)

#print("gdelt text = ", gdelt_response.text)
#print("gdelt json = ", gdelt_response.json())

response_json = gdelt_response.json()
if not response_json:
    print("Empty GDELT response")
    exit

try:
  gdelt_data = gdelt_response.json()['articles']
except JSONDecodeError:
  print("gdelt JSON decoding failed")

filtered_gdelt_data = [
  item for item in gdelt_data
  if (item['sourcecountry'] == 'United States')
  #if any(source in item['url'] for source in preferred_sources)
]


# Directly scrapes the HTML
url = 'https://www.straitstimes.com'
url = 'https://www.channelnewsasia.com'

# Check Content-Encoding header
response = requests.head(url)
content_encoding = response.headers.get('Content-Encoding')

# Disable gzip decoding
headers = {'Accept-Encoding': 'identity'}

# Add standard headers
headers.update({
  'User-Agent': 'MyScraper/1.0',
  'From': 'myemail@domain.com'
})

try:
  # Make GET request
  response = requests.get(url, headers=headers)

  # Handle ContentDecodingError
  html = response.text

except requests.exceptions.ContentDecodingError:
  print("ContentDecodingError occurred, using raw response")
  html = response.text

soup = BeautifulSoup(html, 'html.parser')

articles = soup.find_all('article')
covid_articles = []

no_title = True
no_covid_article = True

for article in articles:
    title_els = article.find_all(['h1','h2','h3'])
    for el in title_els:
        if el.text:
            title = el.text
            no_title = False
        break

    if any(keyword in title.lower() for keyword in search_keywords):
        covid_articles.append({'title': title})
        no_covid_article = False

print("no_title = ", no_title)
print("no_covid_article = ", no_covid_article)
print("COVID articles:", covid_articles)


# Write to file
covidnews = filtered_gnews + \
            filtered_newsapi_data + \
            filtered_google_custom_search + \
            filtered_rss_articles + \
            filtered_newspaper3k + \
            filtered_gdelt_data

print("len(filtered_gnews) = ", len(filtered_gnews))
print("len(filtered_newsapi_data) = ", len(filtered_newsapi_data))
print("len(filtered_google_custom_search) = ", len(filtered_google_custom_search))
print("len(filtered_rss_articles) = ", len(filtered_rss_articles))
print("len(filtered_newpaper3k) = ", len(filtered_newspaper3k))
print("len(filtered_gdelt_data) = ", len(filtered_gdelt_data))

print("len(covidnews) = ", len(covidnews))

with open('covid_news.txt', 'w') as f:
    for article in covidnews:
        if hasattr(article, 'title'):
            f.write(f"Title: {article.title}\n")
        else:
            f.write(f"Title: {article['title']}\n")
        #f.write(f"Description: {article['description']}\n")
        #f.write(f"Published At: {article['publisher']}\n")
        f.write("\n")
