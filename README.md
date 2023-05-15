# twenty-questions-bot
Langchain chatbot that plays the "20 Questions" game

## Installation

1. Clone this repo.
2. Set up a Python 3.11 environment using pyenv + Poetry.

## Play

`export` (or pass before the command) the `OPENAI_API_KEY` env var with your key.

```
poetry run bin/run.py <username>
```

This will start the Gradio server, open the url it gives you in a web browser.

History is stored per-username. If you use a new username (or a fresh db file) you will likely see the same subjects again (we're still picking from a random pool, but LLM tends to generate the same ones every time).

## Notes/thoughts

### TODO

- https://python.langchain.com/en/latest/modules/models/llms/examples/llm_caching.html
- make prompts more robust
- add self-reflection and lookup for post-2021 facts
- If you play lots of games the subject history will eventually overflow the prompt. Also the model tends to pick same subjects (hence need for history)... might be better to pre-gen an extensive dictionary of subjects by whatever means
- "give me a clue" option on the last question? (in case the LLM chose something ambiguous and is being picky)
- feedback loop: rating system for LLM responses which lead to bad games, can form test data for future improvement
  - maybe via: https://gradio.app/docs/#flagging
- https://promptlayer.com/ logging
- try other LLM backends, e.g. are the OSS ones good enough to play it? or local LLaMA?
  - https://github.com/kagisearch/pyllms
- deployment
  - https://docs.beam.cloud/getting-started/langchain ?

https://huggingface.co/spaces/liujch1998/vera might be handy
