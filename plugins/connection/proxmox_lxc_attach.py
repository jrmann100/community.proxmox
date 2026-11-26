# Copyright (c) 2024 Nils Stein (@mietzen) <github.nstein@mailbox.org>
# Copyright (c) 2024 Ansible Project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

"""Connection plugin that enters LXC containers with lxc-attach on the node.

Same transport and options as proxmox_pct_remote, but it does not go through
the pct CLI. pct is a Perl program that loads the PVE API stack on every call,
which costs seconds of CPU per command, while lxc-attach is the process that
pct exec execs into.
"""

from __future__ import annotations

from ansible.errors import AnsibleError
from ansible.utils.display import Display

from ansible_collections.community.proxmox.plugins.connection import proxmox_pct_remote as _pct

display = Display()

DOCUMENTATION = r"""

author: Nils Stein (@mietzen) <github.nstein@mailbox.org>
name: proxmox_lxc_attach
short_description: Run tasks in Proxmox LXC container instances using lxc-attach via SSH
requirements:
  - paramiko
description:
  - Run commands or put/fetch files to an existing Proxmox LXC container using lxc-attach via SSH.
  - Uses the Python SSH implementation (Paramiko) to connect to the Proxmox host.
options:
  remote_addr:
    description:
      - Address of the remote target.
    default: inventory_hostname
    type: string
    vars:
      - name: inventory_hostname
      - name: ansible_host
      - name: ansible_ssh_host
      - name: ansible_paramiko_host
  port:
    description: Remote port to connect to.
    type: int
    default: 22
    ini:
      - section: defaults
        key: remote_port
      - section: paramiko_connection
        key: remote_port
    env:
      - name: ANSIBLE_REMOTE_PORT
      - name: ANSIBLE_REMOTE_PARAMIKO_PORT
    vars:
      - name: ansible_port
      - name: ansible_ssh_port
      - name: ansible_paramiko_port
    keyword:
      - name: port
  remote_user:
    description:
      - User to login/authenticate as.
      - Can be set from the CLI via the C(--user) or C(-u) options.
    type: string
    vars:
      - name: ansible_user
      - name: ansible_ssh_user
      - name: ansible_paramiko_user
    env:
      - name: ANSIBLE_REMOTE_USER
      - name: ANSIBLE_PARAMIKO_REMOTE_USER
    ini:
      - section: defaults
        key: remote_user
      - section: paramiko_connection
        key: remote_user
    keyword:
      - name: remote_user
  password:
    description:
      - Secret used to either login the SSH server or as a passphrase for SSH keys that require it.
      - Can be set from the CLI via the C(--ask-pass) option.
    type: string
    vars:
      - name: ansible_password
      - name: ansible_ssh_pass
      - name: ansible_ssh_password
      - name: ansible_paramiko_pass
      - name: ansible_paramiko_password
    secret: true
  use_rsa_sha2_algorithms:
    description:
      - Whether or not to enable RSA SHA2 algorithms for pubkeys and hostkeys.
      - On paramiko versions older than 2.9, this only affects hostkeys.
      - For behavior matching paramiko<2.9 set this to V(false).
    vars:
      - name: ansible_paramiko_use_rsa_sha2_algorithms
    ini:
      - {key: use_rsa_sha2_algorithms, section: paramiko_connection}
    env:
      - {name: ANSIBLE_PARAMIKO_USE_RSA_SHA2_ALGORITHMS}
    default: true
    type: boolean
  host_key_auto_add:
    description: "Automatically add host keys to C(~/.ssh/known_hosts)."
    env:
      - name: ANSIBLE_PARAMIKO_HOST_KEY_AUTO_ADD
    ini:
      - key: host_key_auto_add
        section: paramiko_connection
    type: boolean
  look_for_keys:
    default: True
    description: "Set to V(false) to disable searching for private key files in C(~/.ssh/)."
    env:
      - name: ANSIBLE_PARAMIKO_LOOK_FOR_KEYS
    ini:
      - {key: look_for_keys, section: paramiko_connection}
    type: boolean
  proxy_command:
    default: ""
    description:
      - Proxy information for running the connection via a jumphost.
    type: string
    env:
      - name: ANSIBLE_PARAMIKO_PROXY_COMMAND
    ini:
      - {key: proxy_command, section: paramiko_connection}
    vars:
      - name: ansible_paramiko_proxy_command
  pty:
    default: True
    description: "C(sudo) usually requires a PTY, V(true) to give a PTY and V(false) to not give a PTY."
    env:
      - name: ANSIBLE_PARAMIKO_PTY
    ini:
      - section: paramiko_connection
        key: pty
    type: boolean
  record_host_keys:
    default: True
    description: "Save the host keys to a file."
    env:
      - name: ANSIBLE_PARAMIKO_RECORD_HOST_KEYS
    ini:
      - section: paramiko_connection
        key: record_host_keys
    type: boolean
  host_key_checking:
    description: "Set this to V(false) if you want to avoid host key checking by the underlying tools Ansible uses to connect to the host."
    type: boolean
    default: true
    env:
      - name: ANSIBLE_HOST_KEY_CHECKING
      - name: ANSIBLE_SSH_HOST_KEY_CHECKING
      - name: ANSIBLE_PARAMIKO_HOST_KEY_CHECKING
    ini:
      - section: defaults
        key: host_key_checking
      - section: paramiko_connection
        key: host_key_checking
    vars:
      - name: ansible_host_key_checking
      - name: ansible_ssh_host_key_checking
      - name: ansible_paramiko_host_key_checking
  use_persistent_connections:
    description: "Toggles the use of persistence for connections."
    type: boolean
    default: False
    env:
      - name: ANSIBLE_USE_PERSISTENT_CONNECTIONS
    ini:
      - section: defaults
        key: use_persistent_connections
  forward_agent:
    description: "Enable SSH agent forwarding."
    type: boolean
    default: False
    env:
      - name: ANSIBLE_PARAMIKO_FORWARD_AGENT
    ini:
      - section: paramiko_connection
        key: forward_agent
  banner_timeout:
    type: float
    default: 30
    description:
      - Configures, in seconds, the amount of time to wait for the SSH
        banner to be presented. This option is supported by paramiko
        version 1.15.0 or newer.
    ini:
      - section: paramiko_connection
        key: banner_timeout
    env:
      - name: ANSIBLE_PARAMIKO_BANNER_TIMEOUT
  timeout:
    type: int
    default: 10
    description: Number of seconds until the plugin gives up on failing to establish a TCP connection.
    ini:
      - section: defaults
        key: timeout
      - section: ssh_connection
        key: timeout
      - section: paramiko_connection
        key: timeout
    env:
      - name: ANSIBLE_TIMEOUT
      - name: ANSIBLE_SSH_TIMEOUT
      - name: ANSIBLE_PARAMIKO_TIMEOUT
    vars:
      - name: ansible_ssh_timeout
      - name: ansible_paramiko_timeout
    cli:
      - name: timeout
  lock_file_timeout:
    type: int
    default: 60
    description: Number of seconds until the plugin gives up on trying to write a lock file when writing SSH known host keys.
    vars:
      - name: ansible_lock_file_timeout
    env:
      - name: ANSIBLE_LOCK_FILE_TIMEOUT
  private_key_file:
    description:
      - Path to private key file to use for authentication.
    type: string
    ini:
      - section: defaults
        key: private_key_file
      - section: paramiko_connection
        key: private_key_file
    env:
      - name: ANSIBLE_PRIVATE_KEY_FILE
      - name: ANSIBLE_PARAMIKO_PRIVATE_KEY_FILE
    vars:
      - name: ansible_private_key_file
      - name: ansible_ssh_private_key_file
      - name: ansible_paramiko_private_key_file
    cli:
      - name: private_key_file
        option: "--private-key"
  vmid:
    description:
      - LXC Container ID
    type: int
    vars:
      - name: proxmox_vmid
  proxmox_become_method:
    description:
      - Become command used in proxmox
    type: str
    default: sudo
    vars:
      - name: proxmox_become_method
notes:
  - >
    When NOT using this plugin as root, you need to have a become mechanism,
    e.g. C(sudo), installed on Proxmox and setup so we can run it without prompting for the password.
    Inside the container, we need a shell, for example C(sh) and the C(cat) command to be available in the C(PATH) for this plugin to work.
  - >
    When there is no key, agent key or password to offer, the plugin asks the SSH server for the C(none) authentication method
    instead of failing with C(No authentication methods available).
    Servers that admit a client by its network identity, for example Tailscale SSH, accept it.
"""

