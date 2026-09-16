# pj1 PROJECT KNOWLEDGE
> このファイルは pj1 プロジェクトのコンテキストです。会話開始時に必ず参照してください。

**最終更新**: 2026-09-15

---

## Project Definition
- **テーマ**: 黒潮を対象とした SWOT 波–風–流れ相互作用研究。Plan A（第1段階）＝南日本黒潮の Hs 勾配の2D統計と、大蛇行(LM 2023–2025/4)/非大蛇行(NLM 2025/5–)の比較。
- **領域**: 黒潮南日本域（130–142°E, 28–36°N；トカラ〜伊豆）
- **主要変数**: wind speed（風速）, significant wave height（有義波高 Hs）, sea surface level（海面高度 SSH→地衡流）, current speed（流速）
- **データ**: SWOT（L2 LR WindWave / L3 SSH。一部 bada 配置）、再解析（ERA5 風・SLP、JCOPE2M / JCOPE-T DA 流れ）、衛星（CFOSAT SWIM）、現場（NOWPHAS、沖縄ブイ航海 2026-09-24〜10-11）
- **手法**: 全パス・スクリーニング → 風寄与の除去（U10–Hs 回帰残差 Hs' ／ WW3 CTRL）→ 流軸直交座標コンポジット（距離×相対角×季節×LM/NLM）。SWOT SSH から地衡流（9×9画素 平面フィット、Qiu & Chen の denoising/subcycle に倣う）
- **目的 / 問い**: (1) 好条件（弱風<7–8 m/s・強流>1 m/s・逆行 相対角>135°）の頻度・季節・場所の気候学、(2) 風寄与を除いた Hs' の2D構造と地衡流の対応（逆行/追い/横切り）、(3) LM vs NLM での違い
- **出発点**: Villas Bôas, Marechal & Bohé (2025, GRL, 10.1029/2024GL114331)。全体計画は Obsidian の研究プラン v2（`Research/Projects/pj1/`）。
- **段階設計**: M.S. 論文は Plan A ステップ0–2 + Plan B（沖縄ブイ逆風ケース）で自己完結 → 同成果が PhD 第1章。

---

## Confirmed Facts
（確認済みの事実。確信度 高。まだ無し）

## Working Hypotheses
- **予測（線形波線理論）**: 逆行（対向流）では流軸付近で Hs' に正のピーク＋縁に急勾配（作用保存・群速度低下）。追い流れでは軸沿いに帯状構造（波束捕捉 trapping; Kudryavtsev et al. 2017 が Agulhas で観測）。→ Gulf Stream の古典ケースと系統的に異なる、という検証可能な予測。
- SWOT 風（σ0 粗度由来）と ERA5 風（モデル）の系統差そのものが結果になりうる（Kaouah et al. 2025 の SST 依存と比較）。

## Rejected Interpretations / Dead Ends
（否定された解釈・失敗した手法と理由。同じ失敗を繰り返さない）

---

## Research Narrative
| 資料 | ストーリー骨格 |
|------|--------------|
| 学会発表 | |
| 投稿論文 | |

---

## Key References
| 論文 | 関連 |
|-----|------|
| Villas Bôas, Marechal & Bohé (2025, GRL) | 出発点。SWOT Hs・風・地衡流 + WW3 の exploratory study（コード: mines-oceanography/swot_wave_current） |
| Woo & Park (2020, IGARSS) | 黒潮での波流相互作用の直接先行（1D高度計+swell-ray）。**必ず引用**、本研究は2D・WW3機構分解へ |
| Wu, Li, Chen & Ma (2025, Ocean Dyn.) | 続流域の渦内 Hs・波向の点統計。**必ず引用** |
| Kaouah et al. (2025, GRL) | SWOT σ0風 と SST の相関。SWOT風 vs ERA5 の系統差の比較対象 |
| Qiu & Chen (2025, JPO); Zhang et al. (2024, GRL) | SWOT SSH 続流微細構造（地衡流計算・denoising・subcycle の手順の借用元） |
| Tamura et al. (2008,2009); Waseda et al. (2014) | 黒潮続流域の波流相互作用の古典（衛星2Dなし） |
