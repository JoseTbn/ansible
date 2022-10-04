#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: my_test

short_description: Modify  user

version_added: "2.4"


description:
    - Create, delete, and update  user.

options:
    tenant:
        description:
            - The tenant ID.
        type: str
        required: True
    state:
        description:
            - State of the ad user. Use C(present) to create or update an ad user and C(absent) to delete an ad user.
        type: str
        default: present
        choices:
            - absent
            - present
    object_id:
        description:
            - The object id for the user.
            - Updates or deletes the user who has this object ID.
            - Mutually exclusive with I(user_principal_name), I(attribute_name), and I(odata_filter).
        type: str
    account_enabled:
        description:
            - A boolean determing whether or not the user account is enabled.
            - Used when either creating or updating a user account.
        type: bool
    display_name:
        description:
            - The display name of the user.
            - Used when either creating or updating a user account.
        type: str
    given_name:
        description:
            - The given name for the user.
            - Used when either creating or updating a user account.
        type: str
    surname:
        description:
            - The surname for the user.
            - Used when either creating or updating a user account.
        type: str
    immutable_id:
        description:
            - The immutable_id of the user.
            - Used when either creating or updating a user account.
        type: str
    mail:
        description:
            - The primary email address of the user.
            - Used when either creating or updating a user account.
        type: str
    mail_nickname:
        description:
            - The mail alias for the user.
            - Used when either creating or updating a user account.
        type: str
    password_profile:
        description:
            - The password for the user.
            - Used when either creating or updating a user account.
        type: str
    usage_location:
        description:
            - A two letter country code, ISO standard 3166.
            - Required for a user that will be assigned licenses due to legal requirement to check for availability of services in countries.
            - Used when either creating or updating a user account.
        type: str
    user_type:
        description:
            - A string value that can be used to classify user types in your directory, such as user and Guest.
            - Used when either creating or updating a user account.
        type: str
    user_principal_name:
        description:
            - The principal name of the user.
            - Creates, updates, or deletes the user who has this principal name.
            - Mutually exclusive with I(object_id), I(attribute_name), and I(odata_filter).
        type: str
    attribute_name:
        description:
            - The name of an attribute that you want to match to attribute_value.
            - If attribute_name is not a collection type it will update or delete the user where attribute_name is equal to attribute_value.
            - If attribute_name is a collection type it will update or delete the user where attribute_value is in attribute_name.
            - Mutually exclusive with I(object_id), I(user_principal_name), and I(odata_filter).
            - Required together with I(attribute_value).
        type: str
    attribute_value:
        description:
            - The value to match attribute_name to.
            - If attribute_name is not a collection type it will update or delete the user where attribute_name is equal to attribute_value.
            - If attribute_name is a collection type it will update or delete the user where attribute_value is in attribute_name.
            - Required together with I(attribute_name).
        type: str
    odata_filter:
        description:
            - Filter that can be used to specify a user to update or delete.
            - Mutually exclusive with I(object_id), I(attribute_name), and I(user_principal_name).
        type: str

extends_documentation_fragment:
    - azure

author:
    - Your Name (@yourhandle)
'''

EXAMPLES = '''
# Create a user account
- name: Create a user account
  my_test_module:
    user_principal_name: "{{ user_id }}"
    tenant: "{{ tenant_id }}"
    state: "present"
    account_enabled: "True"
    display_name: "Test_{{ user_principal_name }}_Display_Name"
    password_profile: "password"
    mail_nickname: "Test_{{ user_principal_name }}_mail_nickname"
    immutable_id: "{{ object_id }}"
    given_name: "First"
    surname: "Last"
    user_type: "user"
    usage_location: "US"
    mail: "{{ user_principal_name }}@M365x91503845.OnMicrosoft.com"


'''

RETURN = '''
display_name:
    description:
        - The display name of the user.
    returned: always
    type: str
    sample: John Smith
user_principal_name:
    description:
        - The principal name of the user.
    returned: always
    type: str
    sample: jsmith@contoso.com
mail_nickname:
    description:
        - The mail alias for the user.
    returned: always
    type: str
    sample: jsmith
mail:
    description:
        - The primary email address of the user.
    returned: always
    type: str
    sample: John.Smith@contoso.com
account_enabled:
    description:
        - Whether the account is enabled.
    returned: always
    type: bool
    sample: False
user_type:
    description:
        - A string value that can be used to classify user types in your directory.
    returned: always
    type: str
    sample: user
