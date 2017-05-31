from marshmallow import Schema, fields, post_load, pre_dump

from connector.fbclient import StorageSchema


class UsersByTypeSchema(Schema):
    default = fields.Int(load_only=True)
    gold = fields.Int(load_only=True)


class ClientSchema(Schema):
    name = fields.Str()
    email = fields.Email()
    users_amount = fields.Int(load_only=True)
    users_by_type = fields.Nested(UsersByTypeSchema)
    storage = fields.Nested(StorageSchema)
    is_integrated = fields.Bool()

    @post_load
    def make_client(self, data):
        return Client(**data)

    @pre_dump
    def dump_client(self, data):
        return {k: v for k, v in data.__dict__.items() if v}


class Client(object):
    name = None
    email = None
    users_amount = None
    is_integrated = True
    storage = None
    reseller = None
    users_by_type = None

    def __init__(self, reseller=None, name=None, email=None, is_integrated=True, users_amount=None,
                 storage=None, users_by_type=None, postal_code=None):
        self.reseller = reseller
        self.name = name
        self.email = email
        self.is_integrated = is_integrated
        self.users_amount = users_amount
        self.storage = storage
        self.users_by_type = users_by_type
        self.postal_code = postal_code

    def api(self):
        return self.reseller.api().resellers(self.reseller.name)

    def __repr__(self):
        return '<Client(name={})>'.format(self.name)

    @property
    def _dump(self):
        return ClientSchema().dump(self).data

    def create(self):
        api = self.api()
        if not self.storage:
            self.storage = {'limit': 10}
        result = api.clients.post(self._dump)
        return result

    def update(self):
        return self.api().clients(self.name).put(self._dump)

    def refresh(self):
        api = self.api()
        result = api.clients(self.name).get()
        c = ClientSchema().load(result).data
        self.__init__(self.reseller, name=c.name, email=c.email, is_integrated=c.is_integrated,
                      users_amount=c.users_amount, storage=c.storage, users_by_type=c.users_by_type)

    def delete(self):
        api = self.api()
        result = api.clients(self.name).delete()
        return result
