# Three-configuration comparison

Model qwen3:8b (temperature 0), embeddings sentence-transformers/all-MiniLM-L6-v2, chunk_size=500, chunk_overlap=50, top_k=3.


## Q1 (answer in one chunk): Which Maple Leaf Foods facility was the source of the 2008 listeriosis outbreak in Canada?

| Config | Context chunks (source, chunk_id, score) | Answer | Correct | Grounded | Refused |
|---|---|---|---|---|---|
| A | none | The 2008 listeriosis outbreak in Canada was linked to the Maple Leaf Foods facility in Toronto, Ontario. This outbreak resulted in multiple deaths and led to a widespread recall of products. It was the largest listeriosis outbreak in Canadian history. | no | n/a | no |
| B | wikipedia_2008_canadian_listeriosis_outbreak.txt #501 (0.8481); wikipedia_2008_canadian_listeriosis_outbreak.txt #502 (0.8144); wikipedia_2008_canadian_listeriosis_outbreak.txt #507 (0.658) | The 2008 listeriosis outbreak in Canada originated from lines 8 and 9 of the Maple Leaf Foods Bartor Road facility in Toronto, Ontario. This facility, with the establishment number 97B, was linked to the contamination of cold cuts that led to 57 confirmed cases and 23 deaths. The bacteria likely contaminated the products during the packaging process. | yes | yes | no |
| C | wikipedia_2008_canadian_listeriosis_outbreak.txt #501 (0.8481); wikipedia_2008_canadian_listeriosis_outbreak.txt #502 (0.8144); wikipedia_2008_canadian_listeriosis_outbreak.txt #507 (0.658) | The source of the 2008 listeriosis outbreak was the Maple Leaf Foods plant in Toronto, Ontario [Source 1]. Specifically, the outbreak originated from lines 8 and 9 of the Maple Leaf Foods Bartor Road facility (Establishment No. 97B) in Toronto, Ontario [Source 2]. | yes | yes | no |

## Q2 (answer needs two chunks): When was the Food Safety Modernization Act signed into law, and what was the original compliance date of the Food Traceability Rule?

| Config | Context chunks (source, chunk_id, score) | Answer | Correct | Grounded | Refused |
|---|---|---|---|---|---|
| A | none | The Food Safety Modernization Act (FSMA) was signed into law on January 4, 2011. The original compliance date for the Food Traceability Rule, which is part of FSMA, was January 1, 2022. However, the compliance date was later extended to January 1, 2025, for most covered products. | no | n/a | no |
| B | fda_fsma_food_traceability_rule.txt #153 (0.7282); fda_fsma_food_traceability_rule.txt #95 (0.7088); fda_fsma_food_traceability_rule.txt #94 (0.7071) | The Food Safety Modernization Act was signed into law in 2011. The original compliance date for the Food Traceability Rule was July 20, 2026. However, it was extended to July 20, 2028, due to a congressional directive. | no | no | no |
| C | fda_fsma_food_traceability_rule.txt #153 (0.7282); fda_fsma_food_traceability_rule.txt #95 (0.7088); fda_fsma_food_traceability_rule.txt #94 (0.7071) | I cannot answer this question from the provided documents. | no | n/a | yes |

## Q3 (similar information across documents): Which company was responsible for the 2008 to 2009 Salmonella outbreak linked to peanut butter, and what happened to the company afterwards?

| Config | Context chunks (source, chunk_id, score) | Answer | Correct | Grounded | Refused |
|---|---|---|---|---|---|
| A | none | The 2008 to 2009 Salmonella outbreak linked to peanut butter was caused by Peanut Corporation of America (PCA). The company was found to have knowingly sold contaminated peanut butter, leading to a massive recall and eventual bankruptcy. Following the outbreak, PCA's owner, Stewart Parnell, was convicted of criminal charges related to the contamination. | yes | n/a | no |
| B | wikipedia_peanut_corporation_of_america.txt #979 (0.6841); wikipedia_peanut_corporation_of_america.txt #972 (0.6499); wikipedia_peanut_corporation_of_america.txt #964 (0.6366) | The company responsible for the 2008 to 2009 Salmonella outbreak linked to peanut butter was the Peanut Corporation of America (PCA). The contamination led to the most extensive food recall in U.S. history, resulting in nine deaths and over 700 illnesses, and ultimately led to the company's bankruptcy. | yes | no | no |
| C | wikipedia_peanut_corporation_of_america.txt #979 (0.6841); wikipedia_peanut_corporation_of_america.txt #972 (0.6499); wikipedia_peanut_corporation_of_america.txt #964 (0.6366) | The Peanut Corporation of America (PCA) was responsible for the 2008 to 2009 Salmonella outbreak linked to peanut butter [Source 2]. The contamination triggered the most extensive food recall in U.S. history up to that time, involving 46 states, more than 360 companies, and more than 3,900 different products manufactured using PCA ingredients [Source 3]. | no | yes | no |

