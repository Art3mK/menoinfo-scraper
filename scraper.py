import requests
import re
from pprint import pprint
from bs4 import BeautifulSoup
from time import sleep
from feedgen.feed import FeedGenerator
from datetime import date
from datetime import datetime
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
        parsed_event = {}
        parsed_event['category'] = event.find("div","event-category-wrapper").find("a","active").string
        if parsed_event['category'] == "Seniorit": continue
        # title_tag is used below to find event url
        title_tag = event.find("div",{"class":"views-field-title"}).find("a")
        parsed_event['title'] = title_tag.string
        # Filter out movies duplicates
        if parsed_event['category'] == "Elokuvat":
            if parsed_event['title'] in movie_titles:
                continue
            movie_titles.append(parsed_event['title'])
        date = event.find("div","views-field-field-event-date-and-time").find("span","field-content").string
        parsed_event['date'] = date
        try:
            start_date, end_date = [datetime.strptime(x, "%d.%m.%Y") for x in date.split('–')]
            delta = end_date - start_date
            parsed_event['start_date'] = start_date
            parsed_event['end_date'] = end_date
            parsed_event['duration_days'] = (end_date - start_date).days
        except ValueError:
            # probably no delimiter there, and only single day is in string
            event_date = datetime.strptime(date, "%d.%m.%Y")
            parsed_event['start_date'] = event_date
            parsed_event['end_date'] = event_date
            parsed_event['duration_days'] = 1
        parsed_event['place'] = event.find("div","event-place-wrapper").string
        try:
            parsed_event['summary'] = event.find("div","views-field-body-summary").find("span","field-content").string
        except:
            parsed_event['summary'] = "summary is missing"
        parsed_event['url'] = f'http://pirkanmaa.menoinfo.fi{title_tag["href"]}'
        events.append(parsed_event)
    return events

def generate_feed(events):
    fg = FeedGenerator()
    fg.id('https://feeds.awsome.click/menoinfo/')
    fg.title('Artem Kajalainen\'s menoinfo filter feed for pirkanmaa.menoinfo.fi')
    fg.author( {'name':'Artem Kajalainen','email':'artem@kayalaynen.ru'} )
    fg.link( href='http://feeds.awsome.click/menoinfo/atom.xml', rel='self' )
    fg.language('fi')
    for event in events:
        if event['duration_days'] > 60:
            pass
            # TODO
            # типа добавлять event в стрим раз в неделю?
            # и нужно будет менять guid ему, чтобы аггрегатор показывал, что это новый event
            # хранить где-то счетчик для ссылок что ли7 Или просто добавлять к url сегодняшнюю дату
        entry = fg.add_entry()
        entry.id(event["url"])
        entry.title(f'{event["title"]} @ {event["date"]}')
        entry.summary(event["summary"])
        entry.category(term=event["category"])
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
