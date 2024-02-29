# gitlab-badges

A simple project to put badges on all of your gitlab projects with easy to write plugins to add support for 3rd party applications.

In its first version, it supports detection of sonar token, so you can automate create of Sonar Badges.

For now, support for SonarQube is provided, but adding support for other 3rd party apps is easy.

## Usage:

By default, it relies on environment variables to detect gitlab and Sonar:

* `export GITLAB_HOST=name.of.your.gitlab.server`
* `export GITLAB_TOKEN=<personal_token>`
* `export SONARQUBE_URL=<url_of_sonar>`
* `SONARQUBE_TOKEN=<token_to_read_sonar>`

### Help

```
usage: main.py [-h] [--gitlab-token GITLAB_TOKEN] [--token-type TOKEN_TYPE] [--token-value TOKEN_VALUE] [--server-url SERVER_URL]
               [--add {confirm,skip,perform}] [--delete {confirm,skip,perform}] [--modify {confirm,skip,perform}] [--show-badges-summary]
               [--badges-summary-format BADGES_SUMMARY_FORMAT] [--yaml-file YAML_FILE]
               ...

Synchronize badges for a repository

positional arguments:
  project_ids           All the projects IDs to run the command on

options:
  -h, --help            show this help message and exit
  --gitlab-token GITLAB_TOKEN
                        token to idenfy with gitlab
  --token-type TOKEN_TYPE
                        Token type: private_token (default) or job_token
  --token-value TOKEN_VALUE
                        Token value (can be autodected: CI_JOB_TOKEN, GITLAB_TOKEN, GITLAB_PRIVATE_TOKEN)
  --server-url SERVER_URL
                        Gitlab server URL
  --add {confirm,skip,perform}
                        What to do with badges to add?
  --delete {confirm,skip,perform}
                        What to do with badges to delete?
  --modify {confirm,skip,perform}
                        What to do with badges to modify?
  --show-badges-summary
                        Show badges summary with format specified by badges-summary-format
  --badges-summary-format BADGES_SUMMARY_FORMAT
                        if --show-badges-summary is set, display badges with fancy formatting, default is markdown compatible:
                        [![{badge.name}]({badge.image_url})]({badge.link_url})
  --yaml-file YAML_FILE
                        template to select the badge to set
```

### Run it to see existing badges on several projects

Will display information about badges with project IDs 146, 150, 188 and a markdown you can directly put in a README.md file. If you don't want the markdown, use 

```
./src/gitlab-badges/main.py 146 150 188
```

### Modify badges for those projects

```
./src/gitlab-badges/main.py --yaml-file badges.yml 146 150 188
```

Same, but automatically apply modifications/adding values, skip deletions if needed:

```
./src/gitlab-badges/main.py --add perform --modify perform --delete skip --yaml-file badges.yml 146 150 188
```


## Context

Gitlab let you use [badges](https://docs.gitlab.com/ee/user/project/badges.html) for repository and limited ways of re-use of badges accross projects with groups.

If offers some form of customization, but, limited to a few variables.

What if you want to apply the same badges to many projects, but those projects have different parameters for badges?

You are stuck or you spend 20 days configuring your badges manually.

This projects aims at injecting badges in all of your projects and being able to do it at scale, but 100s of projects.
