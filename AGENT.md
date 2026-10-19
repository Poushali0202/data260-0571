# AGENT.md

## Project description

- This repository is the DATA-260 project of Poushali Purkayastha (SID4 0571): a grocery supply and recall notice service with a FastAPI backend on port 8571, a React client, and a local assistant that keeps MongoDB memory and file memory.
- The domain entity is a grocery notice: product, source, category (recall, shortage, contamination, distribution), status and dates.

## Technology stack

- Python 3.12 with FastAPI and Pydantic v2. MySQL through SQLAlchemy holds the relational data, MongoDB through PyMongo holds the document view and the chat memory.
- The language model is qwen3:8b served by Ollama and is called only through `src/model_client.py`.

## Coding conventions

- Functions use snake_case names, a type hint on every parameter and on the return value, and start with a one-line docstring.
- Library code returns values and raises ValueError on bad input. It never prints and never exits the process.
- Keep functions short and plain. No decorative comments and no code that is not used.

## Testing approach

- Every new function comes with at least one `test_` function that uses plain assert statements and runs with `python file.py`, without a test framework.
- Smoke tests live in `verify_hwNN.py`, write `reports/hwNN/verification.json`, and must not modify application code.

## Prohibited actions

- Never commit `.env`, API keys or passwords.
- Never drop MongoDB collections or MySQL tables from application code.
- Never call the model outside `src/model_client.py` and never use a paid hosted model for the homework runs.

## Code review output

- When asked to review code, return bullet-only feedback: every line begins with `- `, include only actionable findings or `- No issues found.`, and do not use headings, paragraphs, fenced code or greetings.
