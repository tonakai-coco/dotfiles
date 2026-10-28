"""GitHub HTTP boundary fixture for offline integration tests."""
import copy
from client import ApiError
from fixtures import pr


class FakeGitHub:
    def __init__(self):
        self.pr = pr()
        self.reviews = []
        self.comments = {}
        self.issue_comments = []
        self.calls = []
        self.fail_create = False
        self.fail_delete = False

    def pages(self, path):
        if path.endswith("/files"):
            return [{"filename": "a.py", "patch": "@@ -1,2 +1,2 @@\n def calculate(x):\n-old\n+new\n"}]
        if "/issues/" in path and "comments" in path:
            return copy.deepcopy(self.issue_comments)
        if path.endswith("/reviews"):
            return copy.deepcopy(self.reviews)
        return copy.deepcopy(self.comments.get(int(path.split("/")[-2]), []))

    def call(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET":
            return self.pr
        if method == "POST" and "/issues/" in path and path.rstrip("/").endswith("/comments"):
            row = {"id": len(self.issue_comments) + 1, "user": {"login": "github-actions[bot]"},
                   "body": payload["body"], "html_url": f"https://example.test/issue/{len(self.issue_comments) + 1}"}
            self.issue_comments.append(row)
            return row
        if method == "PATCH" and "/issues/comments/" in path:
            cid = int(path.rstrip("/").split("/")[-1])
            for comment in self.issue_comments:
                if comment["id"] == cid:
                    comment["body"] = payload["body"]
                    return comment
            return None
        if method == "POST":
            if self.fail_create:
                raise ApiError(422)
            rid = len(self.reviews) + 1
            row = {"id": rid, "user": {"login": "github-actions[bot]"},
                   "state": "COMMENTED", "body": payload["body"],
                   "commit_id": payload["commit_id"], "html_url": f"https://example.test/{rid}"}
            self.reviews.append(row)
            self.comments[rid] = [dict(c, id=rid * 100 + i, user=row["user"])
                                  for i, c in enumerate(payload["comments"])]
            return row
        if method == "PUT":
            rid = int(path.split("/")[-1])
            self.reviews[rid - 1]["body"] = payload["body"]
        if method == "PATCH":
            cid = int(path.split("/")[-1])
            for comments in self.comments.values():
                for comment in comments:
                    if comment["id"] == cid:
                        comment["body"] = payload["body"]
        if method == "DELETE":
            if self.fail_delete:
                raise ApiError(403)
            cid = int(path.split("/")[-1])
            for rid in self.comments:
                self.comments[rid] = [c for c in self.comments[rid] if c["id"] != cid]
