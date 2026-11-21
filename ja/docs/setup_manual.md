# 手でセットアップする（日本語版）

AI エージェントや Tableau MCP を使わずに、SampleHyperStore の日本語版を Tableau Cloud に載せる手順です。AI エージェント向けの手順書 [`en/setup/SETUP_FOR_AI.md`](../../en/setup/SETUP_FOR_AI.md) と同じ内容を、人が順に進められる形にしています。

この手順でできあがるのは、生の層と部門の層の2つです。Tableau Knowledge の設定は Tableau MCP を使うため、この手順には含めていません。

日本語版のセットアップは、まだ通しで検証していません。英語版では、生の層 12 本と部門の層の billing 1 本で確かめています。

## 必要なもの

- Tableau Cloud の Creator ロールと、プロジェクトにパブリッシュする権限
- Python 3.10 以上
- Tableau の Web エディターを操作できること（手順3と4）

## 手順0. 準備する

以降のコマンドは、すべて `en/setup/` フォルダーで実行します。

1. 必要なライブラリを入れます。

   ```
   pip install -r requirements.txt
   ```

2. `.env.example` を `.env` にコピーし、`SERVER` と `SITE_NAME` を書きます。どちらも秘密の値ではありません。
3. サインインの状態を確かめます。サインインしていなければ、最初にスクリプトを動かした時にブラウザが開きます。トークンやパスワードをファイルに書く必要はありません。

   ```
   python scripts/tableau_auth.py status
   ```

4. プロジェクトを作ります。`<親プロジェクト>` には、サンドボックスなど既存のプロジェクトのパスを入れます。

   ```
   python scripts/create_projects.py --parent "<親プロジェクト>"
   ```

   次の構成ができ、2つのプロジェクトのパスが表示されます。権限が足りずに失敗した場合は、同じ構成を Web の画面で作ってください。

   ```
   <親プロジェクト>/
     <yyyymmdd>_SampleHyperStore/
       raw/     生の層の 12 データソース
       marts/   部門の層の 6 データソース
   ```

   ほかの SampleHyperStore のデータソースがあるプロジェクトは使わないでください。AI エージェントが両方を見てしまいます。

## 手順1. 生の層をパブリッシュする

まず `--dry-run` で .hyper ファイルだけを作り、エラーがないことを確かめます。そのあとで実際にパブリッシュします。

```
python scripts/publish_raw.py --project "<raw のパス>" --data ../../ja --dry-run
python scripts/publish_raw.py --project "<raw のパス>" --data ../../ja
```

12 テーブルそれぞれが `SampleHyperStore - <table>` という名前でパブリッシュされます。列の表示名と説明も書き込まれます。最後に `done` と出れば完了です。

説明が付いたかは、次のコマンドで確かめます。パブリッシュの直後は、反映に数分かかることがあります。

```
python scripts/check_metadata.py --project "<raw のパス>" --layer raw --data ../../ja
```

## 手順2. 進め方を決める

手順3と4は、Tableau の Web エディターでの手作業です。6 つのデータソースを1つずつ作ります。最初は billing の1本で手順3と4を通し、うまくいったら残りの5本に進むと安全です。

## 手順3. 部門の層を組む

`ja/setup/metadata/rpt_layer.json` に、6 つのデータソースの組み方と計算フィールドが書かれています。

| データソース | 根のテーブル | 関係 |
|---|---|---|
| rpt_samplehyperstore__billing | invoices | invoices →（請求書ID）invoice_lines →（商品ID）products。invoice_lines →（請求書ID と 商品ID）credit_memos |
| rpt_samplehyperstore__sales_orders | products | products →（商品ID）order_lines →（注文ID）orders |
| rpt_samplehyperstore__merchandising | products | sales_orders と同じ |
| rpt_samplehyperstore__shipments | products | products →（商品ID）shipment_lines →（出荷ID）shipments |
| rpt_samplehyperstore__returns_refunds | returns | returns →（商品ID）products。returns →（返品ID）refunds |
| rpt_samplehyperstore__web_analytics | web_sessions | web_sessions →（セッションID）web_searches |

1つのデータソースごとに、次の順で進めます。

1. 「新規」→「パブリッシュ済みデータソース」→「このサイト上」から、根のテーブルの生の層（`SampleHyperStore - <根>`）につなぎます。データソースのタブを開きます。
2. 残りのテーブルを「パブリッシュ済みデータソースを追加」で足します。順番は JSON の `parent_tables` の並びに従い、根は飛ばします。列名が重なると ` (<table>.csv)` が付きます。どちらに付くかは足す順番で決まり、計算式がその名前を使っています。
3. 関係の線は、ツリーにすでにあるテーブルの右端の「+」から、新しいテーブルへ引きます。逆向きに引くと、ベースのテーブルが2つになります。そうなると、ほかのテーブルの項目で分けた時に、総計が繰り返し表示されます。
4. 上の表のキーで、関係の項目を選びます。破線や「!」が残っていないことを確かめます。
5. JSON の `calculated_fields` の計算フィールドを、名前と式をそのまま写して作ります。データペインのメニュー（▾）→「計算フィールドの作成」から作り、「計算は有効です」と出ることを確かめます。
6. パブリッシュします。名前は `rpt_samplehyperstore__<部門>` にします。保存先は、ダイアログで marts のプロジェクトを選び直してください。既定では raw のプロジェクトが選ばれています。「資格情報を埋め込む」はオフのままにします。

パブリッシュしたら、計算フィールドが入ったかを確かめます。

```
python scripts/check_metadata.py --project "<marts のパス>" --layer rpt --data ../../ja
```

さらに、ワークシートで次の合計を出し、値が合うかを確かめます。値は英語版で確かめたものです。日本語版も数値は同じはずですが、まだ確かめていません。

| データソース | 項目 | 期待する値 |
|---|---|---:|
| sales_orders | 数量 | 111,008 |
| merchandising | 数量 / 注文明細数 | 115,435 / 71,007 |
| shipments | 数量 | 110,762 |
| returns_refunds | 返品申請数量 / 返品受領数量 / 返金額 | 7,944 / 6,704 / 907,537.58 |
| web_analytics | セッション数 / トランザクション数 / カート投入数量 | 455,057 / 24,484 / 191,594 |
| billing | 総売上 | 13,347,403.19 |

最後に、商品のカテゴリーで数量を分けてみます。すべてのカテゴリーで同じ値が出たら、ベースのテーブルが2つになっています。手順3の3からやり直してください。

## 手順4. 計算フィールドに説明を付ける

Web エディターでは、計算フィールドに説明を書けません。スクリプトと Web エディターの2段で付けます。

1. スクリプトで説明を書き込みます。この時点では、データソースのつながりが一時的に外れます。

   ```
   python scripts/describe_rpt.py --project "<marts のパス>" --datasources billing --data ../../ja
   ```

2. データソースのページを開き直し、「編集」→「パブリッシュ」で、同じ名前・同じプロジェクトに上書きします。何も変えずに上書きすると、つながりが戻り、説明は残ります。手順1より前に開いていたタブは古い版のままなので使わないでください。

`check_metadata.py --layer rpt` で説明が付いたことを確かめ、手順3の合計がもう一度合うことを確かめます。

## 手順5. 試す

セットアップはこれで使える状態です。[`questions.md`](questions.md) の問いを AI エージェントに尋ねてください。

## 気をつけること

- 生の層の列の説明は、部門の層には引き継がれません。部門の層には、計算フィールドの説明だけを付けています。
- データソースのページの URL は、上書きするたびに変わります。データソースは名前で検索して開いてください。
