# Copyright (c) 2024 Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_bytes
from ansible.playbook.play_context import PlayContext
from ansible.plugins.loader import connection_loader

paramiko = pytest.importorskip("paramiko")


@pytest.fixture
def connection():
    conn = connection_loader.get("community.proxmox.proxmox_lxc_attach", PlayContext(), StringIO())
    conn.set_option("vmid", 100)
    conn.set_option("remote_addr", "192.168.1.100")
    conn.set_option("remote_user", "root")
    return conn


def test_build_command(connection):
    """Test lxc-attach command building with different users"""
    cmd = connection._build_pct_command('/bin/sh -c "ls -la"')
    assert cmd == '/usr/bin/lxc-attach -n 100 --keep-env -- /bin/sh -c "ls -la"'

    connection.set_option("remote_user", "user")
    connection.set_option("proxmox_become_method", "sudo")
    cmd = connection._build_pct_command('/bin/sh -c "ls -la"')
    assert cmd == 'sudo /usr/bin/lxc-attach -n 100 --keep-env -- /bin/sh -c "ls -la"'


@patch("paramiko.SSHClient")
def test_exec_command_container_not_running(mock_ssh, connection):
    """Test command execution when the container is stopped"""
    mock_client = MagicMock()
    mock_ssh.return_value = mock_client
    mock_channel = MagicMock()
    mock_transport = MagicMock()

    mock_client.get_transport.return_value = mock_transport
    mock_transport.open_session.return_value = mock_channel
    mock_channel.recv_exit_status.return_value = 1
    mock_channel.makefile.return_value = [to_bytes("")]
    mock_channel.makefile_stderr.return_value = [to_bytes("lxc-attach: Failed to get init pid")]

    connection._connected = True
    connection.ssh = mock_client

    with pytest.raises(AnsibleError, match="container 100 is not running"):
        connection.exec_command("ls -la")
