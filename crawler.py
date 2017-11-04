import re
from bs4 import BeautifulSoup
import requests
from bs4 import SoupStrainer
from selenium import webdriver
from time import sleep, time
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
import networkx as nx
from datetime import datetime
from sys import argv
import csv
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By

G_follow = nx.DiGraph()
G_follow.name = 'Zomato follower network'


# TIME = 5

# pickle the user and restaurant objects in files

# user_dict = {}  # stores the user objects with entity-id as the key
# rest_dict = {}  # stores the restaurant objects with entity-id as the key

css_sel = {'all_revs': '#selectors > a.item.default-section-title.everyone.empty',
           'load_more': '#reviews-container > div.notifications-content > div.res-reviews-container.res-reviews-area > div > div > div.mt0.ui.segment.res-page-load-more.zs-load-more > div.load-more.bold.ttupper.tac.cursor-pointer.fontsize2'}


class Restaurant:
    def __init__(self, link=None):
        self.link = link
        self.name = None
        self.entity_id = None
        self.cuisines = None
        self.review_count = None
        self.geo_loc = None
        self.rating = None
        self.number_of_ratings = None
        self.cost_for_two = None
        self.get_info()
        self.reviews = self.get_reviews()
        # self.get_reviews2()


    def __repr__(self):
        return '{} | {} | {} |'.format(self.name, self.entity_id, self.link)

    def __str__(self):
        return '{} | {} | {} | {} ratings | {} reviews | {} | {} | {} | \n'.format(self.name, self.entity_id, self.rating, self.number_of_ratings, self.review_count, self.geo_loc, self.link, self.cuisines)

    def get_reviews(self, start=0):
        """
        Get all the reviews of a restaurant
        :return: List of Review objects
        """
        filename = self.link.split('/')[-1]

        contents = check_file(filename, 1)

        if contents is None:
            start = time()
            driver = init_chromedriver()
            # driver = init_firefox()
            driver.get(self.link + r'/reviews')
            # print('There are {} reviews'.format(self.review_count))
            # click on the button 'All reviews'
            sleep(2)

            try:
                el = driver.find_element_by_css_selector('#selectors > a.item.default-section-title.everyone.empty')
                webdriver.ActionChains(driver).move_to_element(el).click(el).perform()
            except NoSuchElementException:
                pass

            sleep(2)
            load_more = '#reviews-container > div.notifications-content > div.res-reviews-container.res-reviews-area > div > div > div.mt0.ui.segment.res-page-load-more.zs-load-more > div.load-more.bold.ttupper.tac.cursor-pointer.fontsize2'
            while element_present(driver, load_more):
                try:
                    el2 = driver.find_element_by_css_selector(load_more)
                    driver.execute_script("return arguments[0].scrollIntoView();", el2)
                    driver.execute_script("window.scrollBy(0, -150);")
                    sleep(0.5)
                    webdriver.ActionChains(driver).move_to_element(el2).click(el2).perform()
                except (StaleElementReferenceException, NoSuchElementException):
                    break

            source = get_source(driver)
            # print(source)
            write_to_file(source, filename, 1)  # 1 for Resto
            print('{} reviews are loaded in {} secs'.format(self.review_count, time() - start))

        else:
            print('Using cached page')
            source = contents

        soup = source_to_soup(source)
        review_blocks = soup.find_all('div', class_=re.compile('ui segments res-review-body'))

        # review_blocks = (soup.find_all('div', class_='ui segment clearfix  brtop '))
        if len(review_blocks) == 0 or self.review_count == 0:
            print('Error in parsing reviews...\n')
            return
        print('Loaded {} reviews'.format(len(review_blocks)))


        with open('reviews_csv_all', 'a', encoding='utf-8') as f:

            spamwriter = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
                # spamwriter.writerow(
                #     [r.entity_id, r.name, r.rating, r.number_of_ratings, r.review_count, r.cuisines, r.link,
                #      r.cost_for_two])

            reviews = []
            i = start
            for review in review_blocks[start: ]:
                name_and_link = review.find('div', class_='header nowrap ui left')
                # print(name_and_link.contents)
                u_link = name_and_link.contents[1].attrs['href']
                u_entity_id = int(name_and_link.contents[1].attrs['data-entity_id'])
                u_name = name_and_link.contents[1].contents[0].strip()
                # print(u_name)
                rating_and_rev_text = review.find('div', text='Rated')

                r = Review()
                # r.user = User(u_link, u_entity_id)
                # if r.user.name is None:
                #     print('Invalid review, skipping')
                #     continue
                # r.user_link = u_link
                #
                r.restaurant = self
                r.time = review.find('time').attrs['datetime']
                r.rating = float(rating_and_rev_text.attrs['aria-label'].split()[-1])
                # r.review_text = rating_and_rev_text.parent.contents[2].strip()
                reviews.append(r)
                #
                # print(f'{i + 1} {u_name}', end=' ')
                # # f.write('{} | {} | {} | {} | {} | {}\n'.format(self.name, self.entity_id, r.user.name, r.user.entity_id, r.rating, r.time))
                # # f.write('{} | {} | {} | {}\n'.format(r.user.name, r.user.entity_id, r.user.followers_count, r.user.reviews_count))
                spamwriter.writerow([self.name, self.entity_id, u_name, u_entity_id, u_link, r.rating, r.time]) #, r.review_text])
                i += 1
        # # print()
        return reviews

    def get_reviews2(self):
        # driver = init_firefox()

        filename = self.link.split('/')[-1]

        contents = check_file(filename, 1)

        if contents is None:
            start = time()
            driver = init_chromedriver()

            driver.implicitly_wait(10)

            driver.get(self.link + r'/reviews')

            try:
                el = driver.find_element_by_css_selector('#selectors > a.item.default-section-title.everyone.empty')
                webdriver.ActionChains(driver).move_to_element(el).click(el).perform()
                driver.execute_script("return arguments[0].scrollIntoView();", el)
                driver.execute_script("window.scrollBy(0, -150);")
                sleep(2)
                ActionChains(driver).click(el).perform()
            except NoSuchElementException:
                pass

            while element_present(driver, css_sel['load_more']):
                el = driver.find_element_by_css_selector(css_sel['load_more'])
                driver.execute_script("return arguments[0].scrollIntoView();", el)
                driver.execute_script("window.scrollBy(0, -150);")
                print(el.text)
                sleep(1)
                ActionChains(driver).click(el).perform()
            source = get_source(driver)
            # print(source)
            write_to_file(source, filename, 1)  # 1 for Resto
            print('{} reviews are loaded in {} secs'.format(self.review_count, time() - start))


    def get_info(self):
        """
        Populates the name, cuisines, entity_id,....
        :return: list of cuisines (str)
        """

        soup = extract_link(self.link)

        if soup is None:
            return

        try:

            self.name = soup.find('a', class_='ui large header left').text.strip()
            print('Visiting ', self.name)

            self.entity_id = int(soup.find(id='resinfo-wtt').attrs['data-entity-id'])
            # review_count = soup.find('a', {'href': '{}/reviews'.format(self.link), 'class': 'item respageMenu-item '}).text
            # reviews_count = list(soup.find('div', class_='review-sorting text-tabs selectors ui secondary pointing menu mt0').children)
            try:
                rev_count_block = soup.find_all('a', {'data-sort': 'reviews-dd'})[0]
                self.review_count = int(rev_count_block.contents[1].text)
            except IndexError:
                rev_count = 0

            print('{} reviews'.format(self.review_count))

            cuisine_block = soup.find('div', class_='res-info-cuisines clearfix')
            list_of_cuisines = []
            for cuisine in cuisine_block.find_all('a', class_='zred'):
                list_of_cuisines.append(cuisine.text.strip())

            self.cuisines = ','.join(list_of_cuisines)

            self.rating = float(soup.find('div', {'aria-label': 'Rated'}).contents[0])

            # geo location
            try:

                loc_text = soup.find(id='res-map-canvas').next_sibling.next_sibling.text.strip()
                lat, long = loc_text[loc_text.find('{') + 1: loc_text.find('}')].split(',')
                lat = float(lat[lat.find(':') + 2:])
                long = float(long[long.find(':') + 2:])
                self.geo_loc = (lat, long)
            except AttributeError:
                self.geo_loc = None  # restaurant's GPS location is not available

            number_of_ratings_block = soup.find('span', class_=re.compile('mt2 mb0 rating-votes-div rrw-votes grey-text fontsize5 ta-right'))
            self.number_of_ratings = int(number_of_ratings_block.find('span', {'itemprop': 'ratingCount'}).contents[0])

            # cost for two


        except:
            pass


