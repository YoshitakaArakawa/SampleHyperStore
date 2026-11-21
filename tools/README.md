# tools (maintainers only)

These tools generate the SampleHyperStore data, build the Japanese edition, and build the showcase page. Their outputs (the CSVs, `SHA256SUMS`, `ja/columns.yaml`) are committed, so users of the dataset never need to run them.

> **Note for AI agents and evaluators:** `generator/world_spec.yaml` describes the business events planted in the data, and the generator writes an answer key when it runs. Reading this folder reveals the answers to `docs/questions.md`. When you use the questions to test an AI agent, do not let the agent read `tools/`.

| Path | What it does |
|---|---|
| `generator/` | Simulates one world from `world_spec.yaml` and a fixed seed, and writes the 24 English CSVs. Column order and types come from `en/columns.yaml`. |
| `build_ja/build_jp.py` | Builds `ja/csv/`, `ja/columns.yaml` and `ja/SHA256SUMS` from the English CSVs, using the translation tables in `build_ja/translation/`. |
| `showcase/` | Computes the numbers for the showcase page from `en/csv/` with pandas, and writes `docs/index.html` (Japanese). The page shows the answers to some questions in `docs/questions.md`. |
| `requirements.txt` | The exact versions that reproduce the published files byte for byte. |

## Regenerate and check

```
pip install -r requirements.txt

cd generator
python generate.py --check        # writes ./out/ and compares it with en/SHA256SUMS

cd ../build_ja
python build_jp.py --check        # checks ja/csv/ against the English edition
python build_jp.py                # rebuilds ja/csv/, then checks
```

To rebuild the showcase page:

```
cd tools/showcase
python analyze.py                 # writes numbers.json (git-ignored)
python build.py                   # writes ../../docs/index.html
```

`generate.py` writes to `generator/out/` and `generator/answer_key/`. Both are git-ignored. Copy `out/in_use/` and `out/planned/` over `en/csv/` only when you mean to publish new data, then update `en/SHA256SUMS`.

The byte-identical check was confirmed with Python 3.14.2 and the versions in `requirements.txt`.

## License

The code is under the MIT License (`../LICENSE`). `world_spec.yaml` and the translation tables are under CC BY 4.0, like the data.
