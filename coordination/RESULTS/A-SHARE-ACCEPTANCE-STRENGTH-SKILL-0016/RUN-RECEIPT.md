# A-Share Acceptance Strength Skill 0016

## Status

SUCCESS_WITH_FINDINGS

## Created Skill

`C:\Users\Administrator\.codex\skills\a-share-acceptance-strength-mapper`

## Files

- `SKILL.md`: trigger, workflow, evidence ladder, downgrade rules
- `references/evidence-map.md`: four-layer user knowledge map and scoring matrix
- `references/research-basis.md`: microstructure and A-share research anchors
- `references/output-template.md`: response template for chengjie / red-turn questions
- `agents/openai.yaml`: UI metadata

## Validation

`quick_validate.py` passed.

## Research Anchors

- Cont, Kukanov, Stoikov, The Price Impact of Order Book Events: https://arxiv.org/abs/1011.6402
- Xu, Gould, Howison, Multi-Level Order-Flow Imbalance: https://ora.ox.ac.uk/objects/uuid:9b7d0422-4ef1-48e7-a2d4-4eaa8a0a7ec1/files/m89dedb16194e627a2c92d14e3329bd48
- Bouchaud, Price Impact: https://arxiv.org/abs/0903.2428
- Bouchaud et al., Trades, Quotes and Prices: https://www.cambridge.org/core/books/trades-quotes-and-prices/029A71078EE4C41C0D5D4574211AB1B5
- Shanghai Stock Exchange trading rules: https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20260424_10816492.shtml
- Shenzhen ChiNext special trading provisions: https://docs.static.szse.cn/www/disclosure/notice/general/W020200612831351578076.pdf

## Governance

- guidance-only
- Experimental
- no raw L2 gate cleared
- no live trading enabled
- no strategy rule promoted without replay validation

## Mother-System Writeback

See `MOTHER-SYSTEM-RECORDS.json`.
