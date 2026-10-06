"""Source providers used by the updater.

Providers keep network/source-specific fetching separate from app-building logic.
""" 

class GitHubProvider:
    def __init__(self, session):
        self.session = session

    def latest_release(self, repo):
        response = self.session.get(
            f"https://api.github.com/repos/{repo}/releases/latest",
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def releases(self, repo, per_page=30):
        response = self.session.get(
            f"https://api.github.com/repos/{repo}/releases?per_page={per_page}",
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


class JsonSourceProvider:
    def __init__(self, fetch_json):
        self.fetch_json = fetch_json

    def fetch(self, url):
        return self.fetch_json(url)
