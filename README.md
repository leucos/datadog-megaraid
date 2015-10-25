Megacli Datadog Check
=====================

Check your LSI MegaRAID adapter with datadog.

# Goals

Monitor your LSI MegaRAID card with datadog.

# Prerequisites

- megacli (see [Leo's PPA](https://launchpad.net/~tuxpoldo/+archive/ubuntu/megacli) for trusty and friends)
- and entry in sudoers so that datado can use megacli (e.g. something like `dd-agent ALL = (root) NOPASSWD: /usr/sbin/megacli`)

# Usage

Put `megaraid.py` in datadog's `checks.d` directory, and `megaraid.yaml` in datadog's `conf.d` directory (usually, these directories lies in `/etc/dd-agent`).

The only global configuration value is `megacli_path`, which, surprisingly, set the full path to the `megabli` binary.


    init_config:
      megacli_path: /usr/sbin/megacli
      adapter_events: 1
      disk_events: 0

    instances:
      - adapter: 0
        adapter_events: 0
        disk_events: 1

# What you get

## Adapter level

At the adapter level, events are emitted if the adapter state is not 'Optimal'. Note that the check is _stateless_, which means events will be triggered at _each check_. You can disable adapter check setting `adapter_events` to 1 in the global or the adapter section in the config file.

## Drives

At the drive level, those metrics are reported (see `megacli -pdlist -aALL`):

- Media Error Count
- Other Error Count
- Predictive Failure Count
- Drive has flagged a S.M.A.R.T alert (0 is good)
- Firmware state (1 is good)
- Drive Temperature

The following events are also reported:

- Drive has flagged a S.M.A.R.T alert (when megacli reports 'Yes')
- Firmware state (when 'Online' or 'Spun Up' are not found in firmware report)

# Misc

See the accompanying [megaraid](https://github.com/leucos/ansible-megaraid) and [datadog-agent](https://github.com/leucos/ansible-datadog-agent) Ansible roles.


