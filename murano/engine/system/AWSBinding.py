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
        self.driver = self.cls('AKIAIETZPSM636GLXORA','rOLla8GFbmAB16Zi3TMzOMgoeoicrB7BUY0nOmg+',region="us-west-1")

    def createnode(self,name):
        images = NodeImage(id='imageID',name=None,driver=self.driver)
        sizes = self.driver.list_sizes()
        node = self.driver.create_node(name=name,image=images,size=sizes[0])
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
        #script1 = ScriptDeployment("sudo apt-get -y update")
        #script2 = ScriptDeployment("sudo apt-get install -y apache2")
        #entry = plan['Scripts']['apacheDeploy']['EntryPoint']
        script = ScriptDeployment(plan['Files'].values()[0]['Body'],args=[str(x) for x in plan['Parameters'].values()])
        msd = MultiStepDeployment([key,script])
        try:
            node = self.driver.deploy_node(name=name,image=images,size=sizes[0],ssh_key=ssh_keypath,ssh_username='ubuntu',deploy=msd,timeout=1800,ex_keyname="avni_key")
        except NotImplementedError:
            print("Deploy Node is not implemented for this driver")
        return node

    def runscripts(self,node, plan):
        ssh_keypath = os.path.expanduser('~/.ssh/id_rsa')
        with open(ssh_keypath+".pub") as f:
            public_key = f.read()

        key = SSHKeyDeployment(public_key)
        script = ScriptDeployment(plan['Files'].values()[0]['Body'],args=plan['Parameters'].values())
        msd = MultiStepDeployment([key,script])

        #Create the SSH client and push the script
        try:
           node.driver._connect_and_run_deployment_script(
                        task=msd, node=node,
                        ssh_hostname=node.public_ips[0], ssh_port=22,
                        ssh_username='ubuntu',
                        ssh_key_file=ssh_keypath, ssh_timeout=1800,
                        timeout=300, max_tries=3,ssh_password='avni1234')
        except Exception:
            print("Unable to run scripts on this driver")    