class Review:
    def __init__(self):
        self.user = None
        self.user_link = None
        self.restaurant = None
        self.time = None
        self.rating = None
        self.review_text = None

    def __repr__(self):
        return '{} | Rating: {} | {} | '.format(self.restaurant.name, self.rating, self.time)

    def __str__(self):
        return '{} | {} | {} | {} | {} | {} | {} |\n '.format(self.restaurant.name, self.user.name, self.user_link,
                                                              self.user.entity_id, self.rating, self.time,
                                                              self.review_text)


class User:
    def __init__(self, link, entity_id):
        self.name = None
        self.entity_id = entity_id
        self.location = None
        self.link = link
        self.reviews_count = None
        self.followers_count = None
        self.been_there_count = None
        self.reviews = None
        self.init_user()

    def __str__(self):
        return '{} | {} | {} | ' \
               '{} | reviews: {} | followers: {} | been there: {} | '.format(self.name,
                                                                             self.entity_id,
                                                                             self.location,
                                                                             self.link,
                                                                             self.reviews_count,
                                                                             self.followers_count,
                                                                             self.been_there_count)

    def __repr__(self):
        return '{} | {} | {} | '.format(self.name, self.entity_id, self.link)

    def followers(self):
        """
        Gets the followers of the user as a list of users
        :return: generator of followers
        """

        followers = []
        filename = self.link.split('/')[-1]

        contents = check_file(filename, 2)

        if contents is None:  # file is not cached
            start = time()
            driver = init_chromedriver()
            driver.get(self.link + r'/network')

            sleep(5)
            load_more = '#network > div > div:nth-child(1) > div > div.ui.segment.col-l-16.tac.zs-load-more.mbot > div'
            while element_present(driver, load_more):
                print('Clicking load more!')

                try:
                    el2 = driver.find_element_by_css_selector(load_more)
                    driver.execute_script("return arguments[0].scrollIntoView();", el2)
                    driver.execute_script("window.scrollBy(0, -150);")
                    sleep(2)
                    ActionChains(driver).move_to_element(el2).click(el2).perform()
                except StaleElementReferenceException:
                    break
            print('Page loaded in {} secs'.format(time() - start))
            source = get_source(driver)
            filename = driver.current_url.split('/')[-2]
            write_to_file(source, filename, 2)  # caching the page
        else:
            source = contents

        soup = source_to_soup(source)

        # now to find all the followers!!
        elements = soup.find_all('div', class_='header nowrap')
        print('{} has {} followers'.format(self.name, self.followers_count))

        with open('followers', 'a', encoding='utf-8') as f:
            f.write('\n\n-------------\t{}\t------------------\n\n'.format(datetime.now()))
            f.write('{}\nFollowers\n'.format(self))
            for i, element in enumerate(elements[: self.followers_count]):
                dic = element.contents[1].attrs
                follower = User(link=dic['href'], entity_id=int(dic['data-entity_id']))
                if follower is None:
                    continue

                f.write('({}) {}\n'.format(i + 1, follower))
                print('({}) {}\n'.format(i + 1, follower))
                # print('({}) Adding edge between {} and {}'.format(i + 1, self.name, follower.name))
                # yield follower
                # followers.append(follower)
                # G.add_edge(self, follower)

        print('Successfully parsed all the followers')
        # print(followers[: 2])
        # print('-------------------')
        return followers

    def get_reviews(self):
        """
        Get all the reviews
        :return: list of Review objects
        """

        filename = self.link.split('/')[-1]
        contents = check_file(filename, 3)

        if contents is None:
            start = time()
            driver = init_chromedriver()
            driver.get(self.link + r'/reviews')
            sleep(2)
            while True:
                elements = driver.find_elements_by_css_selector(r'#reviews-container > div > div.bt.zs-load-more.mtop > div.load-more.ui.segment.tac')
                if len(elements) == 0:
                    break
                ac = ActionChains(driver).move_to_element(elements[0])
                ac.click().perform()
                sleep(5)

            print('Done loading {} reviews in {} secs...'.format(self.reviews_count), time() - start)

            source = get_source(driver)
            write_to_file(source, filename, 3)
        else:
            print('File in cache!')
            source = contents

        soup = source_to_soup(source)
        review_blocks = soup.find_all('div', class_='ui segment brtop')
        print('No of reviews: {}'.format(len(review_blocks)))

        self.reviews = []

        for review_block in review_blocks:
            review_header = review_block.find('div', class_='res-review-header')  # resto name, resto link, timestamp
            review_body = review_block.find('div', class_='res-review-body')

            name_and_link = review_header.find('a', {'data-entity_type': 'RESTAURANT'})

            restaurant = Restaurant(name_and_link.attrs['href'])
            restaurant.name = name_and_link.contents[0]
            restaurant.entity_id = name_and_link.attrs['data-entity_id']

            review = Review()
            review.restaurant = restaurant
            review.time = review_header.find('time').attrs['datetime']
            review.rating = float(review_body.find('div', string='Rated').attrs['aria-label'].split()[-1])
            review.review_text = review_body.find('div', class_='rev-text').text.strip().replace('Rated ', '')

            self.reviews.append(review)

        print('Parsed {} reviews'.format(len(self.reviews)))

    def init_user(self):
        """
            initializes the user - populates name, id, location, no of reviews, followers, been there
            :return: an User object
        """
        soup = extract_link(self.link)
        if soup is None:
            return None

        try:
            name_and_link = list(soup.find('div', class_='user-header-info-middle').children)[1].contents[1].contents[0]
            self.name = name_and_link.contents[0].strip()
            self.link = name_and_link.attrs['href']
            self.location = soup.find('div', class_='meta ').contents[0].strip()
            self.reviews_count = int(list(soup.find('a', {'data-tab': 'reviews'}).children)[1].contents[0])
            self.followers_count = int(list(soup.find('a', {'data-tab': 'network'}).children)[1].contents[0])
            self.been_there_count = int(list(soup.find('a', {'data-tab': 'beenthere'}).children)[1].contents[0])
        except AttributeError:
            pass


