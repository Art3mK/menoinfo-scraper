import requests
import re
from pprint import pprint
from bs4 import BeautifulSoup
from time import sleep

url = 'http://pirkanmaa.menoinfo.fi/events?search_api_views_fulltext=&begin%5Bdate%5D=27.09.2019&begin%5Btime%5D=21%3A00&end%5Bdate%5D=27.09.2019&end%5Btime%5D=23%3A59'

def get_page_count(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    number_of_pages = soup.find("a",{"title":"Siirry viimeiselle sivulle"})["href"]
    page_number = re.search(r'search_api_views.*page=(\d+)$', number_of_pages)
    return int(page_number.group(1))
    
def parse_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    events = soup.find_all("div",["row_image_event","row_no_image_event"])
    titles = []
    for event in events:
        title = event.find("div",{"class":"views-field-title"}).find("a").string
        titles.append(title)
    return titles

if __name__ == "__main__":
    number_of_pages = get_page_count(url)
    titles = []
    for i in range(1,number_of_pages+1):
        single_page = f'{url}&page={i}'
        titles += parse_page(single_page)
        sleep(0.5)
    pprint(titles)

    