EXAMPLES = r"""

# --------------------------------------------------------------
# Setup sudo with password less access to lxc-attach for user 'ansible':
# --------------------------------------------------------------
#
# Open a Proxmox root shell and execute:
# $ useradd -d /opt/ansible-pct -r -m -s /bin/sh ansible
# $ mkdir -p /opt/ansible-pct/.ssh
# $ ssh-keygen -t ed25519 -C 'ansible' -N "" -f /opt/ansible-pct/.ssh/ansible <<< y > /dev/null
# $ cat /opt/ansible-pct/.ssh/ansible
# $ mv /opt/ansible-pct/.ssh/ansible.pub /opt/ansible-pct/.ssh/authorized_keys
# $ rm /opt/ansible-pct/.ssh/ansible*
# $ chown -R ansible:ansible /opt/ansible-pct/.ssh
# $ chmod 700 /opt/ansible-pct/.ssh
# $ chmod 600 /opt/ansible-pct/.ssh/authorized_keys
# $ echo 'ansible ALL = (root) NOPASSWD: /usr/bin/lxc-attach' > /etc/sudoers.d/ansible_pct
#
# Save the displayed private key and add it to your ssh-agent
#
# Or use ansible:
# ---
# - name: Setup ansible-pct user and configure environment on Proxmox host
#   hosts: proxmox
#   become: true
#   gather_facts: false
#
#   tasks:
#     - name: Create ansible user
#       ansible.builtin.user:
#         name: ansible
#         comment: Ansible User
#         home: /opt/ansible-pct
#         shell: /bin/sh
#         create_home: true
#         system: true
#
#     - name: Create .ssh directory
#       ansible.builtin.file:
#         path: /opt/ansible-pct/.ssh
#         state: directory
#         owner: ansible
#         group: ansible
#         mode: '0700'
#
#     - name: Generate SSH key for ansible user
#       community.crypto.openssh_keypair:
#         path: /opt/ansible-pct/.ssh/ansible
#         type: ed25519
#         comment: 'ansible'
#         force: true
#         mode: '0600'
#         owner: ansible
#         group: ansible
#
#     - name: Set public key as authorized key
#       ansible.builtin.copy:
#         src: /opt/ansible-pct/.ssh/ansible.pub
#         dest: /opt/ansible-pct/.ssh/authorized_keys
#         remote_src: yes
#         owner: ansible
#         group: ansible
#         mode: '0600'
#
#     - name: Add sudoers entry for ansible user
#       ansible.builtin.copy:
#         content: 'ansible ALL = (root) NOPASSWD: /usr/bin/lxc-attach'
#         dest: /etc/sudoers.d/ansible_pct
#         owner: root
#         group: root
#         mode: '0440'
#
#     - name: Fetch private SSH key to localhost
#       ansible.builtin.fetch:
#         src: /opt/ansible-pct/.ssh/ansible
#         dest: ~/.ssh/proxmox_ansible_private_key
#         flat: yes
#         fail_on_missing: true
#
#     - name: Clean up generated SSH keys
#       ansible.builtin.file:
#         path: /opt/ansible-pct/.ssh/ansible*
#         state: absent
#
# - name: Configure private key permissions on localhost
#   hosts: localhost
#   tasks:
#     - name: Set permissions for fetched private key
#       ansible.builtin.file:
#         path: ~/.ssh/proxmox_ansible_private_key
#         mode: '0600'
#
# --------------------------------
# Static inventory file: hosts.yml
# --------------------------------
# all:
#   children:
#     lxc:
#       hosts:
#         container-1:
#           ansible_host: 10.0.0.10
#           proxmox_vmid: 100
#           ansible_connection: community.proxmox.proxmox_lxc_attach
#           ansible_user: ansible
#         container-2:
#           ansible_host: 10.0.0.10
#           proxmox_vmid: 200
#           ansible_connection: community.proxmox.proxmox_lxc_attach
#           ansible_user: ansible
#     proxmox:
#       hosts:
#         proxmox-1:
#           ansible_host: 10.0.0.10
#
#
# ---------------------------------------------
# Dynamic inventory file: inventory.proxmox.yml
# ---------------------------------------------
# plugin: community.proxmox.proxmox
# url: https://10.0.0.10:8006
# user: ansible@pam
# token_id: ansible
# token_secret: !vault |
#           $ANSIBLE_VAULT;1.1;AES256
#           ...

# want_facts: true
# exclude_nodes: true
# filters:
#   - proxmox_vmtype == "lxc"
# want_proxmox_nodes_ansible_host: false
# compose:
#   ansible_host: "'10.0.0.10'"
#   ansible_connection: "'community.proxmox.proxmox_lxc_attach'"
#   ansible_user: "'ansible'"
#
#
# ----------------------
# Playbook: playbook.yml
# ----------------------
---
- hosts: lxc
  # On nodes with many containers you might want to deactivate the devices facts
  # or set `gather_facts: false` if you don't need them.
  # More info on gathering fact subsets:
  # https://docs.ansible.com/ansible/latest/collections/ansible/builtin/setup_module.html
  #
  # gather_facts: true
  #   gather_subset:
  #     - "!devices"
  tasks:
    - name: Ping LXC container
      ansible.builtin.ping:
"""


class Connection(_pct.Connection):
    transport = "community.proxmox.proxmox_lxc_attach"

    def _build_pct_command(self, cmd: str) -> str:
        cmd = ["/usr/bin/lxc-attach", "-n", str(self.get_option("vmid")), "--keep-env", "--", cmd]
        if self.get_option("remote_user") != "root":
            cmd = [self.get_option("proxmox_become_method")] + cmd
            display.vvv(
                f"INFO Running as non root user: {self.get_option('remote_user')}, trying to run lxc-attach with "
                + f"become method: {self.get_option('proxmox_become_method')}",
                host=self.get_option("remote_addr"),
            )
        return " ".join(cmd)

    def exec_command(self, cmd: str, in_data: bytes | None = None, sudoable: bool = True) -> tuple[int, bytes, bytes]:
        returncode, stdout, stderr = super().exec_command(cmd, in_data=in_data, sudoable=sudoable)

        if b"Failed to get init pid" in stderr:
            raise AnsibleError(f"container {self.get_option('vmid')} is not running")

        return returncode, stdout, stderr
