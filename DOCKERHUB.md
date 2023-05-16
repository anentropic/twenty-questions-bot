# twenty-questions-bot

Langchain chatbot that plays the "20 Questions" game

## Usage

```sh
docker run \
  -e ADMIN_PASSWORD=****** \
  -e OPENAI_API_KEY=****** \
  anentropic/twenty-questions-bot
```

This will start the web server, open the url it gives you in a web browser.

The game is password protected to avoid the general public burning through your OpenAI credits (it costs ~US$0.04 per game currently).

Server is initalised with an `admin` user, with your password. You can use this to play the game, or go to `http://127.0.0.1:8000/admin/` and login, you can then create non-admin user accounts that can be used to play the game.

History is stored per-username. If you use a new username (or a fresh db file) you will likely see the same subjects again (we're still picking from a random pool, but LLM tends to generate the same ones every time).
