# 問いのカタログ

Tableau 上の SampleHyperStore につないだ AI エージェントに投げる 19 の分析の問い。どれも業務の担当者が尋ねる言い方にしており、必要なテーブルはすべて `setup/` がパブリッシュする。想定する答えとよくある間違いは、問いがテストとして使えるように公開していない。

ただし[分析体験のページ](https://yoshitakaarakawa.github.io/SampleHyperStore/?lang=ja)では、Q02・Q11・Q15・Q17・Q45・Q49・Q50・Q52・Q62・Q63・Q68・Q70 の答えの全部または一部を見せている。これらの問いで AI エージェントを試すときは、このページとリポジトリ直下の `docs/` を読ませないこと。

- 相対的な期間の基準日: 利用者は 2025年12月上旬に尋ねている（データは 2025-12-31 まで）。「先月」= 2025年11月、「前四半期」= 暦の 2025年Q3。
- 会計年度は2月1日に始まる（FY2025 = 2025-02-01 .. 2026-01-31）。

| ID | 範囲 | ドメイン | Question (EN) | 問い（JA） |
|---|---|---|---|---|
| Q01 | 単一ドメイン | Web | For each traffic source, how many sessions did we get last year, and how far do those visitors get — product views, add to cart, checkout, order? | 流入元ごとに、昨年のセッション数と、商品閲覧・カート投入・チェックアウト・注文までどこまで進んだかを見せて。 |
| Q02 | 単一ドメイン | Web | What are customers searching for on our site that we couldn't show in stock? Show me the top search terms by month in 2024. | 2024年に、サイト内検索で在庫ありの商品を出せなかった検索語は何か。月ごとの上位を見せて。 |
| Q10 | 単一ドメイン | 販売 | Show me monthly sales by channel for the last two years, with year-over-year growth. | 直近2年の販路別の月次売上と、前年比を見せて。 |
| Q11 | 単一ドメイン | 販売 | How much of what customers ordered did we end up cancelling, and why? | 注文された数量のうち、どれだけをキャンセルしたか。理由は何か。 |
| Q15 | 単一ドメイン | フルフィルメント | Are our deliveries arriving late more often this year? Break it down by warehouse and carrier. | 今年は配達の遅れが増えているか。倉庫と配送業者で分けて見せて。 |
| Q17 | 単一ドメイン | フルフィルメント | How often do orders with tents get split into more than one shipment in the West, and did that get worse? | 西部でテントを含む注文が複数の出荷に分かれる頻度はどれくらいで、悪化した時期はあるか。 |
| Q18 | 単一ドメイン | 返品・サポート | What are the main reasons products are returned, by category? | カテゴリ別に、返品の主な理由は何か。 |
| Q27 | 単一ドメイン | 財務 | What was our net revenue by fiscal month this year, after returns and marketplace fees? | 今年度の会計月ごとの純売上はいくらか。返品とモール手数料を差し引いて。 |
| Q29 | 単一ドメイン | 財務 | How much do marketplace fees eat into our marketplace revenue? | モール手数料は、モール経由の売上をどれだけ削っているか。 |
| Q45 | 複数ドメイン | 返品・サポート、フルフィルメント | Did extending the return window to 60 days actually raise our return rate, or just delay returns? | 返品期限を60日に延ばしたことで、返品率そのものが上がったのか。単に返品が遅れて来るようになっただけか。 |
| Q47 | 複数ドメイン | 返品・サポート、財務 | Do Support's refund totals match what Finance booked as returns last quarter? | 前四半期、サポートの返金額と、経理が売上控除として計上した額は一致しているか。 |
| Q49 | 複数ドメイン | 販売、財務 | Since we launched on the marketplace, how much of our growth is real after fees? | モールに出店して以来、手数料を引いた後でも、伸びは本物か。 |
| Q50 | 複数ドメイン | 財務、販売 | Our finance report and the sales dashboard disagree on October revenue. Why? | 10月の売上が、経理の報告と販売のダッシュボードで合わない。なぜか。 |
| Q52 | 単一ドメイン | 財務 | Our West region is down year over year since January. Is business actually worse there? | 1月以降、West 地域が前年割れしている。本当に業績が悪いのか。 |
| Q62 | 単一ドメイン | フルフィルメント | How did on-time delivery change at each warehouse when the primary carrier changed? | 主要配送業者が替わった時、倉庫ごとの定時配達はどう変わったか。 |
| Q63 | 複数ドメイン | フルフィルメント、返品・サポート | Are late deliveries showing up in returns and refunds? | 配達の遅れは、返品や返金に表れているか。 |
| Q67 | 単一ドメイン | フルフィルメント | What share of orders were delivered after the date we promised the customer? | 顧客に約束した日より後に届いた注文は、どれくらいの割合か。 |
| Q68 | 複数ドメイン | フルフィルメント、販売 | Do customers who received a late delivery buy again less often than those who didn't? | 配達が遅れた顧客は、遅れなかった顧客より再購入が少ないか。 |
| Q70 | 複数ドメイン | 返品・サポート、フルフィルメント | What percentage of each month's orders were eventually returned? | 各月の注文のうち、最終的に返品された割合はどれくらいか。 |
