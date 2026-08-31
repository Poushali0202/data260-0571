# AI-use statement

1. I used an AI assistant to help scaffold the HTML, JavaScript, Python adapter,
   agent pipeline, Docker configuration, ECS deployment script, and report
   structure. I supplied the personal configuration values and must run,
   inspect, and submit the results myself.
2. One unsuitable initial implementation treated the form as a generic course
   feedback form and did not satisfy the assigned domain or all required fields.
3. I detected this by checking the implementation line-by-line against the
   assignment rubric and by adding `verify_hw01.py` checks for the required
   controls and behaviors.
4. I replaced it with a grocery supply/recall notice schema, added primary and
   secondary fields, description-length and terms validation, JSON parsing,
   destructuring, spread-based `submissionDate`, and a private submission
   counter closure. The self-check verifies these requirements without
   pretending that unavailable Ollama/AWS runs occurred.
