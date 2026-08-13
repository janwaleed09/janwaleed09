"""Rewrites the "Recently merged pull requests" section of README.md.

Lists pull requests by USER that were merged into repositories owned by
someone else, newest first. PRs that maintainers took over by cherry-pick
(closed, not merged on GitHub) are listed in extra-prs.json.
"""
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

USER = "janwaleed09"
LIMIT = 15  # show everything for now; lower it once the list gets long

HEADERS = {
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def escape(title):
    # Square brackets would break the Markdown link text.
    return title.replace("[", "\\[").replace("]", "\\]")


def collect():
    items = {}
    query = urllib.parse.quote(f"is:pr is:merged author:{USER} -user:{USER}")
    for it in get(f"https://api.github.com/search/issues?q={query}&per_page=100")["items"]:
        repo = it["repository_url"].split("/repos/")[1]
        items[it["html_url"]] = (it["pull_request"]["merged_at"], repo, it["title"], it["html_url"], "")

    extra = pathlib.Path("extra-prs.json")
    for ref in json.loads(extra.read_text()) if extra.exists() else []:
        repo, number = ref.split("#")
        pr = get(f"https://api.github.com/repos/{repo}/pulls/{number}")
        items[pr["html_url"]] = (pr["closed_at"], repo, pr["title"], pr["html_url"], " (merged via cherry-pick)")

    return sorted(items.values(), reverse=True)[:LIMIT]


def render(items):
    return "\n".join(
        f"- **{repo}**: [{escape(title)}]({url}){note} · {date[:10]}"
        for date, repo, title, url, note in items
    )


def main():
    readme = pathlib.Path("README.md")
    block = render(collect())
    updated = re.sub(
        r"<!-- recent_prs starts -->.*<!-- recent_prs ends -->",
        lambda _: f"<!-- recent_prs starts -->\n{block}\n<!-- recent_prs ends -->",
        readme.read_text(),
        flags=re.DOTALL,
    )
    readme.write_text(updated)


if __name__ == "__main__":
    main()
