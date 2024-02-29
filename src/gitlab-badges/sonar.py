#!/usr/bin/env python3
from typing import Any
import os
import requests
import sys
from sonarqube import SonarQubeClient
from base64 import b64encode
from functools import lru_cache


def basic_auth(username: str, password: str) -> str:
    res = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {res}"


def bearer_auth(token: str) -> str:
    res = b64encode(token.encode("utf-8")).decode("ascii")
    return f"Bearer {res}"


@lru_cache
def plugin(**kwargs) -> dict[str, Any]:
    project = kwargs["project"]
    assert project
    url = os.environ["SONARQUBE_URL"]
    if url.endswith("/"):
        url = url[0:-1]

    params = {}
    headers = {}
    if "SONAR_TOKEN" in os.environ:
        params["token"] = os.environ["SONAR_TOKEN"]
        headers["Authorization"] = basic_auth(params["token"], "")
    else:
        params["username"] = os.environ["SONARQUBE_USERNAME"]
        params["password"] = os.environ["SONARQUBE_PASSWORD"]
        headers["Authorization"] = basic_auth(params["username"], params["password"])

    sonar = SonarQubeClient(sonarqube_url=url, **params)
    assert (
        sonar.auth.check_credentials()
    ), "Connection to sonar is not valid, check credentials"

    valid_con = requests.get(
        f"{url}/api/authentication/validate", headers=headers
    ).json()
    if not valid_con.get("valid", False):
        raise RuntimeError(f"Cannot authenticate to SonarQube: {valid_con}")

    res = requests.get(
        f"{url}/api/project_badges/token", params={"project": project}, headers=headers
    )
    if res.status_code != 200:
        print(
            f"[ERROR] Cannot get token for project={project}: {res.status_code}: {res}"
        )
        raise RuntimeError(f"Failed to get token for project {project}")
    full_result = {"token": res.json().get("token")}
    return full_result


if __name__ == "__main__":
    print(plugin(project=sys.argv[1]))
