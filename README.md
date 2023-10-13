# covid-scraper
A simple scrapy-splash code for covid related media scraper

Command :

`sudo systemctl start docker`

`sudo docker run --restart=always -p 8050:8050 scrapinghub/splash`

`scrapy crawl covid_news_spider &> scrapy.log`
