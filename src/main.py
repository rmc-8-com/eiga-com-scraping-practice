from libs.eiga import EigaScraper


def main():
    es = EigaScraper()
    df = es.extract_review()
    print(df)


if __name__ == "__main__":
    main()
