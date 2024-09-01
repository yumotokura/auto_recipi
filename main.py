import requests
import json
import pandas as pd
import os
import time
from requests_oauthlib import OAuth1Session as session

# ツイート用URL v2対応
URL_TWEET = "https://api.twitter.com/2/tweets"

# 画像アップロードURL v1.1
URL_IMAGE = "https://upload.twitter.com/1.1/media/upload.json"

# Twitter API認証情報
TWITTER_CONF_PATH = 'conf.json'

class Pytweet:

    def __init__(self, conf_path):
        """constructor

        Args:
            conf_path (string): ツイッターの機密ファイルへのパス
        """
        with open(conf_path, "r", encoding="utf-8") as f:
            cf = json.load(f)

        self.req = session(cf["API_KEY"], cf["API_SECRET_KEY"],
                           cf["ACCESS_TOKEN"], cf["ACCESS_TOKEN_SECRET"])

    def tweet(self, msg, *img_paths):
        """tweetする

        Args:
            msg (str): ツイートするテキスト
            img_paths(list[string]): アップロードする画像のパス。optional.
        """
        try:
            tweet(self.req, msg, *img_paths)
            print("ツイートに成功しました。")
        except Exception as e:
            print(f"ツイートに失敗しました: {e}")

def tweet_image(req, *img_paths):
    """画像をアップロードし、media_idを返す。アップロードのみでツイートはされないので注意。
    """
    media_ids = []
    for img in img_paths:
        with open(img, "rb") as file:
            params = {"media": file}
            data = {"media_category": "tweet_image"}
            res = req.post(URL_IMAGE, files=params, data=data)

        print(f"Image upload response status: {res.status_code}")
        print(f"Image upload response content: {res.text}")

        if res.status_code != 200:
            print(f"error at {img}: {res.json()}")
            continue

        res_data = res.json()
        media_ids.append(res_data["media_id"])

    media_ids_str_list = [str(m) for m in media_ids]
    return media_ids_str_list

def tweet(req, msg: str, *img_paths):
    media_ids = tweet_image(req, *img_paths)  # メディアIDを取得

    body = {}

    if media_ids:
        body = {"text": msg, "media": {"media_ids": media_ids}}  # media_ids を配列として指定
    else:
        body = {"text": msg}

    res = req.post(URL_TWEET, json=body)

    print(f"Tweet response status: {res.status_code}")
    print(f"Tweet response content: {res.text}")

    if not (res.status_code >= 200 and res.status_code <= 299):
        print(f"something went wrong...status:{res.status_code}")
        print(res.json())  # エラーメッセージの詳細を表示

    print(res.json())

def save_image(image_url):
    """画像をローカルに保存する

    Args:
        image_url (str): 画像のURL

    Returns:
        str: 保存した画像ファイルのパス
    """
    if image_url:
        try:
            image_res = requests.get(image_url)
            if image_res.status_code == 200:
                # 画像ファイル名を決定
                image_filename = os.path.join("images.jpg")
                with open(image_filename, 'wb') as file:
                    file.write(image_res.content)
                print(f"画像をローカルに保存しました: {image_filename}")
                return image_filename
            else:
                print(f"画像の取得に失敗しました: {image_res.status_code}")
        except Exception as e:
            print(f"画像のダウンロード中にエラーが発生しました: {e}")
    return None

# 画像保存ディレクトリの設定
IMAGE_DIR = 'images'
os.makedirs(IMAGE_DIR, exist_ok=True)

# 楽天APIキーを設定
API_KEY = ''

