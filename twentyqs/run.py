import argparse
import logging

from langchain import OpenAI

from twentyqs.game import Game


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo")
    parser.add_argument("--simple", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    llm = OpenAI(temperature=0, model_name=args.model)
    game = Game(llm=llm, simple_subject_picker=args.simple)
    game.play()
    