# gitlab-merge-requests-webhook

add automatic merge request thread information using a git commit message

## features

**requirements:**

use merge request thread/discussion URLs like 'http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321' in git commit message
(can be copied from GUI, available when hovering over the age of a comment within a discussion)

use '@cooluser' mentions in git commit messages

**output**:

* will create a automatic thread/discussion comments like '#USER# added a patchset #LINK2COMMIT# related to this thread' (can be changed by ENV variable, multiple threads are supported)
* will create a new top-level thread/discussion if commit is pushed to branch with existing merge request, but without note URL in it (this is new code and needs to be reviewed, so a new thread will enforce this)
* will add all user mentions to the thread/discussion comment, so they will get informed about it

## functional background

We migrated our repositories from Gerrit and tried to achieve a similar usability and notification for updated merge requests, that's why we use the word 'patchset'. But the function is of course not related to Gerrit and also helps for all kinds of review processes in Gitlab.

## usage

#### 1. deploy webhook adding a github token to be used with Gitlab API (see packages on the right side)

```
docker run -e PORT=8080 -e GITLAB_TOKEN=1234567890 ghcr.io/spleenlab-visionairy/gitlab-merge-requests-webhook:latest
```

or

```
docker run -e PORT=8080 -e GITLAB_TOKEN=1234567890 -e THREAD_MESSAGE="#USER# added a patchset #LINK2COMMIT# related to this thread" -e NEW_THREAD_MESSAGE="#USER# added a patchset #LINK2COMMIT# related to no thread" ghcr.io/spleenlab-visionairy/gitlab-merge-requests-webhook:latest
```

#### 2. configure in Gitlab

Admin --> System hooks --> URL: http://hostname:8080/hook --> Execute for "Push events"

This is only for testing purpose - feel free to configure the hook on project level instead of using the global config.

## remarks

This repository is to be understood as an example, for productive operation the image should be hardened and Flask should be executed in productive mode. In addition, the use of system hooks has a global effect. A more fine-grained configuration is recommended.
