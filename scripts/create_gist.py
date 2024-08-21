import argparse

from github import Github, InputFileContent
from pathlib import Path
from typing import Optional


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Create gist for a snippet")
    parser.add_argument(
        "--input",
        required=True,
        type=str,
        help="Path to input file that should be uploaded as a gist",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=str,
        help="Path to the outputfile that would contain the created gist url",
    )
    parser.add_argument(
        "--title",
        required=False,
        type=str,
        help="File name to be displayed in the uploaded gist",
    )
    parser.add_argument(
        "--token",
        required=True,
        type=str,
        help="Github access token",
    )
    return parser.parse_args()


def create_gist(input_file: str, token: str, title: Optional[str] = None) -> str:
    """
    Creates a private GitHub Gist from the contents of the specified input file.
    The URL of the created Gist is returned.

    Args:
        input_file (str): The path to the file whose content will be used to create the Gist.
        token (str): The GitHub personal access token used to authenticate the API request.

    Returns:
        str: The URL of the created Gist.

    Raises:
        RuntimeError: If the specified input file does not exist.

    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise RuntimeError(f"Input file {input_file} doesn't exist")

    input_contents = input_path.read_text(encoding="utf-8")
    input_file_title = title.replace(" ", "_") if title else input_file
    github = Github(token)
    auth_user = github.get_user()
    gist = auth_user.create_gist(
        public=False, files={input_file_title: InputFileContent(content=input_contents)}
    )
    return gist.html_url


def write_url(url: str, output_file: str):
    """Writes the provided URL to the specified output file."""
    output_path = Path(output_file)
    # Create possibly missing output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(url)


def main():
    args = parse_arguments()
    url = create_gist(args.input, args.token, args.title)
    write_url(url, args.output)


if __name__ == "__main__":
    main()