def fetch_and_tweet():
    """楽天レシピAPIからランダムにレシピを取得しエックスでポストする
    """
    # 1. 楽天レシピのレシピカテゴリ一覧を取得する
    res = requests.get(f'https://app.rakuten.co.jp/services/api/Recipe/CategoryList/20170426?applicationId={API_KEY}')
    json_data = json.loads(res.text)

    parent_dict = {}  # mediumカテゴリの親カテゴリの辞書

    df = pd.DataFrame(columns=['category1', 'category2', 'category3', 'categoryId', 'categoryName'])

    # largeカテゴリの処理
    for category in json_data['result']['large']:
        new_row = pd.DataFrame([{'category1': category['categoryId'], 'category2': "", 'category3': "", 'categoryId': category['categoryId'], 'categoryName': category['categoryName']}])
        df = pd.concat([df, new_row], ignore_index=True)

    # mediumカテゴリの処理
    for category in json_data['result']['medium']:
        new_row = pd.DataFrame([{'category1': category['parentCategoryId'], 'category2': category['categoryId'], 'category3': "", 'categoryId': str(category['parentCategoryId']) + "-" + str(category['categoryId']), 'categoryName': category['categoryName']}])
        df = pd.concat([df, new_row], ignore_index=True)
        parent_dict[str(category['categoryId'])] = category['parentCategoryId']

    # smallカテゴリの処理
    for category in json_data['result']['small']:
        parent_category_id = parent_dict.get(category['parentCategoryId'], None)
        
        if parent_category_id is None:
            print(f"Warning: Parent category ID '{category['parentCategoryId']}' not found in parent_dict.")
            continue

        new_row = pd.DataFrame([{'category1': parent_category_id, 'category2': category['parentCategoryId'], 'category3': category['categoryId'], 'categoryId': parent_category_id + "-" + str(category['parentCategoryId']) + "-" + str(category['categoryId']), 'categoryName': category['categoryName']}])
        df = pd.concat([df, new_row], ignore_index=True)

    # 2. カテゴリをランダムに選択する
    random_category = df.sample(1).iloc[0]

    print(f"ランダムに選択されたカテゴリ: {random_category['categoryName']} (CategoryId: {random_category['categoryId']})")

    # 3. ランダムに選択されたカテゴリから人気レシピを1件取得する
    df_recipe = pd.DataFrame(columns=['recipeId', 'recipeTitle', 'foodImageUrl', 'recipeMaterial', 'recipeCost', 'recipeIndication', 'categoryId', 'categoryName', 'recipeUrl', 'recipeName'])

    url = f'https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426?applicationId={API_KEY}&categoryId={random_category["categoryId"]}'
    res = requests.get(url)

    if res.status_code == 200:
        json_data = json.loads(res.text)
        recipes = json_data['result']
        
        # 1件だけ取得
        if recipes:
            recipe = recipes[0]
            recipe_url = recipe.get('recipeUrl', 'URL not available')  # recipeUrlフィールドを取得
            image_url = recipe.get('foodImageUrl', None)  # 画像のURLを取得
            recipe_name = recipe.get('recipeTitle', 'Name not available')  # 料理名を取得

            # 画像をローカルに保存
            image_path = save_image(image_url)

            # DataFrameにレシピ情報を追加
            new_row = pd.DataFrame([{
                'recipeId': recipe['recipeId'],
                'recipeTitle': recipe['recipeTitle'],
                'foodImageUrl': recipe['foodImageUrl'],
                'recipeMaterial': recipe['recipeMaterial'],
                'recipeCost': recipe['recipeCost'],
                'recipeIndication': recipe['recipeIndication'],
                'categoryId': random_category['categoryId'],
                'categoryName': random_category['categoryName'],
                'recipeUrl': recipe_url,
                'recipeName': recipe_name
            }])
            df_recipe = pd.concat([df_recipe, new_row], ignore_index=True)

            # ツイートする内容
            tweet_text = f"今回のおすすめレシピは「{recipe_name} 」 リンク({recipe_url})"
            
            # Twitterにツイート
            twitter_client = Pytweet(TWITTER_CONF_PATH)
            if image_path:
                twitter_client.tweet(tweet_text, image_path)
            else:
                twitter_client.tweet(tweet_text)
        else:
            print("レシピが見つかりませんでした。")
    else:
        print(f"レシピの取得に失敗しました: {res.status_code}")

# 1時間ごとに実行
while True:
    fetch_and_tweet()
    time.sleep(3600)  # 1時間 (3600秒) 待機
