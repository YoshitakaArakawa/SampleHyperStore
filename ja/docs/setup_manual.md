# 手でセットアップする（日本語版）

AI エージェントや Tableau MCP を使わずに、SampleHyperStore の日本語版を Tableau Cloud に載せる手順です。AI エージェント向けの手順書 [`en/setup/SETUP_FOR_AI.md`](../../en/setup/SETUP_FOR_AI.md) と同じ内容を、人が順に進められる形にしています。

日本語版のセットアップは、まだ通しで検証していません。英語版では、生の層 12 本と部門の層の billing 1 本で確かめています。

## 全体の流れ

| 手順 | やること | 誰が動くか | できる物 |
|---|---|---|---|
| 0 | 準備する | スクリプト・あなた | raw と marts の2つのプロジェクト |
| 1 | 生の層をパブリッシュする | スクリプト | 12 データソース `SampleHyperStore - <テーブル名>` |
| 2 | 部門の層を組む | あなた（Web エディター） | 6 データソース `rpt_samplehyperstore__<部門名>` |
| 3 | 計算フィールドに説明を付ける | スクリプト・あなた | 部門の層の計算フィールドの説明 |
| 4 | Tableau Knowledge を設定する（任意） | あなた（Web の画面） | ナレッジグラフとビジネス設定 21 件 |
| 5 | 試す | あなた | — |

手順2と3は、最初は billing の1本で通し、うまくいったら残りの5本に進むと安全です。

## 必要なもの

- Tableau Cloud の Creator ロールと、プロジェクトにパブリッシュする権限
- Python 3.10 以上
- Tableau の Web エディターを操作できること（手順2〜4）
- Tableau+（手順4を行う場合のみ）

## 用語と置き換える値

| 書き方 | 意味 |
|---|---|
| 生の層 | プロジェクト raw にある 12 データソース。スクリプトでは `--layer raw` |
| 部門の層 | プロジェクト marts にある 6 データソース。スクリプトでは `--layer rpt` |
| `<親プロジェクト>` | プロジェクトを作る場所。既存のプロジェクトのパスを、最上位から `/` で区切って書く（例: `Sandbox/Team A`） |
| `<raw のパス>`・`<marts のパス>` | 手順0の最後に表示される2つのパス。そのまま貼る |
| `--data ../../ja` | 日本語版のデータを使う指定。日本語版では、すべてのスクリプトに付ける。付け忘れると英語版で動く |

---

## 手順0. 準備する

### やること

1. このリポジトリを取得します（`git clone` するか、GitHub から ZIP でダウンロードします）。
2. リポジトリのルートから `en/setup/` に移動します。以降のコマンドは、すべてこのフォルダーで実行します。スクリプトは英語版と日本語版で共通です。

   ```
   cd en/setup
   ```

3. 必要なライブラリを入れます。Python の仮想環境（`python -m venv .venv`）を作ってから入れると、ほかの環境を汚しません。

   ```
   pip install -r requirements.txt
   ```

4. `.env.example` を `.env` にコピーし、次の2つを書きます。どちらも秘密の値ではありません。
   - `SERVER`: サイトの URL のホスト部分。例: `https://<pod>.online.tableau.com`
   - `SITE_NAME`: サイト URL の `#/site/<ここ>/` に入る名前
5. プロジェクトを作ります。最初にスクリプトを動かした時にブラウザが開くので、Tableau Cloud にサインインします。サインインは OAuth で行い、トークンやパスワードを自分でファイルに書く必要はありません。

   ```
   python scripts/create_projects.py --parent "<親プロジェクト>"
   ```

   次の構成ができます。`<yyyymmdd>` には実行した日付が入ります。

   ```
   <親プロジェクト>/
     <yyyymmdd>_SampleHyperStore/
       raw/     生の層の 12 データソース
       marts/   部門の層の 6 データソース
   ```

### 確かめ方

- 最後に raw と marts のパスが表示されます。控えておきます。
- 権限が足りずに失敗した場合は、同じ構成を Web の画面で作ります。パスは `<親プロジェクト>/<yyyymmdd>_SampleHyperStore/raw` の形になります。
- ほかの SampleHyperStore のデータソースがあるプロジェクトは使わないでください。後で AI エージェントから使う時に、両方が混ざります。

