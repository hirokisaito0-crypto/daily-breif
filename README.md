# Daily brief（レイアウトサンプル）

静的 HTML のみです。**編集するファイルは `index.html` だけ**で大丈夫です（サイトのトップページになります）。

## 他の人に見せる方法

### A. GitHub Pages（無料・URL を発行）

1. [GitHub](https://github.com) で新しいリポジトリを作成する（空でよい）。
2. このフォルダで次を実行し、表示された URL に `YOUR_USER` / `YOUR_REPO` を入れてプッシュする。

```powershell
cd "c:\Users\hirok\OneDrive\Desktop\My-Second-Project"
git init
git add .
git commit -m "Add daily brief static site"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

3. GitHub のリポジトリで **Settings → Pages** を開く。
4. **Build and deployment** の **Source** で **GitHub Actions** を選ぶ。
5. 数分後、`https://YOUR_USER.github.io/YOUR_REPO/` で表示される（初回は Actions の完了を待つ）。

### B. Netlify（ドラッグ＆ドロップ）

1. [Netlify Drop](https://app.netlify.com/drop) を開く。
2. このプロジェクトフォルダをブラウザにドラッグする。
3. 発行された `*.netlify.app` の URL を共有する。

（`netlify.toml` で公開ディレクトリはルートに設定済みです。）

### C. 社内／同じ LAN のみ

```powershell
npx --yes serve "c:\Users\hirok\OneDrive\Desktop\My-Second-Project"
```

表示された `http://localhost:…` を、同一ネットワークの PC からは `http://あなたのPCのIP:ポート` で開ける場合があります（ファイアウォール設定が必要なことがあります）。