## Q4 (ambiguous): What caused the outbreak?

| Config | Context chunks (source, chunk_id, score) | Answer | Correct | Grounded | Refused |
|---|---|---|---|---|---|
| A | none | The cause of the outbreak depends on the specific disease or event in question. It could be due to a virus, bacteria, environmental factors, or human activity. To provide an accurate answer, more context is needed about the outbreak being referred to. | yes | n/a | no |
| B | wikipedia_2011_germany_e_coli_outbreak.txt #528 (0.7633); wikipedia_2006_spinach_e_coli_outbreak.txt #493 (0.6633); wikipedia_2011_germany_e_coli_outbreak.txt #533 (0.5863) | The outbreak was likely caused by contaminated spinach, as the data indicated spinach was a probable source. Most victims became infected in Germany or France, suggesting the contamination may have originated from these regions. The source investigation is ongoing to confirm the exact cause. | no | n/a | no |
| C | wikipedia_2011_germany_e_coli_outbreak.txt #528 (0.7633); wikipedia_2006_spinach_e_coli_outbreak.txt #493 (0.6633); wikipedia_2011_germany_e_coli_outbreak.txt #533 (0.5863) | The outbreak was caused by contaminated food, specifically spinach, which was identified as a likely source [Source 2]. The contamination led to an ongoing outbreak with most or all victims becoming infected in Germany or France [Source 3]. The exact cause was not specified in the provided documents. | no | n/a | yes |

## Q5 (answer not in the documents): What is the FDA's toll-free phone number for reporting a problem with a recalled food?

| Config | Context chunks (source, chunk_id, score) | Answer | Correct | Grounded | Refused |
|---|---|---|---|---|---|
| A | none | The FDA's toll-free phone number for reporting a problem with a recalled food is 1-800-FDA-1040 (1-800-323-1040). This number connects you to the FDA's Food Emergency Response Team. You can also report issues online through the FDA's Safety Reporting Portal. | no | n/a | no |
| B | ecfr_21_cfr_part_7_subpart_c_recalls.txt #50 (0.7445); fda_food_recalls_what_you_need_to_know.txt #75 (0.7027); ecfr_21_cfr_part_7_subpart_c_recalls.txt #21 (0.6933) | The context provided does not include the FDA's toll-free phone number for reporting a problem with a recalled food. The information focuses on the recall process and regulations rather than contact details. For reporting issues with recalled foods, consumers should visit the FDA's website or contact their local FDA district office. | yes | n/a | yes |
| C | ecfr_21_cfr_part_7_subpart_c_recalls.txt #50 (0.7445); fda_food_recalls_what_you_need_to_know.txt #75 (0.7027); ecfr_21_cfr_part_7_subpart_c_recalls.txt #21 (0.6933) | I cannot answer this question from the provided documents. | yes | n/a | yes |

## Q6 (unrelated): Who won the 2018 FIFA World Cup?

| Config | Context chunks (source, chunk_id, score) | Answer | Correct | Grounded | Refused |
|---|---|---|---|---|---|
| A | none | France won the 2018 FIFA World Cup, defeating Croatia 4-2 in the final held in Moscow. This was France's second World Cup title, with the victory coming after a penalty shootout in extra time. The tournament was hosted by Russia for the first time in its history. | no | n/a | no |
| B | wikipedia_food_distribution.txt #817 (0.382); wikipedia_food_distribution.txt #796 (0.2249); wikipedia_food_distribution.txt #816 (0.2023) | The 2018 FIFA World Cup was won by France. They defeated Croatia in the final match, which took place in Moscow, Russia. This victory marked France's second World Cup title in their history. | no | no | no |
| C | wikipedia_food_distribution.txt #817 (0.382) | I cannot answer this question from the provided documents. | yes | n/a | yes |
