from pytest_postgresql import factories

postgresql_my_proc = factories.postgresql_proc(
    port=None, unixsocketdir='/var/run')
postgresql_my = factories.postgresql('postgresql_my_proc')