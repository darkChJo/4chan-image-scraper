# 4chan-image-scraper
Simple 4chan image scraper with support for scraping multiple threads.

## Usage
```
usage: scraper.py [options] URL(s)

Scrapes images from 4chan threads using the 4chan api.

positional arguments:
  URLs              links to 4chan threads

optional arguments:
  -h, --help        show this help message and exit
  -k, --keep-names  keep original filenames, defaults to False
  --path directory  where to create the thread directories, defaults to './'
```
### Example
```
$ ./scraper.py -k --path="~/output" https://boards.4chan.org/wg/thread/7587778
```

## Dependencies
This script uses the [requests](https://pypi.org/project/requests/) library. The dependencies are listed in [requirements.txt](../master/requirements.txt) and can be installed using ```pip```
```bash
pip install -r requirements.txt
```
