import requests
import re
from pprint import pprint
from bs4 import BeautifulSoup
from time import sleep
from feedgen.feed import FeedGenerator
from datetime import date, datetime, timedelta
import boto3

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
        raw_date = event.find("div","views-field-field-event-date-and-time").find("span","field-content").string
        parsed_event['date'] = raw_date
        try:
            start_date, end_date = [datetime.strptime(x, "%d.%m.%Y") for x in raw_date.split('–')]
            delta = end_date - start_date
            parsed_event['start_date'] = start_date
            parsed_event['end_date'] = end_date
            parsed_event['duration_days'] = (end_date - start_date).days + 1
        except ValueError:
            # probably no delimiter there, and only single day is in string
            event_date = datetime.strptime(raw_date, "%d.%m.%Y")
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

def filter_event(event, search_date, single_day_events_only=False):
    event_duration = event['duration_days']
    # used to filter out events for specific days without taking into account day of week, month, etc
    if single_day_events_only:
        if event_duration == 1 and event['start_date'].date() == search_date:
            return True
        else:
            return False
    # If event lasts only single day and it's on search date -> return
    if event_duration == 1 and event['start_date'].date() == search_date:
        return True
    # some long lasting events, show weekly
    elif 1 < event_duration < 31 and date.today().weekday() == 6:
        return True
    # very long events, show monthly
    elif event_duration > 31 and date.today().day == 1:
        return True
    else:
        return False

def generate_feed(events):
    fg = FeedGenerator()
    fg.id('https://feeds.awsome.click/menoinfo/')
    fg.title('Artem Kajalainen\'s menoinfo filter feed for pirkanmaa.menoinfo.fi')
    fg.author( {'name':'Artem Kajalainen','email':'artem@kayalaynen.ru'} )
    fg.link( href='http://feeds.awsome.click/menoinfo/atom.xml', rel='self' )
    fg.language('fi')
    today_string = date.today().strftime("%d.%m.%Y")
    for event in events:
        entry = fg.add_entry()
        if event['duration_days'] > 1:
            # next time the long lasting same event appears in stream - id will change with current date, so
            # client will show it again
            event_id = f'{event["url"]}-{today_string}'
        else:
            event_id = event["url"]
        entry.id(event_id)
        entry.title(f'{event["title"]} @ {event["date"]}')
        entry.summary(event["summary"])
        entry.category(term=event["category"], label=event["category"])
        entry.link(href=event["url"])
    fg.atom_file('/tmp/atom.xml')

def main():
    search_date = date.today() + timedelta(weeks=2)
    end_date = search_date
    if (date.today().weekday() == 6):
        end_date = (search_date + timedelta(days=7))
        print(f'searching from {search_date.strftime("%d.%m.%Y")} till {end_date.strftime("%d.%m.%Y")}')
    url = f'http://pirkanmaa.menoinfo.fi/events?search_api_views_fulltext=&begin[date]={search_date.strftime("%d.%m.%Y")}&end[date]={end_date.strftime("%d.%m.%Y")}&end[time]=23:59&f[0]=county:Hämeenkyrö&f[1]=county:Ikaalinen&f[2]=county:Kangasala&f[3]=county:Lempäälä&f[4]=county:Nokia&f[5]=county:Pirkkala&f[6]=county:Tampere&f[7]=county:Ylöjärvi'
    print(url)

    number_of_pages = get_page_count(url)
    events = []
    for i in range(0,number_of_pages+1):
        if i == 0:
            events += parse_page(url)
            continue
        single_page = f'{url}&page={i}'
        events += parse_page(single_page)
    events = [event for event in events if filter_event(event, search_date)]
    print(f'Number of events: {len(events)}')

    # search for single day events for next week (duplicates are filtered out on client side by id)
    # закрывает кейс, когда ивент был добавлен за время, меньшее чем 2 недели до его начала.
    search_date = date.today() + timedelta(weeks=1)
    end_date = search_date
    url = f'http://pirkanmaa.menoinfo.fi/events?search_api_views_fulltext=&begin[date]={search_date.strftime("%d.%m.%Y")}&end[date]={end_date.strftime("%d.%m.%Y")}&end[time]=23:59&f[0]=county:Hämeenkyrö&f[1]=county:Ikaalinen&f[2]=county:Kangasala&f[3]=county:Lempäälä&f[4]=county:Nokia&f[5]=county:Pirkkala&f[6]=county:Tampere&f[7]=county:Ylöjärvi'
    print(url)
    one_day_events = []
    number_of_pages = get_page_count(url)
    for i in range(0,number_of_pages+1):
        if i == 0:
            one_day_events += parse_page(url)
            continue
        single_page = f'{url}&page={i}'
        one_day_events += parse_page(single_page)
    one_day_events = [event for event in one_day_events if filter_event(event, search_date, single_day_events_only=True)]
    events += one_day_events
    generate_feed(events)
    print(f'Number of events: {len(events)}')
    print(f'Number of pages: {number_of_pages}')

if __name__ == "__main__":
    main()

def lambda_handler(event, context):
    main()
    s3 = boto3.client('s3')
    filename = '/tmp/atom.xml'
    bucket_name = 'feeds.awsome.click'
    # Uploads the given file using a managed uploader, which will split up large
    # files automatically and upload parts in parallel.
    s3.upload_file(filename, bucket_name, 'menoinfo/atom.xml', ExtraArgs={'ACL':'public-read', 'ContentType': "text/xml"})
