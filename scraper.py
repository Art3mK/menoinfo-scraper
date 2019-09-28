import requests
import re
from pprint import pprint
from bs4 import BeautifulSoup
from time import sleep
from feedgen.feed import FeedGenerator

url = 'http://pirkanmaa.menoinfo.fi/events?search_api_views_fulltext=&begin%5Bdate%5D=29.09.2019&begin%5Btime%5D=08%3A00&end%5Bdate%5D=29.09.2019&end%5Btime%5D=23%3A59&f[0]=county%3AHämeenkyrö&f[1]=county%3AIkaalinen&f[2]=county%3AKangasala&f[3]=county%3ALempäälä&f[4]=county%3ANokia&f[5]=county%3APirkkala&f[6]=county%3ATampere&f[7]=county%3AYlöjärvi'

def get_page_count(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    number_of_pages = soup.find("a",{"title":"Siirry viimeiselle sivulle"})["href"]
    page_number = re.search(r'search_api_views.*page=(\d+)$', number_of_pages)
    return int(page_number.group(1))
    
def parse_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    events_raw = soup.find_all("div",["row_image_event","row_no_image_event"])
    events = []
    for event in events_raw:
        category = event.find("div","event-category-wrapper").find("a","active").string
        if category == "Seniorit": continue
        date = event.find("div","views-field-field-event-date-and-time").find("span","field-content").string
        place = event.find("div","event-place-wrapper").string
        try:
            summary = event.find("div","views-field-body-summary").find("span","field-content").string
        except:
            summary = "summary is missing"
        title_tag = event.find("div",{"class":"views-field-title"}).find("a")
        title = title_tag.string
        event_url = f'http://pirkanmaa.menoinfo.fi{title_tag["href"]}'
        event = {'title':title, 'date': date, 'place': place, 'summary': summary, 'url': event_url}
        events.append(event)
    return events

def generate_feed(events):
    fg = FeedGenerator()
    fg.id('https://feeds.awsome.click/menoinfo/')
    fg.title('Artem Kajalainen\'s menoinfo filter feed for pirkanmaa.menoinfo.fi')
    fg.author( {'name':'Artem Kajalainen','email':'artem@kayalaynen.ru'} )
    fg.link( href='https://feeds.awsome.click/menoinfo/', rel='alternate' )
    # fg.link( href='http://larskiesow.de/test.atom', rel='self' )
    fg.language('fi')
    for event in events:
        entry = fg.add_entry()
        entry.id(event["url"])
        entry.title(event["title"])
        entry.summary(event["summary"])
        entry.link(href=event["url"])
    fg.atom_file('atom.xml')

if __name__ == "__main__":
    number_of_pages = get_page_count(url)
    events = []
    for i in range(1,number_of_pages+1):
        single_page = f'{url}&page={i}'
        events += parse_page(single_page)
    generate_feed(events)
    print(f'Number of events: {len(events)}')
    print(f'Number of pages: {number_of_pages}')
