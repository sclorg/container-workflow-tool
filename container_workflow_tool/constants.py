action_map = {}
action_map['git'] = {
    'pullupstream': 'dist_git_changes',
    'clonedownstream': 'pull_downstream',
    'cloneupstream': 'pull_upstream',
    'rebase': 'dist_git_rebase',
    'merge': 'merge_future_branches',
    'show': 'show_git_changes',
    'push': 'push_changes',
}


action_map['koji'] = {
    'latestbuilds': 'print_brew_builds',
}

action_map['utils'] = {
    'showconfig': 'show_config_contents',
    'listimages': 'list_images',
    'listupstream': 'print_upstream',
}
action_map['koji']['latestbase'] = 'print_latest_base'
action_map['koji']['hashids'] = 'print_hash_ids'
action_map['git']['diff'] = 'check_downstream_diffs'
action_map['utils']['setuprepo'] = 'setup_repo_file'
action_map['utils']['notifymail'] = 'print_email_notification'

actions = {}
actions['git'] = ['pullupstream', 'clonedownstream', 'cloneupstream',
                  'rebase', 'merge', 'show', 'push', ]
actions['koji'] = ['latestbuilds', ]
actions['utils'] = ['showconfig', 'listimages', 'listupstream', ]

COMMAND = ""
