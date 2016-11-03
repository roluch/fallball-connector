from marshmallow import Schema, fields, post_load, pre_dump

from connector.fbclient import StorageSchema


class ClientSchema(Schema):
    name = fields.Str()
    users_amount = fields.Int(load_only=True)
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
    users_amount = None
    is_integrated = True
    storage = None
    reseller = None

    def __init__(self, reseller=None, name=None, is_integrated=True, users_amount=None,
                 storage=None):
        self.reseller = reseller
        self.name = name
        self.is_integrated = is_integrated
        self.users_amount = users_amount
        self.storage = storage

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
        self.__init__(self.reseller, name=c.name, is_integrated=c.is_integrated,
                      users_amount=c.users_amount, storage=c.storage)

    def delete(self):
        api = self.api()
        result = api.clients(self.name).delete()
        return result
