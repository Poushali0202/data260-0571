# top_k sweep

Model qwen3:8b (temperature 0), embeddings sentence-transformers/all-MiniLM-L6-v2, chunk_size=500, chunk_overlap=50, top_k=3.


Question Q2: When was the Food Safety Modernization Act signed into law, and what was the original compliance date of the Food Traceability Rule?

| k | Retrieved (source, chunk_id, score) | Kept after filtering | Answer | Correct | Cited |
|---|---|---|---|---|---|
| 1 | fda_fsma_food_traceability_rule.txt #153 (0.7282) | [153] | I cannot answer this question from the provided documents. | no | [] |
| 3 | fda_fsma_food_traceability_rule.txt #153 (0.7282); fda_fsma_food_traceability_rule.txt #95 (0.7088); fda_fsma_food_traceability_rule.txt #94 (0.7071) | [153, 95, 94] | The Food Safety Modernization Act was signed into law on January 4, 2011 [Source 3]. The original compliance date of the Food Traceability Rule was July 20, 2026, but it was extended to July 20, 2028 [Source 3]. | no | [3, 3] |
| 5 | fda_fsma_food_traceability_rule.txt #153 (0.7282); fda_fsma_food_traceability_rule.txt #95 (0.7088); fda_fsma_food_traceability_rule.txt #94 (0.7071); fda_fsma_food_traceability_rule.txt #93 (0.7028); fda_fsma_food_traceability_rule.txt #169 (0.6987) | [153, 95, 94, 93, 169] | The Food Safety Modernization Act was signed into law on January 4, 2011 [Source 3]. The original compliance date of the Food Traceability Rule was January 20, 2026 [Source 4]. | yes | [3, 4] |
