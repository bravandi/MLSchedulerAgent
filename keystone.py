from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client

if __name__ == "__main__":
    auth = v3.Password( auth_url="http://controller:35357/v3",
                        username = 'admin',
                        password = 'ADMIN_PASS',
                        project_name = 'admin',
                        # user_domain_id = 'default',
                        # project_domain_id = 'default',
                        user_domain_name = 'default',
                        project_domain_name = 'default'
                        )

    sess = session.Session(auth=auth, verify='/path/to/ca.cert')

    ks = client.Client(session=sess)

    users = ks.users.list()

    print(users)






