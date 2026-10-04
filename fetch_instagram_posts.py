"""
Instaloaderを使って、指定したInstagramアカウントの最新投稿データを取得し、
CSVファイルに保存するスクリプト。

取得項目: 投稿日, いいね数, コメント数, キャプションテキスト

事前に下記でログインし、セッションファイルを保存しておく必要があります:
    python -m instaloader --login=<ログインアカウント名>

使い方:
    python fetch_instagram_posts.py [アカウント名] [取得件数] [ログインアカウント名]

例:
    python fetch_instagram_posts.py alcohol_iday 20 alcohol_iday
"""

import csv
import sys

import instaloader

DEFAULT_USERNAME = "alcohol_iday"
DEFAULT_POST_COUNT = 20
OUTPUT_FILE = "insta_data.csv"


def fetch_posts(username: str, post_count: int, output_file: str, login_username: str | None) -> None:
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
    )

    if login_username:
        loader.load_session_from_file(login_username)

    profile = instaloader.Profile.from_username(loader.context, username)

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["投稿日", "いいね数", "コメント数", "キャプションテキスト"])

        for i, post in enumerate(profile.get_posts()):
            if i >= post_count:
                break
            writer.writerow(
                [
                    post.date_utc.strftime("%Y-%m-%d %H:%M:%S"),
                    post.likes,
                    post.comments,
                    (post.caption or "").replace("\n", " "),
                ]
            )
            print(f"[{i + 1}/{post_count}] {post.date_utc.strftime('%Y-%m-%d')} 取得完了")

    print(f"\n完了: {output_file} に保存しました。")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USERNAME
    post_count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_POST_COUNT
    login_username = sys.argv[3] if len(sys.argv) > 3 else None
    fetch_posts(username, post_count, OUTPUT_FILE, login_username)
