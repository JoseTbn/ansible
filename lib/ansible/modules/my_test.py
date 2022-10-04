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
            - A string value that can be used to classify user types in your directory, such as Member and Guest.
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
    user_type: "Member"
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
    sample: Member
'''

import time
import json
import re
from unittest import result
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url,url_argument_spec
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

class MicrosoftOficce365(object):
    ms_graph_api_url = "https://graph.microsoft.com"
    
    def __init__(self, module):
        self._module = module
        token = self._get_token()
        self.headers = {"Content-Type": "application/json", "Authorization": "Bearer %s" % token.get("access_token")}

    def _send_request(self, url, data=None, headers=None, method="GET", api_version="v1.0"):
        if data is not None:
            data = json.dumps(data, sort_keys=True)  # Json.dumps to transform the data to dict
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
    

    def get_user(self ):
        url = "/users/{user_principal_name}".format(user_principal_name=self._module.params.get("user_principal_name"))

        if self._module.params.get("odata_filter"):
            url = "/users?$filter={odata_filter}".format(odata_filter=self._module.params.get("odata_filter"))
        
        return self._send_request(url, headers=self.headers, method="GET")
    
    def get_userAnotherWay(self ):
        url = "/users/{user_principal_name}".format(user_principal_name=self._module.params.get("user_principal_name"))
        return self._send_request(url, headers=self.headers, method="GET") 

    
    def create_user(self):
        url = "/users"
        data = {
            "accountEnabled": self._module.params.get("account_enabled"),
            "displayName": self._module.params.get("display_name"),
            "mailNickname": self._module.params.get("mail_nickname"),
            "passwordProfile": {
                "password": self._module.params.get("password_profile"),
                "forceChangePasswordNextSignIn": self._module.params.get("force_change_password_next_sign_in")
            },
            "userPrincipalName": self._module.params.get("user_principal_name"),
            "immutableId": self._module.params.get("immutable_id"),
            "givenName": self._module.params.get("given_name"),
            "surname": self._module.params.get("surname"),
            "userType": self._module.params.get("user_type"),
            "usageLocation": self._module.params.get("usage_location"),
            "mail": self._module.params.get("mail")
        }
        return self._send_request(url, data=data, headers=self.headers, method="POST")
    
    
    
    
    
    
    
    def create_user(self, user):         
        ad_user = None         
        url = "/users"         
        data = {             "accountEnabled": user.get("account_enabled"),             "displayName": "Test_{{ user_principal_name }}_Display_Name",             "mailNickname": "Test_{{ user_principal_name }}_mail_nickname",             "userPrincipalName": "Test_{{ user_principal_name }}_mail_nickname",             "jobTitle": "Test_{{ user_principal_name }}_job_title",             "department":   "Test_{{ user_principal_name }}_department",             "passwordProfile": {             "forceChangePasswordNextSignIn": True,             "password": "password"         }         }         
        response = self._send_request(url, data=data, headers=self.headers, method="POST")         
        if response.status_code == 201:             


            ad_user = response.json()         
        return ad_user     
    
    
    def update_user(self):
        url = "/users/{user_principal_name}".format(user_principal_name=self._module.params.get("user_principal_name"))
        data = {
            "accountEnabled": self._module.params.get("account_enabled"),
            "displayName": self._module.params.get("display_name"),
            "mailNickname": self._module.params.get("mail_nickname"),
            "passwordProfile": {
                "password": self._module.params.get("password_profile"),
                "forceChangePasswordNextSignIn": self._module.params.get("force_change_password_next_sign_in")
            },
            "userPrincipalName": self._module.params.get("user_principal_name"),
            "immutableId": self._module.params.get("immutable_id"),
            "givenName": self._module.params.get("given_name"),
            "surname": self._module.params.get("surname"),
            "userType": self._module.params.get("user_type"),
            "usageLocation": self._module.params.get("usage_location"),
            "mail": self._module.params.get("mail")
        }
        return self._send_request(url, data=data, headers=self.headers, method="PATCH")
    
    def delete_user(self):
        url = "/users/{user_principal_name}".format(user_principal_name=self._module.params.get("user_principal_name"))
        return self._send_request(url, headers=self.headers, method="DELETE")
    
    
    def get_group(self):
        url = "/groups/{group_id}".format(group_id=self._module.params.get("group_id"))
        return self._send_request(url, headers=self.headers, method="GET")
    
    def create_group(self):
        url = "/groups"
        data = {
            "description": self._module.params.get("description"),
            "displayName": self._module.params.get("display_name"),
            "groupTypes": self._module.params.get("group_types"),
            "mailEnabled": self._module.params.get("mail_enabled"),
            "mailNickname": self._module.params.get("mail_nickname"),
            "securityEnabled": self._module.params.get("security_enabled"),
            "visibility": self._module.params.get("visibility")
        }
        return self._send_request(url, data=data, headers=self.headers, method="POST")
    
    def update_group(self):
        url = "/groups/{group_id}".format(group_id=self._module.params.get("group_id"))
        data = {
            "description": self._module.params.get("description"),
            "displayName": self._module.params.get("display_name"),
            "groupTypes": self._module.params.get("group_types"),
            "mailEnabled": self._module.params.get("mail_enabled"),
            "mailNickname": self._module.params.get("mail_nickname"),
            "securityEnabled": self._module.params.get("security_enabled"),
            "visibility": self._module.params.get("visibility")
        }
        return self._send_request(url, data=data, headers=self.headers, method="PATCH")
    
    def delete_group(self):
        url = "/groups/{group_id}".format(group_id=self._module.params.get("group_id"))
        return self._send_request(url, headers=self.headers, method="DELETE")
    
    



    


    # def create_user(self, user):
    #     ad_user = None

    #     url = "/users"
        
    #     data = {
    #         "accountEnabled": user.get("account_enabled"),
    #         "displayName": "Test_{{ user_principal_name }}_Display_Name",
    #         "mailNickname": "Test_{{ user_principal_name }}_mail_nickname",
    #         "userPrincipalName": "Test_{{ user_principal_name }}_mail_nickname",
    #         "jobTitle": "Test_{{ user_principal_name }}_job_title",
    #         "department":   "Test_{{ user_principal_name }}_department",
    #         "passwordProfile": {
    #         "forceChangePasswordNextSignIn": True,
    #         "password": "password"
    # }
    #     }
        
    #     response = self._send_request(url, data=data, headers=self.headers, method="POST")
    #     return response


# If user exist return user object else return None     
# 
# 
# def get_user(self, user_principal_name):      
# ad_user = None         
# url = "/users/{user_principal_name}".format(user_principal_name=user_principal_name)         
# response = self._send_request(url, headers=self.headers, method="GET")        
# if response.status_code == 200:             
# ad_user = response.json()         
# return ad_user     
# 
# 
# def create_user(self, user):         
# ad_user = None         
# url = "/users"         
# data = {             "accountEnabled": user.get("account_enabled"),             "displayName": "Test_{{ user_principal_name }}_Display_Name",             "mailNickname": "Test_{{ user_principal_name }}_mail_nickname",             "userPrincipalName": "Test_{{ user_principal_name }}_mail_nickname",             "jobTitle": "Test_{{ user_principal_name }}_job_title",             "department":   "Test_{{ user_principal_name }}_department",             "passwordProfile": {             "forceChangePasswordNextSignIn": True,             "password": "password"         }         }         
# response = self._send_request(url, data=data, headers=self.headers, method="POST")         
# if response.status_code == 201:             


# ad_user = response.json()         
# return ad_user     
# 
# 
# def update_user(self, user):         
# ad_user = None         
# url = "/users/{user_principal_name}".format(user_principal_name=user.get("user_principal_name"))         
# data = {             "accountEnabled": user.get("account_enabled"),             "displayName": "Test_{{ user_principal_name }}_Display_Name",             "mailNickname": "Test_{{ user_principal_name }}_mail_nickname",             "userPrincipalName": "Test_{{ user_principal_name }}_mail_nickname",             "jobTitle": "Test_{{ user_principal_name }}_job_title",             "department":   "Test_{{ user_principal_name }}_department",             "passwordProfile": {             "forceChangePasswordNextSignIn": True,             "password": "password"         }         }         
# response = self._send_request(url, data=data, headers=self.headers, method="PATCH")         
# if response.status_code == 200:             
# ad_user = response.json()         
# return ad_user     
# def delete_user(self, user_principal_name):         
# ad_user = None         
# url = "/users/{user_principal_name}".format(user_principal_name=user_principal_name)         
# response = self._send_request(url, headers=self.headers, method="DELETE")         
# if response.status_code == 204:             
# ad_user = response.json()         
# return ad_user     
# 
# def get_group(self, group_id):         ad_group = None         url = "/groups/{group_id}".format(group_id=group_id)         response = self._send_request(url, headers=self.headers, method="GET")         if response.status_code == 200:             ad_group = response.json()         return ad_group     def create_group(self, group):         ad_group = None         url = "/groups"         data = {             "description": group.get("description"),             "displayName": group.get("display_name"),             "groupTypes": group.get("group_types"),             "mailEnabled": group.get("mail_enabled"),             "mailNickname": group.get("mail_nickname"),             "securityEnabled": group.get("security_enabled"),             "visibility": group.get("visibility")         }         response = self._send_request(url, data=data, headers=self.headers, method="POST")         if response.status_code == 201:             ad_group = response.json()         return ad_group     def update_group(self, group):         ad_group = None         url = "/groups/{group_id}".format(group_id=group.get("group_id"))         data = {             "description": group.get("description"),             "displayName": group.get("display_name"),             "groupTypes": group.get("group_types"),             "mailEnabled": group.get("mail_enabled"),             "mailNickname": group.get("mail_nickname"),             "securityEnabled": group.get("security_enabled"),             "visibility": group.get("visibility")         }         response = self._send_request(url, data=data, headers=self.headers, method="PATCH")         if response.status_code == 200:             ad_group = response.json()         return ad_group     def delete_group(self, group_id):         ad_group = None         url = "/groups/{group_id}".format(group_id=group_id)         response = self._send_request(url, headers=self.headers, method="DELETE")         if response.status_code == 204:             ad_group = response.json()         return ad_group    def get_group_members(self, group_id):         ad_group_members = None         url = "/groups/{group_id}/members".format(group_id=group_id)         response = self._send_request(url, headers=self.headers, method="GET")         if response.status_code == 200:             ad_group_members = response.json()         return ad_group_members     def add_group_member(self, group_id, member_id):         ad_group_member = None         url = "/groups/{group_id}/members/$ref".format(group_id=group_id)         data = {             "@odata.id": "https://graph.microsoft.com/v1.0/directoryObjects/{member_id}".format(member_id=member_id)         }         response = self._send_request(url, data=data, headers=self.headers, method="POST")         if response.status_code == 204:             ad_group_member = response.json()         return ad_group_member     def remove_group_member(self, group_id, member_id):         ad_group_member = None         url = "/groups/{group_id}/members/{member_id}/$ref".format(group_id=group_id, member_id=member_id)         response = self._send_request(url, headers=self.headers, method="DELETE")         if response.status_code == 204:             ad_group_member = response.json()         return ad_group_member     def get_group_owners(self, group_id):         ad_group_owners = None         url = "/groups/{group_id}/owners".format(group_id=group_id)         response = self._send_request(url, headers=self.headers, method="GET")         if response.status_code == 200:             ad_group_owners = response.json()         return ad_group_owners     def add_group_owner(self, group_id, owner_id):         ad_group_owner = None         url = "/groups/{group_id}/owners/$ref".format(group_id=group_id)         data = {             "@odata.id": "https://graph.microsoft.com/v1.0/directoryObjects/{owner_id}".format(owner_id=owner_id)         }         response = self._send_request(url, data=data, headers=self.headers, method="POST")         if response.status_code == 204:             ad_group_owner = response.json()         return ad_group_owner     def remove_group_owner(self, group_id, owner_id):         ad_group_owner = None         url = "/groups/{group_id}/owners/{    # def update_user(self, user):    # def update_user(self, user):





argument_spec = url_argument_spec()
argument_spec.update(
    user_principal_name=dict(type='str'),
    state=dict(type='str', default='present', choices=['present', 'absent']),
        object_id=dict(type='str'),
        attribute_name=dict(type='str'),
        attribute_value=dict(type='str'),
        odata_filter=dict(type='str'),
        account_enabled=dict(type='bool'),
        display_name=dict(type='str'),
        password_profile=dict(type='str', no_log=True),
        mail_nickname=dict(type='str'),
        mmutable_id=dict(type='str'),
        usage_location=dict(type='str'),
        given_name=dict(type='str'),
        urname=dict(type='str'),
        user_type=dict(type='str'),
        mail=dict(type='str'),
        tenant=dict(type='str', required=True),
)





    # mutually_exclusive = [['odata_filter', 'attribute_name', 'object_id', 'user_principal_name']]
    # required_together = [['attribute_name', 'attribute_value']]
    # required_one_of = [['odata_filter', 'attribute_name', 'object_id', 'user_principal_name']]



#     # seed the result dict in the object
#     # we primarily care about changed and state
#     # change is if this module effectively modified the target
#     # state will include any data that you want your module to pass back
#     # for consumption, for example, in a subsequent task
#     result = dict(
#         changed=False,
#         original_message='',
#         message=''
#     )






    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
module = AnsibleModule(
    argument_spec=module_args,
    supports_check_mode=False ,
    mutually_exclusive=mutually_exclusive,
    required_together=required_together,
    required_one_of=required_one_of,
)

#     # if the user is working with this module in only check mode we do not
#     # want to make any changes to the environment, just return the current
#     # state with no modifications
      # check_mode ("dry run") allows a playbook to be executed or just verifies if changes are required
if module.check_mode:
        module.exit_json(**result)

#     # manipulate or modify the state as needed (this is going to be the
#     # part where your module will do what it needs to do)
#     result['original_message'] = module.params['name']
#     result['message'] = 'goodbye'

        result[]

#     # during the execution of the module, if there is an exception or a
#     # conditional state that effectively causes a failure, run
#     # AnsibleModule.fail_json() to pass in the message and the result
#     if module.params['name'] == 'fail me':
#         module.fail_json(msg='You requested this to fail', **result)

#     # in the event of a successful module execution, you will want to
#     # simple AnsibleModule.exit_json(), passing the key/value results
#     module.exit_json(**result)

def main():
    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    module = setup_module_object()
    
    if not HAS_DEPS:
        module.fail_json(msg="module requires requests and requests-oauthlib")
    
        argument_spec = url_argument_spec()
        argument_spec.update(
        user_principal_name=dict(type='str'),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        object_id=dict(type='str'),
        attribute_name=dict(type='str'),
        attribute_value=dict(type='str'),
        odata_filter=dict(type='str'),
        account_enabled=dict(type='bool'),
        display_name=dict(type='str'),
        password_profile=dict(type='str', no_log=True),
        mail_nickname=dict(type='str'),
        mmutable_id=dict(type='str'),
        usage_location=dict(type='str'),
        given_name=dict(type='str'),
        urname=dict(type='str'),
        user_type=dict(type='str'),
        mail=dict(type='str'),
        tenant=dict(type='str', required=True),
)

    
    # if module.params['state'] == 'present': module.exit_json(changed=False, user=user)    else: module.exit_json(changed=False, user=None) 
    
    
    mail_nickname = module.params['mail_nickname'] 
    display_name = module.params['display_name']
    state = module.params['state']
    user_principal_name = module.params['user_principal_name']
    object_id = module.params['object_id']
    
    
    
    
            
            
    
#     # use whatever logic you need to determine whether or not this module
#     # made any modifications to your target
#     if module.params['new']:
#         result['changed'] = True



def get_user(module, graphrbac_client, user_principal_name):
    try:
        user = graphrbac_client.users.get(user_principal_name)
        return user
    except GraphErrorException as e:
        if e.code == "Request_ResourceNotFound":
            return None
        else:
            module.fail_json(msg="Error getting user {0} - {1}".format(user_principal_name, str(e)))
                
    if state == 'present': 
        user = get_user(module)
        if user is None:
            user = create_user(module)
            module.exit_json(changed=True, user=user)
        else:
            module.exit_json(changed=False, user=user)
    
    if state == 'absent':
        user = get_user(module)
        if user is None:
            module.exit_json(changed=False, user=None)
        else:
            delete_user(module)
            module.exit_json(changed=True, user=None)
            
            

    
            
            
            

if __name__ == '__main__':
    main()