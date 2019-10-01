import requests
import re
from pprint import pprint
from bs4 import BeautifulSoup
from time import sleep
from feedgen.feed import FeedGenerator
from datetime import date
from datetime import timedelta

date = (date.today() + timedelta(days=1)).strftime("%d.%m.%Y")
url = f'http://pirkanmaa.menoinfo.fi/events?search_api_views_fulltext=&begin[date]={date}&end[date]={date}&f[0]=county:Hämeenkyrö&f[1]=county:Ikaalinen&f[2]=county:Kangasala&f[3]=county:Lempäälä&f[4]=county:Nokia&f[5]=county:Pirkkala&f[6]=county:Tampere&f[7]=county:Ylöjärvi'

movie_titles = []

def get_page_count(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    number_of_pages = soup.find("a",{"title":"Siirry viimeiselle sivulle"})["href"]
    page_number = re.search(r'search_api_views.*page=(\d+)$', number_of_pages)
    return int(page_number.group(1))
    
def parse_page(url):
    global movie_titles
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    events_raw = soup.find_all("div",["row_image_event","row_no_image_event"])
    events = []
    for event in events_raw:
        category = event.find("div","event-category-wrapper").find("a","active").string
        if category == "Seniorit": continue
        title_tag = event.find("div",{"class":"views-field-title"}).find("a")
        title = title_tag.string
        # Filter out movies duplicates
        if category == "Elokuvat":
            if title in movie_titles:
                continue
            movie_titles.append(title)
        date = event.find("div","views-field-field-event-date-and-time").find("span","field-content").string
        place = event.find("div","event-place-wrapper").string
        try:
            summary = event.find("div","views-field-body-summary").find("span","field-content").string
        except:
            summary = "summary is missing"
        event_url = f'http://pirkanmaa.menoinfo.fi{title_tag["href"]}'
        event = {'title':title, 'date': date, 'place': place, 'summary': summary, 'url': event_url, 'category': category}
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
        entry.category(term=event["category"],scheme='something')
        entry.link(href=event["url"])
    fg.atom_file('atom.xml')

if __name__ == "__main__":
    number_of_pages = get_page_count(url)
    events = []
    for i in range(0,number_of_pages+1):
        if i == 0:
            events += parse_page(url)
            continue
        single_page = f'{url}&page={i}'
        events += parse_page(single_page)
    generate_feed(events)
    print(f'Number of events: {len(events)}')
    print(f'Number of pages: {number_of_pages}')
