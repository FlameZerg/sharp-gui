# Dependency Baseline Record

## Commands and Results

### npm view

Command:

```bash
npm view @sparkjsdev/spark version peerDependencies --json
```

Result:

```json
{
  "version": "2.0.0",
  "peerDependencies": {
    "three": "^0.180.0"
  }
}
```

### npm ls

Command:

```bash
npm ls @sparkjsdev/spark three --depth=0
```

Result:

```text
frontend@0.0.0
├── @sparkjsdev/spark@2.0.0
└── three@0.180.0
```

### package-lock resolution

Command used:

```bash
grep -n "node_modules/@sparkjsdev/spark\|resolved" frontend/package-lock.json
```

Validated entry:

- resolved: https://registry.npmjs.org/@sparkjsdev/spark/-/spark-2.0.0.tgz

### clean install

Command:

```bash
rm -rf node_modules && npm ci
```

Result:

- Completed successfully.
- Confirms lockfile is reproducible in clean environment.

## Conclusion

- Spark resolved to npm stable 2.0.0.
- three peer dependency constraint is satisfied.
- No git dependency source remains in frontend lockfile for Spark.
