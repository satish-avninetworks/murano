# Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from murano.common.i18n import _
from murano.common import uuidutils
from murano.db import models
from murano.db import session as db_session

from oslo_db import exception as db_exc
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class InstanceCredentialServices(object):
    @staticmethod
    def get_instance_credentials_by(filters):
        """Returns list of Instance Credentials
           :param filters: property filters
           :return: Returns list of instance Credentials
        """
        unit = db_session.get_session()
        instance_credentials = unit.query(models.InstanceCredentials). \
            filter_by(**filters).all()

        return instance_credentials

    @staticmethod
    def create(params, context):
        """Creates Instance Credentials with specified params, in particular -
        name.

           :param params: Dict, e.g. {'name': 'temp-name'}
           :param tenant_id: Tenant Id
           :return: Created Cloud Credential
        """
        params['id'] = uuidutils.generate_uuid()
        params['tenant_id'] = context.tenant
        instance_credential = models.InstanceCredentials()
        instance_credential.update(params)

        unit = db_session.get_session()
        with unit.begin():
            try:
                unit.add(instance_credential)
            except db_exc.DBDuplicateEntry:
                msg = _("Instance Credential specified name already exists")
                LOG.error(msg)
                raise db_exc.DBDuplicateEntry(explanation=msg)
        instance_credential.save(unit)

        return instance_credential

    @staticmethod
    def remove(instance_cred_id):
        """It deletes the Instance Credential from database.

           :param instance_cred_id: Cloud Credential Id to be deleted.
        """

        unit = db_session.get_session()
        template = unit.query(models.InstanceCredentials).get(instance_cred_id)
        if template:
            with unit.begin():
                unit.delete(template)

    @staticmethod
    def update(instance_cred_id, body):
        """It updates the instance credential.

           :param instance_cred_id: instance Credential Id to be deleted.
           :param body: The instance credentials updated.
           :return the updated instance credential
        """

        unit = db_session.get_session()
        instance_cred = unit.query(models.InstanceCredentials).get(instance_cred_id)
        instance_cred.update(body)
        instance_cred.save(unit)
        return instance_cred

    @staticmethod
    def instance_credential_exist(instance_cred_id):
        """It checks if the Instance credential exits in database.

           :param id: The Instance credential ID
           :return True if exist's else false
        """

        return True if InstanceCredentialServices.get_instance_credentials_by(
            instance_cred_id) else False

    @staticmethod
    def get_instance_credential(instance_cred_id):
        """It return if the instance credential exits in database.

           :param id: The instance credential ID
           :return InstanceCredential
        """

        session = db_session.get_session()
        return session.query(models.InstanceCredentials).get(instance_cred_id)
