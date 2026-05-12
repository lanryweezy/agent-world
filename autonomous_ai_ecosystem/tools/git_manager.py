import subprocess
import os
from ..core.logger import Logger

class GitManager:
    """A class to manage Git repositories using subprocess."""

    def __init__(self, base_dir):
        """Initialize the GitManager with a base directory for clones."""
        self.base_dir = base_dir
        self.logger = Logger(self.__class__.__name__)
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def _run_command(self, command, cwd):
        """Run a shell command and return its output."""
        try:
            self.logger.info(f"Running command: {' '.join(command)} in {cwd}")
            result = subprocess.run(
                command, 
                cwd=cwd, 
                check=True, 
                text=True, 
                capture_output=True
            )
            self.logger.info(f"Command successful: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e.stderr}")
            raise

    def clone(self, repo_url, repo_name):
        """Clone a repository into the base directory."""
        repo_path = os.path.join(self.base_dir, repo_name)
        if os.path.exists(repo_path):
            self.logger.warning(f"Repository already exists at {repo_path}. Skipping clone.")
            return repo_path
        
        command = ["git", "clone", repo_url, repo_path]
        self._run_command(command, cwd=self.base_dir)
        return repo_path

    def pull(self, repo_path):
        """Pull the latest changes for a repository."""
        command = ["git", "pull"]
        self._run_command(command, cwd=repo_path)

    def commit(self, repo_path, message):
        """Commit changes in a repository."""
        # Stage all changes
        add_command = ["git", "add", "."]
        self._run_command(add_command, cwd=repo_path)

        # Commit
        commit_command = ["git", "commit", "-m", message]
        self._run_command(commit_command, cwd=repo_path)

    def push(self, repo_path, remote="origin", branch="main"):
        """Push changes to a remote repository."""
        command = ["git", "push", remote, branch]
        self._run_command(command, cwd=repo_path)

    def create_branch(self, repo_path, branch_name):
        """Create and switch to a new branch."""
        command = ["git", "checkout", "-b", branch_name]
        self._run_command(command, cwd=repo_path)
