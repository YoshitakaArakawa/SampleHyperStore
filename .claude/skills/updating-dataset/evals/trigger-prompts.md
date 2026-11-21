---
purpose: updating-dataset のトリガー回帰テスト用プロンプト集
note: description・本文の修正時に fresh session で全プロンプトを確認する。運用中に観測された不発・誤発火はここに追記する
---

# トリガーテスト

## 起動すべき（should fire）

- planned にある customers の表も Tableau で使えるようにしたい
- world_spec.yaml の seed を変えて CSV を作り直して
- billing に計算フィールドを1つ足したい。英日どちらも
- raw_layer.json の orders の列の説明を直したい
- sales_orders に refunds を関連付けたい
- Add the suppliers table to the Tableau setup and update the docs

## 起動すべきでない（should not fire）

- SampleHyperStore を自分の Tableau Cloud にセットアップしたい（→ en/setup/SETUP_FOR_AI.md）
- questions.md の Q11 を Tableau MCP で解いてみて
- 訴求ページの配色を変えたい
- README の英語の言い回しを直して
