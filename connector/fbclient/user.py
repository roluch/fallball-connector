from marshmallow import Schema, fields, post_load, pre_dump

from connector.fbclient import StorageSchema


class UserSchema(Schema):
    user_id = fields.UUID()
    email = fields.Email()
    password = fields.Str()
    storage = fields.Nested(StorageSchema)
    admin = fields.Bool()
    superadmin = fields.Bool()
    profile_type = fields.Str()

    @post_load
    def make_user(self, data):
        return User(**data)

    @pre_dump
    def dump_user(self, data):
        return {k: v for k, v in data.__dict__.items() if v}


class User(object):
    user_id = None
    email = None
    password = None
    admin = None
    storage = None
    profile_type = None

    def __init__(self, client=None, user_id=None, email=None, password=None, admin=None,
                 superadmin=None, storage=None, profile_type=None):
        self.client = client
        self.user_id = user_id
        self.email = email
        self.password = password
        self.admin = admin
        self.superadmin = superadmin
        self.storage = storage
        self.profile_type = profile_type

    def api(self):
        return self.client.api().clients(self.client.name)

    def __repr__(self):
        return '<User(email={})>'.format(self.email)

    @property
    def _dump(self):
        return UserSchema().dump(self).data

    def create(self):
        api = self.api()
        if not self.storage:
            self.storage = {'limit': 2}
        if not self.password:
            self.password = 'password'
        result = api.users.post(self._dump)
        if 'user_id' in result:
            self.user_id = result['user_id']
        return result

    def update(self):
        self.api().users(self.user_id).put(self._dump)

    def refresh(self):
        api = self.api()
        result = api.users(self.user_id).get()
        u = UserSchema().load(result).data
        self.__init__(self.client, user_id=u.user_id, email=u.email, password=u.password,
                      admin=u.admin, superadmin=u.superadmin, storage=u.storage,
                      profile_type=u.profile_type)

    def delete(self):
        api = self.api()
        result = api.users(self.user_id).delete()
        return result

    def token(self):
        api = self.api()
        result = api.users(self.user_id).token.get()
        return result

    def login_link(self):
        api = self.api()
        result = api.users(self.user_id).link.get()
        return result