---

## 手順1. 生の層をパブリッシュする

### やること

まず `--dry-run` で実行します。このモードは .hyper ファイルを作るだけで、サインインもパブリッシュもしません。エラーが出なければ、`--dry-run` を外して実際にパブリッシュします。

```
python scripts/publish_raw.py --project "<raw のパス>" --data ../../ja --dry-run
python scripts/publish_raw.py --project "<raw のパス>" --data ../../ja
```

12 テーブルそれぞれが、列の表示名と説明付きでパブリッシュされます。

### 確かめ方

- `publish_raw.py` の最後に `done` と出れば成功です。
- 説明が付いたかを、次のコマンドで確かめます。各データソースで `described 列数/列数` が揃い、最後に `all present` と出れば合格です。

  ```
  python scripts/check_metadata.py --project "<raw のパス>" --layer raw --data ../../ja
  ```

---

## 手順2. 部門の層を組む

部門の層の6本を、Tableau の Web エディターで1本ずつ作ります。組み方と計算フィールドは `ja/setup/metadata/rpt_layer.json` に書かれています。画面の名前は英語の画面で確かめた操作を元にしており、括弧内は英語の画面での名前です。

| データソース | ルートのテーブル | 関係（→ の右がつなぐ先、括弧はキー） |
|---|---|---|
| rpt_samplehyperstore__billing | invoices | invoices →（請求書ID）invoice_lines →（商品ID）products。invoice_lines →（請求書ID と 商品ID）credit_memos |
| rpt_samplehyperstore__sales_orders | products | products →（商品ID）order_lines →（注文ID）orders |
| rpt_samplehyperstore__merchandising | products | sales_orders と同じ |
| rpt_samplehyperstore__shipments | products | products →（商品ID）shipment_lines →（出荷ID）shipments |
| rpt_samplehyperstore__returns_refunds | returns | returns →（商品ID）products。returns →（返品ID）refunds |
| rpt_samplehyperstore__web_analytics | web_sessions | web_sessions →（セッションID）web_searches |

ルートのテーブルは、関係のツリーの起点になるテーブルです。1つのデータソースに、ルートは必ず1つだけにします。

### 2-1. 組む

1. **ルートにつなぐ**: 「新規」（New）→「パブリッシュ済みデータソース」（Published Data Source）→「このサイト上」（On this site）で、ルートのテーブルの生の層（`SampleHyperStore - <ルート>`）につなぎ、データソースのタブを開きます。
2. **テーブルを足して線を引く**: JSON の `parent_tables` の並び順に、残りのテーブルを1つずつ「パブリッシュ済みデータソースを追加」（Add published data source）で足します。1つ足すごとに、すぐ関係の線を引きます。
   - 線は必ず、ツリーにすでにあるテーブルの右端の「+」から、新しいテーブルへ引きます。逆向きに引くとルートが2つになります。
   - キーは上の表のとおりに選びます。破線や「!」が残っていないことを確かめます。
3. **列名を確かめる**: 列名が重なると、後から足した側に ` (<テーブル名>.csv)` が付きます。sales_orders では、データペインに `注文ID (order_lines.csv)` があることを確かめます。計算フィールド「出荷可能注文数」がこの名前を使います。
4. **計算フィールドを作る**: JSON の `calculated_fields` を、名前と式をそのまま写して作ります。データペインのメニュー（▾）→「計算フィールドの作成」（Create Calculated Field）から作り、「計算は有効です」（The calculation is valid）と出ることを確かめます。
5. **パブリッシュする**: 名前は `rpt_samplehyperstore__<部門名>` にします。ダイアログで保存先のプロジェクトを marts に選び直します（既定は raw）。「資格情報を埋め込む」（Embed credentials）はオフのままにします。

### 2-2. 確かめる

1. **計算フィールド**: 次のコマンドで、作ったデータソースの `formula match 件数/件数` が揃えば合格です。まだ作っていないデータソースは `[missing]` と出ますが、途中ではそれで正常です。

   ```
   python scripts/check_metadata.py --project "<marts のパス>" --layer rpt --data ../../ja
   ```

