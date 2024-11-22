#! /usr/bin/env python

"""
This class is used as webhook implementation.
There are many ways to optimize the code, but as a showcase, a linear run-through is better for understanding.
(people will understand scripts, but not all of them will understand OOP)
"""

import flask
import logging
import os
import re
import requests
import urllib.parse

app = flask.Flask(__name__)

# log configuration, please use DEBUG for maintenance
logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                    # level=logging.INFO,
                    level=logging.DEBUG,
                    datefmt='%Y-%m-%d %H:%M:%S')

# ENV variables
gitlab_api_token = os.getenv('GITLAB_TOKEN')
thread_message = os.getenv('THREAD_MESSAGE', '#USER# added a patchset #LINK2COMMIT# related to this thread')
new_thread_message = os.getenv('NEW_THREAD_MESSAGE', '#USER# added a patchset #LINK2COMMIT# related to no thread')


@app.route('/hook', methods=['POST'])
def hook():
    """Gitlab webhook to react on events

    Returns:
        flask.Response: {'spl-gitlab-webhook':'ok'}
    """
    data = flask.request.get_json()
    logging.debug(data)

    # validate object kind
    object_kind = data.get('object_kind', 'unknown')
    if object_kind == 'unknown':
        logging.warning('SKIPPED:')
        logging.warning(data)
        return flask.Response("{'spl-gitlab-webhook':'skipped'}", status=200, mimetype='application/json')

    # extract information
    project_id = str(data['project']['id'])
    project_name = data['project']['name']
    user = data['user_username']
    web_url = data['project']['web_url']
    ref = data['ref']
    branch_name = ref.rsplit('/', 1)[-1]
    path_with_namespace = data['project']['path_with_namespace']
    gitlab_url = web_url.replace(path_with_namespace, '')

    logging.info(user + ' pushed to ' + project_name + ' (' + project_id + ')')

    # handle pushes
    # as we just want to handle commit messages, 'push' is fine for our use case
    if object_kind == 'push':
        commits = data['commits']
        for commit in commits:
            commitid = commit['id']
            message = commit['message']
            logging.debug('commitid: ' + commitid)

            # patterns to search
            merge_request_url_pattern = re.escape(gitlab_url) + r'[a-zA-Z0-9-_/]*/merge_requests/[0-9]*#note_[0-9]*'
            mention_pattern = r'@[a-zA-Z0-9]*'

            # find thread-related URLs and mentioned users
            note_urls = []
            mentions = []
            for line in message.splitlines():
                note_urls += re.findall(merge_request_url_pattern, line)
                mentions += re.findall(mention_pattern, line)

            # read assigned merge requests to branch (should be one)
            # /api/v4/projects/PROJECTID/merge_requests?state=opened&source_branch=BRANCHNAME
            api_url = gitlab_url + 'api/v4/projects/' + project_id
            api_url += '/merge_requests?state=opened&source_branch=' + branch_name
            response = requests.get(api_url, headers={"PRIVATE-TOKEN": gitlab_api_token})
            branch_merge_requests = response.json()
            merge_request_ids_to_check = []
            for branch_merge_request in branch_merge_requests:
                merge_request_ids_to_check.append(str(branch_merge_request['id']))

            # validate merge requests thread-related URLs
            for merge_request_id in merge_request_ids_to_check:
                found = 0
                for not_url in note_urls:
                    # need to find /merge_requests/MERGEREQUESTID#note_
                    if '/merge_requests/' + merge_request_id + '#note_' in not_url:
                        found = 1

                # in case there is no thread note requested for this merge request,
                # we are going to create a new top level one thats needs to be reviewed
                if found == 0:
                    diff_link = build_diff_link(web_url, merge_request_id, commitid)
                    create_new_thread(user, diff_link, merge_request_id, mentions, gitlab_url, project_id)

            # add thread note for all committed note URLs
            for note_url in note_urls:
                # parse URL to get the required information (might have groups)
                # http://gitlab.INTERNAL:8080/project1/-/merge_requests/123#note_54321
                # http://gitlab.INTERNAL:8080/group1/groupX/.../project1/-/merge_requests/123#note_54321

                note_url_short = note_url.replace(gitlab_url, '')
                note_url_split = note_url_short.split('/-/')
                logging.debug(note_url_split)
                note_group_name = note_url_split[0]
                logging.debug('note_group_name: ' + note_group_name)

                # note_repo_name, note_merge_request_id and note_id read from the end of the url
                note_url_split = note_url_short.rsplit('/')
                logging.debug(note_url_split)
                note_repo_name = note_url_split[-4]
                logging.debug('note_repo_name: ' + note_repo_name)
                note_merge_request_id = note_url_split[-1].split('#')[0]
                logging.debug('note_merge_request_id: ' + note_merge_request_id)
                note_id = note_url_split[-1].split('#')[1].split('_')[1]
                logging.debug('note_id: ' + note_id)

                # get project_id from repo_name (alternative: read from note id, should be available)
                # /api/v4/projects?search=test
                api_url = gitlab_url + 'api/v4/projects?search=' + note_repo_name
                response = requests.get(api_url, headers={"PRIVATE-TOKEN": gitlab_api_token})
                found_repos = response.json()
                note_project_id = ''
                logging.debug('found_repos: ' + str(len(found_repos)))
                for found_repo in found_repos:
                    path_with_namespace = found_repo['path_with_namespace']

                    # there could be projects with same name, we need to check the path, too
                    if path_with_namespace in note_group_name:
                        note_project_id = str(found_repo['id'])
                        break

                # add comment to found project
                if len(note_project_id) > 0:

                    # we need to get the discussion_id for the note_id
                    # /api/v4/projects/PROJECTID/merge_requests/MERGEREQUESTID/discussions
                    api_url = gitlab_url + 'api/v4/projects/' + note_project_id
                    api_url += '/merge_requests/' + note_merge_request_id + '/discussions'
                    response = requests.get(api_url, headers={"PRIVATE-TOKEN": gitlab_api_token})
                    note_discussions = response.json()
                    discussion_id = ''
                    for note_discussion in note_discussions:
                        found_discussion_id = False
                        for note in note_discussion['notes']:
                            if note_id in str(note['id']):
                                discussion_id = note_discussion['id']
                                found_discussion_id = True
                                break
                        if found_discussion_id:
                            break

                    # now we have everything to add a comment to discussion
                    if len(discussion_id) > 0:
                        diff_link = build_diff_link(web_url, note_merge_request_id, commitid)
                        extend_thread(user, diff_link, note_merge_request_id, mentions, gitlab_url, note_project_id,
                                      discussion_id)
                    else:
                        logging.warning('no discussion found for note: ' + note_id)
                else:
                    logging.warning('no project found for: ' + note_repo_name)

    # here you can handle other types of object_kinds next to pushes

    return flask.Response("{'spl-gitlab-webhook':'ok'}", status=200, mimetype='application/json')