def source_to_soup(page_source):
    """
    takes in page source, removes br tags and makes a Beautiful Soup object
    """
    page_source = re.sub('<br>', '', page_source)
    page_source = re.sub('<br/', '', page_source)
    page_source = re.sub('<br />', '', page_source)
    return BeautifulSoup(page_source, 'html.parser', parse_only=SoupStrainer('div'))


def extract_link(url):
    """
    Creates a BeautifulSoup object from the link
    :param url: the link
    :return: a BeautifulSoup object equivalent of the url
    """
    headers = {"Host": "www.zomato.com",
               "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.5",
               "Accept-Encoding": "gzip, deflate, br",
               "Referer": "https://www.zomato.com/",
               "Connection": "keep-alive"}

    if url.startswith('file'):
        with open(url.replace('file:\\\\', ''), encoding='utf-8') as fp:
            page_source = fp.read()

    else:
        r = requests.get(url, headers=headers)
        if r.status_code == 404:
            return None
        page_source = r.text

    page_source = re.sub('<br>', '', page_source)
    page_source = re.sub('<br />', '', page_source)
    page_source = re.sub('<br/>', '', page_source)
    soup = BeautifulSoup(page_source, 'html.parser')

    return soup


def init_chromedriver():
    """
    Initializes the chromedriver to not to load images
    :return: A chromedriver object
    """
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2, "profile.default_content_settings.state.flash": 0}
    chrome_options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome('./chromedriver', chrome_options=chrome_options)


