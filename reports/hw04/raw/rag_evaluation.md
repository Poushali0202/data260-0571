# Evaluation

Model qwen3:8b (temperature 0), embeddings sentence-transformers/all-MiniLM-L6-v2, chunk_size=500, chunk_overlap=50, top_k=3.


| Question | Config | Correct retrieval | Correct answer | Grounded | Refused when needed | Format OK |
|---|---|---|---|---|---|---|
| Q1 | A | no | no | n/a | yes | yes |
| Q1 | B | yes | yes | yes | yes | yes |
| Q1 | C | yes | yes | yes | yes | yes |
| Q2 | A | no | no | n/a | yes | yes |
| Q2 | B | no | no | no | yes | yes |
| Q2 | C | no | no | n/a | no | yes |
| Q3 | A | no | yes | n/a | yes | yes |
| Q3 | B | no | yes | no | yes | yes |
| Q3 | C | no | no | yes | yes | yes |
| Q4 | A | n/a | yes | n/a | yes | yes |
| Q4 | B | n/a | no | n/a | yes | yes |
| Q4 | C | n/a | no | n/a | no | no |
| Q5 | A | n/a | no | n/a | no | yes |
| Q5 | B | n/a | yes | n/a | yes | yes |
| Q5 | C | n/a | yes | n/a | yes | yes |
| Q6 | A | n/a | no | n/a | no | yes |
| Q6 | B | n/a | no | no | no | yes |
| Q6 | C | n/a | yes | n/a | yes | yes |

| Config | Accuracy (correct answers / 6) | Faithfulness (grounded / answered with context) | Format compliance | Robustness (Q5, Q6 refused) |
|---|---|---|---|---|
| A | 2/6 | n/a (no context) | 6/6 | 0/2 |
| B | 3/6 | 1/4 | 6/6 | 1/2 |
| C | 3/6 | 2/2 | 5/6 | 2/2 |