2. **合計の値**: データソースのページから新しいワークブックを開き、下の項目の合計を出します。値は英語版で確かめたものです。日本語版も同じ数値になるはずですが、未検証です。

   | データソース | 項目 | 期待する値 |
   |---|---|---:|
   | billing | 総売上 | 13,347,403.19 |
   | sales_orders | 数量 | 111,008 |
   | merchandising | 数量 / 注文明細数 | 115,435 / 71,007 |
   | shipments | 数量 | 110,762 |
   | returns_refunds | 返品申請数量 / 返品受領数量 / 返金額 | 7,944 / 6,704 / 907,537.58 |
   | web_analytics | セッション数 / トランザクション数 / カート投入数量 | 455,057 / 24,484 / 191,594 |

   sales_orders と merchandising は組み方が同じですが、「数量」の定義が違います。sales_orders はキャンセルされた数量を除き、merchandising は含みます。

3. **ルートが1つか**: products を含む5本（web_analytics 以外）を、商品のカテゴリーで分けます。billing は総売上、ほかは数量を使います。すべてのカテゴリーで同じ値が出たら、ルートが2つになっています。2-1 の2からやり直します。

---

## 手順3. 計算フィールドに説明を付ける

Web エディターでは、計算フィールドに説明を書けません。スクリプトと Web エディターの2段で付けます。

### やること

1. スクリプトで説明を書き込みます。`--datasources` には、データソース名から `rpt_samplehyperstore__` を除いた名前を、スペース区切りで渡します（例: `billing`、`sales_orders shipments`）。省くと6本すべてが対象になります。この時点で、データソースの関係が一時的に外れます。

   ```
   python scripts/describe_rpt.py --project "<marts のパス>" --datasources billing --data ../../ja
   ```

2. データソースのページを開き直し、「編集」→「パブリッシュ」で、同じ名前・同じプロジェクトに上書きします。何も変えずに上書きすると、関係が戻り、説明は残ります。
   - 1でスクリプトを動かす前から開いていたエディターのタブは使いません。古い版で上書きしてしまいます。
   - 「パブリッシュ」を押しても反応しない時は、もう一度押します。

### 確かめ方

- 次のコマンドで、作ったデータソースの `described 件数/件数` が揃えば合格です。

  ```
  python scripts/check_metadata.py --project "<marts のパス>" --layer rpt --data ../../ja
  ```

- 手順2-2 の合計が、もう一度合うことを確かめます。

---

## 手順4. Tableau Knowledge を設定する（任意）

Tableau Knowledge は、AI エージェントに「何をいつ使うべきか」を伝える仕組みです。使うには Tableau+ が必要です。Knowledge は公式には英語だけに対応しているため、日本語版では効き方が弱い可能性があります。

### やること