'''

import json
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url, url_argument_spec
from ansible.module_utils.common.dict_transformations import snake_dict_to_camel_dict

try:
    from requests_oauthlib import OAuth2Session
    from oauthlib.oauth2 import BackendApplicationClient

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

__metaclass__ = type


OBJECT_TYPE_MAP = {
    '#microsoft.graph.user': "graph.microsoft.com/v1.0/users",
    '#microsoft.graph.servicePrincipal': "graph.microsoft.com/v1.0/servicePrincipals"
}


class AzureActiveDirectoryInterface(object):
    ms_graph_api_url = "https://graph.microsoft.com"

    def __init__(self, module):
        self._module = module
        token = self._get_token()
        self.headers = {"Content-Type": "application/json", "Authorization": "Bearer %s" % token.get("access_token")}

    def _send_request(self, url, data=None, headers=None, method="GET", api_version="v1.0"):
        if data is not None:
            data = json.dumps(data, sort_keys=True)
        if not headers:
            headers = []

        full_url = "{ms_graph_api_url}/{version}/{path}".format(ms_graph_api_url=self.ms_graph_api_url,
                                                                version=api_version, path=url)
        resp, info = fetch_url(self._module, full_url, data=data, headers=headers, method=method)
        status_code = info["status"]
        if status_code == 404:
            return None
        elif status_code == 400:
            self._module.fail_json(msg=json.loads(info["body"]).get("error"))
        elif status_code == 401:
            self._module.fail_json(msg="Unauthorized to perform action '%s' on '%s'" % (method, full_url))
        elif status_code == 403:
            self._module.fail_json(msg="Permission Denied")
        elif 200 <= status_code < 299:
            body = resp.read()
            if body:
                return self._module.from_json(body)
            return
        self._module.fail_json(failed=True, msg="Microsoft Graph API answered with HTTP %d" % status_code)

    def _get_token(self):
        client_id = self._module.params.get("client_id")
        client_secret = self._module.params.get("client_secret")
        scope = ["https://graph.microsoft.com/.default"]
        token_url = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token".format(
            tenant_id=self._module.params.get("tenant_id"))

        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(token_url=token_url,
                                  client_id=client_id,
                                  client_secret=client_secret,
                                  scope=scope)
        return token

    def create_user(self, user):
        url = "/users"
        users = user.pop("users")
        if user.get("users") is not None:
            users = user.pop("users")
            user["users@odata.bind"] = users
        user["users@odata.bind"] = users
        response = self._send_request(url, data=user, headers=self.headers, method="POST")
        return response

    def get_user(self, name):
        url = "/users?$filter=startswith(displayName,'%s')" % name
        response = self._send_request(url, headers=self.headers, method="GET")
        users = response.get("value")
        if len(users) > 1:
            self.module.fail_json(msg="Expected 1 user matching query, found %d" % len(users))
        elif len(users) == 0:
            return None
        return users[0]

    def update_user(self, user_id, user):
        url = "/users/{user_id}".format(user_id=user_id)
        self._send_request(url, data=user, headers=self.headers, method="PATCH")

    def delete_user(self, user_id):
        url = "/users/{user_id}".format(user_id=user_id)
        response = self._send_request(url, headers=self.headers, method="DELETE")
        return response

    def converge_users(self, user_id, current, new, enforce):
        changed = False
        for user in new:
            if user not in current:
                changed = True
                self.add_user(user_id, user)
        if enforce:
            for user in current:
                if user not in new:
                    changed = True
                    self.remove_user(user_id, user)
        return changed

    def get_users(self, user_id):
        url = "/users/{user_id}/users".format(user_id=user_id)
        response = self._send_request(url, headers=self.headers, method="GET",
                                      api_version="beta")
        return response.get("value")

    def get_users_id(self, user_id):
        users = self.get_users(user_id)
        users_id = []
        for user in users:
            obj_type = user.get('@odata.type')
            obj_uri = OBJECT_TYPE_MAP.get(obj_type)
            user_url = "https://{uri}/{obj_id}".format(uri=obj_uri, obj_id=user.get('id'))
            users_id.append(user_url)
        return users_id

    def add_user(self, user_id, user):
        url = "/users/{user_id}/users/$ref".format(user_id=user_id)
        data = {"@odata.id": user}
        response = self._send_request(url, data=data, headers=self.headers, method="POST")
        return response

    def remove_user(self, user_id, user):
        user_id = user.split("/")[-1]
        url = "/users/{user_id}/users/{user_id}/$ref".format(user_id=user_id, user_id=user_id)
        response = self._send_request(url, headers=self.headers, method="DELETE")
        return response

    def converge_users(self, user_id, current, new, enforce):
        changed = False
        for user in new:
            if user not in current:
                changed = True
                self.add_user(user_id, user)
        if enforce:
            for user in current:
                if user not in new:
                    changed = True
                    self.remove_user(user_id, user)
        return changed

    def get_users(self, user_id):
        url = "/users/{user_id}/users".format(user_id=user_id)
        response = self._send_request(url, headers=self.headers, method="GET")
        return response.get("value")

    def get_users_id(self, user_id):
        users = self.get_users(user_id)
        # not users but directoryObjects because users can also be users
        users_id = ["https://graph.microsoft.com/v1.0/directoryObjects/" + user.get('id') for user in users]
        return users_id

    def add_user(self, user_id, user):
        url = "/users/{user_id}/users/$ref".format(user_id=user_id)
        data = {"@odata.id": user}
        response = self._send_request(url, data=data, headers=self.headers, method="POST")
        return response

    def remove_user(self, user_id, user):
        user_id = user.split("/")[-1]
        url = "/users/{user_id}/users/{user_id}/$ref".format(user_id=user_id, user_id=user_id)
        response = self._send_request(url, headers=self.headers, method="DELETE")
        return response


def setup_module_object():
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=true,
    )
    return module


def build_user_from_params(params):
    user_PARAMS = ["display_name", "description", "user_types", "mail_enabled",
                    "mail_nickname", "security_enabled", "users", "users"]
    user = {}
    for param in user_PARAMS:
        user[param] = params[param]
    if user["users"] == []:
        user.pop("users")
    return snake_dict_to_camel_dict(user)


argument_spec = url_argument_spec()
argument_spec.update(
    state=dict(type='str', required=True, choices=["present", "absent"]),
    client_id=dict(type='str', required=True),
    client_secret=dict(type='str', required=True, no_log=True),
    tenant_id=dict(type='str', required=True),
    display_name=dict(type='str', required=True, aliases=["name"]),
    description=dict(type='str', required=True),
    user_types=dict(type='list', elements='str', default=[], choices=["Unified", "Dynamicusership"]),
    mail_enabled=dict(type='bool', default=False),
    mail_nickname=dict(type='str', required=True),
    security_enabled=dict(type='bool', default=True),
    users=dict(type='list', elements='str', required=True),
    enforce_users=dict(type='bool', required=False, default=False),
    users=dict(type='list', elements='str', default=[]),
    enforce_users=dict(type='bool', required=False, default=False)
)


def compare_users(current, new):
    current_keys = current.keys()
    new_keys = new.keys()
    current_keys_to_remove = [item for item in current_keys if item not in new_keys]
    new_keys_to_remove = ["users", "users"]
    # Remove the unknown keys from remote user
    for item in current_keys_to_remove:
        if item in current:
            current.pop(item)
    # Remove the keys that are not returned by Get method from new user
    for item in new_keys_to_remove:
        if item in new:
            new.pop(item)
    if current != new:
        return dict(before=current, after=new)


def main():
    module = setup_module_object()

    if not HAS_DEPS:
        module.fail_json(msg="module requires requests and requests-oauthlib")

    state = module.params['state']
    name = module.params['display_name']
    users = module.params['users']
    enforce_users = module.params['enforce_users']

    users = module.params['users']
    enforce_users = module.params['enforce_users']

    azuread_iface = AzureActiveDirectoryInterface(module)
    user = azuread_iface.get_user(name)

    changed = False
    diff = None
    if state == 'present':
        new_user = build_user_from_params(module.params)
        if user is None:
            user = azuread_iface.create_user(new_user)
            changed = True
        else:

            diff = compare_users(user.copy(), new_user.copy())
            if diff is not None:
                azuread_iface.update_user(user.get("id"), diff["after"])
                changed = True

            current_users = azuread_iface.get_users_id(user.get("id"))
            if current_users != users:
                users_changed = azuread_iface.converge_users(user.get("id"), current_users, users, enforce_users)
                if users_changed:
                    changed = True
# print users_changed
            current_users = azuread_iface.get_users_id(user.get("id"))
            if current_users != users:
                users_changed = azuread_iface.converge_users(user.get("id"), current_users, users,
                                                                 enforce_users)
                if users_changed:
                    changed = True

        user = azuread_iface.get_user(name)
        user["users"] = azuread_iface.get_users(user.get("id"))
        user["users"] = azuread_iface.get_users(user.get("id"))
        module.exit_json(changed=changed, user=user, diff=diff)
    elif state == 'absent':
        if user is None:
            module.exit_json(failed=False, changed=False, message="No user found")
        azuread_iface.delete_user(user.get("id"))
        module.exit_json(failed=False, changed=True, message="user deleted")


if __name__ == '__main__':
    main()