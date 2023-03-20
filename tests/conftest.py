# MIT License
#
# Copyright (c) 2020 SCL team at Red Hat
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest
import json

import tempfile


from tests.spellbook import DATA_DIR


@pytest.fixture()
def brewapi_get_nvrs():
    return [
        ("s2i-core-0-51.container", "s2i-core", "s2i-core"),
        (None, "httpd", "httpd"),
        (None, "mariadb", "mariadb"), (None, "nginx", "nginx"),
        ("s2i-base-1-63.container", "s2i-base", "s2i-base"),
        (None, "nodejs", "nodejs"), (None, "perl", "perl"),
        (None, "php", "php"), ("python3-0-31.container", "python3", "python3")
    ]


@pytest.fixture()
def brewapi_get_buildinfo_s2i_base():
    return json.loads((DATA_DIR / "brewapi_get_buildinfo_s2i_base.json").read_text())


@pytest.fixture()
def brewapi_get_buildinfo_s2i_core():
    return json.loads((DATA_DIR / "brewapi_get_buildinfo_s2i_core.json").read_text())


@pytest.fixture()
def brewapi_get_buildinfo_python3():
    return json.loads((DATA_DIR / "brewapi_get_buildinfo_python3.json").read_text())


@pytest.fixture()
def brewapi_list_archives_s2i_base():
    return json.loads((DATA_DIR / "brewapi_list_archives_s2i_base.json").read_text())


@pytest.fixture()
def brewapi_list_archives_s2i_core():
    return json.loads((DATA_DIR / "brewapi_list_archives_s2i_core.json").read_text())


@pytest.fixture()
def brewapi_list_archives_python3():
    return json.loads((DATA_DIR / "brewapi_list_archives_python3.json").read_text())


def get_tmp_workdir():
    return tempfile.TemporaryDirectory()
