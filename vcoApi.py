import requests
import json

class ApiException(Exception):
    pass

class VcoRequestManager(object):

    def __init__(self, hostname, verify_ssl=True):
        self._session = requests.Session()
        self._verify_ssl = verify_ssl
        self._root_url = self._get_root_url(hostname)
        self._portal_url = self._root_url + "/portal/"
        self._livepull_url = self._root_url + "/livepull/liveData/"
        self._seqno = 0
        self.is_operator = None

    def _get_root_url(self, hostname):
        """
        Translate VCO hostname to a root url for API calls
        """
        if hostname.startswith("http"):
            re.sub('http(s)?://', '', hostname)
        proto = "https://"
        return proto + hostname

    def authenticate(self, username, password, is_operator=True):
        """
        Authenticate to API - on success, a cookie is stored in the session
        """
        self.is_operator = is_operator
        path = "/login/operatorLogin" if is_operator else "/login/enterpriseLogin"
        url = self._root_url + path
        data = { "username": username, "password": password }
        headers = { "Content-Type": "application/json" }
        r = self._session.post(url, headers=headers, data=json.dumps(data),
                               allow_redirects=False, verify=self._verify_ssl)

    def call_api(self, method, params):
        """
        Build and submit a request
        Returns method result as a Python dictionary
        """
        self._seqno += 1
        headers = { "Content-Type": "application/json" }
        method = self._clean_method_name(method)
        payload = { "jsonrpc": "2.0",
                    "id": self._seqno,
                    "method": method,
                    "params": params }

        if method in ("liveMode/readLiveData", "liveMode/requestLiveActions", "liveMode/clientExitLiveMode"):
            url = self._livepull_url
        else:
            url = self._portal_url

        r = self._session.post(url, headers=headers,
                               data=json.dumps(payload), verify=self._verify_ssl)

        response_dict = r.json()
        if "error" in response_dict:
            print(response_dict)
            raise ApiException(response_dict["error"]["message"])
        return response_dict["result"]

    def _clean_method_name(self, raw_name):
        """
        Ensure method name is properly formatted prior to initiating request
        """
        return raw_name.strip("/")

