# twenty-questions-bot
Langchain chatbot that plays the "20 Questions" game

## Installation

### Python install

1. Clone this repo.
2. Set up a Python 3.11 environment using pyenv + Poetry.

### Docker

There is also an image published to Docker Hub: `anentropic/twenty-questions-bot`.

## Play

History is stored per-username. If you use a new username (or a fresh db file) you will likely see the same subjects again (we're still picking from a random pool, but LLM tends to generate the same ones every time).

### Python install

`export` (or pass before the command) the `OPENAI_API_KEY` env var with your key, then:

```
poetry run src/bin/run.py <username>
```

This will start the Gradio server, open the url it gives you in a web browser.

### Docker

```sh
docker run \
  -e ADMIN_PASSWORD=****** \
  -e OPENAI_API_KEY=****** \
  anentropic/twenty-questions-bot
```

This will start the web server, open the url it gives you in a web browser.

The game is password protected to avoid the general public burning through your OpenAI credits (it costs ~US$0.04 per game currently).

Server is initalised with an `admin` user, with your password. You can use this to play the game, or go to `http://127.0.0.1:8000/admin/` and login, you can then create non-admin user accounts that can be used to play the game.

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
  - https://api.openai.com/dashboard/billing/usage can be accessed via HTTP basic auth using username + API key
  - see also https://api.openai.com/dashboard/billing/credit_grants
- try other LLM backends, e.g. are the OSS ones good enough to play it? or local LLaMA?
  - https://github.com/kagisearch/pyllms
  - https://huggingface.co/liujch1998/vera might be handy (it did well at recognising yes/no questions when I tried it)

