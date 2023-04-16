# twenty-questions-bot
Langchain chatbot that plays the "20 Questions" game

## Installation

1. Clone this repo.
2. Set up a Python 3.11 environment using pyenv + Poetry.

## Play

`export` (or pass before the command) the `OPENAI_API_KEY` env var with your key.

```
poetry run python -m twentyqs.run <username> --simple
```

This will start the Gradio server, open the url it gives you in a web browser.

## Notes/thoughts

### TODO

- https://python.langchain.com/en/latest/modules/models/llms/examples/llm_caching.html
- make prompts more robust
- add self-reflection and lookup for post-2021 facts
- If you play lots of games the subject history will eventually overflow. Also the model tends to pick same subjects (hence need for history)... might be better to pre-gen an extensive dictionary of subjects by whatever means
- "give me a clue" option on the last question? (in case the LLM chose something ambiguous and is being picky)
- feedback loop: rating system for LLM responses which lead to bad games, can form test data for future improvement
  - maybe via: https://gradio.app/docs/#flagging
- https://promptlayer.com/ logging
- try other LLM backends, e.g. are the OSS ones from goose.ai good enough to play it? or local LLaMA?
  - https://github.com/kagisearch/pyllms
- deployment
  - https://docs.beam.cloud/getting-started/langchain ?
