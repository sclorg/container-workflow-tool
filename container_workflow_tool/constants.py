action_map = {}
action_map["git"] = {
    "pullupstream": "dist_git_merge_changes",
    "clonedownstream": "pull_downstream",
    "cloneupstream": "pull_upstream",
    "rebase": "dist_git_rebase",
    "merge": "merge_future_branches",
    "show": "show_git_changes",
    "push": "push_changes",
    "diff": "check_downstream_diffs",
}

action_map["utils"] = {
    "showconfig": "show_config_contents",
    "listimages": "list_images",
    "listupstream": "print_upstream",
    "setuprepo": "setup_repo_file",
    "notifymail": "print_email_notification",
}

actions = {}
actions["git"] = [
    "pullupstream",
    "clonedownstream",
    "cloneupstream",
    "rebase",
    "merge",
    "show",
    "push",
]

actions["utils"] = [
    "showconfig",
    "listimages",
    "listupstream",
]

COMMAND = ""
