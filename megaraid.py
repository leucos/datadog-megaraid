# Megacli check for datadog
# requires the following line in sudoers

# dd-agent ALL = (root) NOPASSWD: /usr/sbin/megacli

import time
import shlex
import os

from subprocess import Popen, PIPE
from checks import AgentCheck
from hashlib import md5

class Megaraid(AgentCheck):
    def check_adapter(self, instance, megacli):
        adapter = instance['adapter']
        cmd = "sudo %s -LDInfo -Lall -a%s" % (megacli, instance.get('adapter', 0))
        process = Popen(shlex.split(cmd), stdout=PIPE, close_fds=True)
        (output, err) = process.communicate()
        exit_code = process.wait()
        
        adapters = dict()
        if exit_code != 0:
            self.log.error("Got exit code %s for command '%s' and output %s" % (exit_code, cmd, output))
            self.check_error_event("Unable to check adapter %s with command '%s': error '%s' (code: %s)" % (adapter, cmd, err, exit_code), md5(megacli).hexdigest())
            return

        current_adapter=None

        for line in output.split('\n'):
            if line.startswith('Adapter'):
                current_adapter = line.split(' ')[1]
                adapters['0'] = dict()
            if line.startswith('State'):
                if "Optimal" in line:
                    adapters[current_adapter]['state'] = 1
                else:
                    adapters[current_adapter]['state'] = 0
                    self.send_megaraid_alert(instance, 'Adapter %s state is not optimal: %s' % (current_adapter, adapters[current_adapter]['state']), current_adapter)

                self.gauge('megaraid.adapter.status', adapters[current_adapter]['state'], tags=['megaraid'])

    def check_disks(self, instance, megacli):
        adapter = instance.get('adapter', 0)
        cmd = "sudo %s -pdlist -a%s" % (megacli, adapter)
        process = Popen(shlex.split(cmd), stdout=PIPE, close_fds=True)
        (output, err) = process.communicate()
        exit_code = process.wait()
        
        disks = dict()

        if exit_code != 0:
            self.log.error("Got exit code %s for command '%s' and output %s" % (exit_code, cmd, output))            
            self.check_error_event('Unable to check disks with command %s : %s (code: %s)' % (cmd, err, exit_code), md5(megacli).hexdigest())
            return

        current_disk = None

        for line in output.split('\n'):
            if line.startswith('Adapter #'):
                adapter = line.split('#')[1]
                disks[adapter] = dict()
            if line.startswith('Device Id:'):
                current_disk = line.split(' ')[2]
                disks[adapter][current_disk] = dict()
            if line.startswith('Media Error Count'):
                disks[adapter][current_disk]['media_error_count'] = int(line.split(' ')[3])
            elif line.startswith('Other Error Count'):
                disks[adapter][current_disk]['other_error_count'] = int(line.split(' ')[3])
            elif line.startswith('Predictive Failure Count'):
                disks[adapter][current_disk]['predictive_failure_count'] = int(line.split(' ')[3])
            elif line.startswith('Drive has flagged a S.M.A.R.T alert'):
                if "No" in line:
                    disks[adapter][current_disk]['smart_alert'] = 0
                else:
                    disks[adapter][current_disk]['smart_alert'] = 1                   
                    self.send_megaraid_alert(instance,'SMART Alert on disk megaraid/%s/%s', (adapter, disk), adapter, disk)
            elif line.startswith('Drive Temperature'):
                disks[adapter][current_disk]['temperature'] = int(line.split(':')[1].split('C')[0])
                self.log.debug("Got temp %s for disk 'megaraid/%s/%s'" % (disks[adapter][current_disk]['temperature'], adapter, current_disk))
            elif line.startswith('Firmware state'):
                if "Online" not in line or "Spun Up" not in line:
                    self.send_megaraid_alert(instance, 'Abnormal firmware state %s on megaraid/%s/%s' % ( line.split(':')[1], adapter, current_disk ), adapter, current_disk)
                    disks[adapter][current_disk]['firmware_ok'] = 0
                else:
                    disks[adapter][current_disk]['firmware_ok'] = 1

        for adapt in disks:
            for disk in disks[adapt]: 
                for key in disks[adapt][disk]: 
                    self.gauge('megaraid.device.%s' % key, disks[adapt][disk][key], tags=['megaraid'], device_name="megaraid/%s/%s" % (adapt, disk))

    def check(self, instance):
        megacli = self.init_config.get('megacli_path', '/usr/sbin/megacli')

        if not (os.path.isfile(megacli) and os.access(megacli, os.X_OK)): 
            self.check_error_event('Unable to use megacli executable at %s' % megacli, md5(megacli).hexdigest())
            self.log.error("Unable to use megacli at %s" % megacli)
        else:
            self.check_adapter(instance, megacli)
            self.check_disks(instance, megacli)

    def check_error_event(self, text, aggregation_key):
        self.event({
            'timestamp': int(time.time()),
            'event_type': 'megaraid',
            'msg_title': 'Unable to check megaraid',
            'msg_text': text
        })

    def send_megaraid_alert(self, instance, text, adapter, disk=None):
        send_adapter_events = int(instance.get('adapter_events', self.init_config.get('adapter_events', 0)))
        send_disks_events   = int(instance.get('adapter_events', self.init_config.get('adapter_events', 0)))

        if disk == None:
            # We have an adapter event
            # We return if we don't need to send them
            if not send_adapter_events:
                return
            device =  'megaraid#%s' % adapter
        else:
            # We have a disk event
            # We return if we don't need to send them
            if not send_disk_events:
                return
            device =  'megaraid/%s/%s' % (adapter, current_disk)

        aggregation_key = md5(device).hexdigest()

        self.event({
            'timestamp': int(time.time()),
            'event_type': 'megaraid',
            'msg_title': 'Megaraid alert on %s' % device,
            'msg_text': text,
            'aggregation_key': aggregation_key
        })

if __name__ == '__main__':
    check, instances = Megaraid.from_yaml('/etc/dd-agent/conf.d/megaraid.yaml')
    for instance in instances:
        print "\nRunning MegaRAID checks"
        check.check()
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())