1. Tableau Cloud の左のメニューから「Tableau Knowledge」を開き、「Manage Graphs」を選びます。
2. 「New knowledge graph」でグラフを作ります。データソースには、生の層と部門の層の 18 本（`samplehyperstore` で検索して出るもの）をすべて選びます。
3. 作ったグラフを開き、右上の「Actions」→「Add Business Preferences」→「Add Preference」を選びます。
4. [付録](#付録-ビジネス設定の一覧)の21件を1件ずつ、次のように入力して「Save」を押します。
   - Name: 付録の「名前」
   - Scope: 「Global (all entities)」のまま
   - Preference Rules: 付録の「本文」（上限は 1,000 文字。どの本文も収まります）
   - 1件目の本文にある `{{RPT_PROJECT_PATH}}` は、部門の層のプロジェクトのパスに書き換えます。階層の間は「 > 」でつなぎます（例: `Sandbox > 20261121_SampleHyperStore > marts`）。

### 確かめ方

- グラフにビジネス設定が 21 件あることを確かめます。
- 最後にデータソースをパブリッシュしてから 15 分ほど待ってから使います。Knowledge は、パブリッシュの時に列の説明を読み込みます。

---

## 手順5. 試す

セットアップはこれで完了です。ここまで AI は使っていません。

- Tableau だけで確かめる場合: 手順2-2 の合計の表が、そのまま確認になります。
- AI エージェントから試す場合: Tableau MCP をつないだ AI エージェントに、[`questions.md`](questions.md) の問いを尋ねます。Tableau MCP のつなぎ方は、使う AI エージェントの説明を参照してください。

作業が終わったら、サインインの記録を消しておきます。記録はリポジトリの外（Windows では `%LOCALAPPDATA%\samplehyperstore`）に保存されています。

```
python scripts/tableau_auth.py logout
```

---

## うまくいかない時

| 症状 | 対処 |
|---|---|
| `publish_raw.py` が `done` ではなく `check these tables: [...]` で終わる | そのテーブルを `--tables` で指定して実行し直します（例: `--tables orders`）。raw にそのデータソースがすでにできていたら、先に Web の画面で削除します。 |
| `check_metadata.py` で `[missing]` が出る | パブリッシュの直後なら、数分おいて実行し直します。プロジェクトのパスの最後の階層（raw や marts）が合っているかも確かめます。 |
| 合計が期待する値と合わない | 2-1 の2（線の向き）と3（列名の ` (<テーブル名>.csv)`）を見直します。 |
| 手順3で「パブリッシュ済みデータソースにしか接続されていない」という趣旨のエラーが出る | 手順3の2（上書きでの再パブリッシュ）がまだ済んでいません。 |

## 気をつけること

- **部門の層の列の説明**: 部門の層の列には、生の層の列の説明がそのまま付いて見えます（Metadata API で確認）。部門の層で自分で付けるのは、計算フィールドの説明だけです。
- **部門の層の既定の集計**: 部門の層の列は、生の層の既定の集計を引き継ぎません。数値の列は SUM が既定になります。Tableau MCP で問い合わせるエージェントには影響しません。集計はクエリごとに指定するためです。
- **Tableau MCP で説明が見えない時**: Tableau MCP の `get-datasource-metadata` は、説明を返さないことがあります。MCP は説明を Metadata API から取りますが、Metadata API を使わない設定（`DISABLE_METADATA_API_REQUESTS`）の時や、その呼び出しが失敗した時は、エラーを出さずに説明なしで返します。データソースの設定の問題ではありません。説明が付いているかは `check_metadata.py` で確かめてください。
- **データソースのページの URL**: 上書きするたびに変わります。データソースは名前で検索して開いてください。

---

## 付録: ビジネス設定の一覧

手順4で入力する21件です。内容は `ja/setup/metadata/business_preferences.json` と同じです。

| # | 名前 | 本文 |
|---|---|---|
| 1 | 使い方: 使うデータソース | 分析には {{RPT_PROJECT_PATH}} にある `rpt_samplehyperstore__` のデータソースを使う。`SampleHyperStore - <table>` のデータソースはリネージのための元テーブルにすぎない。 |
| 2 | 使い方: どのデータソースの指標を使ったかを示す | 同じ名前の指標を持つデータソースが複数ある。どのデータソースの指標を使ったかを必ず示す。 |
| 3 | 用語: 売上の既定の意味 | 修飾のない「売上」は `rpt_samplehyperstore__sales_orders` の `売上` を指す。質問が会計期間、純売上、返品、マーケットプレイス手数料に触れているときは `rpt_samplehyperstore__billing` の `売上` を使う。 |
| 4 | 用語: 経理の質問での会計期間 | 経理の質問では、「今年」「昨年」「月次」は会計期間を指す: `会計月` でまとめる。 |
| 5 | 用語: 配達遅れは約束日より後 | `配達日` が `約束配達日` より後なら配達遅れとする。`配送業者予定配達日` は配送業者の実績を見るときにだけ使う。 |
| 6 | 用語: 検索の結果なしと在庫なし | 検索の質問では、「結果なし」は `検索結果ゼロ率`（一致する商品がない）、「在庫なし」は `在庫あり結果ゼロ率` を指す。 |
| 7 | 方法: 2025-01-01 の営業地域の再編 | 2025-01-01 をまたいで年ごとに営業地域を比べるときは、`営業地域ID` ではなく `州コード` で比べる。 |
| 8 | 既定の日付: rpt_samplehyperstore__billing | `rpt_samplehyperstore__billing` の指標は `請求日`（または `会計月`）で推移を見る。例外: `クレジット` と `純返金コスト` は `クレジットメモ日`（または `会計月 (credit_memos.csv)`）。経理の計上ベースでは、クレジットメモの金額もすべて、元の請求書の月ではなく `会計月 (credit_memos.csv)` でまとめる。 |
| 9 | 既定の日付: rpt_samplehyperstore__sales_orders | `rpt_samplehyperstore__sales_orders` の指標はすべて `注文日` の暦月で推移を見る。 |
| 10 | 既定の日付: rpt_samplehyperstore__merchandising | `rpt_samplehyperstore__merchandising` の指標はすべて `注文日` の暦月で推移を見る。 |
| 11 | 既定の日付: rpt_samplehyperstore__shipments | `rpt_samplehyperstore__shipments` の指標は `出荷日` の暦月で推移を見る。例外: `パーフェクトオーダー率` は `注文日`。 |
| 12 | 既定の日付: rpt_samplehyperstore__returns_refunds | `rpt_samplehyperstore__returns_refunds` の指標は `申請日` の暦月で推移を見る。例外: `返金額` と `現金返金額` は `返金日`、`返品受領数量` は `受領日`、`注文から返品申請までの日数` と `返品注文明細数` は `注文日`（注文コホート）。 |
| 13 | 既定の日付: rpt_samplehyperstore__web_analytics | `rpt_samplehyperstore__web_analytics` の指標は `セッション開始日` の暦月で推移を見る。例外: `検索結果ゼロ率`、`在庫あり結果ゼロ率`、`ノークリック率` は `検索日`、`カート投入数量` は `カート追加日`。 |
| 14 | 複数ソースの指標: 申請ベースの返品率 | 申請ベースの返品率（カスタマーサポート）= `rpt_samplehyperstore__returns_refunds` の `返品申請数量`（`申請日` の月別） ÷ `rpt_samplehyperstore__sales_orders` の `数量`（`注文日` の月別）。 |
| 15 | 複数ソースの指標: 注文コホートの返品率 | 注文コホートの返品率（マーチャンダイジング）= `rpt_samplehyperstore__returns_refunds` の `返品申請数量` ÷ `rpt_samplehyperstore__merchandising` の `純注文数量`。どちらも `注文日` の月別で、両方に同じフィルターをかける。 |
| 16 | 複数ソースの指標: 受領ベースの返品率 | 受領ベースの返品率（物流）= `rpt_samplehyperstore__returns_refunds` の `返品受領数量`（`受領日` の月別） ÷ `rpt_samplehyperstore__shipments` の `数量`（`出荷日` の月別）。 |
| 17 | 複数ソースの指標: 返品明細の発生率 | 返品明細の発生率（マーチャンダイジング）= `rpt_samplehyperstore__returns_refunds` の `返品注文明細数` ÷ `rpt_samplehyperstore__merchandising` の `注文明細数`。商品別、`注文日` の月別。 |
| 18 | 複数ソースの指標: 純送料コスト | 純送料コスト（経理）= `rpt_samplehyperstore__shipments` の `運賃`（`出荷日` の月別） − `rpt_samplehyperstore__billing` の `請求送料`（`請求日` の月別）。 |
| 19 | 複数ソースの指標: セッションあたり注文数 | セッションあたり注文数（営業）= `rpt_samplehyperstore__sales_orders` の `注文数`（Webとアプリのチャネル、`注文日` 基準） ÷ `rpt_samplehyperstore__web_analytics` の `セッション数`（`セッション開始日` 基準）。 |
| 20 | 複数ソースの指標: 数量ベースのカート放棄率 | 数量ベースのカート放棄率（マーチャンダイジング）= 1 − `rpt_samplehyperstore__merchandising` の `数量`（Webとアプリの注文） ÷ `rpt_samplehyperstore__web_analytics` の `カート投入数量`。どちらも週別（`注文日` と `カート追加日`）。 |
| 21 | 複数ソースの指標: 受注売上に対するマーケットプレイス手数料率 | 受注売上に対するマーケットプレイス手数料率（営業）= `rpt_samplehyperstore__billing` の `マーケットプレイス手数料`（`請求日` の月別） ÷ `rpt_samplehyperstore__sales_orders` の `売上`（マーケットプレイスチャネル、`注文日` の月別）。 |
