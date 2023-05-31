# 🤖 twenty-questions-bot
Langchain chatbot that plays the "20 Questions" game

## Installation

### Python install

1. Clone this repo.
2. Set up a Python 3.11 environment using pyenv + Poetry.

### Docker

There is also an image published to Docker Hub: `anentropic/twenty-questions-bot` (no local install required).

## Play

History is stored per-username. If you use a new username (or a fresh db file) you will likely see the same subjects again (we're still picking from a random pool, but LLM tends to generate the same ones every time).

### Python install

`export OPENAI_API_KEY=*****` env var with your key, then:

```sh
poetry run src/bin/run.py <username>
```

This will start the Gradio server, open the url it gives you in a web browser.

### Docker

There is also an image published to Docker Hub, which runs a web server with a couple more features. This is mostly intended for hosting twenty-questions-bot on the internet, but is also a handy way to run locally. 

```sh
docker run \
  -e ADMIN_PASSWORD=****** \
  -e OPENAI_API_KEY=****** \
  anentropic/twenty-questions-bot
```

This will start the web server, open the url it gives you in a web browser.

The game is password protected to avoid the general public burning through your OpenAI credits (it costs ~US$0.04 per game currently).

Server is initalised with an `admin` user, with your password. You can use this to play the game, or go to `http://127.0.0.1:8000/admin/` and login, you can then create non-admin user accounts that can be used to play the game.

#### Building locally

To build the Docker image locally you need to set the `ARCHPREFIX` build arg, e.g. `--build-arg ARCHPREFIX=aarch64` for Apple Silicon macs, or `x86_64` for Intel.

### Non-Docker local web app

`export OPENAI_API_KEY=*****` env var with your key, then:

```sh
ADMIN_PASSWORD=****** poetry run uvicorn server.app:app
```

## Notes/thoughts

### TODO

- LLM backend:
  - make prompts more robust... key problems currently are:
    - yes/no question validator is prone to false negatives (better than the opposite, but annoying)
    - when generating a list of subjects to choose from (random choice from generated list happens in Python) we have to add a list of previously-chosen subjects to the prompt, otherwise it tends to generate the same choices every time
    - so if you play lots of games the subject history would eventually overflow the prompt
    - this list is generated per-user which mitigates slightly, as it takes longer to go wrong
    - but this list of "subjects not to choose" inadvertently acts as a list of examples, so it starts to influence the generated subjects in negative ways e.g. if it previously generated "The Mona Lisa" (a good choice) it may later riff on that and generate "The Mona Lisa's eyes" (an awkward, over-specific choice)
    - it might be better to do it iteratively
    - https://twitter.com/altryne/status/1661236951629066241?s=20 suggests a 'base model' like text-davinci-003	may do better than a chat model for task of completing lists of examples
  - add self-reflection and lookup for post-2021 facts
  - "give me a clue" option on the last question? (in case the LLM chose something ambiguous and is being picky)
  - feedback loop: rating system for LLM responses which lead to bad games, can form test data for future improvement
    - maybe via: https://gradio.app/docs/#flagging
  - https://promptlayer.com/ logging
  - maybe a quota system would allow an open public demo user
  - try other LLM backends, e.g. are the OSS ones good enough to play it? or local LLaMA?
    - https://github.com/kagisearch/pyllms
    - https://huggingface.co/liujch1998/vera might be handy, it did well at recognising yes/no questions when I tried it (it is a 4.7B param T5 model)
    - in practice it's probably more expensive to self-host one of those than just use OpenAI API
- UI:
  - Gradio was a quick way to get up and running but it'd be better to have stateless backend + custom frontend
    - so that games can be resumed e.g. in case of server error, or continued across a deployment
    - freedom in styling