def init_firefox():
    firefox_profile = webdriver.FirefoxProfile()
    # firefox_profile.set_preference('permissions.default.stylesheet', 2)
    firefox_profile.set_preference('permissions.default.image', 2)
    firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')

    return webdriver.Firefox(firefox_profile=firefox_profile)


def element_present(driver, sel):
    try:
        driver.find_element_by_css_selector(sel)
        return True
    except (NoSuchElementException, StaleElementReferenceException):
        return False


def get_source(driver):
    """
    Returns the page source - waits until it detects <html> tag
    :param driver:
    :return: the page source
    """
    sleep(5)
    while True:
        source = driver.page_source
        if '<html' in source:
            return source
        else:
            print('Waiting for page to load')
            sleep(5)


def write_to_file(source, filename, type):
    """
    Writes the source to a file.
    Type = 1 for Restaurant review, 2 for user follower,
    3 for user review
    """
    path = './scraped_pages'
    if type == 1:
        path += '/Restaurants/' + filename
    elif type == 2:
        path += '/Users/Followers/' + filename
    elif type == 3:
        path += '/Users/Reviews/' + filename

    with open(path, 'w', encoding='utf-8') as f:
        f.write(source)

    print('Source saved for {}'.format(filename))


def check_file(filename, type):
    """
    Checks if a webpage has already been cached in the disk, if so, return the contents
    otherwise return None
    type 1 for restaurant review, 2 for user follower, 3 for user reviews
    """
    path = './scraped_pages'
    if type == 1:
        path += '/Restaurants/' + filename
    elif type == 2:
        path += '/Users/Followers/' + filename
    elif type == 3:
        path += '/Users/Reviews/' + filename

    contents = None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            contents = f.read()
    except FileNotFoundError:
        print('File not in cache, loading the page')
    return contents


