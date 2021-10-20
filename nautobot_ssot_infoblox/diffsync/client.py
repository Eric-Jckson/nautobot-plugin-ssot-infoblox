"""All interactions with infoblox."""

import logging
import os
import copy
import re
import requests

from nautobot.core.settings_funcs import is_truthy
from requests.compat import urljoin
from dns import reversename

logger = logging.getLogger("rq.worker")


class InfobloxApi:  # pylint: disable=too-few-public-methods
    """Representation and methods for interacting with infoblox."""

    def __init__(
        self,
        url=os.environ["NAUTOBOT_INFOBLOX_URL"],
        username=os.environ["NAUTOBOT_INFOBLOX_USERNAME"],
        password=os.environ["NAUTOBOT_INFOBLOX_PASSWORD"],
        verify_ssl=is_truthy(os.getenv("NAUTOBOT_INFOBLOX_VERIFY_SSL", "true")),
        cookie=None,
    ):  # pylint: disable=too-many-arguments
        """Initialization of infoblox class."""
        self.url = url.rstrip()
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.cookie = cookie
        if self.verify_ssl is False:
            requests.packages.urllib3.disable_warnings(  # pylint: disable=no-member
                requests.packages.urllib3.exceptions.InsecureRequestWarning  # pylint: disable=no-member
            )  # pylint: disable=no-member
        self.headers = {"Content-Type": "application/json"}
        self.extra_vars = {}

    def _request(self, method, path, **kwargs):
        """Return a response object after making a request to by other methods.

        Args:
            method (str): Request HTTP method to call with requests.
            path (str): URL path to call.

        Returns:
            :class:`~requests.Response`: Response from the API.
        """
        kwargs["verify"] = self.verify_ssl
        kwargs["headers"] = self.headers
        api_path = f"/wapi/v2.12/{path}"
        url = urljoin(self.url, api_path)

        if self.cookie:
            resp = requests.request(method, url, cookies=self.cookie, **kwargs)
        else:
            kwargs["auth"] = requests.auth.HTTPBasicAuth(self.username, self.password)
            resp = requests.request(method, url, **kwargs)
            self.cookie = copy.copy(resp.cookies.get_dict("ibapauth"))
        resp.raise_for_status()
        return resp

    def get_all_ipv4address_networks(self, prefix, status):
        """Gets all used / unused IPv4 addresses within the supplied network.

        Args:
            prefix (str): Network prefix - '10.220.0.0/22'
            status (str): USED or UNUSED

        Returns:
            (list): IPv4 dict objects

        Return Response:
        [
            {
                "_ref": "ipv4address/Li5pcHY0X2FkZHJlc3MkMTAuMjIwLjAuMTAwLzA:10.220.0.100",
                "ip_address": "10.220.0.100",
                "is_conflict": false,
                "lease_state": "FREE",
                "mac_address": "55:55:55:55:55:55",
                "names": [],
                "network": "10.220.0.0/22",
                "network_view": "default",
                "objects": [
                    "fixedaddress/ZG5zLmZpeGVkX2FkZHJlc3MkMTAuMjIwLjAuMTAwLjAuLg:10.220.0.100/default"
                ],
                "status": "USED",
                "types": [
                    "FA",
                    "RESERVED_RANGE"
                ],
                "usage": [
                    "DHCP"
                ]
            },
            {
                "_ref": "ipv4address/Li5pcHY0X2FkZHJlc3MkMTAuMjIwLjAuMTAxLzA:10.220.0.101",
                "ip_address": "10.220.0.101",
                "is_conflict": false,
                "lease_state": "FREE",
                "mac_address": "11:11:11:11:11:11",
                "names": [
                    "testdevice1.test"
                ],
                "network": "10.220.0.0/22",
                "network_view": "default",
                "objects": [
                    "record:host/ZG5zLmhvc3QkLl9kZWZhdWx0LnRlc3QudGVzdGRldmljZTE:testdevice1.test/default"
                ],
                "status": "USED",
                "types": [
                    "HOST",
                    "RESERVED_RANGE"
                ],
                "usage": [
                    "DNS",
                    "DHCP"
                ]
            }
        ]
        """
        params = {"network": prefix, "status": status, "_return_as_object": 1}
        api_path = "ipv4address"
        response = self._request("GET", api_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def get_host_record_by_name(self, fqdn):
        """Gets the host record by using FQDN.

        Args:
            fqdn (str): IPv4 Address to look up

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "record:host/ZG5zLmhvc3QkLl9kZWZhdWx0LnRlc3QudGVzdGRldmljZTE:testdevice1.test/default",
                "ipv4addrs": [
                    {
                        "_ref": "record:host_ipv4addr/ZG5zLmhvc3RfYWRkcmVzcyQuX2RlZmF1bHQudGVzdC50ZXN0ZGV2aWNlMS4xMC4yMjAuMC4xMDEu:10.220.0.101/testdevice1.test/default",
                        "configure_for_dhcp": true,
                        "host": "testdevice1.test",
                        "ipv4addr": "10.220.0.101",
                        "mac": "11:11:11:11:11:11"
                    }
                ],
                "name": "testdevice1.test",
                "view": "default"
            }
        ]
        """
        url_path = "record:host"
        params = {"name": fqdn, "_return_as_object": 1}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def get_host_record_by_ip(self, ip_address):
        """Gets the host record by using IP Address.

        Args:
            ip_address (str): IPv4 Address to look up

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "record:host/ZG5zLmhvc3QkLl9kZWZhdWx0LnRlc3QudGVzdGRldmljZTE:testdevice1.test/default",
                "ipv4addrs": [
                    {
                        "_ref": "record:host_ipv4addr/ZG5zLmhvc3RfYWRkcmVzcyQuX2RlZmF1bHQudGVzdC50ZXN0ZGV2aWNlMS4xMC4yMjAuMC4xMDEu:10.220.0.101/testdevice1.test/default",
                        "configure_for_dhcp": true,
                        "host": "testdevice1.test",
                        "ipv4addr": "10.220.0.101",
                        "mac": "11:11:11:11:11:11"
                    }
                ],
                "name": "testdevice1.test",
                "view": "default"
            }
        ]
        """
        url_path = "record:host"
        params = {"ipv4addr": ip_address, "_return_as_object": 1}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def get_a_record_by_name(self, fqdn):
        """Gets the A record for a FQDN.

        Args:
            fqdn (str): "testdevice1.test"

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "record:a/ZG5zLmJpbmRfYSQuX2RlZmF1bHQudGVzdCx0ZXN0ZGV2aWNlMSwxMC4yMjAuMC4xMDE:testdevice1.test/default",
                "ipv4addr": "10.220.0.101",
                "name": "testdevice1.test",
                "view": "default"
            }
        ]
        """
        url_path = "record:a"
        params = {"name": fqdn, "_return_as_object": 1}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def get_a_record_by_ip(self, ip_address):
        """Gets the A record for a IP Address.

        Args:
            ip_address (str): "10.220.0.101"

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "record:a/ZG5zLmJpbmRfYSQuX2RlZmF1bHQudGVzdCx0ZXN0ZGV2aWNlMSwxMC4yMjAuMC4xMDE:testdevice1.test/default",
                "ipv4addr": "10.220.0.101",
                "name": "testdevice1.test",
                "view": "default"
            }
        ]
        """
        url_path = "record:a"
        params = {"ipv4addr": ip_address, "_return_as_object": 1}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def get_ptr_record_by_name(self, fqdn):
        """Gets the PTR record by FQDN.

        Args:
            fqdn (str): "testdevice1.test"

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "record:ptr/ZG5zLmJpbmRfcHRyJC5fZGVmYXVsdC50ZXN0LjEwMS4wLjIyMC4xMC50ZXN0ZGV2aWNlMS50ZXN0:10.220.0.101.test/default",
                "ptrdname": "testdevice1.test",
                "view": "default"
            }
        ]
        """
        url_path = "record:ptr"
        params = {"ptrdname": fqdn, "_return_as_object": 1}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def get_all_dns_views(self):
        """Gets all dns views.

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "view/ZG5zLnZpZXckLl9kZWZhdWx0:default/true",
                "is_default": true,
                "name": "default"
            },
            {
                "_ref": "view/ZG5zLnZpZXckLjE:default.operations/false",
                "is_default": false,
                "name": "default.operations"
            }
        ]
        """
        url_path = "view"
        params = {"_return_as_object": 1}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def create_a_record(self, fqdn, ip_address):
        """Create an A record for a given FQDN.

        Please note:  This API call with work only for host records that do not have an associated a record.
        If an a record already exists, this will return a 400 error.

        Returns:
            Dict: Dictionary of _ref and name

        Return Response:
        {
            "_ref": "record:a/ZG5zLmJpbmRfYSQuX2RlZmF1bHQudGVzdCx0ZXN0ZGV2aWNlMiwxMC4yMjAuMC4xMDI:testdevice2.test/default",
            "name": "testdevice2.test"
        }
        """
        url_path = "record:a"
        params = {"_return_fields": "name", "_return_as_object": 1}
        payload = {"name": fqdn, "ipv4addr": ip_address}
        response = self._request("POST", url_path, params=params, json=payload)
        logger.info(response.json)
        return response.json().get("result")

    def get_dhcp_lease(self, lease_to_check):  # pylint: disable=no-self-use
        """Gets a DHCP lease for the IP/hostname passed in.

        Args:
            lease_to_check (str): "192.168.0.1" or "testdevice1.test"

        Returns:
            Output of
                get_dhcp_lease_from_ipv4
                    or
                get_dhcp_lease_from_hostname
        """
        ips = len(
            re.findall(
                r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)",
                lease_to_check,
            )
        )
        data = []
        if ips > 0:
            # Data used for demo
            data = [
                {
                    "_ref": "lease/ZG5zLmxlYXNlJDQvMTcyLjE2LjIwMC4xMDEvMC8:172.26.1.250/default1",
                    "binding_state": "ACTIVE",
                    "fingerprint": "Cisco/Linksys SPA series IP Phone",
                    "hardware": "16:55:a4:1b:98:c9",
                }
            ]
            # Delete lines above!!
            # return self.get_dhcp_lease_from_ipv4(lease_to_check)
        else:
            # Data used for demo
            data = [
                {
                    "_ref": "lease/ZG5zLmxlYXNlJC8xOTIuMTY4LjQuMy8wLzE3:192.168.4.3/Company%201",
                    "binding_state": "STATIC",
                    "client_hostname": "test",
                    "hardware": "12:34:56:78:91:23",
                }
            ]
            # Delete lines above!!
            # return self.get_dhcp_lease_from_hostname(lease_to_check)
        return data

    def get_dhcp_lease_from_ipv4(self, ip_address):
        """Gets a DHCP lease for the IP address passed in.

        Args:
            ip_address (str): "192.168.0.1"

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                '_ref': 'lease/ZG5zLmxlYXNlJDQvMTcyLjE2LjIwMC4xMDEvMC8:172.26.1.250/default1',
                'binding_state': 'ACTIVE',
                'fingerprint': 'Cisco/Linksys SPA series IP Phone',
                'hardware': '16:55:a4:1b:98:c9'
            }
        ]
        """
        url_path = "lease"
        params = {
            "address": ip_address,
            "_return_fields": "binding_state,hardware,client_hostname,fingerprint",
            "_return_as_object": 1,
        }
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json()

    def get_dhcp_lease_from_hostname(self, hostname):
        """Gets a DHCP lease for the hostname passed in.

        Args:
            hostnames (str): "testdevice1.test"

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "lease/ZG5zLmxlYXNlJC8xOTIuMTY4LjQuMy8wLzE3:192.168.4.3/Company%201",
                "binding_state": "STATIC",
                "client_hostname": "test",
                "hardware": "12:34:56:78:91:23"
            }
        ]
        """
        url_path = "lease"
        params = {
            "client_hostname": hostname,
            "_return_fields": "binding_state,hardware,client_hostname,fingerprint",
            "_return_as_object": 1,
        }
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json()

    def get_all_subnets(self):
        """Get all Subnets.

        Returns:
            (list) of record dicts

        Return Response:
        [
            {
                "_ref": "network/ZG5zLm5ldHdvcmskMTAuMjIzLjAuMC8yMS8w:10.223.0.0/21/default",
                "network": "10.223.0.0/21",
                "network_view": "default"
            },
            {
                "_ref": "network/ZG5zLm5ldHdvcmskMTAuMjIwLjY0LjAvMjEvMA:10.220.64.0/21/default",
                "network": "10.220.64.0/21",
                "network_view": "default"
            },
        ]
        """
        url_path = "network"
        params = {"_return_as_object": 1}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json)
        return response.json().get("result")

    def _find_network_reference(self, network):
        """Finds the reference for the given network.

        Returns:
            Dict: Dictionary of _ref and name

        Return Response:
        [
            {
                "_ref": "network/ZG5zLm5ldHdvcmskMTAuMjIwLjAuMC8yMi8w:10.220.0.0/22/default",
                "network": "10.220.0.0/22",
                "network_view": "default"
            }
        ]
        """
        url_path = "network"
        params = {"network": network}
        response = self._request("GET", url_path, params=params)
        logger.info(response.json())
        return response.json()

    def find_next_available_ip(self, network):
        """Finds the next available ip address for a given network.

        Returns:
            Dict:

        Return Response:
        {
            "ips": [
                "10.220.0.1"
            ]
        }
        """
        next_ip_avail = ""
        # Find the Network reference id
        try:
            network_ref_id = self._find_network_reference(network)
        except Exception as err:  # pylint: disable=broad-except
            logger.warning("Network reference not found for %s: %s", network, err)
            return next_ip_avail

        if network_ref_id and isinstance(network_ref_id, list):
            network_ref_id = network_ref_id[0].get("_ref")
            url_path = network_ref_id
            params = {"_function": "next_available_ip"}
            payload = {"num": 1}
            response = self._request("POST", url_path, params=params, json=payload)
            logger.info(response.json())
            next_ip_avail = response.json().get("ips")[0]

        return next_ip_avail

    def reserve_fixed_address(self, network, mac_address):
        """Reserves the next available ip address for a given network range.

        Returns:
            Str: The IP Address that was reserved

        Return Response:
            "10.220.0.1"
        """
        # Get the next available IP Address for this network
        ip_address = self.find_next_available_ip(network)
        if ip_address:
            url_path = "fixedaddress"
            params = {"_return_fields": "ipv4addr", "_return_as_object": 1}
            payload = {"ipv4addr": ip_address, "mac": mac_address}
            response = self._request("POST", url_path, params=params, json=payload)
            logger.info(response.json())
            return response.json().get("result").get("ipv4addr")
        return False

    def create_host_record(self, fqdn, ip_address):
        """Create an host record for a given FQDN.

        Please note:  This API call with work only for host records that do not have an associated a record.
        If an a record already exists, this will return a 400 error.

        Returns:
            Dict: Dictionary of _ref and name

        Return Response:
        {

            "_ref": "record:host/ZG5zLmhvc3QkLjEuY29tLmluZm9ibG94Lmhvc3Q:host.infoblox.com/default.test",
            "name": "host.infoblox.com",
        }
        """
        url_path = "record:host"
        params = {"_return_fields": "name", "_return_as_object": 1}
        payload = {"name": fqdn, "ipv4addrs": [{"ipv4addr": ip_address}]}
        response = self._request("POST", url_path, params=params, json=payload)
        logger.info("Infoblox host record created: %s", response.json())
        return response.json().get("result")

    def create_ptr_record(self, fqdn, ip_address):
        """Create an PTR record for a given FQDN.

        Args:
            fqdn (str): Fully Qualified Domain Name
            ip_address (str): Host IP address

        Returns:
            Dict: Dictionary of _ref and name

        Return Response:
        {
            "_ref": "record:ptr/ZG5zLmJpbmRfcHRyJC5fZGVmYXVsdC5hcnBhLmluLWFkZHIuMTAuMjIzLjkuOTYucjQudGVzdA:96.9.223.10.in-addr.arpa/default",
            "ipv4addr": "10.223.9.96",
            "name": "96.9.223.10.in-addr.arpa",
            "ptrdname": "r4.test"
        }
        """
        url_path = "record:ptr"
        params = {"_return_fields": "name,ptrdname,ipv4addr", "_return_as_object": 1}
        reverse_host = str(reversename.from_address(ip_address))[
            0:-1
        ]  # infoblox does not accept the top most domain '.', so we strip it
        payload = {"name": reverse_host, "ptrdname": fqdn, "ipv4addr": ip_address}
        response = self._request("POST", url_path, params=params, json=payload)
        logger.info("Infoblox PTR record created: %s", response.json())
        return response.json().get("result")