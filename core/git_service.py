import git
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GitService:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        try:
            self.repo = git.Repo(self.repo_path)
            logger.info(f"GitService initialized for repository: {self.repo_path}")
        except git.InvalidGitRepositoryError:
            logger.error(f"Invalid Git repository at {self.repo_path}")
            self.repo = None
        except git.NoSuchPathError:
            logger.error(f"Path {self.repo_path} does not exist")
            self.repo = None

    def get_status(self) -> Optional[str]:
        if not self.repo:
            return None
        return self.repo.git.status()

    def get_diff(self, cached: bool = False) -> Optional[str]:
        if not self.repo:
            return None
        return self.repo.git.diff(cached=cached)

    def get_log(self, count: int = 10) -> Optional[List[Dict[str, str]]]:
        if not self.repo:
            return None
        logs = []
        for commit in self.repo.iter_commits(max_count=count):
            logs.append({
                "sha": commit.hexsha,
                "author": commit.author.name,
                "date": commit.authored_datetime.isoformat(),
                "message": commit.message.strip(),
            })
        return logs

    def add(self, paths: List[str]) -> bool:
        if not self.repo:
            return False
        try:
            self.repo.git.add(paths)
            logger.info(f"Added {paths} to the index")
            return True
        except git.GitCommandError as e:
            logger.error(f"Error adding {paths} to the index: {e}")
            return False

    def commit(self, message: str) -> bool:
        if not self.repo:
            return False
        try:
            self.repo.git.commit("-m", message)
            logger.info(f"Committed with message: {message}")
            return True
        except git.GitCommandError as e:
            logger.error(f"Error committing: {e}")
            return False
