import dotenv
dotenv.load_dotenv()

import argparse
import os
from tools.folder_ingestion_tool import FolderIngestionTool

print(f"DEBUG: GITHUB_TOKEN from .env: {os.getenv('GITHUB_TOKEN')}")

def main():
    parser = argparse.ArgumentParser(description="Ingest documents from a folder into the knowledge base.")
    parser.add_argument("--path", type=str, required=True, help="Path to the folder containing documents to ingest.")
    args = parser.parse_args()

    folder_path = args.path
    ingestion_tool = FolderIngestionTool()
    result = ingestion_tool._run(folder_path)
    print(result)

if __name__ == "__main__":
    main()
