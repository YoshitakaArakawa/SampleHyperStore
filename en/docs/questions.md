# Question catalog

19 analysis questions to ask an AI agent connected to SampleHyperStore on Tableau. Each is phrased the way a business user would ask it, and every table it needs is published by `setup/`. The intended answers and the common mistakes are not published, so that the questions stay useful as a test.

The [showcase page](https://yoshitakaarakawa.github.io/SampleHyperStore/) reveals all or part of the answers to Q02, Q11, Q15, Q17, Q45, Q49, Q50, Q52, Q62, Q63, Q68, Q70. When you test an AI agent with these questions, do not let it read that page or the top-level `docs/` folder.

- "As of" for relative periods: the user asks in early December 2025 (data ends 2025-12-31). "last month" = November 2025; "last quarter" = calendar Q3 2025.
- The fiscal year starts on February 1 (FY2025 = 2025-02-01 .. 2026-01-31).

| ID | Scope | Domains | Question (EN) | 問い（JA） |
|---|---|---|---|---|
| Q01 | single domain | web | For each traffic source, how many sessions did we get last year, and how far do those visitors get — product views, add to cart, checkout, order? | 流入元ごとに、昨年のセッション数と、商品閲覧・カート投入・チェックアウト・注文までどこまで進んだかを見せて。 |
| Q02 | single domain | web | What are customers searching for on our site that we couldn't show in stock? Show me the top search terms by month in 2024. | 2024年に、サイト内検索で在庫ありの商品を出せなかった検索語は何か。月ごとの上位を見せて。 |
| Q10 | single domain | sales | Show me monthly sales by channel for the last two years, with year-over-year growth. | 直近2年の販路別の月次売上と、前年比を見せて。 |
| Q11 | single domain | sales | How much of what customers ordered did we end up cancelling, and why? | 注文された数量のうち、どれだけをキャンセルしたか。理由は何か。 |
| Q15 | single domain | fulfillment | Are our deliveries arriving late more often this year? Break it down by warehouse and carrier. | 今年は配達の遅れが増えているか。倉庫と配送業者で分けて見せて。 |
| Q17 | single domain | fulfillment | How often do orders with tents get split into more than one shipment in the West, and did that get worse? | 西部でテントを含む注文が複数の出荷に分かれる頻度はどれくらいで、悪化した時期はあるか。 |
| Q18 | single domain | returns_support | What are the main reasons products are returned, by category? | カテゴリ別に、返品の主な理由は何か。 |
| Q27 | single domain | finance | What was our net revenue by fiscal month this year, after returns and marketplace fees? | 今年度の会計月ごとの純売上はいくらか。返品とモール手数料を差し引いて。 |
| Q29 | single domain | finance | How much do marketplace fees eat into our marketplace revenue? | モール手数料は、モール経由の売上をどれだけ削っているか。 |
| Q45 | cross domain | returns_support, fulfillment | Did extending the return window to 60 days actually raise our return rate, or just delay returns? | 返品期限を60日に延ばしたことで、返品率そのものが上がったのか。単に返品が遅れて来るようになっただけか。 |
| Q47 | cross domain | returns_support, finance | Do Support's refund totals match what Finance booked as returns last quarter? | 前四半期、サポートの返金額と、経理が売上控除として計上した額は一致しているか。 |
| Q49 | cross domain | sales, finance | Since we launched on the marketplace, how much of our growth is real after fees? | モールに出店して以来、手数料を引いた後でも、伸びは本物か。 |
| Q50 | cross domain | finance, sales | Our finance report and the sales dashboard disagree on October revenue. Why? | 10月の売上が、経理の報告と販売のダッシュボードで合わない。なぜか。 |
| Q52 | single domain | finance | Our West region is down year over year since January. Is business actually worse there? | 1月以降、West 地域が前年割れしている。本当に業績が悪いのか。 |
| Q62 | single domain | fulfillment | How did on-time delivery change at each warehouse when the primary carrier changed? | 主要配送業者が替わった時、倉庫ごとの定時配達はどう変わったか。 |
| Q63 | cross domain | fulfillment, returns_support | Are late deliveries showing up in returns and refunds? | 配達の遅れは、返品や返金に表れているか。 |
| Q67 | single domain | fulfillment | What share of orders were delivered after the date we promised the customer? | 顧客に約束した日より後に届いた注文は、どれくらいの割合か。 |
| Q68 | cross domain | fulfillment, sales | Do customers who received a late delivery buy again less often than those who didn't? | 配達が遅れた顧客は、遅れなかった顧客より再購入が少ないか。 |
| Q70 | cross domain | returns_support, fulfillment | What percentage of each month's orders were eventually returned? | 各月の注文のうち、最終的に返品された割合はどれくらいか。 |
