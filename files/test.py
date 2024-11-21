#! /usr/bin/env python

"""
this class is only used as helper for local development - I'm too lazy to rewrite this every time...
"""

import re

gitlab_url = 'http://gitlab.INTERNAL:8080/'


def main():
    print('manual parsing test')

    ref = "refs/heads/master"
    branch_name = ref.rsplit('/', 1)[-1]
    print(branch_name)

    # typical messages to test
    message = 'bla bla bla \n  PATCHSET \n\n  http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321\n  http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321\nbla bla @cooluser bla'  # noqa: E501
    # message = 'http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321' # noqa: E501
    # message = 'http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321 http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321' # noqa: E501
    # message = 'http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321 @cooluser' # noqa: E501
    # message = '@cooluser http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321' # noqa: E501
    # message = 'http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321,http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321,@cooluser' # noqa: E501
    # print(message)

    # patterns to test
    mr_url_pattern = re.escape(gitlab_url) + r'[a-zA-Z0-9-_/]*/merge_requests/[0-9]*#note_[0-9]*'
    mention_pattern = r'@[a-zA-Z]*'

    note_urls = []
    mentions = []

    linenumber = 0
    for line in message.splitlines():
        linenumber += 1
        print(str(linenumber) + ': ' + line)
        note_urls += re.findall(mr_url_pattern, line)
        mentions += re.findall(mention_pattern, line)

    print('URLs found:\n' + str(note_urls))
    print('mentions found:\n' + str(mentions))

    for note_url in note_urls:
        # http://gitlab.INTERNAL:8080/group1/project1/-/merge_requests/123#note_54321

        note_url_short = note_url.replace(gitlab_url, '')
        note_url_split = note_url_short.split('-')
        print(note_url_split)
        note_group_name = note_url_split[0][:-1]
        print('note_group_name: ' + note_group_name)

        # note_repo_name, note_merge_request_id and note_id read from the end of the url
        note_url_split = note_url_short.rsplit('/')
        print(note_url_split)
        note_repo_name = note_url_split[-4]
        print('note_repo_name: ' + note_repo_name)
        note_merge_request_id = note_url_split[-1].split('#')[0]
        print('note_merge_request_id: ' + note_merge_request_id)
        discussion_id = note_url_split[-1].split('#')[1].split('_')[1]
        print('discussion_id: ' + discussion_id)


if __name__ == "__main__":
    main()
