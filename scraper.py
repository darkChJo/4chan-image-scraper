#!/usr/bin/env python3
import requests
import json
import sys
import os
import hashlib
import base64
import re

banned_threads = [9112225, 12370429]
error_file = "error.txt"

class Scraper:
    def __init__(self, url: str, keep_names: bool, save_path: str):
        self.__url = url
        self.__keep_names = keep_names

        self.__board, self.__thread_id = self.__parse_url(url)
        self.__destination = os.path.join(os.path.expanduser(save_path), self.__board, self.__thread_id)
        self.__json_filename = os.path.join(os.path.expanduser(save_path), self.__board, self.__thread_id, "{}.json".format(self.__thread_id))

        if self.__keep_names:
            self.downloaded_files = []

        self.bar_length = 20
        self.bar_character_limit = 20

        self.__get_thread()

        if not os.path.exists(self.__destination):
            try:
                os.makedirs(self.__destination)
                #self.__get_thread()
                dump_json(self.__json_filename, self.__thread)
            except PermissionError:
                print("Cannot scrape to {}: Insufficient Permissions".format(save_path))
                exit(1)
            print("Saving images to {}".format(self.__destination))

    def __parse_url(self, url: str) -> tuple:
        url = url.split("/") # ['https:', '', 'boards.4channel.org', 'g', 'thread', '51971506']
        board = url[3]
        thread_id = url[5]

        return board, thread_id

    def __get_thread(self) -> None:
        response = requests.get("https://a.4cdn.org/{0}/thread/{1}.json".format(
            self.__board,
            self.__thread_id,
            timeout=5
        ))
        if len(response.text) == 0:
            raise ThreadDoesNotExist(self.__board, self.__thread_id)

        self.__thread = json.loads(response.text)
        print("Found thread with ID {} in board {}".format(self.__thread_id, self.__board))

    def __get_images(self) -> None:
        posts = self.__thread["posts"]
        images = [post for post in posts if "tim" in post] # isolates posts that have an attachment from ones that don't
        self.__image_total = len(images)

        for self.__image_count, image in enumerate(images, 1):
            self.__download_image(image)

    def __download_image(self, image: dict) -> None:
        filename = ""

        if self.__keep_names:
            filename = image["filename"] + image["ext"]
            self.downloaded_files.append(filename)

            if filename in self.downloaded_files[:-1]:
                # filename_1 if there is already a file called filename
                filename = "{0}_{1}{2}".format(
                    image["filename"],
                    self.downloaded_files.count(filename)-1,
                    image["ext"]
                )
        else:
            filename = str(image["tim"]) + image["ext"]

        file_path = os.path.join(self.__destination, filename)

        # redownloads if file is corrupted or missing
        if os.path.exists(file_path):
            # dumb 4chan api decides to encode their md5 strings into base64
            md5 = base64.b64decode(image["md5"]).hex()

            if self.__md5check(file_path, md5):
                print("{} already exists. Skipping...".format(filename))
                return

        response = requests.get("https://i.4cdn.org/{0}/{1}".format(
            self.__board,
            str(image["tim"]) + image["ext"],
            timeout=5
        ))

        #print("{} {}".format(response.url, response.status_code))
        if response.status_code != 404:
            size = int(response.headers["Content-length"])
            dl = 0

            try:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            dl += len(chunk)
                            file.write(chunk)

                            progress = dl / size
                            self.__draw_progress_bar(
                                progress,
                                filename,
                                self.__image_count,
                                self.__image_total
                            )

                    sys.stdout.write('\n')

            except KeyboardInterrupt:
                os.remove(file_path)
                raise KeyboardInterrupt
            #finally:
            #    file.close()
        else:
            with open(error_file, 'a') as f:
                f.write("{}\t{}\n".format(self.__thread_id, response.url))


    def __md5check(self, path: str, md5: str) -> bool:
        """ https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file """
        with open(path, 'rb') as file:
            data = file.read()
            file_md5 = hashlib.md5(data).hexdigest()
            file.close()
            return file_md5 == md5

    def __draw_progress_bar(self, progress: float, filename: str,
                            image_count: int, image_total: int) -> None:

        bar_percent = int(round(progress * self.bar_length))
        bar = '█'*bar_percent + " "*(self.bar_length - bar_percent)

        if len(filename) < self.bar_character_limit:
            filename = filename.ljust(self.bar_character_limit, ' ')
        else:
            filename = filename[:self.bar_character_limit-3]+"..."

        text = "\rDownloading {filename} |{bar}| {percent:.2f}% {current} of {total}".format(
            filename=filename,
            bar=bar,
            percent=progress*100,
            current=image_count,
            total=image_total
        )

        sys.stdout.write(text)
        sys.stdout.flush()



    def Scrape(self) -> None:
        print("Scraping thread {} in board {}".format(self.__thread_id, self.__board))
        self.__get_images()
        print("Finished scraping thread {} in board {}".format(self.__thread_id, self.__board))


