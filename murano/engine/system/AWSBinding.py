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

import eventlet
import os
import heatclient.exc as heat_exc
from oslo_log import log as logging
from murano.common.i18n import _LW
from murano.common import utils
from murano.dsl import dsl
from murano.dsl import helpers
from pprint import pprint
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.base import NodeImage
from libcloud.compute.deployment import ScriptDeployment
from libcloud.compute.deployment import MultiStepDeployment, SSHKeyDeployment
from libcloud.compute.base import NodeAuthSSHKey
LOG = logging.getLogger(__name__)


@dsl.name('io.murano.system.AWSBinding')
class AWSBinding(object):
    def __init__(self):
        self.cls = get_driver(Provider.EC2)
        self.driver = self.cls('userID','password',region="us-west-1")

    def createnode(self,name):
        images = NodeImage(id='imageID',name=None,driver=self.driver)
        sizes = self.driver.list_sizes()
        node = self.driver.create_node(name=name,image=images,size=sizes[0])
        # Wait until node is up and running and has IP assigned
        try:
            node, ip_addresses = self.driver.wait_until_running(nodes=[node])[0]
        except Exception:
            print("Unable to ping the node, TODO how to handle this")

        return node

    def destroynode(self,node):
        self.driver.destroy_node(node)
  
    def deploynode(self,plan,imageid,name):
        ssh_keypath = os.path.expanduser('~/.ssh/id_rsa')
        with open(ssh_keypath+".pub") as f:
            public_key = f.read()
        key = SSHKeyDeployment(public_key)
        images = NodeImage(id=imageid,name=None,driver=self.driver)
        sizes = self.driver.list_sizes()

        #TODO - deploy_node() with no script, get rid of "plan"
        script = ScriptDeployment(plan['Files'].values()[0]['Body'])
        msd = MultiStepDeployment([key,script])
        try:
            node = self.driver.deploy_node(name=name,image=images,size=sizes[0],ssh_key=ssh_keypath,ssh_username='ubuntu',deploy=msd,timeout=1800,ex_keyname="avni_key")
        except NotImplementedError:
            print("Deploy Node is not implemented for this driver")
        return node
   
