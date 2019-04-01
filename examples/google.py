from queue import Queue
import threading
import requests
import datetime
import time
import argparse
import sys
from bs4 import BeautifulSoup


add_lock = threading.Lock()
count_queue = Queue()
search_results = set()

parser = argparse.ArgumentParser(description='FireProx API Google Scraper')
parser.add_argument('--proxy', help='FireProx API URL', type=str, default=None)
parser.add_argument('--search', help='Search term', type=str, default=None)
parser.add_argument('--pages', help='Google search pages to enumerate (default:1000)', type=int, default=1000)
args = parser.parse_args()


def check_query(count, url, query):
	if url[-1] == '/':
		url = url[:-1]

	url = f'{url}/search?q={query}&start={count}&num=100'
	headers = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0',
	}
	results = requests.get(url, headers=headers)

	soup = BeautifulSoup(results.text, 'lxml')

	with add_lock:
		idx = 1
		for g in soup.find_all('div', class_='r'):
			link = g.find_all('a')[0]['href']
			title = g.find_all('h3')[0]
			item = f'{title.text} ({link})'
			search_results.add(item)
			idx+=1


def process_queue(url, query):
	while True:
		current_count = count_queue.get()
		check_query(current_count, url, query)
		count_queue.task_done()


def main():
	if not any([args.proxy, args.search]):
		parser.print_help()
		sys.exit(1)

	for i in range(100):
		t = threading.Thread(target=process_queue, args=(args.proxy, args.search,))
		t.daemon = True
		t.start()

	start = time.time()

	count_queue.put(0)
	for count in range(1,args.pages+1)[99::100]:
		count_queue.put(count)

	count_queue.join()

	for x in list(search_results):
		print(x)

	print(f'Results: {len(search_results)}')
	print('Execution time: {0:.5f}'.format(time.time() - start))


if __name__ == '__main__':
	main()
