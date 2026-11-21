# 手でセットアップする（日本語版）

AI エージェントや Tableau MCP を使わずに、SampleHyperStore の日本語版を Tableau Cloud に載せる手順です。AI エージェント向けの手順書 [`en/setup/SETUP_FOR_AI.md`](../../en/setup/SETUP_FOR_AI.md) と同じ内容を、人が順に進められる形にしています。

この手順でできあがるのは、次の2つの層です。

| 層 | Tableau のプロジェクト | データソース名 | スクリプトでの呼び名 |
|---|---|---|---|
| 生の層 | raw | `SampleHyperStore - <テーブル名>`（12本） | `--layer raw` |
| 部門の層 | marts | `rpt_samplehyperstore__<部門名>`（6本） | `--layer rpt` |

Tableau Knowledge の設定は Tableau MCP を使うため、この手順には含めていません。

日本語版のセットアップは、まだ通しで検証していません。英語版では、生の層 12 本と部門の層の billing 1 本で確かめています。

## 必要なもの

- Tableau Cloud の Creator ロールと、プロジェクトにパブリッシュする権限
- Python 3.10 以上
- Tableau の Web エディターを操作できること（手順2と3）

## 手順0. 準備する

1. このリポジトリを取得します（`git clone` するか、GitHub から ZIP でダウンロードします）。
2. リポジトリのルートから `en/setup/` に移動します。以降のコマンドは、すべてこのフォルダーで実行します。

   ```
   cd en/setup
   ```

   スクリプトは英語版と日本語版で共通です。日本語版のデータは、各コマンドに `--data ../../ja` を付けて指定します。これを付け忘れると、英語版のデータとメタデータで動きます。

3. 必要なライブラリを入れます。Python の仮想環境（`python -m venv .venv`）を作ってから入れると、ほかの環境を汚しません。

   ```
   pip install -r requirements.txt
   ```

4. `.env.example` を `.env` にコピーし、次の2つを書きます。どちらも秘密の値ではありません。
   - `SERVER`: サイトの URL のホスト部分。例: `https://<pod>.online.tableau.com`
   - `SITE_NAME`: サイト URL の `#/site/<ここ>/` に入る名前
5. サインインの状態を確かめます。サインインしていなければ、最初にスクリプトを動かした時にブラウザが開きます。サインインは OAuth で行い、トークンやパスワードを自分でファイルに書く必要はありません。

   ```
   python scripts/tableau_auth.py status
   ```

6. プロジェクトを作ります。`<親プロジェクト>` には、サンドボックスなど既存のプロジェクトのパスを入れます。パスは最上位から書き、階層を `/` で区切ります（例: `Sandbox/Team A`）。

   ```
   python scripts/create_projects.py --parent "<親プロジェクト>"
   ```

   次の構成ができます。`<yyyymmdd>` には実行した日付が入ります。最後に表示される raw と marts のパスを控えてください。以降の `<raw のパス>` と `<marts のパス>` に、そのまま貼ります。

   ```
   <親プロジェクト>/
     <yyyymmdd>_SampleHyperStore/
       raw/     生の層の 12 データソース
       marts/   部門の層の 6 データソース
   ```

   権限が足りずに失敗した場合は、同じ構成を Web の画面で作ってください。その場合のパスは `<親プロジェクト>/<yyyymmdd>_SampleHyperStore/raw` の形になります。

   ほかの SampleHyperStore のデータソースがあるプロジェクトは使わないでください。後で AI エージェントから使う時に、両方が混ざります。

## 手順1. 生の層をパブリッシュする

まず `--dry-run` で実行します。このモードは .hyper ファイルを作るだけで、サインインもパブリッシュもしません。エラーが出なければ、`--dry-run` を外して実際にパブリッシュします。

```
python scripts/publish_raw.py --project "<raw のパス>" --data ../../ja --dry-run
python scripts/publish_raw.py --project "<raw のパス>" --data ../../ja
```

