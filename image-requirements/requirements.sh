#!/bin/bash

echo -e "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile=/dev/null\n" >> ${HOME}/ssh_config

export GIT_SSL_NO_VERIFY=true
