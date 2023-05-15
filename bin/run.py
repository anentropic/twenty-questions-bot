#!/usr/bin/env python3
import argparse
import logging

from twentyqs.runner import run


"""
IMPORTANT:
Beware of https://gradio.app/sharing-your-app/#security-and-file-access
> Gradio apps grant users access to three kinds of files:
> - Files in the same folder (or a subdirectory) of where the Gradio script is launched from. 
"""

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", type=str)
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo")
    parser.add_argument("--simple-subject-picker", action="store_true")
    parser.add_argument("--verbose-langchain", action="store_true")
    parser.add_argument("--db-path", type=str, default="twentyqs.db")
    parser.add_argument("--clear-db", action="store_true")
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    run(
        username=args.username,
        openai_model=args.model,
        db_path=args.db_path,
        clear_db=args.clear_db,
        simple_subject_picker=args.simple_subject_picker,
        verbose_langchain=args.verbose_langchain,
        log_level=args.log_level,
    )