12 テーブルそれぞれが `SampleHyperStore - <テーブル名>` という名前でパブリッシュされます。列の表示名と説明も書き込まれます。最後に `done` と出れば完了です。`check these tables: [...]` と出た場合は、そのテーブルを確かめます。

説明が付いたかを、次のコマンドで確かめます。

```
python scripts/check_metadata.py --project "<raw のパス>" --layer raw --data ../../ja
```

各データソースについて `described 列数/列数` が揃い、最後に `all present` と出れば合格です。パブリッシュの直後は反映に数分かかることがあります。`[missing]` が出たら、数分おいてから実行し直してください。

## 手順2. 部門の層を組む

部門の層の6本を、Tableau の Web エディターで1本ずつ作ります。最初は billing の1本で手順2と手順3を通し、うまくいったら残りの5本に進むと安全です。

組み方と計算フィールドは `ja/setup/metadata/rpt_layer.json` に書かれています。

| データソース | ルートのテーブル | 関係（→ の右がつなぐ先、括弧はキー） |
|---|---|---|
| rpt_samplehyperstore__billing | invoices | invoices →（請求書ID）invoice_lines →（商品ID）products。invoice_lines →（請求書ID と 商品ID）credit_memos |
| rpt_samplehyperstore__sales_orders | products | products →（商品ID）order_lines →（注文ID）orders |
| rpt_samplehyperstore__merchandising | products | sales_orders と同じ |
| rpt_samplehyperstore__shipments | products | products →（商品ID）shipment_lines →（出荷ID）shipments |
| rpt_samplehyperstore__returns_refunds | returns | returns →（商品ID）products。returns →（返品ID）refunds |
| rpt_samplehyperstore__web_analytics | web_sessions | web_sessions →（セッションID）web_searches |

ルートのテーブルとは、関係のツリーの起点になるテーブルです。1つのデータソースに、ルートは必ず1つだけにします。

画面の名前は、英語の画面で確かめた操作を元にしています。括弧内は英語の画面での名前です。

1つのデータソースごとに、次の順で進めます。

1. Tableau Cloud で「新規」（New）→「パブリッシュ済みデータソース」（Published Data Source）を選びます。接続先の一覧で「このサイト上」（On this site）を選び、ルートのテーブルの生の層（`SampleHyperStore - <ルート>`）につなぎます。データソースのタブを開きます。
2. JSON の `parent_tables` の並び順に、残りのテーブルを1つずつ足します。ルートは飛ばします。足すには「パブリッシュ済みデータソースを追加」（Add published data source）を使います。
3. テーブルを1つ足すごとに、すぐ関係の線を引きます。線は必ず、ツリーにすでにあるテーブルの右端の「+」から、新しいテーブルへ引きます。逆向きに引くとルートが2つになり、ほかのテーブルの項目で分けた時に総計が繰り返し表示されます。
4. 上の表のキーで、関係の項目を選びます。破線や「!」が残っていないことを確かめます。
5. 列名が重なると、後から足した側に ` (<テーブル名>.csv)` が付きます。どちらに付くかは、足す順番で決まります。sales_orders では、データペインに `注文ID (order_lines.csv)` があることを確かめます。計算フィールド「出荷可能注文数」がこの名前を使います。
6. JSON の `calculated_fields` の計算フィールドを、名前と式をそのまま写して作ります。データペインのメニュー（▾）→「計算フィールドの作成」（Create Calculated Field）から作ります。「計算は有効です」（The calculation is valid）と出ることを確かめます。
7. パブリッシュします。名前は `rpt_samplehyperstore__<部門名>` にします。ダイアログで、保存先のプロジェクトを marts に選び直します。既定では raw が選ばれています。「資格情報を埋め込む」（Embed credentials）はオフのままにします。

パブリッシュしたら、計算フィールドが入ったかを確かめます。

```
python scripts/check_metadata.py --project "<marts のパス>" --layer rpt --data ../../ja
```

