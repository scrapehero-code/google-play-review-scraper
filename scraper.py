import re
import csv
import json
from datetime import datetime

import requests
from lxml import html


def get_app_id(search_query: str) -> str:
    """
    Function to get app_id

    Args:
        search_query (string): Name of the app

    Returns:
        string: app_id corresponding to the the search query
    """
    url = 'https://play.google.com/store/search'

    params = {
        'q': search_query,
        'c': 'apps',
        'hl': 'en',
        'gl': 'US',
    }

    headers = {
        'authority': 'play.google.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
        'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;'
        'v=b3;q=0.7',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    response = requests.get(url=url, headers=headers, params=params, timeout=30)
    parser = html.fromstring(response.text)
    try:
        app_id = parser.xpath('//a[@class="Qfxief"]/@href')[0].split('id=')[1]
        return app_id
    except IndexError:
        print('No app_id found.')


def review_pagination(app_id: str, page_count: int = 20) -> list[dict]:
    """
    Function to get the required number of pages of reviews

    Args:
        app_id (string): unique id of the application

    Returns:
        list: A list of dictionaries where each dictionary is a review
    """
    all_reviews = []

    pagination_token = None
    current_page = 1
    while True:
        reviews, pagination_token = get_reviews(
            app_id, pagination_token=pagination_token)
        all_reviews.extend(reviews)
        if not pagination_token or current_page == page_count:
            break
        current_page += 1
    return all_reviews


def get_reviews(app_id: str, count: int = 50,
                device_id: int = 2, pagination_token: str = None, sort: int = 2, star_count: int = None) -> list[dict]:
    """This function gets the app reviews according to the given parameters
    Args:
        app_id (string): unique id of the application
        count (int, optional): Number of reviews to be returned in the response. Defaults to 50.
        device_id (int, optional): Id representing the device of which the reviews are needed. Defaults to 2(Mobile).
        pagination_token (string, optional): Token to get the next set of reviews. Defaults to None.
        sort (int, optional): Number representing the way of sorting reviews. Defaults to 2(Newest).
        star_count (str, optional): Number representing which star_count reviews are needed. Have to give 'null' to get all star counts.

    Returns:
        reviews(list): A list of dictionaries where each dictionary is a review
        pagination_token(string): The pagination token to get the next set of reviews.
    """

    if not star_count:
        star_count = 'null'

    url = 'https://play.google.com/_/PlayStoreUi/data/batchexecute'

    headers = {
        'authority': 'play.google.com',
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'origin': 'https://play.google.com',
        'referer': 'https://play.google.com/',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", '
        '"Google Chrome";v="120"',
        'sec-ch-ua-full-version-list': '"Not_A Brand";v="8.0.0.0", "Chromium";'
        'v="120.0.6099.199", "Google Chrome";v="120.0.6099.199"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    params = {
        'hl': 'en',
        'gl': 'US'
        }

    if pagination_token:
        data = f'f.req=%5B%5B%5B%22oCPfdb%22%2C%22%5Bnull%2C%5B2%2C{sort}%2C%5B{count}%2Cnull%2C%5C%22{pagination_token}%5C%22%5D%2Cnull%2C%5Bnull%2C{star_count}%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C{device_id}%5D%5D%2C%5B%5C%22{app_id}%5C%22%2C7%5D%5D%22%2Cnull%2C%22generic%22%5D%5D%5D%0A'
    else:
        data = f'f.req=%5B%5B%5B%22oCPfdb%22%2C%22%5Bnull%2C%5B2%2C{sort}%2C%5B{count}%5D%2Cnull%2C%5Bnull%2C{star_count}%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C{device_id}%5D%5D%2C%5B%5C%22{app_id}%5C%22%2C7%5D%5D%22%2Cnull%2C%22generic%22%5D%5D%5D%0A'

    # sending request
    review_response = requests.post(url=url, headers=headers,
                                    params=params, data=data, timeout=30)
    if review_response.status_code != 200:
        print('There was an issue with the request')
        return

    # selecting only  the required portion of the response
    review_response_cleaned = re.findall(
        r"\)]}'\n\n([\s\S]+)", review_response.text)[0]

    # selecting the list containing reviews
    raw_reviews = json.loads(json.loads(review_response_cleaned)[0][2])[0]

    # getting pagination token from the response
    pagination_token = json.loads(
                            json.loads(review_response_cleaned)[0][2])[-2][-1]

    reviews = []

    # taking only the required fields of the reviews
    for raw_review in raw_reviews:
        review = {
            'reviewer_name': raw_review[1][0],
            'review_content': raw_review[4],
            'review_datetime': datetime.fromtimestamp(
                raw_review[5][0]).isoformat(),
            'star_count': raw_review[2],
            'review_likes': raw_review[6]
        }
        reviews.append(review)
    return (reviews, pagination_token)


def save_data(data: list[dict]):
    """This function saves the reviews to a csv file

    Args:
        data (list): A list of dictionaries where each dictionary corresponds to a review.
    """
    if not data:
        return
    fields = data[0].keys()
    with open('app_reviews.csv', 'w') as file:
        dict_writer = csv.DictWriter(file, fields)
        dict_writer.writeheader()
        dict_writer.writerows(data)


def main():
    search_query = 'instagram'

    app_id = get_app_id(search_query)

    if app_id:
        reviews = review_pagination(app_id)
        save_data(reviews)
    else:
        print('Search query did not match any app')


if __name__ == '__main__':
    main()
