# Создание политики

```Bash
vault policy write autotests-policy - <<EOF
path "dotnet/data/config/Development/474/*" {
  capabilities = ["read", "create", "update"]
}
path "dotnet/metadata/config/Development/474/*" {
  capabilities = ["read", "list"]
}
EOF
```

в ответе success


# Создание роли (AppRole)

```Bash
vault write auth/approle/role/autotests \
  bind_secret_id=false \
  token_policies="default,autotests-policy" \
  token_ttl=1h \
  token_max_ttl=24h
```
В ответ тоже просто Success!.


# Получение Role ID (обязательно)
```Bash
vault read auth/approle/role/autotests/role-id
```


# Получение Secret ID (только если bind_secret_id=true)
```Bash
vault write -f auth/approle/role/autotests/secret-id
```
