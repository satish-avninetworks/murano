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


class CloudCredentialServices(object):
    @staticmethod
    def get_cloud_credentials_by(filters):
        """Returns list of Cloud Credentials
           :param filters: property filters
           :return: Returns list of Cloud Credentials
        """
        unit = db_session.get_session()
        cloud_credentials = unit.query(models.CloudCredentials). \
            filter_by(**filters).all()

        return cloud_credentials

    @staticmethod
    def create(params, tenant_id):
        """Creates Cloud Credentials with specified params, in particular -
        name.

           :param params: Dict, e.g. {'name': 'temp-name'}
           :param tenant_id: Tenant Id
           :return: Created Cloud Credential
        """
        params['id'] = uuidutils.generate_uuid()
        params['tenant_id'] = tenant_id
        cloud_credential = models.CloudCredentials()
        cloud_credential.update(params)

        unit = db_session.get_session()
        with unit.begin():
            try:
                unit.add(cloud_credential)
            except db_exc.DBDuplicateEntry:
                msg = _("Cloud Credential specified name already exists")
                LOG.error(msg)
                raise db_exc.DBDuplicateEntry(explanation=msg)
        cloud_credential.save(unit)

        return cloud_credential

    @staticmethod
    def remove(cloud_cred_id):
        """It deletes the Cloud Credential from database.

           :param cloud_cred_id: Cloud Credential Id to be deleted.
        """

        unit = db_session.get_session()
        template = unit.query(models.CloudCredentials).get(cloud_cred_id)
        if template:
            with unit.begin():
                unit.delete(template)

    @staticmethod
    def update(id, body):
        """It updates the cloud credential.

           :param id: Cloud Credential Id to be deleted.
           :param body: The cloud credentials updated.
           :return the updated cloud credential
        """

        unit = db_session.get_session()
        template = unit.query(models.CloudCredentials).get(id)
        template.update(body)
        template.save(unit)
        return template

    @staticmethod
    def cloud_credential_exist(cloud_cred_id):
        """It checks if the cloud credential exits in database.

           :param id: The cloud credential ID
           :return True if exist's else false
        """

        return True if CloudCredentialServices.get_cloud_credential(
            cloud_cred_id) else False

    @staticmethod
    def get_cloud_credential(cloud_cred_id):
        """It return if the cloud credential exits in database.

           :param id: The cloud credential ID
           :return CloudCredential
        """

        session = db_session.get_session()
        return session.query(models.CloudCredentials).get(cloud_cred_id)
