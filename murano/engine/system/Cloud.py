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
import muranoclient.v1.client as muranoclient

LOG = logging.getLogger(__name__)


@dsl.name('io.murano.system.Cloud')
class Cloud(object):
    def __init__(self, cloud_id):
        self.credentials = muranoclient.cloud_credentials.get(cloud_id)



