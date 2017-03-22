#!/usr/bin/python3

import amulet
import os
import unittest
import yaml
import requests

from amulet_utils import check_systemd_service
from amulet_utils import kubectl
from amulet_utils import run
from amulet_utils import valid_certificate
from amulet_utils import valid_key

SECONDS_TO_WAIT = 1800


def find_bundle(name='bundle.yaml'):
    '''Locate the bundle to load for this test.'''
    # Check the environment variables for BUNDLE.
    bundle_path = os.getenv('BUNDLE_PATH')
    if not bundle_path:
        # Construct bundle path from the location of this file.
        bundle_path = os.path.join(os.path.dirname(__file__), '..', name)
    return bundle_path


class MasterTest(unittest.TestCase):
    bundle_file = find_bundle()

    @classmethod
    def setUpClass(cls):
        cls.deployment = amulet.Deployment(series='xenial')
        with open(cls.bundle_file) as stream:
            bundle_yaml = stream.read()
        bundle = yaml.safe_load(bundle_yaml)
        cls.deployment.load(bundle)

        # Allow some time for Juju to provision and deploy the bundle.
        cls.deployment.setup(timeout=SECONDS_TO_WAIT)

        # Wait for the system to settle down.
        application_messages = {'kubernetes-worker':
                                'Kubernetes worker running.'}
        cls.deployment.sentry.wait_for_messages(application_messages,
                                                timeout=900)

        # Make every unit available through self reference
        # eg: for worker in self.workers:
        #         print(worker.info['public-address'])
        cls.easyrsas = cls.deployment.sentry['easyrsa']
        cls.etcds = cls.deployment.sentry['etcd']
        cls.flannels = cls.deployment.sentry['flannel']
        cls.loadbalancers = cls.deployment.sentry['kubeapi-load-balancer']
        cls.masters = cls.deployment.sentry['kubernetes-master']
        cls.workers = cls.deployment.sentry['kubernetes-worker']

    def test_master_services(self):
        for master in self.masters:
            self.deployment.destroy_unit(master.info['unit_name'])
        self.deployment.sentry.wait()
        self.deployment.add_unit('kubernetes-master')
        self.deployment.sentry.wait()
        lb_ip = self.loadbalancers[0].info['public-address']
        url = "https://{}/api/v1/proxy/namespaces/kube-system/services/kubernetes-dashboard/api/v1/workload/default".format(lb_ip)
        r = requests.get(url, verify=False )
        assert r.status_code != 500


if __name__ == '__main__':
    unittest.main()