class InvalidThreadURL(Exception):
    def __init__(self, url: str):
        self.message = url

    def __str__(self) -> str:
        return "{} is an invalid thread URL.".format(self.message)

class ThreadDoesNotExist(Exception):
    def __init__(self, board: str, thread_id: str):
        self.board = board
        self.thread_id = thread_id

    def __str__(self) -> str:
        return "Thread with ID {} in board {} does not exist.".format(self.thread_id, self.board)

def check_url(url) -> bool:
    exp = re.compile(r"^(https:\/\/boards.4channel.org\/|https:\/\/boards.4chan.org\/)[a-z]{1,5}\/thread\/[0-9]{1,}.*")
    match = re.search(exp, url)
    return True if match else False

def dump_json(filename: str, obj: dict) -> None:
    with open(filename, 'w') as f:
        json.dump(obj, f)

def get_live_threads(board: str) -> list:
    response = requests.get("https://a.4cdn.org/{}/catalog.json".format(board), timeout=5)
    catalog = json.loads(response.text)
    threadnos = []
    for page in catalog:
        for post in page['threads']:
            threadno = post['no']
            if threadno not in banned_threads:
                threadnos.append(threadno)
    return threadnos

def get_archived_threads(board: str) -> list:
    response = requests.get("https://a.4cdn.org/{}/archive.json".format(board), timeout=5)
    catalog = json.loads(response.text)
    threadnos = catalog
    threadnos.reverse()
    return threadnos

def main(args) -> None:
    exitcode = 0
    # check if the URLs are valid
    # inform user if not
    validURLs = []

    for url in args.URLs:
        try:
            valid = check_url(url)

            if valid == False:
                raise InvalidThreadURL(url)
            validURLs.append(url)

        except InvalidThreadURL as err:
            print(err)
            exitcode = 1

    threads = []
    for url in validURLs:
        try:
            threads.append(Scraper(url, args.keep_names, args.path))
        except ThreadDoesNotExist as err:
            print(err)
            exitcode = 1

    for thread in threads:
        thread.Scrape()

    exit(exitcode)


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Scrapes images from 4chan threads using the 4chan api.",
        usage=f"{sys.argv[0]} [options] URL(s)"
    )

    parser.add_argument(
        "URLs", nargs="*",
        help="links to 4chan threads"
    )

    parser.add_argument(
        "-k", "--keep-names", action="store_true",
        help="keep original filenames, defaults to False"
    )

    parser.add_argument(
        "--path", metavar="directory",
        default=".",
        help="where to create the thread directories, defaults to './'"
    )

    parser.add_argument(
        "--board", metavar="board",
        help="which board to download from"
    )

    parser.add_argument(
        "-a", "--no-archived", action="store_true",
        help="Archived thread won't be downloaded, defaults to False"
    )

    parser.add_argument(
        "-l", "--no-live", action="store_true",
        help="Live threads won't be downloaded, defaults to False"
    )


    args = parser.parse_args()

    if args.board:
        board = args.board
        if not args.no_archived:
            threadnos = get_archived_threads(board)
            args.URLs += ["https://boards.4chan.org/{}/thread/{}/".format(board, threadno) for threadno in threadnos]
        if not args.no_live:
            threadnos = get_live_threads(board)
            args.URLs += ["https://boards.4chan.org/{}/thread/{}/".format(board, threadno) for threadno in threadnos]
    try:
        main(args)
    except KeyboardInterrupt:
        print("\nProgram Aborted.")
        exit(130)
