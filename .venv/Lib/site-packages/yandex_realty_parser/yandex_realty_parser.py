import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
import re
from ratelimit import limits, sleep_and_retry


@sleep_and_retry
@limits(calls=1, period=5)
def get(*args, **kwargs):
    return requests.get(*args, **kwargs)


def parse(link: str,
          headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/116.0',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                   'Accept-Language': 'en-GB,en;q=0.5',
                   'Accept-Encoding': 'gzip, deflate, br'},
          start_page=1, end_page=None, fields=('link', 'address')):
    flats = []
    amount_of_flats = 0
    if end_page is None:
        end_page = int(re.search('page=(\d+)', get(link + '&page=500', headers=headers).url).group(1)) + 1
    for page in (pbar := tqdm(range(start_page, end_page + 1))):
        pbar.set_description(f'Page: {page}', refresh=True)
        html = get(link + f'&page={page-1}', headers=headers).text
        soup = BeautifulSoup(html, features='lxml')
        flats_on_page = soup.find_all(class_=re.compile('Item__info-inner$'))
        amount_of_flats_on_page = len(flats_on_page)
        amount_of_flats += amount_of_flats_on_page
        data = {}
        data['link'] = ['https://realty.ya.ru' + x.a['href'] for x in flats_on_page]
        data['address'] = [' '.join(list(map(lambda y: y.text, x.find(
            class_=re.compile('address$')).find_all('a')))) for x in flats_on_page]
        flats.extend(({'link': x, 'address': y} for x, y in zip(data['link'], data['address'])))
        is_next = soup.find(string='Следующая')
        if is_next is None and page != end_page:
            tqdm.write(f'Exception: There isn\'t page {page+1}. Aborting...')
            break
        pbar.set_postfix({'flats': amount_of_flats})

    return flats


if __name__ == "__main__":
    parse('https://realty.ya.ru/moskva/snyat/kvartira/odnokomnatnaya/?priceMax=42500&priceMin=38500', start_page=24)
