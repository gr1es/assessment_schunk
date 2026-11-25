#!/usr/bin/env python3
"""Upload or download AAS shells (.aasx) to/from the local BaSyx AAS Environment.

Usage:
  python3 aas_client.py list
  python3 aas_client.py upload <file.aasx>
  python3 aas_client.py download <out.aasx> <aas-id> [<aas-id> ...]

Only the Python standard library is used. Server URL can be changed with the
AAS_SERVER environment variable (default: http://localhost:8081).
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid

SERVER = os.environ.get("AAS_SERVER", "http://localhost:8081").rstrip("/")
AASX_MIME = "application/asset-administration-shell-package+xml"


def b64url(identifier: str) -> str:
    """AAS ids are passed base64url-encoded (without padding) in URLs."""
    return base64.urlsafe_b64encode(identifier.encode()).decode().rstrip("=")


def request(method, path, data=None, headers=None):
    req = urllib.request.Request(SERVER + path, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def list_shells():
    shells = json.loads(request("GET", "/shells"))["result"]
    for s in shells:
        print(f"{s['id']}\t{s.get('idShort', '')}")


def upload(path):
    boundary = uuid.uuid4().hex
    with open(path, "rb") as f:
        content = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\n'
        f"Content-Type: {AASX_MIME}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    request("POST", "/upload", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    print(f"Uploaded {path}")


def download(out_path, aas_ids):
    """Download the given shells, with all their submodels, as one .aasx package."""
    query = []
    for aas_id in aas_ids:
        shell = json.loads(request("GET", f"/shells/{b64url(aas_id)}"))
        query.append(("aasIds", b64url(aas_id)))
        query += [("submodelIds", b64url(ref["keys"][-1]["value"])) for ref in shell.get("submodels", [])]
    query.append(("includeConceptDescriptions", "true"))
    data = request("GET", "/serialization?" + urllib.parse.urlencode(query), headers={"Accept": AASX_MIME})
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"Downloaded {', '.join(aas_ids)} -> {out_path}")


def main(argv):
    if len(argv) == 2 and argv[1] == "list":
        list_shells()
    elif len(argv) == 3 and argv[1] == "upload":
        upload(argv[2])
    elif len(argv) >= 4 and argv[1] == "download":
        download(argv[2], argv[3:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
