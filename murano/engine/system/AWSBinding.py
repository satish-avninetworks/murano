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

import os
from oslo_log import log as logging
from murano.dsl import dsl
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.compute.base import NodeImage
from libcloud.compute.deployment import ScriptDeployment
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.deployment import SSHKeyDeployment
LOG = logging.getLogger(__name__)


@dsl.name('io.murano.system.AWSBinding')
class AWSBinding(object):
    def __init__(self,cloud):
        self.cls = get_driver(Provider.EC2)
        #self.driver = self.cls('AKIAIETZPSM636GLXORA','rOLla8GFbmAB16Zi3TMzOMgoeoicrB7BUY0nOmg+', region="us-west-1")
        import pdb;pdb.set_trace()
        self.driver = self.cls(cloud.user, cloud.key, region="us-east-1")
        self.cloud = cloud

    def createnode(self, image,flavor,name):
        #TODO: Remove hardcoding
        import pdb;pdb.set_trace()
        images = NodeImage(id=image, name=None,driver=self.driver)
        sizes = self.driver.list_sizes()
        size = [s for s in sizes if s.id == flavor][0]
        node = self.driver.create_node(name=name,image=images,size=size)
        # Wait until node is up and running and has IP assigned
        # this blocking call is needed to ensure instance is up
        try:
            node, ipaddresses = self.driver.wait_until_running(nodes=[node])[0]
        except Exception:
            print("Unable to ping the node, TODO how to handle this")

        return node

    def getpublicips(self, node):
        return node.public_ips

    def destroynode(self, node):
        self.driver.destroy_node(node)
 
    #TODO - Deprecated API 
    def deploynode(self, plan, imageid, name):
        ssh_keypath = os.path.expanduser('~/.ssh/id_rsa')
        with open(ssh_keypath+".pub") as f:
            public_key = f.read()
        key = SSHKeyDeployment(public_key)
        images = NodeImage(id=imageid, name=None, driver=self.driver)
        sizes = self.driver.list_sizes()
        script = ScriptDeployment(plan['Files'].values()[0]['Body'],args=[str(x) for x in plan['Parameters'].values()])
        msd = MultiStepDeployment([key, script])
        try:
            node = self.driver.deploy_node(name=name, image=images, size=sizes[0], ssh_key=ssh_keypath, ssh_username='ubuntu', deploy=msd, timeout=1800, ex_keyname="avni_key")
        except NotImplementedError:
            print("Deploy Node is not implemented for this driver")
        return node