def extend_thread(user, diff_link, merge_request_id, mentions, gitlab_url, project_id, discussion_id):
    """extend a thread in merge request

    Args:
        user (str): user name
        diff_link (str): diff URL
        merge_request_id (str): ID of the merge request
        mentions (str[]): all mentioned users
        gitlab_url (str): Gitlab instance URL
        project_id (str): ID of the project
        discussion_id (str): ID of the discussion / thread
    """

    # create the message
    result_message = build_thread_message(thread_message, user, diff_link, mentions)

    # create and send post url
    api_url = gitlab_url + 'api/v4/projects/' + project_id + '/merge_requests/' + merge_request_id
    api_url += '/discussions/' + discussion_id + '/notes?body=' + urllib.parse.quote(result_message)
    response = requests.post(api_url, headers={"PRIVATE-TOKEN": gitlab_api_token})
    logging.info(response.json())


def create_new_thread(user, diff_link, merge_request_id, mentions, gitlab_url, project_id):
    """creates a new thread in merge request

    Args:
        user (str): user name
        diff_link (str): diff URL
        merge_request_id (str): ID of the merge request
        mentions (str[]): all mentioned users
        gitlab_url (str): Gitlab instance URL
        project_id (str): ID of the project
    """

    # create the message
    result_message = build_thread_message(new_thread_message, user, diff_link, mentions)

    # create and send post url
    api_url = gitlab_url + 'api/v4/projects/' + project_id + '/merge_requests/' + merge_request_id
    api_url += '/discussions?body=' + urllib.parse.quote(result_message)
    response = requests.post(api_url, headers={"PRIVATE-TOKEN": gitlab_api_token})
    logging.info(response.json())


def build_thread_message(input_message, user, diff_link, mentions) -> str:
    """builds the message to be added to merge request

    Args:
        input_message (str): comment_message or new_comment_message
        user (str): user name
        diff_link (str): diff URL
        mentions (str[]): all mentioned users

    Returns:
        str: the created message
    """

    result_message = input_message.replace('#USER#', user)
    result_message = result_message.replace('#LINK2COMMIT#', diff_link)

    # add user mentions
    for mention in mentions:
        result_message += ' ' + mention

    return result_message


def build_diff_link(web_url, merge_request_id, commitid) -> str:
    """creates the diff url for thread comment

    Args:
        web_url (str): web URL of the project in Gitlab
        merge_request_id (str): ID of the merge request
        commitid (str): ID of the commit

    Returns:
        str: the diff URL
    """

    # create diff link to commit
    return web_url + '/-/merge_requests/' + merge_request_id + '/diffs?commit_id=' + commitid


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
