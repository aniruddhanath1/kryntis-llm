# Environment File Encryption

The `.env-*.enc` files in this repository are encrypted with
[Fernet](https://cryptography.io/en/latest/fernet/) symmetric encryption
(AES-128-CBC + HMAC-SHA256). Plaintext `.env-*` files are **never committed**.

---

## Prerequisites

Install the `cryptography` package once on the machine doing the
encrypting or decrypting:

```bash
# macOS / Linux
pip install cryptography

# Windows (PowerShell)
pip install cryptography
```

---

## Encrypt — add or rotate env files

Run this whenever you change a plaintext `.env-*` file and need to update
the encrypted version committed to the repo.

```python
# encrypt_envs.py
from cryptography.fernet import Fernet
from pathlib import Path

KEY_PATH = Path(".env-encryption.key")   # NEVER commit this file

# --- Generate key (first time only) ---
# Uncomment the next two lines on first run, then comment them out again.
# key = Fernet.generate_key()
# KEY_PATH.write_bytes(key)

key = KEY_PATH.read_bytes()
fernet = Fernet(key)

env_files = [".env-develop", ".env-qa", ".env-stage", ".env-prod"]

for name in env_files:
    src = Path(name)
    if not src.exists():
        print(f"  SKIP  {name} (not found)")
        continue
    token = fernet.encrypt(src.read_bytes())
    enc_path = Path(name + ".enc")
    enc_path.write_bytes(token)
    print(f"  OK    {name}  →  {enc_path.name}")
```

```bash
python encrypt_envs.py
# then commit the updated .enc files:
git add .env-*.enc
git commit -m "chore: update encrypted env files"
```

---

## Decrypt — restore env files on a new machine

```python
# decrypt_envs.py
from cryptography.fernet import Fernet
from pathlib import Path

KEY_PATH = Path(".env-encryption.key")   # obtain from your secrets store

key = KEY_PATH.read_bytes()
fernet = Fernet(key)

for enc_file in sorted(Path(".").glob(".env-*.enc")):
    plain_name = enc_file.name[:-4]      # strips trailing .enc
    out = Path(plain_name)
    out.write_bytes(fernet.decrypt(enc_file.read_bytes()))
    print(f"  Decrypted  {enc_file.name}  →  {plain_name}")
```

```bash
python decrypt_envs.py
# files are written next to the .enc files in the current directory
```

---

## Key management rules

| Rule | Detail |
|---|---|
| **Never commit the key** | `.env-encryption.key` and `*.key` are in `.gitignore` |
| **One key per environment set** | All four env files share the same Fernet key |
| **Store the key out-of-band** | AWS Secrets Manager, HashiCorp Vault, Doppler, 1Password, etc. |
| **Key rotation** | Generate a new key → re-encrypt all env files → update the secrets store → commit new `.enc` files |
| **Team onboarding** | New developer fetches the key from the secrets store, drops it at `<repo-root>/.env-encryption.key`, runs `decrypt_envs.py` |

---

## Quick reference (copy-paste one-liners)

**Encrypt a single file:**
```python
python -c "
from cryptography.fernet import Fernet; from pathlib import Path
f = Fernet(Path('.env-encryption.key').read_bytes())
Path('.env-prod.enc').write_bytes(f.encrypt(Path('.env-prod').read_bytes()))
print('done')
"
```

**Decrypt a single file:**
```python
python -c "
from cryptography.fernet import Fernet; from pathlib import Path
f = Fernet(Path('.env-encryption.key').read_bytes())
Path('.env-prod').write_bytes(f.decrypt(Path('.env-prod.enc').read_bytes()))
print('done')
"
```

**Verify a file round-trips correctly (no writes):**
```python
python -c "
from cryptography.fernet import Fernet; from pathlib import Path
f = Fernet(Path('.env-encryption.key').read_bytes())
for enc in Path('.').glob('.env-*.enc'):
    plain = f.decrypt(enc.read_bytes()).decode()
    print(f'{enc.name}: {len(plain.splitlines())} lines — OK')
"
```
