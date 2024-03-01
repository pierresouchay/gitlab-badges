#!/usr/bin/env python3
import argparse
import os
import gitlab
from gitlab.v4.objects.badges import ProjectBadge
from gitlab.v4.objects.projects import Project
from gitlab.exceptions import GitlabOperationError
import yaml
from yaml.scanner import ScannerError
from typing import Any, Union, cast
from .sonar import plugin as sonar_plugin
from jinja2 import Template


def get_default_server_url() -> str:
    server_url = "https://gitlab.com"
    if "CI_SERVER_URL" in os.environ:
        server_url = os.environ["CI_SERVER_URL"]
    elif "GITLAB_HOST" in os.environ:
        server_url = f"https://{os.environ['GITLAB_HOST']}"
    return server_url


def evaluate_yaml(yaml_file: str, scope: dict[str, Any]) -> dict[str, Any]:
    with open(yaml_file, "rt", encoding="UTF-8") as f:
        tpl = Template(f.read())
    result = tpl.render(**scope)
    try:
        yaml_content = yaml.safe_load(result)
        assert isinstance(yaml_content, dict)
        return yaml_content
    except ScannerError as err:
        msg = f"{err} while reading rendered YAML file from {yaml_file}"
        print("[ERROR]", msg, "\nContent:\n", result)
        raise RuntimeError(msg) from err


def should_perform_operation(res: Any, operation: str) -> bool:
    op = getattr(res, operation)
    if op == "confirm":
        for i in range(2):
            print("Perform operation ? (Y/N)", end=": ", flush=True)
            c = input()
            if c.lower() in ["y", "yes"]:
                return True
            if c.lower() in ["n", "no", "cancel", "skip"]:
                return False
            print("Option not recognized, select yes or no")
        print(" => Assuming we don't do the operation")
        return False
    if op == "perform":
        return True
    return False


def refresh_badges(project: Project) -> dict[str, ProjectBadge]:
    badges_found: dict[str, ProjectBadge] = {}
    for badge in project.badges.list(all=True):
        if badge.kind == "project":
            # We don't deal with group badges
            badges_found[badge.name] = cast(ProjectBadge, badge)
    return badges_found


