import re
import time
from typing import List, Dict, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup


class EigaScraper:
    URL_FMT: str = "https://eiga.com/movie/{movie_id}/review/all/{{page_num}}/"
    headers: Dict[str, str] = {"User-Agent": "Mozilla/5.0"}
    WAIT: float = 1.0

    def __init__(self, movie_id: str = "50969") -> None:
        self.base_url = self.URL_FMT.format(movie_id=movie_id)

    @staticmethod
    def _scrape(bs: BeautifulSoup) -> List[Dict[str, Optional[str]]]:
        reviews: List[Dict[str, Optional[str]]] = []
        review_elms = bs.find_all("div", class_="user-review")
        for review_elm in review_elms:
            # User ID
            user_id: str = review_elm["data-review-user"]

            # Rate
            rating_elm = review_elm.find("span", class_="rating-star")
            rating: Optional[str] = rating_elm.text if rating_elm else None

            # Title
            title_elm = review_elm.find("h2", class_="review-title")
            if title_elm:
                title = title_elm.text.replace(str(rating), "").strip()
            else:
                title = None

            # Review text
            # NOTE: 通常のレビューとネタバレありレビューで構成が異なるので２つの要素でレビューの有無を確認する
            review_text_element = review_elm.find("p", class_="short")
            hidden_review_text_element = review_elm.find("p", class_="hidden")
            review_text: Optional[str]
            if review_text_element:
                review_text = review_text_element.text.strip()
            elif hidden_review_text_element:
                review_text = hidden_review_text_element.text.strip()
            else:
                review_text = None

            # Append to list
            reviews.append(
                {
                    "user_id": user_id,
                    "rating": rating,
                    "title": title,
                    "review_text": review_text,
                }
            )
        return reviews

    @staticmethod
    def _get_last_page_num(bs: BeautifulSoup) -> Optional[int]:
        REVIEW_COUNT_BY_PAGE = 20
        res_num_elm = bs.find("p", class_="result-number")
        if res_num_elm is None:
            return None

        text: str = res_num_elm.text
        match = re.search(r"(\d+)件中", text)
        if not match:
            return None

        review_count = int(match.group(1))
        # NOTE: 20の倍数の時にページ数が適切に表示されるように1引いて、最終的な結果に+1をする
        last_page_num = (review_count - 1) // REVIEW_COUNT_BY_PAGE + 1
        return last_page_num

    def extract_review(self) -> pd.DataFrame:
        reviews: List[Dict[str, Optional[str]]] = []
        page_num: int = 1
        while True:
            url = self.base_url.format(page_num=page_num)
            try:
                res = requests.get(url, headers=self.headers)
                res.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error occurred while fetching {url}: {e}")
                break
            bs = BeautifulSoup(res.text, "lxml")
            review_list = self._scrape(bs)
            reviews.extend(review_list)
            last_page_num = self._get_last_page_num(bs)
            if last_page_num is None or page_num >= last_page_num:
                break
            page_num += 1
            time.sleep(self.WAIT)
        df = pd.DataFrame(reviews)
        return df
