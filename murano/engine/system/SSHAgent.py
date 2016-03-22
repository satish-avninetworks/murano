# Copyright (c) 2016 Avni
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import os
import types
import urlparse
import uuid

from yaql import specs

from murano.dsl import dsl
from libcloud.compute.deployment import ScriptDeployment
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.deployment import SSHKeyDeployment
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


@dsl.name('io.murano.system.SSHAgent')
class SSHAgent(object):
    def __init__(self, interfaces, host,cloud):
        self._enabled = False
        if CONF.engine.disable_murano_agent:
            LOG.debug('Use of murano-agent is disallowed '
                      'by the server configuration')
            return

        self.cloud = cloud
        self._environment = self._get_environment(interfaces, host)
        self._enabled = True
        self._queue = str('e%s-h%s' % (
            self._environment.id, host.id)).lower()

    def setnode(self, node):
        self.node = node

    def _get_environment(self, interfaces, host):
        return interfaces.yaql()(
            "$.find('io.murano.Environment').require()", host)

    @property
    def enabled(self):
        return self._enabled

    def _check_enabled(self):
        if CONF.engine.disable_murano_agent:
            raise exceptions.PolicyViolationException(
                'Use of murano-agent is disallowed '
                'by the server configuration')

    @specs.parameter(
        'resources', dsl.MuranoType('io.murano.system.Resources'))
    def call(self, template, resources, timeout=None):
        if timeout is None:
            timeout = CONF.engine.agent_timeout
        self._check_enabled()
        plan = self.build_execution_plan(template, resources())
        if self.node:
            self.runscripts(self.node, plan)

    def runscripts(self, node, plan):
        #TODO: Read from id mgmt
        ssh_keypath = os.path.expanduser('~/.ssh/id_rsa')
        with open(ssh_keypath + ".pub") as f:
            public_key = f.read()

        key = SSHKeyDeployment(public_key)
        #Get the argument keys
        body = plan['Body'].split('.format(')[-1]
        keys = ','+body.split(')).stdout')[0]
        keys = filter(None,keys.split(',args.'))
        params = []
        for k in keys:
            params.append(str(plan['Parameters'][k]))

        script = ScriptDeployment(plan['Files'].values()[0]['Body'], args=params)
        msd = MultiStepDeployment([key, script])

        # Create the SSH client and push the script
        try:
           node.driver._connect_and_run_deployment_script(
                        task=msd, node=node,
                        ssh_hostname=node.public_ips[0], ssh_port=22,
                        ssh_username='ubuntu',
                        ssh_key_file=ssh_keypath, ssh_timeout=1800,
                        timeout=300, max_tries=3, ssh_password='avni1234')
        except Exception:
            print("Unable to run scripts on this driver")

    def build_execution_plan(self, template, resources):
        template = copy.deepcopy(template)
        if not isinstance(template, types.DictionaryType):
            raise ValueError('Incorrect execution plan ')
        format_version = template.get('FormatVersion')
        if not format_version or format_version.startswith('1.'):
            return self._build_v1_execution_plan(template, resources)
        else:
            return self._build_v2_execution_plan(template, resources)

    def _build_v1_execution_plan(self, template, resources):
        scripts_folder = 'scripts'
        script_files = template.get('Scripts', [])
        scripts = []
        for script in script_files:
            script_path = os.path.join(scripts_folder, script)
            scripts.append(resources.string(
                script_path).encode('base64'))
        template['Scripts'] = scripts
        return template

    def _build_v2_execution_plan(self, template, resources):
        scripts_folder = 'scripts'
        plan_id = uuid.uuid4().hex
        template['ID'] = plan_id
        if 'Action' not in template:
            template['Action'] = 'Execute'
        if 'Files' not in template:
            template['Files'] = {}

        files = {}
        for file_id, file_descr in template['Files'].items():
            files[file_descr['Name']] = file_id

        for name, script in template.get('Scripts', {}).items():
            if 'EntryPoint' not in script:
                raise ValueError('No entry point in script ' + name)

            if 'Application' in script['Type']:
                script['EntryPoint'] = self._place_file(scripts_folder,
                                                        script['EntryPoint'],
                                                        template, resources,
                                                        files)
            if 'Files' in script:
                for i, file in enumerate(script['Files']):
                    if self._get_name(file) not in files:
                        script['Files'][i] = self._place_file(
                            scripts_folder, file, template, resources, files)
                    else:
                        script['Files'][i] = files[file]
        return template

    def _is_url(self, file):
        file = self._get_url(file)
        parts = urlparse.urlsplit(file)
        if not parts.scheme or not parts.netloc:
            return False
        else:
            return True

    def _get_url(self, file):
        if isinstance(file, dict):
            return file.values()[0]
        else:
            return file

    def _get_name(self, file):
        if isinstance(file, dict):
            name = file.keys()[0]
        else:
            name = file

        if self._is_url(name):
            name = name[name.rindex('/') + 1:len(name)]
        elif name.startswith('<') and name.endswith('>'):
            name = name[1: -1]
        return name

    def _get_file_value(self, file):
        if isinstance(file, dict):
            file = file.values()[0]
        return file

    def _get_body(self, file, resources, folder):
        use_base64 = self._is_base64(file)
        if use_base64 and file.startswith('<') and file.endswith('>'):
            file = file[1: -1]
        body = resources.string(os.path.join(folder, file))
        if use_base64:
            body = body.encode('base64')
        return body

    def _is_base64(self, file):
        return file.startswith('<') and file.endswith('>')

    def _get_body_type(self, file):
        return 'Base64' if self._is_base64(file) else 'Text'

    def _place_file(self, folder, file, template, resources, files):
        file_value = self._get_file_value(file)
        name = self._get_name(file)
        file_id = uuid.uuid4().hex

        if self._is_url(file_value):
            template['Files'][file_id] = self._get_file_des_downloadable(file)
            files[name] = file_id

        else:
            template['Files'][file_id] = self._get_file_description(
                file, resources, folder)
            files[name] = file_id
        return file_id

    def _get_file_des_downloadable(self, file):
        name = self._get_name(file)
        file = self._get_file_value(file)
        return {
            'Name': str(name),
            'URL': file,
            'Type': 'Downloadable'
        }

    def _get_file_description(self, file, resources, folder):
        name = self._get_name(file)
        file_value = self._get_file_value(file)

        body_type = self._get_body_type(file_value)
        body = self._get_body(file_value, resources, folder)
        return {
            'Name': name,
            'BodyType': body_type,
            'Body': body
        }
