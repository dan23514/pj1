@research/PROGRESS.md
@research/KNOWLEDGE.md
@research/LOG.md

# pj1 Repository — Claude Code Instructions

このリポジトリは **pj1 プロジェクト＝黒潮を対象とした SWOT 波–風–流れ相互作用研究（Plan A / 第1段階）** のコード＋研究コンテキスト。
ローカル(このPC)・研究室デスクトップ(atomic)・研究室サーバー(bada) が git で同期して作業する。
- **主要変数**: wind speed（風速）／ significant wave height（有義波高 Hs）／ sea surface level（海面高度 SSH→地衡流）／ current speed（流速）
- **領域**: 黒潮域（トカラ〜伊豆の南日本域を中心に検討中。具体的な範囲は未確定）
- **データ**: SWOT（L2 LR WindWave / L3 SSH。一部 bada に配置）＋ 再解析（ERA5・JCOPE）＋ 衛星（CFOSAT）＋ 現場（NOWPHAS・沖縄ブイ）
- テーマ・問い・計画の詳細は `research/KNOWLEDGE.md`／`research/PROGRESS.md`、全体計画は Obsidian の研究プラン（`Research/Projects/pj1/`）を参照。

## このリポジトリの構成
- `research/` — 研究コンテキスト（進捗・知見・ログ・解析記録・技術メモ）
- コード置き場（`scripts/` など）はプロジェクトの都合で作る。1プロジェクト=1リポジトリ。

## 実行環境
- **ローカル**: uv製の共有環境 `C:\Users\tkm14\envs\py312`（Python 3.12）。`activatepy312` で有効化してから `python ...`。
- **サーバー(bada/atomic)**: 各サーバーの py312 環境を有効化してから実行（システムpythonは使わない）。
  - atomic: Miniforge(conda-forge) の `~/envs/py312`（= `/home/akule/takamio/envs/py312`）。`activatepy312`（= `conda activate ~/envs/py312`）で有効化。

## データの場所（重要・repoには入れない）
- データ(`.nc`/`.npz`/`.csv` 等)は git に入れない。`.gitignore` で除外済み。
- 参照は環境変数 **`RESEARCH_DATA`** をベースにする（マシンごとに設定）:
  - ローカル: `C:\Users\tkm14\data`
  - bada: `/export/bada1/seolab/Data`
  - atomic: `/data4`（外付けマウント。`export RESEARCH_DATA=/data4` を `~/.bashrc` に追記。ホームは `/home/akule/takamio`）
  ```python
  import os; from pathlib import Path
  BASE = Path(os.environ["RESEARCH_DATA"])
  # ds = xr.open_dataset(BASE / "<dataset>/...")
  ```
- **解析は「データのある場所」で行う**。複数データを組み合わせる時は、大きい方のマシンに小さい方を寄せて1か所に集めてから結合する（恒久的な二重持ちはしない）。

## 進捗ファイルの3層（混同しない）
- `research/LOG.md` — 大まかな時系列ログ。解析のたび先頭に1行追記。
- `research/PROGRESS.md` — 現在地ダッシュボード。上書き更新。
- `research/KNOWLEDGE.md` — 確定知見・仮説・棄却解釈・ナラティブ。

## 解析を行ったとき
1. コードを保存し `/code-review` を実行
2. `research/analyses/YYYYMMDD_<解析名>.md` を新規作成（`_TEMPLATE.md` をコピー）。`## コード解説` と `## コードレビュー結果` を記入
3. 最終図のみ `results/` に保存（`<解析名>_<内容>.png`）。没図・中間データは入れない
4. `research/LOG.md` の先頭に1行追記
5. 作業前に `git pull`、作業後に `git commit && git push`

## 注意
- AIの出力は常にユーザーが確認する。確認前の結果は「暫定値」（`status: pending_review`→本人確認後 `reviewed`）
- プロジェクト固有の仮説・知見は他プロジェクトに流用しない（混入防止）
- 全研究共通ルールは OneDrive `Research/RESEARCH_RULES.md`（正本・ローカルから参照可）。**サーバーからはOneDriveが見えない**ため、共通ルールをサーバー側でも参照する仕組み（shared-core）は別途整備する。
- Obsidian（論文ノート・議事録・解釈の散文）はPC専用。解析に必要な技術知識はこのリポジトリに置く。