作ったデータソースについて `formula match 件数/件数` が揃えば合格です。まだ作っていないデータソースは `[missing]` と出ます。途中ではそれで正常です。6本すべてを作り終えると、最後に `all present` と出ます。

次に、合計の値を確かめます。データソースのページから新しいワークブックを開き、下の項目をシートに置いて合計を出します。値は英語版で確かめたものです。日本語版も同じ数値になるはずですが、まだ確かめていません。

| データソース | 項目 | 期待する値 |
|---|---|---:|
| billing | 総売上 | 13,347,403.19 |
| sales_orders | 数量 | 111,008 |
| merchandising | 数量 / 注文明細数 | 115,435 / 71,007 |
| shipments | 数量 | 110,762 |
| returns_refunds | 返品申請数量 / 返品受領数量 / 返金額 | 7,944 / 6,704 / 907,537.58 |
| web_analytics | セッション数 / トランザクション数 / カート投入数量 | 455,057 / 24,484 / 191,594 |

sales_orders と merchandising は組み方が同じですが、「数量」の定義が違います。sales_orders はキャンセルされた数量を除き、merchandising は含みます。

最後に、products を含む5本（web_analytics 以外）で、商品のカテゴリーで分けてみます。billing は総売上、ほかは数量を使います。すべてのカテゴリーで同じ値が出たら、ルートが2つになっています。この手順の3からやり直してください。

## 手順3. 計算フィールドに説明を付ける

Web エディターでは、計算フィールドに説明を書けません。スクリプトと Web エディターの2段で付けます。

1. スクリプトで説明を書き込みます。`--datasources` には、データソース名から `rpt_samplehyperstore__` を除いた名前を、スペース区切りで渡します（例: `billing`、`sales_orders shipments`）。省くと6本すべてが対象になります。この時点で、データソースの関係が一時的に外れます。

   ```
   python scripts/describe_rpt.py --project "<marts のパス>" --datasources billing --data ../../ja
   ```

2. データソースのページを開き直し、「編集」→「パブリッシュ」で、同じ名前・同じプロジェクトに上書きします。何も変えずに上書きすると、関係が戻り、説明は残ります。「パブリッシュ」を押しても反応しない時は、もう一度押します。

   この手順の1でスクリプトを動かす前から開いていたエディターのタブは、使わないでください。古い版で上書きしてしまいます。

次のコマンドで、説明が付いたことを確かめます。作ったデータソースについて `described 件数/件数` が揃えば合格です。そのうえで、手順2の合計がもう一度合うことを確かめます。

```
python scripts/check_metadata.py --project "<marts のパス>" --layer rpt --data ../../ja
```

エラーに「パブリッシュ済みデータソースにしか接続されていない」という趣旨の文が出た場合は、この手順の2がまだ済んでいません。

## 手順4. 試す

セットアップはこれで完了です。ここまで AI は使っていません。

- Tableau だけで確かめる場合: 手順2の合計の表が、そのまま確認になります。
- AI エージェントから試す場合: Tableau MCP をつないだ AI エージェントに、[`questions.md`](questions.md) の問いを尋ねます。Tableau MCP のつなぎ方は、使う AI エージェントの説明を参照してください。

## うまくいかない時

- `done` の代わりに `check these tables: [...]` と出た: そのテーブルを `--tables` で指定して実行し直します（例: `--tables orders`）。そのテーブルのデータソースが raw にすでにできていたら、先に Web の画面で削除します。
- `check_metadata.py` で `[missing]` が出る: パブリッシュの直後なら、数分おいて実行し直します。プロジェクトのパスの最後の階層（raw や marts）が合っているかも確かめます。
- 合計が合わない: 手順2の3（線の向き）と5（列名の ` (<テーブル名>.csv)`）を見直します。

## 気をつけること

- 生の層の列の説明は、部門の層には引き継がれません。部門の層には、計算フィールドの説明だけを付けています。
- データソースのページの URL は、上書きするたびに変わります。データソースは名前で検索して開いてください。