def fn():
    if len(argv) < 2:
        print('Enter link of restaurant')
        return
    elif len(argv) < 3:
        start_idx = 0
    else:
        start_idx = int(argv[2])
    start = time()
    r = Restaurant(argv[1])
    r.get_reviews(start_idx)
    print('Done in {} secs'.format(time() - start))
    # h()
    # g()

def get_restaurant_from_page(restaurant_card):
    '''
    link, name, entity_id, cuisines, review_count, geo_loc, rating, number_of_rating, cost_for_two

    :param restaurant_card:
    :return:
    '''
    r = Restaurant()

    try:

        r.name = restaurant_card.find('a', class_=re.compile('result-title hover_feedback zred bold ln24')).contents[0].strip()
        r.link = restaurant_card.find('a', class_=re.compile('result-title hover_feedback zred bold ln24')).attrs['href'].strip()
        r.entity_id = int(restaurant_card.find('div', class_=re.compile('js-search-result-li even')).attrs['data-res_id'])
        r.cost_for_two = int(restaurant_card.find('span', class_=re.compile('col-s-11 col-m-12 pl0')).contents[0].strip()[1: ].replace(',', ''))
        print(r.name)

        cuisines = restaurant_card.find('span', class_=re.compile('col-s-11 col-m-12 nowrap '))

        list_of_cuisines = []
        for cuisine in cuisines.contents:
            if len(cuisine) == 1:
                list_of_cuisines.append(cuisine.attrs['title'].strip())

        r.cuisines = ','.join(list_of_cuisines)
        r.rating = float(restaurant_card.find('div', class_=re.compile('rating-popup rating')).contents[0].strip())
        r.number_of_ratings = int(restaurant_card.find('span', class_=re.compile('rating-votes-div')).contents[0].split()[0])
        r.review_count = int(restaurant_card.find('a', {'data-result-type': 'ResCard_Reviews'}).contents[0].split()[0])


    except:
        pass
    return r

def get_all_restaurants(link, csv_file):
    soup = extract_link(link)

    restaurant_cards = soup.find_all('div', class_=re.compile('card search-snippet-card'))
    # print(len(restaurant_cards))



        # with open(csv_file, 'a') as csvfile:
        #     spamwriter = csv.writer(csvfile,
        #                             quoting=csv.QUOTE_NONNUMERIC)
        # for restaurant_card in restaurant_cards:
        #     # link = restaurant_card.find('a', class_=re.compile('result-title hover_feedback zred bold ln24')).attrs['href']
        #     r = get_restaurant_from_page(restaurant_card)
        #     spamwriter.writerow([r.entity_id, r.name, r.rating, r.number_of_ratings, r.review_count, r.cuisines, r.link, r.cost_for_two])


def get_all_resto_driver():
    csv_file = 'restaurant_info_chennai.csv'
    # with open(csv_file, 'w') as csvfile:
    #     spamwriter = csv.writer(csvfile,
    #                             quoting=csv.QUOTE_NONNUMERIC)
    #     spamwriter.writerow(['Rest_id', 'Rest_name', 'Rating', 'Number_of_ratings', 'Reviews', 'Cuisines', 'Link', 'Cost_for_two'])

    #
    link = 'https://www.zomato.com/chennai/restaurants?page='
    for i in range(135, 136):
        print('Page: {}'.format(i))
        get_all_restaurants(link + str(i), csv_file)


def test_review():

    urls = []
    with open('./csv_all_restos/restaurant_info_kolkata.csv') as csv_file:
        resto_reader = csv.DictReader(csv_file)
        for row in resto_reader:
            # print(row['Link'])
            urls.append(row['Link'].split('/')[-1])

    for i in range(0, 3783):
        url = 'https://www.zomato.com/kolkata/' + urls[i]
        print(url)
        try:
            r = Restaurant(url)
        except:
            continue
def main():
    test_review()


if __name__ == '__main__':
    main()