def perform_operation(
    project: Project, operation: str, badge: Union[ProjectBadge, dict[str, Any]]
) -> None:
    try:
        if operation == "add":
            assert isinstance(badge, dict)
            project.badges.create(badge)
        elif operation == "modify":
            assert isinstance(badge, dict)
            project.badges.update(badge["id"], badge)
        elif operation == "delete":
            assert isinstance(badge, ProjectBadge)
            project.badges.delete(badge.id)
        else:
            assert False, f"Unexpected operation={operation}"
    except GitlabOperationError as err:
        print(
            f"[ERROR] performing {operation} on {project.get_id()} with payload {badge}: {err}"
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize badges for a repository")

    parser.add_argument(
        "--gitlab-token",
        dest="gitlab_token",
        action="store",
        default=os.getenv("GITLAB_TOKEN"),
        help="token to idenfy with gitlab",
    )
    parser.add_argument(
        "--token-type",
        dest="token_type",
        action="store",
        default="private_token",
        help="Token type: private_token (default) or job_token",
    )
    parser.add_argument(
        "--token-value",
        dest="token_value",
        action="store",
        help="Token value (can be autodected: CI_JOB_TOKEN, GITLAB_TOKEN, GITLAB_PRIVATE_TOKEN)",
    )
    parser.add_argument(
        "--server-url",
        dest="server_url",
        action="store",
        default=get_default_server_url(),
        help="Gitlab server URL",
    )
    parser.add_argument(
        "--add",
        dest="add",
        choices=["confirm", "skip", "perform"],
        default="confirm",
        help="What to do with badges to add?",
    )
    parser.add_argument(
        "--delete",
        dest="delete",
        choices=["confirm", "skip", "perform"],
        default="confirm",
        help="What to do with badges to delete?",
    )
    parser.add_argument(
        "--modify",
        dest="modify",
        choices=["confirm", "skip", "perform"],
        default="confirm",
        help="What to do with badges to modify?",
    )
    parser.add_argument(
        "--show-badges-summary",
        action="store_true",
        default=False,
        help="Show badges summary with format specified by badges-summary-format",
    )
    DEFAULT_BADGE_SUMMARY = "[![{badge.name}]({badge.image_url})]({badge.link_url})"
    parser.add_argument(
        "--badges-summary-format",
        dest="badges_summary_format",
        default=DEFAULT_BADGE_SUMMARY,
        help=f"if --show-badges-summary is set, display badges with fancy formatting, default is markdown compatible: {DEFAULT_BADGE_SUMMARY}",
    )
    parser.add_argument(
        "--yaml-file", dest="yaml_file", help="template to select the badge to set"
    )
    parser.add_argument(
        "project_ids",
        help="All the projects IDs to run the command on",
        nargs=argparse.REMAINDER,
    )

    res = parser.parse_args()

    if not res.token_value:
        res.token_type = "private_token"
        if "GITLAB_PRIVATE_TOKEN" in os.environ:
            res.token_value = os.environ["GITLAB_PRIVATE_TOKEN"]
        elif "GITLAB_TOKEN" in os.environ:
            res.token_value = os.environ["GITLAB_TOKEN"]
        else:
            res.token_type = "job_token"
            res.token_value = os.getenv("CI_JOB_TOKEN")
        if not res.token_value:
            raise RuntimeError("Could not detect GITLAB token")

    args = {res.token_type: res.token_value}
    gl = gitlab.Gitlab(url=res.server_url, **args)  # type: ignore[arg-type,unused-ignore]  # noqa: arg-type

    gl.auth()
    for project_id in res.project_ids:
        project = gl.projects.get(project_id)
        badges_modified = False
        badges_found = refresh_badges(project=project)

        if badges_found:
            print(project)
            print(f"[INFO]{project.name}[{project.id}] {project.web_url}")
            print(
                f"[INFO]{project.name}[{project.id}] Found {len(badges_found)} badges:",
                ", ".join(badges_found.keys()),
            )
        else:
            print(f"[INFO]{project.name}[{project.id}] No existing badges found")

        if res.yaml_file:
            scope = {
                "getenv": os.getenv,
                "gitlab_url": res.server_url,
                "environ": os.environ,
                "project": project,
                "sonar_token": sonar_plugin,
            }
            operations: dict[str, list[Union[dict[str, str], ProjectBadge]]] = {
                "add": [],
                "modify": [],
                "delete": [],
            }
            badges_dict = evaluate_yaml(res.yaml_file, scope).get("badges", [])
            existing_badges = dict(badges_found)
            for badge_name, badge_params in badges_dict.items():
                if not badge_params.get("active", True):
                    continue
                badge_info = badge_params | {"name": badge_name}
                existing = existing_badges.pop(badge_name, None)
                if existing is None:
                    operations["add"].append(badge_info)
                else:
                    if (
                        existing.image_url != badge_params["image_url"]
                        or existing.link_url != badge_params["link_url"]
                    ):
                        operations["modify"].append(badge_info | {"id": existing.id})
            for badge in existing_badges.values():
                operations["delete"].append(badge)
            for operation, badges in operations.items():
                if badges:
                    badge_names = "\n - ".join(
                        map(
                            lambda a: str(a.get("name"))
                            if isinstance(a, dict)
                            else f"{a.name} [{a.id}]",
                            badges,
                        )
                    )
                    print(
                        f"About to {operation} the {len(badges)} following badge(s):\n - {badge_names}"
                    )
                    if should_perform_operation(res, operation):
                        for dict_or_badge in badges:
                            perform_operation(
                                project=project,
                                operation=operation,
                                badge=dict_or_badge,
                            )
                            badges_modified = True
        if badges_modified:
            badges_found = refresh_badges(project=project)
        if res.badges_summary_format and badges_found:
            print(
                f"[INFO]{project.name}[{project.id}] summary with format --badges-summary-format={res.badges_summary_format}"
            )
            for badge in badges_found.values():
                print(res.badges_summary_format.format_map({"badge": badge}))


if __name__ == "__main__":
    main()
