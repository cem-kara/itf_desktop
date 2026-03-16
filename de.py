import os, inspect, database.auth_repository as m
print("Dosya:", m.__file__)
print("Metodlar:", [x for x in dir(m.AuthRepository) if not x.startswith("_")])