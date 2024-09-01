# ベースイメージとしてPython 3.10を使用
FROM python:3.10-slim

# 作業ディレクトリを作成
WORKDIR /app

# 必要なパッケージをコピー
COPY requirements.txt .
COPY conf.json .

# 必要なPythonパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# スクリプトをコピー
COPY main.py .

# スクリプトを実行
CMD ["python", "main.py"]
